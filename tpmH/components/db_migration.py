import os
import logging
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# --- 1. CARGA DE ENTORNO Y LOGS ---
load_dotenv()

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# --- 2. IMPORTA TUS MODELOS ---
from db.models import (
    Base, User, SchedulePref, AsignedClasses, ScheduleProf, 
    ScheduleProfEsp, TeacherProfile, Material, HWork, 
    StudentMaterial, StudentHWork
)

# Lista de tablas a clonar (El orden importa si hay claves foráneas)
MODELS_TO_SYNC = [
    User, TeacherProfile, Material, HWork, 
    ScheduleProf, ScheduleProfEsp, SchedulePref, 
    AsignedClasses, StudentMaterial, StudentHWork
]

def backup_entire_database():
    """
    Sincronización Inteligente (Upsert):
    Actualiza existentes, inserta nuevos y elimina obsoletos.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO SMART SYNC (NEON -> SUPABASE)")
    logger.info("==================================================")

    NEON_URL = os.getenv('POSTGRES_URL')       
    SUPABASE_URL = os.getenv('SUPABASE_DB_URL') 

    if not NEON_URL or not SUPABASE_URL:
        return {"success": False, "error": "Faltan variables de entorno."}

    session_source = None
    session_dest = None
    
    try:
        # Motor Origen
        engine_source = create_engine(NEON_URL, pool_pre_ping=True)
        SessionSource = sessionmaker(bind=engine_source)
        session_source = SessionSource()

        # Motor Destino
        engine_dest = create_engine(SUPABASE_URL, pool_pre_ping=True)
        SessionDest = sessionmaker(bind=engine_dest)
        session_dest = SessionDest()
        
        logger.info("📡 Conexión establecida.")

        # Crear tablas si no existen
        Base.metadata.create_all(engine_dest)

        stats = {}

        for ModelClass in MODELS_TO_SYNC:
            table_name = ModelClass.__tablename__
            
            # 1. Obtener todos los registros del Origen
            source_data = session_source.query(ModelClass).all()
            source_ids = []

            count_updated = 0
            
            # 2. PROCESO DE MERGE (Insertar o Actualizar)
            for obj in source_data:
                # Guardamos el ID para saber luego qué borrar
                # Asumimos que tu PK se llama 'id', ajusta si es 'user_id' etc.
                if hasattr(obj, 'id'): 
                    source_ids.append(obj.id)
                
                # Desvinculamos el objeto de la sesión origen para no confundir a SQLAlchemy
                session_source.expunge(obj)
                
                # --- LA MAGIA ESTÁ AQUÍ: MERGE ---
                # merge busca por Primary Key en destino:
                # - Si existe: actualiza los campos.
                # - Si no existe: crea uno nuevo.
                session_dest.merge(obj)
                count_updated += 1
            
            # 3. PROCESO DE LIMPIEZA (Borrar lo que ya no existe en origen)
            # Si quieres un espejo exacto, descomenta el bloque siguiente.
            # Si solo quieres guardar histórico y nunca borrar del respaldo, déjalo comentado.
            
            deleted_count = 0
            if hasattr(ModelClass, 'id') and source_ids:
                 # Borrar registros en Destino cuyo ID no esté en la lista de Origen
                 delete_q = session_dest.query(ModelClass).filter(
                     ~ModelClass.id.in_(source_ids)
                 )
                 deleted_count = delete_q.delete(synchronize_session=False)
            elif hasattr(ModelClass, 'id') and not source_ids:
                 # Si origen está vacío, borrar todo en destino
                 deleted_count = session_dest.query(ModelClass).delete()

            # 4. Guardar cambios por tabla
            session_dest.commit()
            
            msg = f"✅ '{table_name}': {count_updated} procesados (Add/Upd)"
            if deleted_count > 0:
                msg += f" | 🗑️ {deleted_count} eliminados (Obsoletos)"
            
            logger.info(msg)
            stats[table_name] = {"upsert": count_updated, "deleted": deleted_count}

        final_msg = "✨ Sincronización inteligente completada."
        logger.info(final_msg)
        
        return {"success": True, "stats": stats, "msg": final_msg}

    except Exception as e:
        if session_dest:
            session_dest.rollback()
        logger.error(f"❌ Error en sync: {e}")
        return {"success": False, "error": str(e)}
        
    finally:
        if session_source: session_source.close()
        if session_dest: session_dest.close()