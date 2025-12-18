import os
import json
import logging
import random
from datetime import datetime, timedelta
from dateutil import parser
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

# Importamos tus modelos y sesión
from db.models import AsignedClasses
from db.postgres_db import PostgresSession

# --- CONFIGURACIÓN DE LOGS ---
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

def sync_google_calendar_logic(teacher_email):
    """
    Sincronización Inteligente BD -> Google Calendar:
    - Crea eventos faltantes.
    - Elimina eventos en Google que ya no existen en BD (clases canceladas/movidas).
    - Evita duplicados mediante firmas únicas.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO SYNC: MODO ESPEJO ESTRICTO")
    logger.info("==================================================")
    
    # --- 1. CONFIGURACIÓN DE CREDENCIALES ---
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    try:
        json_creds_env = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if json_creds_env:
            creds_dict = json.loads(json_creds_env)
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        elif os.path.exists('credentials.json'):
            creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
        else:
            raise Exception("ERROR: No se encontraron credenciales válidas")

        service = build('calendar', 'v3', credentials=creds)
        logger.info("📡 Conexión con Google Calendar establecida.")
    except Exception as e:
        logger.error(f"❌ Error crítico en autenticación: {e}")
        raise e
    
    session = PostgresSession()
    header_msg = "📅 Clase gestionada por Tuprofemaria"
    
    count_created = 0
    count_deleted = 0

    try:
        # --- 2. OBTENER CLASES DE LA BASE DE DATOS (Fuente de Verdad) ---
        today_str = datetime.now().strftime("%Y-%m-%d")
        local_classes = session.query(AsignedClasses).filter(
            AsignedClasses.date_prof >= today_str,
            AsignedClasses.status.notin_(['Cancelada', 'Cancelled'])
        ).all()

        db_signatures = set()
        db_data_map = {}

        for lc in local_classes:
            full_name = f"{lc.name} {lc.surname}".strip()
            name_key = full_name.lower()
            current_date = lc.date_prof if lc.date_prof else lc.date
            
            # Formatear horas
            s_time_str = str(lc.start_prof_time).zfill(4)
            e_time_str = str(lc.end_prof_time).zfill(4)
            
            start_dt = datetime.strptime(f"{current_date} {s_time_str[:2]}:{s_time_str[2:]}", "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(f"{current_date} {e_time_str[:2]}:{e_time_str[2:]}", "%Y-%m-%d %H:%M")
            
            if lc.end_prof_time < lc.start_prof_time:
                end_dt += timedelta(days=1)

            # Firma única para comparar (Nombre + Inicio + Fin)
            sig = (name_key, start_dt.isoformat(), end_dt.isoformat())
            db_signatures.add(sig)
            db_data_map[sig] = {
                "name": full_name,
                "start": start_dt,
                "end": end_dt
            }

        # --- 3. OBTENER EVENTOS DE GOOGLE CALENDAR ---
        now_iso = datetime.utcnow().isoformat() + 'Z'
        events_result = service.events().list(
            calendarId=teacher_email, 
            timeMin=now_iso,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        google_events = events_result.get('items', [])
        google_signatures = set()

        # --- 4. FASE DE LIMPIEZA: ELIMINAR SI ESTÁ EN GOOGLE PERO NO EN BD ---
        # Solo eliminamos eventos que tengan nuestra marca (header_msg)
        for event in google_events:
            summary = event.get('summary', '').strip().lower()
            description = event.get('description', '')
            event_id = event['id']
            
            start_raw = event['start'].get('dateTime')
            end_raw = event['end'].get('dateTime')
            
            if not start_raw or not end_raw:
                continue

            # Normalizar fechas de Google para comparación
            g_start_dt = parser.parse(start_raw).replace(tzinfo=None)
            g_end_dt = parser.parse(end_raw).replace(tzinfo=None)
            g_sig = (summary, g_start_dt.isoformat(), g_end_dt.isoformat())
            
            google_signatures.add(g_sig)

            # Lógica de eliminación
            if header_msg in description:
                if g_sig not in db_signatures:
                    logger.info(f"🗑️ Eliminando de Google (no existe en BD): {event.get('summary')}")
                    service.events().delete(calendarId=teacher_email, eventId=event_id).execute()
                    count_deleted += 1

        # --- 5. FASE DE CREACIÓN: CREAR SI ESTÁ EN BD PERO NO EN GOOGLE ---
        for sig in db_signatures:
            if sig not in google_signatures:
                data = db_data_map[sig]
                logger.info(f"➕ Creando en Calendar: {data['name']}")
                
                event_body = {
                    "summary": data['name'],
                    "location": "Online - Tuprofemaria App",
                    "description": f"{header_msg}\nSincronizado desde el Panel Admin.",
                    "start": {
                        "dateTime": data['start'].isoformat(),
                        "timeZone": "America/Caracas"
                    },
                    "end": {
                        "dateTime": data['end'].isoformat(),
                        "timeZone": "America/Caracas"
                    }
                }
                
                service.events().insert(calendarId=teacher_email, body=event_body).execute()
                count_created += 1

        final_msg = f"Sync Finalizado: ➕ {count_created} creados, 🗑️ {count_deleted} eliminados."
        logger.info(final_msg)
        
        # Retorno con las llaves que espera run_sync()
        return {
            "msg": final_msg,
            "new_count": count_created,
            "updated_count": count_deleted
        }

    except Exception as e:
        session.rollback()
        logger.error(f"🔥 Error en Sync Logic: {e}", exc_info=True)
        raise e
    finally:
        session.close()