from db.database import get_connection  # Importe la fonction pour établir une connexion à la base de données

def insert_facture(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO Factures (numero, date, client, ice, cnss, [if], total_ht, tva, total_ttc)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('numero'),
        data.get('date'),
        data.get('client'),
        data.get('ice'),
        data.get('cnss'),
        data.get('if'),  # clé Python 'if'
        data.get('total_ht'),
        data.get('tva'),
        data.get('total_ttc'),
    ))

    conn.commit()
    conn.close()
