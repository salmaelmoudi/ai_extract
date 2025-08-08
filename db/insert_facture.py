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

    try:
        # parse date / float helpers ...
        invoice_number = data.get('invoice_number') or data.get('numero')
        parsed_date = (data.get('invoice_date') or data.get('date'))  # ensure it's already validated/formatted by caller
        fournisseur_id = insert_fournisseur({
            "nom": data.get('fournisseur_name') or data.get('client'),
            "ice": data.get('fournisseur_ice') or data.get('ice'),
            "if": data.get('fournisseur_if') or data.get('if'),
            "adresse": data.get('fournisseur_address') or ""
        }, conn=conn)

        cursor.execute("""
            INSERT INTO Factures (numero, date, fournisseur_id, total_ht, tva, total_ttc)
            OUTPUT INSERTED.id
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            invoice_number,
            parsed_date,
            fournisseur_id,
            safe_float(data.get('total_ht') or data.get('total_ht')),
            safe_float(data.get('vat_amount') or data.get('tva')),
            safe_float(data.get('total_ttc') or data.get('total_ttc'))
        ))
        facture_id = cursor.fetchone()[0]

        # insert products using same conn (no separate commit inside)
        produits = data.get("products", [])
        if produits:
            insert_produits(facture_id, produits, conn=conn)

        conn.commit()
        return facture_id

    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
