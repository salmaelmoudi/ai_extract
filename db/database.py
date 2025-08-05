import pyodbc

def get_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=DESKTOP-USGNQ8J\SQLEXPRESS;"
        "DATABASE=FactureDB;"
        "Trusted_Connection=yes;"
    )
    return conn
