import pyodbc

def get_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        r"SERVER=MSI\SQLEXPRESS01;"
        "DATABASE=FactureDB;"
        "Trusted_Connection=yes;"
    )
    return conn
