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

from db.fournisseur import create_fournisseur_table
from db.produit import create_produit_table

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
    create_fournisseur_table()
    create_produit_table()

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

# 🧹 Product sanity filter
def clean_products(products):
    cleaned = []
    for p in products:
        if not isinstance(p, dict):
            continue

        desc = str(p.get("designation", "")).strip()
        qty = safe_float(p.get("quantity"))
        unit_price = safe_float(p.get("unit_price"))
        total_price = safe_float(p.get("total_price"))

        # Skip if designation contains banking info or is empty
        if not desc or re.search(r"\bRIB\b|\bIBAN\b|\bcompte\b|Crédit du Maroc", desc, re.IGNORECASE):
            continue

        # Skip unrealistic quantities or prices
        if qty <= 0 or qty > 100000:
            continue
        if unit_price <= 0 or unit_price > 1_000_000:
            continue
        if total_price <= 0 or total_price > 1_000_000_000:
            continue

        cleaned.append({
            "designation": desc,
            "quantity": qty,
            "unit_price": unit_price,
            "total_price": total_price
        })
    return cleaned

# 📦 Extraction avec Azure OpenAI
def extract_entities_with_ai(text: str, excluded_entreprise: dict) -> dict:
    try:
        client_info = "\n".join([
            f"Nom: {excluded_entreprise.get('nom') or ''}",
            f"ICE: {excluded_entreprise.get('ice') or ''}",
            f"IF: {excluded_entreprise.get('if') or ''}",
            f"CNSS: {excluded_entreprise.get('cnss') or ''}",
            f"Adresse: {excluded_entreprise.get('adresse') or ''}"
        ])

        prompt = f"""
You are parsing an invoice. The following enterprise is the client (do NOT extract this one):

{client_info}

Your job is to identify and return structured data about the *other* company (the supplier), check header and footer if needed.

Please extract the following fields:
- invoice_number
- invoice_date
- fournisseur_name
- fournisseur_address
- fournisseur_ice
- fournisseur_cnss
- fournisseur_if
- total_ht
- vat_amount
- total_ttc
- currency

Also extract product details as a list of objects with:
- designation
- quantity
- unit_price
- total_price

⚠️ Do NOT include payment instructions, bank details, RIB, IBAN, contact info, or footer text as products.
"""

        completion = openai.ChatCompletion.create(
            engine=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant that extracts supplier information from invoices."},
                {"role": "user", "content": prompt.strip()},
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

        parsed = json.loads(json_str)

        # Apply product cleanup
        if "products" in parsed:
            parsed["products"] = clean_products(parsed["products"])

        return parsed

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
            "invoice_number", "invoice_date", "fournisseur_name", "fournisseur_address",
            "fournisseur_ice", "fournisseur_cnss", "fournisseur_if",
            "total_ht", "vat_amount", "total_ttc", "currency"
        ]
        missing = []
        for k in required_keys:
            val = ai_entities.get(k)
            if val is None or str(val).strip() in ["", "null"]:
                missing.append(k)

        if missing:
            print(f"⚠️ Missing keys from AI: {missing}")
            ai_entities = extract_entities_fallback(text)

        if isinstance(ai_entities, dict) and not ai_entities.get("error"):
            if not ai_entities.get("invoice_number"):
                match = re.search(r"(Facture|Invoice)[^\d]{0,5}(\d{2,}/\d{2,}|\d+)", text, re.IGNORECASE)
                if match:
                    ai_entities["invoice_number"] = match.group(2)
                    print(f"✅ Numéro de facture récupéré depuis le texte: {ai_entities['invoice_number']}")

            if not ai_entities.get("invoice_date") and not ai_entities.get("date"):
                date_match = re.search(r"(\d{2}/\d{2}/\d{4})|(\d{4}-\d{2}-\d{2})", text)
                if date_match:
                    found_date = date_match.group(0)
                    ai_entities["invoice_date"] = found_date
                    print(f"✅ Date récupérée par fallback regex: {found_date}")

            date_valide = ai_entities.get("invoice_date") or ai_entities.get("date")
            if not date_valide:
                return JSONResponse(status_code=400, content={"error": "Date manquante ou invalide dans les données extraites."})

            insert_facture({
                "numero": ai_entities.get("invoice_number") or ai_entities.get("numero"),
                "date": safe_date(date_valide),
                "fournisseur_name": ai_entities.get("fournisseur_name") or ai_entities.get("fournisseur"),
                "fournisseur_address": ai_entities.get("fournisseur_address") or ai_entities.get("adresse"),
                "fournisseur_ice": ai_entities.get("fournisseur_ice") or ai_entities.get("ice"),
                "fournisseur_cnss": ai_entities.get("fournisseur_cnss") or ai_entities.get("cnss"),
                "fournisseur_if": ai_entities.get("fournisseur_if") or ai_entities.get("if"),
                "total_ht": ai_entities.get("total_ht") or ai_entities.get("montant_ht"),
                "vat_amount": ai_entities.get("vat_amount") or ai_entities.get("tva"),
                "total_ttc": ai_entities.get("total_ttc") or ai_entities.get("montant_ttc"),
                "products": clean_products(ai_entities.get("products", []))
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
