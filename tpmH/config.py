import os

# SQLite local
SQLITE_URL = "sqlite:///db/usuarios.db"

# PostgreSQL remoto (Render)
POSTGRES_URL = "postgresql://horarios_tuprofemaria_user:ebfUqBNuWWErqEv4vjXG579zztz5RnYC@dpg-d4ct3ii4d50c73ddgkvg-a.oregon-postgres.render.com/horarios_tuprofemaria"
if POSTGRES_URL is None:
    raise RuntimeError("La variable de entorno DATABASE_URL no está definida")