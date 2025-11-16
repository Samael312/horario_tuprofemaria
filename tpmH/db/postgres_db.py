from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import POSTGRES_URL

PostgresEngine = create_engine(POSTGRES_URL, echo=False)
PostgresSession = sessionmaker(bind=PostgresEngine)

# Crear tablas en PostgreSQL si no existen
Base.metadata.create_all(PostgresEngine)
