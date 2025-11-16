from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base
from config import SQLITE_URL

sqlite_engine = create_engine(SQLITE_URL, echo=False)
SQLiteSession = sessionmaker(bind=sqlite_engine)

# Crear tablas SQLite si no existen
Base.metadata.create_all(sqlite_engine)
