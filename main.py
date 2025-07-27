import json
import os
import re
import shutil
import tempfile
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import openai
from sqlalchemy import create_engine

from extractor.extractor_router import extract_text_from_pdf
from db.entreprise import (
    insert_entreprise,
    get_all_entreprises,
    get_entreprise_by_id,
    create_entreprise_table
)
from db.insert_facture import insert_facture
from extractor.extractor_router import extract_entities as extract_entities_fallback
from parser.file_router import parse_file

# 🔐 Load environment variables
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 🧠 Setup Azure OpenAI client
openai.api_type = "azure"
openai.api_base = os.getenv("AZURE_OPENAI_ENDPOINT")
openai.api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai.api_version = os.getenv("AZURE_OPENAI_API_VERSION")

# 🚀 FastAPI app setup
app = FastAPI()

@app.on_event("startup")
def startup():
    create_entreprise_table()

# 🌐 CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def safe_float(val):
    try:
        if not val:
            return 0.0
        s = str(val)
        filtered = re.sub(r"[^0-9,.\-]", "", s)
        filtered = filtered.replace(",", ".")
        return float(filtered)
    except Exception as e:
        print(f"Erreur conversion float pour '{val}': {e}")
        return 0.0

def safe_date(date_str):
    if not date_str:
        return None
    date_str = str(date_str).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()
        except:
            continue
    return None

def extract_first_json(text):
    stack = []
    start_idx = None
    for i, c in enumerate(text):
        if c == '{':
            if start_idx is None:
                start_idx = i
            stack.append(c)
        elif c == '}' and stack:
            stack.pop()
            if not stack and start_idx is not None:
                return text[start_idx:i+1]
    return None

# 📦 Extraction avec Azure OpenAI
def extract_entities_with_ai(text: str, excluded_entreprise: dict) -> dict:
    try:
        exclusion_block = "\n".join([
            f"Nom: {excluded_entreprise.get('nom') or ''}",
            f"ICE: {excluded_entreprise.get('ice') or ''}",
            f"IF: {excluded_entreprise.get('if') or ''}",
            f"CNSS: {excluded_entreprise.get('cnss') or ''}",
            f"Adresse: {excluded_entreprise.get('adresse') or ''}"
        ])

        prompt = f"""
You are an AI invoice parser.

📌 IMPORTANT: The invoice you are parsing contains information about TWO companies:
- The issuer (our own company — you must ignore it)
- The client or provider (the other company — you must extract it)

🚫 DO NOT extract or return information about the following company:
{exclusion_block}

✅ Your job is to identify and return structured data for the OTHER company (the counterparty).
Look for company details in the header, footer, or body text of the invoice.

You must return a JSON object containing the following fields:
- invoice_number
- invoice_date
- client_name
- client_address
- client_ice
- client_cnss
- client_if
- total_ht
- vat_amount
- total_ttc
- currency

Return only a valid JSON object. Do not include explanations, markdown, or any formatting.
If any field is missing, return null or an empty string — do not omit it from the JSON.
        """

        completion = openai.ChatCompletion.create(
            engine=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": prompt.strip()},
                {"role": "user", "content": text}
            ],
            temperature=0.7,
            max_tokens=1024,
            top_p=1,
            stream=False
        )

        raw_reply = completion.choices[0].message.content.strip()
        json_str = extract_first_json(raw_reply)
        if not json_str:
            return {"error": "Could not find JSON object in AI reply", "raw_reply": raw_reply}
        return json.loads(json_str)

    except Exception as e:
        return {"error": "Failed to call AI model", "details": str(e)}

# 📥 Upload + extraction
@app.post("/extract")
async def extract_invoice(file: UploadFile = File(...), entreprise_id: int = Form(...)):
    suffix = file.filename.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        text = parse_file(file.filename, open(tmp_path, "rb").read())
        local_entreprise = get_entreprise_by_id(entreprise_id)

        if not local_entreprise:
            return JSONResponse(status_code=400, content={"error": "Invalid entreprise_id"})

        ai_entities = extract_entities_with_ai(text, local_entreprise)

        required_keys = [
            "invoice_number", "invoice_date", "client_name", "client_address",
            "client_ice", "client_cnss", "client_if",
            "total_ht", "vat_amount", "total_ttc", "currency"
        ]
        missing = [k for k in required_keys if ai_entities.get(k) in [None, "", "null"]] if isinstance(ai_entities, dict) else required_keys

        if missing:
            print(f"⚠️ Missing keys from AI: {missing}")
            ai_entities = extract_entities_fallback(text)

        if isinstance(ai_entities, dict) and not ai_entities.get("error"):
            if not ai_entities.get("invoice_number"):
                match = re.search(r"(Facture|Invoice)[^\d]{0,5}(\d{4,})", text, re.IGNORECASE)
                if match:
                    ai_entities["invoice_number"] = match.group(2)
                    print(f"✅ Numéro de facture récupéré depuis le texte: {ai_entities['invoice_number']}")
                else:
                    print("❌ Numéro de facture introuvable dans le texte.")

            date_valide = ai_entities.get("invoice_date") or ai_entities.get("date")
            if not date_valide:
                return JSONResponse(status_code=400, content={"error": "Date manquante ou invalide dans les données extraites."})

            insert_facture({
                "numero": ai_entities.get("invoice_number") or ai_entities.get("numero"),
                "date": date_valide,
                "client": ai_entities.get("client_name") or ai_entities.get("client"),
                "ice": ai_entities.get("client_ice") or ai_entities.get("ice"),
                "cnss": ai_entities.get("client_cnss", "") or ai_entities.get("cnss", ""),
                "if": ai_entities.get("client_if", "") or ai_entities.get("if", ""),
                "total_ht": ai_entities.get("total_ht") or ai_entities.get("montant_ht"),
                "tva": ai_entities.get("vat_amount") or ai_entities.get("tva"),
                "total_ttc": ai_entities.get("total_ttc") or ai_entities.get("montant_ttc"),
            })

        return JSONResponse(content={
            "text_preview": text[:1000],
            "entities": ai_entities
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": str(e)})

# 🌐 Static web frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")

@app.get("/entreprises")
def list_entreprises():
    return get_all_entreprises()

@app.get("/entreprise/{ent_id}")
def get_entreprise(ent_id: int):
    data = get_entreprise_by_id(ent_id)
    if not data:
        return JSONResponse(status_code=404, content={"error": "Entreprise not found"})
    return data

@app.post("/entreprises")
def add_entreprise(
    nom: str = Form(...),
    type: str = Form(None),
    ice: str = Form(None),
    if_: str = Form(None),
    cnss: str = Form(None),
    adresse: str = Form(None),
    tel: str = Form(None),
    email: str = Form(None),
    siteweb: str = Form(None)
):
    insert_entreprise({
        "nom": nom,
        "type": type,
        "ice": ice,
        "if": if_,
        "cnss": cnss,
        "adresse": adresse,
        "tel": tel,
        "email": email,
        "siteweb": siteweb
    })
    return {"status": "success"}
