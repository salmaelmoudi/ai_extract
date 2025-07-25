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

    # ✅ Conversion sûre de la date
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

    cursor.execute("""
        INSERT INTO Factures (numero, date, client, ice, cnss, [if], total_ht, tva, total_ttc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('numero'),
        parsed_date,
        data.get('client'),
        data.get('ice'),
        data.get('cnss'),
        data.get('if'),
        safe_float(data.get('total_ht')),
        safe_float(data.get('tva')),
        safe_float(data.get('total_ttc')),
    ))

    conn.commit()
    conn.close()
