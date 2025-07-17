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
from parser.file_router import parse_file
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
                        "You are an AI invoice parser. Extract the following fields:\n"
                        "- invoice_number\n- invoice_date\n- client_name\n- client_address\n"
                        "- client_ice\n- client_cnss\n- client_if\n- total_ht\n"
                        "- vat_amount\n- total_ttc\n- currency\n\n"
                        "Return ONLY a valid JSON object. No explanations, no markdown, no preambles."
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

        # 🕵️‍♀️ Try to extract JSON from any extra formatting or text
        json_match = re.search(r'\{.*\}', raw_reply, re.DOTALL)
        if not json_match:
            return {
                "error": "Could not find JSON object in AI reply",
                "raw_reply": raw_reply
            }

        json_str = json_match.group(0)
        return json.loads(json_str)

    except Exception as e:
        return {
            "error": "Failed to parse AI response",
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

        return JSONResponse(content={
            "text_preview": text[:1000],
            "entities": ai_entities
        })

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# 🌐 Static web frontend
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")
