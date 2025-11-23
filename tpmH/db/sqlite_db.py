import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base

# =====================================================
# CONFIGURACIÓN DE LA BASE DE DATOS
# =====================================================

# 1. Obtener ruta absoluta del directorio actual (donde está este archivo)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. Definir ruta completa para el archivo .sqlite
# Esto asegura que se cree en /opt/render/project/src/tpmH/db/database.sqlite
DB_NAME = "database.sqlite"
DB_PATH = os.path.join(BASE_DIR, DB_NAME)

# 3. Crear URL de conexión usando la ruta absoluta
DATABASE_URL = f"sqlite:///{DB_PATH}"

# Crear el motor
# check_same_thread=False es necesario para SQLite en entornos web
sqlite_engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

# Crear tablas
Base.metadata.create_all(sqlite_engine)

# Crear sesión
SQLiteSession = sessionmaker(bind=sqlite_engine)