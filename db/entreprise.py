import pyodbc
from .database import get_connection

def create_entreprise_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Entreprise' AND xtype='U')
    CREATE TABLE Entreprise (
        id INT PRIMARY KEY IDENTITY,
        nom NVARCHAR(255),
        type NVARCHAR(100),
        ice NVARCHAR(100),
        [if] NVARCHAR(100),
        cnss NVARCHAR(100),
        adresse NVARCHAR(255),
        tel NVARCHAR(50),
        email NVARCHAR(100),
        siteweb NVARCHAR(100)
    )
    """)
    conn.commit()
    conn.close()

def insert_entreprise(data):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO Entreprise (nom, type, ice, [if], cnss, adresse, tel, email, siteweb)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nom"], data["type"], data["ice"], data["if"], data["cnss"],
        data["adresse"], data["tel"], data["email"], data["siteweb"]
    ))
    conn.commit()
    conn.close()

def get_all_entreprises():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom FROM Entreprise")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "nom": row[1]} for row in rows]

def get_entreprise_by_id(ent_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Entreprise WHERE id = ?", (ent_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0], "nom": row[1], "type": row[2], "ice": row[3], "if": row[4],
            "cnss": row[5], "adresse": row[6], "tel": row[7], "email": row[8], "siteweb": row[9]
        }
    return None
