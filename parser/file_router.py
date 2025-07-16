import io
from pathlib import Path
import pdfplumber
import pytesseract
from PIL import Image
from docx import Document
import pandas as pd

def parse_file(filename: str, content: bytes) -> str:
    ext = Path(filename).suffix.lower()

    if ext == ".pdf":
        return parse_pdf(content)
    elif ext in {".jpg", ".jpeg", ".png", ".tiff"}:
        return parse_image(content)
    elif ext in {".docx"}:
        return parse_docx(content)
    elif ext in {".xlsx", ".xls"}:
        return parse_excel(content)
    else:
        return "Unsupported file type"

def parse_pdf(content: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
            else:
                # fallback to OCR if no text
                image = page.to_image(resolution=300).original
                text += pytesseract.image_to_string(image, lang="eng+fra") + "\n"
    return text

def parse_image(content: bytes) -> str:
    image = Image.open(io.BytesIO(content))
    return pytesseract.image_to_string(image, lang="eng+fra")

def parse_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join([para.text for para in doc.paragraphs])

def parse_excel(content: bytes) -> str:
    with pd.ExcelFile(io.BytesIO(content)) as xls:
        result = []
        for sheet in xls.sheet_names:
            df = xls.parse(sheet)
            result.append(f"Sheet: {sheet}\n{df.to_string(index=False)}\n")
        return "\n".join(result)
