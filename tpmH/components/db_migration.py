import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, make_transient

# --- 1. CARGA DE ENTORNO Y LOGS ---
load_dotenv() # <--- ESTO ES CRUCIAL PARA LEER EL .ENV

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- 2. IMPORTA TUS MODELOS ---
# Asegúrate de que la ruta 'db.models' sea correcta según tu estructura de carpetas
from db.models import (
    Base, User, SchedulePref, AsignedClasses, ScheduleProf, 
    ScheduleProfEsp, TeacherProfile, Material, HWork, 
    StudentMaterial, StudentHWork
)

# Lista de tablas a clonar
MODELS_TO_SYNC = [
    User, TeacherProfile, Material, HWork, 
    ScheduleProf, ScheduleProfEsp, SchedulePref, 
    AsignedClasses, StudentMaterial, StudentHWork
]

def backup_entire_database():
    """
    Copia masiva de NEON (Postgres) a SUPABASE.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO RESPALDO DE BASE DE DATOS (NEON -> SUPABASE)")
    logger.info("==================================================")

    # --- 3. OBTENER VARIABLES ---
    # Usamos los nombres exactos que tienes en tu .env
    NEON_URL = os.getenv('POSTGRES_URL')       
    SUPABASE_URL = os.getenv('SUPABASE_DB_URL') 

    # Diagnóstico de error específico
    if not NEON_URL:
        return {"success": False, "error": "Falta POSTGRES_URL en .env"}
    if not SUPABASE_URL:
        return {"success": False, "error": "Falta SUPABASE_DB_URL en .env"}

    # --- 4. CONFIGURAR MOTORES ---
    session_source = None
    session_dest = None
    
    try:
        # Motor Origen (Neon)
        engine_source = create_engine(NEON_URL, pool_pre_ping=True)
        SessionSource = sessionmaker(bind=engine_source)
        session_source = SessionSource()

        # Motor Destino (Supabase)
        engine_dest = create_engine(SUPABASE_URL, pool_pre_ping=True)
        SessionDest = sessionmaker(bind=engine_dest)
        session_dest = SessionDest()
        
        logger.info("📡 Conexión establecida con ambas bases de datos.")

        # --- 5. LÓGICA DE COPIA ---
        stats = {}
        
        # Crear tablas en destino si no existen
        Base.metadata.create_all(engine_dest)

        for ModelClass in MODELS_TO_SYNC:
            table_name = ModelClass.__tablename__
            
            # A. Leer de Neon
            source_data = session_source.query(ModelClass).all()
            count = len(source_data)
            
            if count == 0:
                # logger.info(f"   ⏩ Tabla '{table_name}' vacía. Saltando.")
                continue

            # B. Limpiar Supabase (Borrado total de la tabla)
            session_dest.query(ModelClass).delete()
            
            # C. Copiar Datos (Desvincular -> Vincular)
            for obj in source_data:
                session_source.expunge(obj) # Desconectar de sesión A
                make_transient(obj)         # Hacerlo "nuevo"
                session_dest.add(obj)       # Conectar a sesión B

            # D. Guardar cambios
            session_dest.commit()
            logger.info(f"   ✅ Tabla '{table_name}': {count} registros copiados.")
            stats[table_name] = count

        final_msg = "✨ Respaldo completado exitosamente."
        logger.info(final_msg)
        
        return {"success": True, "stats": stats, "msg": final_msg}

    except Exception as e:
        if session_dest:
            session_dest.rollback()
        logger.error(f"❌ Error crítico en respaldo: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        if session_source: session_source.close()
        if session_dest: session_dest.close()