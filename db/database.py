import pyodbc

def get_connection():
    conn = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=localhost;"  # Change if needed
        "DATABASE=invoice;"
        "Trusted_Connection=yes;"
    )
    return conn
