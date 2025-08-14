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
        siteweb NVARCHAR(100),
        cnss NVARCHAR(100)
    )
    """)
    conn.commit()
    conn.close()


def insert_fournisseur(data, conn=None):
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Fournisseur
        (nom, ice, [if], cnss, adresse, tel, email, siteweb)
        OUTPUT INSERTED.id
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('nom'),
        data.get('ice'),
        data.get('if'),
        data.get('cnss') or data.get('fournisseur_cnss'),
        data.get('adresse') or data.get('fournisseur_address'),
        data.get('tel', ""),
        data.get('email', ""),
        data.get('siteweb', "")
    ))
    new_id = cursor.fetchone()[0]

    if close_conn:
        conn.commit()
        conn.close()
    return new_id

def get_all_fournisseurs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nom FROM Fournisseur")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": row[0], "nom": row[1]} for row in rows]
