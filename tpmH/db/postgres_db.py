from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import POSTGRES_URL

# AGREGADO: pool_pre_ping=True verifica que la conexión esté viva antes de usarla.
# Es obligatorio para bases de datos en la nube como Neon.
PostgresEngine = create_engine(POSTGRES_URL, echo=False, pool_pre_ping=True)

# Esta será tu sesión PRINCIPAL para leer y escribir
PostgresSession = sessionmaker(bind=PostgresEngine)

# Crear tablas en PostgreSQL si no existen
Base.metadata.create_all(PostgresEngine)