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
# Forzamos nivel INFO para que veas todo en la consola
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

load_dotenv()

def sync_google_calendar_logic(teacher_email):
    """
    Sincronización BIDIRECCIONAL con LOGS DETALLADOS.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO SINCRONIZACIÓN BIDIRECCIONAL")
    logger.info("==================================================")
    
    # --- 1. CONFIGURACIÓN DE CREDENCIALES ---
    creds = None
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    
    try:
        json_creds_env = os.getenv('GOOGLE_CREDENTIALS_JSON')
        if json_creds_env:
            creds_dict = json.loads(json_creds_env)
            creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
            logger.info("🔑 Credenciales cargadas desde variable de entorno.")
        elif os.path.exists('credentials.json'):
            creds = service_account.Credentials.from_service_account_file('credentials.json', scopes=SCOPES)
            logger.info("🔑 Credenciales cargadas desde archivo local.")
        else:
            logger.error("❌ No se encontraron credenciales.")
            raise Exception("ERROR: No se encontraron credenciales")

        service = build('calendar', 'v3', credentials=creds)
        logger.info("📡 Conexión con Google Calendar establecida.")

    except Exception as e:
        logger.error(f"❌ Error crítico en autenticación: {e}")
        raise e
    
    # Definimos AHORA en UTC
    now_utc = datetime.utcnow()
    now_iso = now_utc.isoformat() + 'Z'
    
    # --- 2. OBTENER EVENTOS DE GOOGLE (Lectura) ---
    try:
        logger.info(f"📥 Solicitando eventos a Google desde {now_iso}...")
        events_result = service.events().list(
            calendarId=teacher_email, timeMin=now_iso,
            maxResults=100, singleEvents=True,
            orderBy='startTime').execute()
    except Exception as e:
        logger.error(f"❌ Error al pedir eventos a Google: {e}")
        raise Exception(f"Error conectando al calendario: {e}")

    google_events = events_result.get('items', [])
    logger.info(f"📥 Eventos recibidos de Google: {len(google_events)}")
    
    session = PostgresSession()
    count_added_db = 0
    count_updated_google = 0
    count_uploaded_google = 0
    
    tuprofemaria_url = "https://horario-tuprofemaria.onrender.com"
    header_msg = "📅 Clase gestionada por Tuprofemaria"
    google_busy_slots = set()

    try:
        # =========================================================================
        # FASE A: GOOGLE -> BASE DE DATOS
        # =========================================================================
        logger.info("--- 🔽 FASE A: PROCESANDO DE GOOGLE HACIA BD ---")

        for event in google_events:
            summary = event.get('summary', 'Sin Nombre')
            start_raw = event['start'].get('dateTime')
            end_raw = event['end'].get('dateTime')
            event_id = event.get('id')

            # LOG: Evento básico detectado
            if not start_raw: 
                logger.info(f"  ⏭️ Saltando evento de día completo: {summary}")
                continue
            
            # Guardar slot ocupado
            try:
                dt_start_gcal = parser.parse(start_raw)
                slot_iso = dt_start_gcal.strftime("%Y-%m-%dT%H:%M:%S")
                google_busy_slots.add(slot_iso)
            except Exception as e:
                logger.error(f"  ❌ Error parseando fecha Google ({summary}): {e}")
                continue

            # Actualizar Link
            description = event.get('description', '')
            if "- Preply lesson" not in summary and tuprofemaria_url not in description:
                try:
                    new_description = f"{header_msg}\n🔗 Entra aquí: {tuprofemaria_url}\n--------------------------------\n{description}"
                    service.events().patch(
                        calendarId=teacher_email, eventId=event_id,
                        body={'description': new_description, 'location': tuprofemaria_url}
                    ).execute()
                    count_updated_google += 1
                    logger.info(f"  ✏️ Link añadido a evento Google: {summary}")
                except Exception as e:
                    logger.warning(f"  ⚠️ Fallo al actualizar link en Google: {e}")

            # Guardar en BD
            try:
                start_dt = parser.parse(start_raw)
                end_dt = parser.parse(end_raw)
                date_str = start_dt.strftime("%Y-%m-%d")

                # Helpers de formato
                def get_hhmm_int(dt_obj, round_up=False):
                    minute_val = int(dt_obj.minute)
                    if round_up and minute_val >= 45:
                        dt_obj = dt_obj + timedelta(hours=1)
                        dt_obj = dt_obj.replace(minute=0)
                    return int(dt_obj.strftime("%H%M"))

                start_int = get_hhmm_int(start_dt)
                
                # VERIFICACIÓN EN BD
                slot_occupied = session.query(AsignedClasses).filter(
                    AsignedClasses.date == date_str,
                    AsignedClasses.start_time == start_int,
                    AsignedClasses.status.notin_(['Cancelada', 'Cancelled'])
                ).first()

                if slot_occupied:
                    # logger.info(f"  ⏭️ Ya existe en BD: {summary} ({date_str} {start_int})")
                    pass # Reducimos ruido, ya sabemos que existe
                else:
                    # LOGICA DE INSERCIÓN
                    duration_minutes = float((end_dt - start_dt).total_seconds() / 60)
                    if 20 <= duration_minutes <= 40: str_duration = "30"
                    elif 45 <= duration_minutes <= 60: str_duration = "50"
                    else: str_duration = str(int(duration_minutes))
                    
                    end_int = get_hhmm_int(end_dt, round_up=True)
                    
                    parts = summary.split(' ')
                    name_val = parts[0]
                    surname_val = " ".join(parts[1:]) if len(parts) > 1 else ""
                    clean_name = "".join(c for c in name_val if c.isalnum())
                    clean_surname = "".join(c for c in surname_val if c.isalnum())
                    rand_num = random.randint(100, 999)
                    
                    new_class = AsignedClasses(
                        username=f"{clean_name}{clean_surname}{rand_num}",
                        name=name_val,
                        surname=surname_val,
                        date=date_str,
                        days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][start_dt.weekday()],
                        duration=str_duration,
                        start_time=start_int,
                        end_time=end_int,
                        start_prof_time=start_int,
                        end_prof_time=end_int,
                        date_prof=date_str,
                        package="Preply" if "Preply" in summary else "Externo",
                        status="Pendiente",
                        class_count="1/1",
                        total_classes=0
                    )
                    session.add(new_class)
                    count_added_db += 1
                    logger.info(f"  ✅ NUEVA CLASE GUARDADA EN BD: {summary} - {date_str}")
            
            except Exception as e_db:
                logger.error(f"  ❌ Error procesando datos BD para '{summary}': {e_db}")
                continue

        session.commit()
        logger.info(f"💾 BD actualizada. Commit realizado.")

        # =========================================================================
        # FASE B: BD -> GOOGLE
        # =========================================================================
        logger.info("--- 🔼 FASE B: PROCESANDO DE BD HACIA GOOGLE ---")
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        local_classes = session.query(AsignedClasses).filter(
            AsignedClasses.date >= today_str,
            AsignedClasses.status != 'Cancelada'
        ).all()
        
        logger.info(f"🔍 Clases locales futuras encontradas: {len(local_classes)}")

        for local_class in local_classes:
            full_name = f"{local_class.name} {local_class.surname}"
            
            # Construir fecha/hora para log y comparación
            time_str = str(local_class.start_time).zfill(4) 
            dt_str = f"{local_class.date}T{time_str[:2]}:{time_str[2:]}:00"
            
            # --- FILTRO 1: PREPLY ---
            if "- Preply Lesson" in full_name or local_class.package == "Preply":
                # logger.info(f"  ⛔ Omitido (Es Preply): {full_name}")
                continue 

            # --- FILTRO 2: DUPLICADO EN GOOGLE ---
            if dt_str in google_busy_slots:
                logger.info(f"  ⛔ Omitido (Ya en Google): {full_name} el {dt_str}")
                continue

            # --- ACCIÓN: SUBIR ---
            logger.info(f"  🚀 Intentando subir: {full_name} el {dt_str}")
            
            try:
                start_dt_obj = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
                dur_min = int(local_class.duration) if local_class.duration.isdigit() else 60
                end_dt_obj = start_dt_obj + timedelta(minutes=dur_min)
                
                event_body = {
                    "summary": full_name,
                    "location": "Online - TuProfemaria App",
                    "description": f"{header_msg}\nClase creada desde el Panel Admin.",
                    "start": {
                        "dateTime": start_dt_obj.isoformat(),
                        "timeZone": "Europe/Madrid"
                    },
                    "end": {
                        "dateTime": end_dt_obj.isoformat(),
                        "timeZone": "Europe/Madrid"
                    }
                }
                
                service.events().insert(calendarId=teacher_email, body=event_body).execute()
                
                # Actualizamos cache local para no re-intentar en este mismo bucle
                google_busy_slots.add(dt_str)
                count_uploaded_google += 1
                logger.info(f"  ✅ SUBIDA EXITOSA: {full_name}")

            except Exception as e_post:
                logger.error(f"  ❌ Error subiendo clase local {local_class.id} a Google: {e_post}")
                continue

        # RESUMEN FINAL
        final_msg = f"Sync Completo: ⬇️ {count_added_db} bajadas, ⬆️ {count_uploaded_google} subidas."
        logger.info("==================================================")
        logger.info(final_msg)
        logger.info("==================================================")

        return {
            "msg": final_msg,
            "new_count": count_added_db + count_uploaded_google,
            "updated_count": count_updated_google
        }

    except Exception as e:
        session.rollback()
        logger.error(f"🔥 Error CRÍTICO y FINAL en Sync: {e}", exc_info=True)
        raise e
    finally:
        session.close()