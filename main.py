import os
import json
import re
import shutil
import tempfile
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.insert_facture import insert_facture
from parser.file_router import parse_file
from extractor.extractor_router import extract_entities as extract_entities_fallback
from sqlalchemy import create_engine
from db.entreprise import (
    insert_entreprise,
    get_all_entreprises,
    get_entreprise_by_id,
    create_entreprise_table
)

# 🔐 Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 🧠 Setup Groq client
client = Groq(api_key=GROQ_API_KEY)

# 🚀 FastAPI app setup
app = FastAPI()

# 🚦 Create Entreprise table on startup
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

# 📦 AI entity extraction function with entreprise exclusion

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

        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
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
        json_match = re.search(r'\{.*?\}', raw_reply, re.DOTALL)

        if not json_match:
            return {"error": "Could not find JSON object in AI reply", "raw_reply": raw_reply}

        json_str = json_match.group(0)

        try:
            return json.loads(json_str)
        except Exception as e:
            return {"error": "Failed to parse AI response", "details": str(e), "raw_json": json_str}

    except Exception as e:
        return {"error": "Failed to call AI model", "details": str(e)}

# 📥 File upload + extraction endpoint with entreprise selection
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
            insert_facture({
                "numero": ai_entities.get("invoice_number") or ai_entities.get("numero"),
                "date": ai_entities.get("invoice_date") or ai_entities.get("date"),
                "client": ai_entities.get("client_name") or ai_entities.get("client"),
                "ice": ai_entities.get("client_ice") or ai_entities.get("ice"),
                "cnss": ai_entities.get("client_cnss") or ai_entities.get("cnss"),
                "if": ai_entities.get("client_if") or ai_entities.get("if"),
                "total_ht": ai_entities.get("total_ht"),
                "tva": ai_entities.get("vat_amount") or ai_entities.get("tva"),
                "total_ttc": ai_entities.get("total_ttc"),
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

# 🏢 Entreprise API endpoints
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
