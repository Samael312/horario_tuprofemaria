import logging
from sqlalchemy.exc import SQLAlchemyError
from .models import User  
from .postgres_db import PostgresSession
from .sqlite_db import BackupSession

# Configurar logger para ver qué pasa en la consola
logger = logging.getLogger(__name__)

def create_user_service(user_data: dict):
    """
    1. Intenta guardar en Neon (Postgres).
    2. Si falla Neon, cancela todo (porque es la base principal).
    3. Si funciona Neon, intenta guardar una copia en SQLite local.
    """
    
    # --- FASE 1: GUARDAR EN LA NUBE (NEON) ---
    session_pg = PostgresSession()
    new_user_pg = User(**user_data) # Convierte el diccionario a objeto User
    
    try:
        session_pg.add(new_user_pg)
        session_pg.commit()
        session_pg.refresh(new_user_pg)
        logger.info(f"✅ [NUBE] Usuario '{user_data.get('username')}' guardado en Neon.")
        
    except SQLAlchemyError as e:
        session_pg.rollback()
        logger.error(f"❌ [ERROR CRÍTICO] Falló Neon: {str(e)}")
        session_pg.close()
        # Si falla la nube, lanzamos el error para que la UI avise al usuario
        raise e 
    
    finally:
        session_pg.close()

    # --- FASE 2: RESPALDO LOCAL (SQLITE) ---
    # Solo llegamos aquí si la Fase 1 fue un éxito.
    try:
        session_sqlite = BackupSession()
        # Creamos una instancia nueva porque no podemos mezclar sesiones
        new_user_sqlite = User(**user_data)
        
        session_sqlite.add(new_user_sqlite)
        session_sqlite.commit()
        logger.info(f"💾 [BACKUP] Copia guardada en SQLite local.")
        
    except Exception as e:
        # Si falla el backup, NO detenemos el programa. 
        # Lo importante es que está en la nube. Solo avisamos en consola.
        logger.warning(f"⚠️ [ADVERTENCIA] El usuario está en la nube pero falló el backup local: {e}")
    
    finally:
        session_sqlite.close()

    return True