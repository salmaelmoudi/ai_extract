import re
import pytesseract
from datetime import datetime

# ✅ Adjust path if Tesseract isn't in your environment PATH
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

def extract_entities(text: str) -> dict:
    print("🧠 Fallback extractor active. Extracting entities from text...\n")

    vat_value = extract_vat(text)
    data = {
        "invoice_number": extract_invoice_number(text),
        "invoice_date": extract_date(text),
        "fournisseur_name": extract_fournisseur_name(text),
        "fournisseur_address": extract_fournisseur_address(text),
        "fournisseur_ice": extract_ice(text),
        "fournisseur_cnss": extract_cnss(text),
        "fournisseur_if": extract_if(text),
        "total_ht": extract_total_ht(text),
        "vat_amount": vat_value,
        "total_ttc": extract_total_ttc(text),
        "currency": extract_currency(text),
        "products": extract_products(text),
    }

    # 🔍 Debug print all extracted values
    print("🔍 Extracted Fields:")
    for k, v in data.items():
        print(f"{k}: {repr(v)}")

    return data

def normalize_float(val):
    try:
        return float(str(val).replace(",", ".").replace(" ", ""))
    except:
        return None

def extract_invoice_number(text):
    # Flexible match: long format or just a number near "facture"
    match = re.search(r"(?:Facture|Invoice)[^\d]{0,5}(\d{3,10})", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    match = re.search(r"\bFC-\d{2}-\d{4}[A-Z]*-\d{3}-\d{2}-\d{2}\b", text)
    return match.group(0) if match else None

def extract_date(text):
    match = re.search(r"\d{2}-\d{2}-\d{2}", text)
    if match:
        try:
            return datetime.strptime(match.group(0), "%d-%m-%y").strftime("%Y-%m-%d")
        except:
            return match.group(0)
    return None

def extract_fournisseur_name(text):
    match = re.search(r"Paiements à exécuter.*?:\s*(.+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Fallback: look for supplier phrases
    match = re.search(r"\b(INGRAM MICRO|SOCIÉTÉ.*?AU CAPITAL|Société.*?SARL)\b.*", text, re.IGNORECASE)
    return match.group(0).strip() if match else None

def extract_fournisseur_address(text):
    match = re.search(r"(Lot\s+\d+.*?(Casablanca|Rabat|Maroc).+)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback to anything after fournisseur name
    match = re.search(r"(Siège\s+Social.*?)\n", text, re.IGNORECASE)
    return match.group(1).strip() if match else None

def extract_ice(text):
    match = re.search(r"ICE[:\s]+(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_cnss(text):
    match = re.search(r"CNSS[:\s]+(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_if(text):
    match = re.search(r"\bIF[:\s]+(\d+)", text, re.IGNORECASE)
    return match.group(1) if match else None

def extract_total_ht(text):
    match = re.search(r"MONTANT HT[:\s]+([\d\.,]+)", text, re.IGNORECASE)
    return normalize_float(match.group(1)) if match else None

def extract_vat(text):
    match = re.search(r"(VAT|TVA)[\s:]*[\d\.%]*[\s:]*([\d\.,]+)", text, re.IGNORECASE)
    return normalize_float(match.group(2)) if match else None

def extract_total_ttc(text):
    match = re.search(r"MONTANT TTC.*?([\d\.,]+)", text, re.IGNORECASE | re.DOTALL)
    return normalize_float(match.group(1)) if match else None

def extract_currency(text):
    match = re.search(r"\b(MAD|EUR|USD)\b", text)
    return match.group(0) if match else "MAD"

def extract_products(text):
    products = []
    lines = text.split("\n")

    for line in lines:
        # Remove extra spaces, normalize line
        line = line.strip()

        # Match: description followed by qty, unit price, total price
        match = re.match(r"(.+?)\s+(\d{1,3})\s+([\d\.,]+)\s+([\d\.,]+)$", line)
        if match:
            designation = match.group(1).strip()
            quantity = normalize_float(match.group(2))
            unit_price = normalize_float(match.group(3))
            total_price = normalize_float(match.group(4))

            # Only add if all values are valid
            if designation and quantity and unit_price and total_price:
                products.append({
                    "designation": designation,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })

    return products


def extract_text_from_pdf(content: bytes) -> str:
    from pdf2image import convert_from_bytes
    from PIL import Image
    poppler_path = r"C:\poppler\Library\bin"

    images = convert_from_bytes(content, poppler_path=poppler_path)
    texte_complet = ""
    for image in images:
        texte = pytesseract.image_to_string(image, lang='fra')
        texte_complet += texte + "\n"
    return texte_complet
