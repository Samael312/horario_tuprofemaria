from sqlalchemy import text # Asegúrate de importar text
from fastapi import FastAPI, Response
from db.postgres_db import PostgresSession

app = FastAPI()

@app.get('/ping_db')
def keep_db_awake():
    try:
        # Usa tu sesión de base de datos aquí
        with PostgresSession() as session:
            session.execute(text("SELECT 1"))
        return {"status": "Neon está despierto"}
    except Exception as e:
        return {"error": str(e)}