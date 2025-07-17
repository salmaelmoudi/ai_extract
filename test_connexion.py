from db.database import get_connection

try:
    conn = get_connection()
    print("✅ Connexion réussie à la base de données !")
    conn.close()
except Exception as e:
    print("❌ Erreur de connexion :", e)
