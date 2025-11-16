import os

# SQLite local
SQLITE_URL = "sqlite:///db/usuarios.db"

# PostgreSQL remoto (Render)
POSTGRES_URL = os.getenv("DATABASE_URL")
if POSTGRES_URL is None:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida")