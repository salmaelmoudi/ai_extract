from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import shutil
import os
import requests
from parser.file_router import parse_file

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to extract entities using Groq AI
def extract_entities_with_ai(text: str) -> dict:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = f"""
You are an AI invoice parser. Extract the following fields from the given invoice text:
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

Return a JSON object. Here is the invoice text:

{text}
"""

    body = {
        "model": "mixtral-8x7b-32768",
        "messages": [
            {"role": "system", "content": "You extract invoice fields from raw text."},
            {"role": "user", "content": prompt}
        ]
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=body,
        timeout=30
    )

    try:
        result = response.json()["choices"][0]["message"]["content"]
        return eval(result) if isinstance(result, str) else result
    except Exception as e:
        return {"error": "Failed to parse AI response", "details": str(e)}

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



from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def home():
    return FileResponse("static/index.html")
