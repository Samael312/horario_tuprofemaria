import os
from dotenv import load_dotenv

# Cargar las variables del archivo .env (solo funciona en local)
load_dotenv()

# Leer la variable
POSTGRES_URL = os.getenv("POSTGRES_URL")

# Verificación
if not POSTGRES_URL:
    raise RuntimeError("❌ ERROR: No se encontró la variable POSTGRES_URL. Asegúrate de tener el archivo .env creado o la variable configurada en Render.")
else:
    print("✅ Configuración de base de datos cargada correctamente.")