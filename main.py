import os 
import json
import re
import shutil
import tempfile
from dotenv import load_dotenv
from groq import Groq
from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db.insert_facture import insert_facture
from parser.file_router import parse_file
from extractor.extractor_router import extract_entities as extract_entities_fallback  # <-- added
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# 🔐 Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

# 🧠 Setup Groq client
client = Groq(api_key=GROQ_API_KEY)

# 🚀 FastAPI app setup
app = FastAPI()

# 🌐 CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📦 Extract AI entities from invoice text using Groq
def extract_entities_with_ai(text: str) -> dict:
    try:
        completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an AI invoice parser. Extract the following fields EXACTLY as listed:\n"
                        "- invoice_number\n- invoice_date\n- client_name\n- client_address\n"
                        "- client_ice\n- client_cnss (social security number)\n- client_if (tax ID)\n"
                        "- total_ht\n- vat_amount\n- total_ttc\n- currency\n\n"
                        "Return ONLY a valid JSON object with those keys. Do NOT return null if the field is present in the text."
                    )
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            temperature=1,
            max_tokens=1024,
            top_p=1,
            stream=False
        )

        raw_reply = completion.choices[0].message.content.strip()

        # 🕵️ Try to extract only the first valid JSON object
        json_match = re.search(r'\{.*?\}', raw_reply, re.DOTALL)
        if not json_match:
            return {
                "error": "Could not find JSON object in AI reply",
                "raw_reply": raw_reply
            }

        json_str = json_match.group(0)

        try:
            return json.loads(json_str)
        except Exception as e:
            return {
                "error": "Failed to parse AI response",
                "details": str(e),
                "raw_json": json_str
            }

    except Exception as e:
        return {
            "error": "Failed to call AI model",
            "details": str(e)
        }

# 📥 File upload + extraction endpoint
@app.post("/extract")
async def extract_invoice(file: UploadFile = File(...)):
    suffix = file.filename.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{suffix}") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        text = parse_file(file.filename, open(tmp_path, "rb").read())
        ai_entities = extract_entities_with_ai(text)

        # Define required fields for completeness check
        required_keys = [
            "invoice_number", "invoice_date", "client_name", "client_address",
            "client_ice", "client_cnss", "client_if",
            "total_ht", "vat_amount", "total_ttc", "currency"
        ]

        # Check if any key is missing or blank/null
        missing = [k for k in required_keys if ai_entities.get(k) in [None, "", "null"]] if isinstance(ai_entities, dict) else required_keys
        if missing:
            print(f"⚠️ Missing keys from AI: {missing}")
            ai_entities = extract_entities_fallback(text)

        # Only insert if it's a dict and no top-level error
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
