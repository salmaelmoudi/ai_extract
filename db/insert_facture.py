from datetime import datetime
from db.database import get_connection
from db.fournisseur import insert_fournisseur
from db.produit import insert_produits

def insert_facture(data):
    conn = get_connection()
    cursor = conn.cursor()

    def safe_float(value):
        if not value:
            return None
        try:
            cleaned = str(value).replace("€", "").replace("$", "").replace(",", ".").replace(" ", "")
            return float(cleaned)
        except ValueError:
            return None

    # ✅ Parse date
    raw_date = data.get('date') or data.get('invoice_date')
    parsed_date = None
    if raw_date:
        for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d-%m-%y"):
            try:
                parsed_date = datetime.strptime(raw_date, fmt).strftime("%Y-%m-%d")
                break
            except ValueError:
                continue
    if not parsed_date:
        print(f"⚠️ Date non reconnue: {raw_date}")

    # ✅ Use shared fournisseur insert logic
    fournisseur_id = insert_fournisseur({
        "nom": data.get('fournisseur_name'),
        "ice": data.get('fournisseur_ice'),
        "if": data.get('fournisseur_if'),
        "adresse": data.get('fournisseur_address'),
        "tel": "",
        "email": "",
        "siteweb": ""
    })

    # ✅ Insert facture
    cursor.execute("""
        INSERT INTO Factures (numero, date, fournisseur_id, total_ht, tva, total_ttc)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get('invoice_number'),
        parsed_date,
        fournisseur_id,
        safe_float(data.get('total_ht')),
        safe_float(data.get('vat_amount')),
        safe_float(data.get('total_ttc')),
    ))
    facture_id = cursor.fetchone()[0]

    # ✅ Insert products
    produits = data.get("products", [])
    if produits:
        insert_produits(facture_id, produits)

    conn.commit()
    conn.close()
    return facture_id
