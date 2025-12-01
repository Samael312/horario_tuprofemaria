import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base # Asegúrate que la importación apunte a tus modelos

# =====================================================
# CONFIGURACIÓN DE LA BASE DE DATOS (RESPALDO)
# =====================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Nombre del archivo de respaldo
DB_NAME = "backup_local.sqlite" # Le cambié el nombre para identificarlo mejor
DB_PATH = os.path.join(BASE_DIR, DB_NAME)

DATABASE_URL = f"sqlite:///{DB_PATH}"

sqlite_engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Crear tablas en el archivo local
Base.metadata.create_all(sqlite_engine)

# RENOMBRADO: Ahora se llama BackupSession para distinguirla
BackupSession = sessionmaker(bind=sqlite_engine)