import pyodbc  # Import du module permettant la connexion à une base de données via ODBC

def get_connection():
    # Établit une connexion à une base de données SQL Server via ODBC
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"  # Utilisation du driver ODBC pour SQL Server
        "SERVER=MSI\\SQLEXPRESS01;"  # Adresse du serveur SQL (double antislash requis)
        "DATABASE=FactureDB;"  # Nom de la base de données cible
        "Trusted_Connection=yes;"  # Utilise l'authentification Windows
    )
    return conn  # Retourne l'objet connexion
