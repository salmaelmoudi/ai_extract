import pyodbc
from .database import get_connection

def create_fournisseur_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Fournisseur' AND xtype='U')
    CREATE TABLE Fournisseur (
        id INT PRIMARY KEY IDENTITY,
        nom NVARCHAR(255),
        ice NVARCHAR(100),
        [if] NVARCHAR(100),
        adresse NVARCHAR(255),
        tel NVARCHAR(50),
        email NVARCHAR(100),
        siteweb NVARCHAR(100)
    )
    """)
    conn.commit()
    conn.close()

def insert_fournisseur(data):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Fournisseur WHERE nom = ? AND ice = ?", (data["nom"], data["ice"]))
    row = cursor.fetchone()
    if row:
        conn.close()
        return row[0]

    cursor.execute("""
    INSERT INTO Fournisseur (nom, ice, [if], adresse, tel, email, siteweb)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["nom"], data["ice"], data["if"], data["adresse"],
        data["tel"], data["email"], data["siteweb"]
    ))
    cursor.execute("SELECT SCOPE_IDENTITY()")
    inserted_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return inserted_id

def get_all_fournisseurs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom FROM Fournisseur")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "nom": row[1]} for row in rows]
