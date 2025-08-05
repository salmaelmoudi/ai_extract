import pyodbc
from .database import get_connection

def create_produit_table():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Produit' AND xtype='U')
    CREATE TABLE Produit (
        id INT PRIMARY KEY IDENTITY,
        factures_id INT FOREIGN KEY REFERENCES Factures(id),
        nom NVARCHAR(255),
        quantite INT,
        prix_unitaire FLOAT,
        total FLOAT
    )
    """)
    conn.commit()
    conn.close()

def insert_produits(factures_id, produits):
    conn = get_connection()
    cursor = conn.cursor()
    for p in produits:
        cursor.execute("""
        INSERT INTO Produit (factures_id, nom, quantite, prix_unitaire, total)
        VALUES (?, ?, ?, ?, ?)
        """, (
            factures_id,
            p.get("name") or p.get("nom"),
            int(p.get("quantity", 0)),
            float(p.get("unit_price", 0)),
            float(p.get("total", 0))
        ))
    conn.commit()
    conn.close()
