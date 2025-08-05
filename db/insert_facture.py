from datetime import datetime
from db.database import get_connection

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

    # 🔄 Parse date
    raw_date = data.get('date')
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

    # 🔎 Search or insert supplier
    fournisseur_id = None
    cursor.execute("""
        SELECT id FROM Fournisseur WHERE nom = ? AND ice = ?
    """, (data.get('client'), data.get('ice')))
    row = cursor.fetchone()

    if row:
        fournisseur_id = row[0]
    else:
        cursor.execute("""
            INSERT INTO Fournisseur (nom, adresse, ice, cnss, [if])
            VALUES (?, ?, ?, ?, ?)
        """, (
            data.get('client'),
            data.get('adresse', ''),
            data.get('ice'),
            data.get('cnss'),
            data.get('if'),
        ))
        # Fetch the ID using SCOPE_IDENTITY for SQL Server
        cursor.execute("SELECT SCOPE_IDENTITY()")
        fournisseur_id = cursor.fetchone()[0]

    # 🧾 Insert invoice
    cursor.execute("""
        INSERT INTO Factures (numero, date, fournisseur_id, total_ht, tva, total_ttc)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        data.get('numero'),
        parsed_date,
        fournisseur_id,
        safe_float(data.get('total_ht')),
        safe_float(data.get('tva')),
        safe_float(data.get('total_ttc')),
    ))
    facture_id = cursor.fetchone()[0]

    conn.commit()
    conn.close()
    return facture_id
