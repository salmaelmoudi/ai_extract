from datetime import datetime
from db.database import get_connection
def insert_facture(data):
    conn = get_connection()
    cursor = conn.cursor()

    from datetime import datetime

    def safe_float(value):
        if not value:
            return None
        try:
            cleaned = str(value).replace("€", "").replace("$", "").replace(",", ".").replace(" ", "")
            return float(cleaned)
        except ValueError:
            return None

    try:
        parsed_date = datetime.strptime(data.get('date'), "%d/%m/%Y").strftime("%Y-%m-%d")
    except ValueError:
        try:
            parsed_date = datetime.strptime(data.get('date'), "%Y-%m-%d").strftime("%Y-%m-%d")
        except ValueError:
            parsed_date = None

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
