import re
import pytesseract
from datetime import datetime


# Chemin vers Tesseract installé (adapter si besoin)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Fonction principale : extraire toutes les entités d'une facture
def extract_entities(text: str) -> dict:
    vat_value = extract_vat(text)
    return {
        "invoice_number": extract_invoice_number(text),
        "date": extract_date(text),
        "client": extract_client(text),
        "ice": extract_ice(text),
        "cnss": extract_cnss(text),
        "if": extract_if(text),
        "total_ht": extract_total_ht(text),
        "tva": vat_value,
        "vat_amount": vat_value,
        "total_ttc": extract_total_ttc(text),
        "products": extract_products(text)
    }

# Utilitaires
def normalize_float(val):
    try:
        return float(val.replace(",", "."))
    except:
        return None

# Fonctions d'extraction via regex
#def extract_invoice_number(text):
 #   match = re.search(r"(?:FC|Facture)[-:\s]*\d{2,4}[-A-Z]*[-\d]{2,}", text)
  #  return match.group(0).strip() if match else None
def extract_invoice_number(text):
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

def extract_client(text):
    match = re.search(r"Facturer à:.*?\n([A-Za-z].+?)\n", text)
    if match:
        return match.group(1).strip()
    match = re.search(r"\n(Teknologiate)\n", text)
    return match.group(1) if match else "Teknologiate"


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
    match = re.search(r"MONTANT HT[:\s]+([\d\.,]+)", text, re.IGNORECASE)
    return normalize_float(match.group(1)) if match else None

def extract_vat(text):
    match = re.search(r"(VAT|TVA)[\s:]*[\d\.%]*[\s:]*([\d\.,]+)", text, re.IGNORECASE)
    return normalize_float(match.group(2)) if match else None

def extract_total_ttc(text):
    match = re.search(r"MONTANT TTC.*?([\d\.,]+)", text, re.IGNORECASE | re.DOTALL)
    return normalize_float(match.group(1)) if match else None

def extract_products(text):
    products = []
    lines = text.split("\n")
    product_section = False

    for line in lines:
        # Détection du début de la section des produits
        if re.search(r"(Désignation|Produit|Article)", line, re.IGNORECASE):
            product_section = True
            continue

        if product_section:
            # Exemple ligne: "Stylo bleu    10    2.50    25.00"
            match = re.match(r"(.+?)\s{2,}([\d]+)\s+([\d\.,]+)\s+([\d\.,]+)", line)
            if match:
                designation = match.group(1).strip()
                quantity = normalize_float(match.group(2))
                unit_price = normalize_float(match.group(3))
                total_price = normalize_float(match.group(4))
                products.append({
                    "designation": designation,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price
                })

            if re.search(r"(Total TTC|MONTANT TTC|TOTAL)", line, re.IGNORECASE):
                break

    return products

# Fonction OCR : extrait le texte à partir d’un PDF scanné
def extract_text_from_pdf(content: bytes) -> str:
    from pdf2image import convert_from_bytes
    from PIL import Image

    # Remplace par le chemin vers Poppler (comme avant)
    poppler_path = r"C:\poppler\Library\bin"

    images = convert_from_bytes(content, poppler_path=poppler_path)
    texte_complet = ""

    for image in images:
        texte = pytesseract.image_to_string(image, lang='fra')
        texte_complet += texte + "\n"

    return texte_complet
