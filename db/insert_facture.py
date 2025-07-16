from db.database import get_connection

def insert_facture(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Factures (numero, date, client, ice, cnss, if, total_ht, tva, total_ttc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data['numero'],
        data['date'],
        data['client'],
        data['ice'],
        data['cnss'],
        data['if'],
        data['total_ht'],
        data['tva'],
        data['total_ttc']
    ))

    conn.commit()
    conn.close()