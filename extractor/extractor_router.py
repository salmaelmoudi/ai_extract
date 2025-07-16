import re
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

# Chemin vers Tesseract installé (adapter si besoin)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Fonction principale : extraire toutes les entités d'une facture
def extract_entities(text: str) -> dict:
    return {
        "invoice_number": extract_invoice_number(text),
        "date": extract_date(text),
        "client": extract_client(text),
        "ice": extract_ice(text),
        "cnss": extract_cnss(text),
        "if": extract_if(text),
        "total_ht": extract_total_ht(text),
        "vat": extract_vat(text),
        "total_ttc": extract_total_ttc(text),
    }

# Fonctions d'extraction via regex
def extract_invoice_number(text):
    match = re.search(r"FC-\d{2}-\d{4}[A-Z]*-\d{3}-\d{2}-\d{2}", text)
    return match.group(0) if match else None

def extract_date(text):
    match = re.search(r"\d{2}-\d{2}-\d{2}", text)
    return match.group(0) if match else None

def extract_client(text):
    match = re.search(r"Facturer à:\s+(.*?)\n", text)
    return match.group(1).strip() if match else "Teknologiate"  # fallback

def extract_ice(text):
    match = re.search(r"ICE[:\s]+(\d+)", text)
    return match.group(1) if match else None

def extract_cnss(text):
    match = re.search(r"CNSS[:\s]+(\d+)", text)
    return match.group(1) if match else None

def extract_if(text):
    match = re.search(r"IF[:\s]+(\d+)", text)
    return match.group(1) if match else None

def extract_total_ht(text):
    match = re.search(r"MONTANT HT\s+([\d\.,]+)", text)
    return match.group(1).replace(",", ".") if match else None

def extract_vat(text):
    match = re.search(r"VAT\s+[\d\.%]+\s+([\d\.,]+)", text)
    return match.group(1).replace(",", ".") if match else None

def extract_total_ttc(text):
    match = re.search(r"MONTANT TTC.*?([\d\.,]+)", text, re.DOTALL)
    return match.group(1).replace(",", ".") if match else None

# Fonction OCR : extrait le texte à partir d’un PDF scanné
def extract_text_from_pdf(content: bytes) -> str:
    from pdf2image import convert_from_bytes
    from PIL import Image

    # Remplace par le chemin vers Poppler (comme avant)
    poppler_path = r"C:\poppler\Library\bin"

    # Convertit le contenu PDF (bytes) en images
    images = convert_from_bytes(content, poppler_path=poppler_path)

    texte_complet = ""
    for image in images:
        texte = pytesseract.image_to_string(image, lang='fra')  # OCR en français
        texte_complet += texte + "\n"

    return texte_complet

