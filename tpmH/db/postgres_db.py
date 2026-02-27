from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import POSTGRES_URL

# CONFIGURACIÓN OPTIMIZADA PARA NEON / CLOUD DB
# 1. pool_pre_ping: Verifica si la conexión sigue viva
# 2. pool_size y max_overflow: Mantiene un "pool" de conexiones listas para usar
# 3. pool_recycle: Renueva las conexiones cada 30 minutos (1800s) para que Neon no las corte
# 4. connect_args: ¡EL SALVAVIDAS! Fuerza un timeout de 3 segundos para evitar el cuelgue de 25s de IPv6

PostgresEngine = create_engine(
    POSTGRES_URL, 
    echo=False, 
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    pool_recycle=1800,
    connect_args={
        "connect_timeout": 3,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5
    }
)

# Esta será tu sesión PRINCIPAL para leer y escribir
PostgresSession = sessionmaker(bind=PostgresEngine)

# Crear tablas en PostgreSQL si no existen
Base.metadata.create_all(PostgresEngine)