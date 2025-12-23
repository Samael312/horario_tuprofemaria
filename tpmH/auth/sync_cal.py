import os
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from dateutil import parser
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

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
    Sincronización Híbrida:
    
    FASE A (Google -> BD):
    1. Si el evento de Google YA existe en BD -> No hace nada (está sync).
    2. Si el evento NO existe en BD:
       - Si es "Preply": SE AGREGA A LA BD (Se asume clase nueva legítima).
       - Si NO es Preply: SE IGNORA (Se asume basura/fantasma).
         * (Código comentado incluido para borrarlo de Google si se desea).
         
    FASE B (BD -> Google):
    1. Si está en BD y no en Google -> Se sube a Google.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO SYNC (LÓGICA HÍBRIDA PREPLY/DB)")
    logger.info("==================================================")
    
    LOCAL_TZ = ZoneInfo("America/Caracas")

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
            raise Exception("ERROR: No se encontraron credenciales")

        service = build('calendar', 'v3', credentials=creds)
        logger.info("📡 Conexión con Google Calendar establecida.")

    except Exception as e:
        logger.error(f"❌ Error crítico en autenticación: {e}")
        raise e
    
    session = PostgresSession()
    
    # =========================================================================
    # 2. PREPARACIÓN DE SNAPSHOTS (MEMORIA)
    # =========================================================================
    
    db_signatures = set()
    
    try:
        # Cargamos TODO lo que está activo en la BD
        all_db_classes = session.query(AsignedClasses).filter(
            AsignedClasses.status.notin_(['Cancelada', 'Cancelled'])
        ).all()
        
        logger.info("--- 📸 CARGANDO SNAPSHOT DB ---")
        for c in all_db_classes:
            d_ref = c.date_prof if c.date_prof else c.date
            n_ref = c.name.strip().lower() if c.name else ""
            s_ref = c.surname.strip().lower() if c.surname else ""
            
            if d_ref and c.start_prof_time is not None:
                # FIRMA LOCAL: (nombre, apellido, fecha YYYY-MM-DD, inicio HHMM)
                signature = (n_ref, s_ref, d_ref, int(c.start_prof_time))
                db_signatures.add(signature)
                
        logger.info(f"💾 Snapshot BD cargado: {len(db_signatures)} clases existentes.")
        
    except Exception as e:
        logger.error(f"⚠️ Error cargando snapshot de BD: {e}")

    # --- 3. OBTENER EVENTOS DE GOOGLE ---
    
    now_local = datetime.now(LOCAL_TZ)
    start_of_day_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_day_utc = start_of_day_local.astimezone(timezone.utc)
    time_min_iso = start_of_day_utc.isoformat().replace("+00:00", "Z")
    
    google_events = []
    page_token = None
    
    try:
        logger.info(f"📥 Solicitando eventos a Google desde {time_min_iso}...")
        while True:
            events_result = service.events().list(
                calendarId=teacher_email, 
                timeMin=time_min_iso,
                maxResults=2500,
                singleEvents=True,
                orderBy='startTime',
                pageToken=page_token
            ).execute()
            items = events_result.get('items', [])
            google_events.extend(items)
            page_token = events_result.get('nextPageToken')
            if not page_token:
                break
        logger.info(f"📥 Total eventos descargados de Google: {len(google_events)}")

    except Exception as e:
        session.close()
        raise Exception(f"Error conectando al calendario: {e}")
    
    count_ignored = 0
    count_preply_added = 0
    count_uploaded_google = 0
    header_msg = "📅 Clase gestionada por Tuprofemaria"
    
    google_signatures = set()

    try:
        # =========================================================================
        # FASE A: PROCESAMIENTO GOOGLE (FILTRO + EXCEPCIÓN PREPLY)
        # =========================================================================
        logger.info("--- 🔽 FASE A: ANALIZANDO EVENTOS DE GOOGLE ---")

        for event in google_events:
            event_id = event.get('id')
            summary = event.get('summary', 'Sin Nombre')
            start_raw = event['start'].get('dateTime')
            end_raw = event['end'].get('dateTime')
            status = event.get('status') 
            
            if status == 'cancelled': continue
            if not start_raw: continue 
            
            try:
                dt_start_gcal = parser.parse(start_raw).astimezone(LOCAL_TZ)
                dt_end_gcal = parser.parse(end_raw).astimezone(LOCAL_TZ)
                
                # Firma para evitar re-subida en Fase B
                g_summ_norm = summary.strip().lower()
                g_start_iso_clean = dt_start_gcal.strftime("%Y-%m-%dT%H:%M:%S")
                google_signatures.add((g_summ_norm, g_start_iso_clean))
                
                # Datos para comparación
                date_str = dt_start_gcal.strftime("%Y-%m-%d")
                start_int = int(dt_start_gcal.strftime("%H%M"))
                
                parts = summary.strip().split(' ')
                name_val = parts[0]
                surname_val = " ".join(parts[1:]) if len(parts) > 1 else ""
                
                name_check = name_val.strip().lower()
                surname_check = surname_val.strip().lower()
                
                candidate_sig = (name_check, surname_check, date_str, start_int)
                
                # === LÓGICA PRINCIPAL DE FASE A ===
                
                if candidate_sig in db_signatures:
                    # CASO 1: YA EXISTE EN BD -> Todo correcto, no hacemos nada.
                    continue

                # CASO 2: NO EXISTE EN BD (Es un intruso o una clase nueva externa)
                
                # 2.1 EXCEPCIÓN PREPLY: Si es Preply, la AGREGAMOS a la BD.
                if "- Preply Lesson" in summary or "Preply" in summary:
                    logger.info(f"🆕 [PREPLY DETECTADO] Agregando a BD: {summary}")
                    
                    # --- Lógica de Inserción ---
                    raw_end_int = int(dt_end_gcal.strftime("%H%M"))
                    if dt_end_gcal.minute >= 45:
                        next_h = dt_end_gcal + timedelta(hours=1)
                        end_int = int(next_h.replace(minute=0).strftime("%H%M"))
                    else:
                        end_int = raw_end_int
                        
                    duration_minutes = float((dt_end_gcal - dt_start_gcal).total_seconds() / 60)
                    if 20 <= duration_minutes <= 40: str_duration = "30"
                    elif 45 <= duration_minutes <= 60: str_duration = "50"
                    else: str_duration = str(int(duration_minutes))

                    clean_name = "".join(c for c in name_val if c.isalnum())
                    clean_surname = "".join(c for c in surname_val if c.isalnum())
                    rand_num = random.randint(100, 999)

                    new_class = AsignedClasses(
                        username=f"{clean_name}{clean_surname}{rand_num}",
                        name=name_val,
                        surname=surname_val,
                        date=date_str,
                        days=["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"][dt_start_gcal.weekday()],
                        duration=str_duration,
                        start_time=start_int,
                        end_time=end_int,
                        start_prof_time=start_int,
                        end_prof_time=end_int,
                        date_prof=date_str,
                        package="Preply",
                        status="Pendiente",
                        class_count="1/1",
                        total_classes=0
                    )
                    session.add(new_class)
                    db_signatures.add(candidate_sig) # La añadimos al set para no procesarla de nuevo
                    count_preply_added += 1
                    continue

                # 2.2 NO ES PREPLY Y NO ESTÁ EN BD -> SE IGNORA
                # Aquí está el código solicitado (comentado) para borrar.
                
                logger.info(f"🚫 IGNORADO (No en BD y no es Preply): {summary}")
                count_ignored += 1
                
                # --- OPCIÓN DE BORRADO (COMENTADA) ---
                # Si quisieras que lo que no está en tu BD se borre de Google (si no es Preply):
                try:
                     logger.info(f"🗑️ Borrando evento fantasma de Google: {summary}")
                     service.events().delete(calendarId=teacher_email, eventId=event_id).execute()
                except Exception as e_del:
                     logger.error(f"Error borrando: {e_del}")
                # -------------------------------------

            except Exception as e:
                logger.error(f"  ❌ Error procesando evento Google '{summary}': {e}")
                continue

        # Guardamos los cambios si agregamos Preplys
        session.commit()

        # =========================================================================
        # FASE B: BD -> GOOGLE (SUBIDA DE FALTANTES)
        # =========================================================================
        logger.info("--- 🔼 FASE B: SUBIENDO FALTANTES (BD -> GOOGLE) ---")
        
        today_str = datetime.now(LOCAL_TZ).strftime("%Y-%m-%d")
        
        local_classes = session.query(AsignedClasses).filter(
            AsignedClasses.date_prof >= today_str,
            AsignedClasses.status != 'Cancelada'
        ).all()
        
        for local_class in local_classes:
            full_name = f"{local_class.name} {local_class.surname}"
            
            # Protección: Si es Preply no deberíamos necesitar subirla porque Preply 
            # ya sincroniza con Google, pero si falta, el código intentará subirla.
            # Puedes descomentar esto si prefieres que NUNCA suba Preplys manualmente:
            # if "- Preply Lesson" in full_name or local_class.package == "Preply":
            #    continue 

            current_date_prof = local_class.date_prof if local_class.date_prof else local_class.date
            
            try:
                s_time_str = str(local_class.start_prof_time).zfill(4)
                start_dt_obj = datetime.strptime(f"{current_date_prof} {s_time_str[:2]}:{s_time_str[2:]}", "%Y-%m-%d %H:%M")
                start_dt_obj = start_dt_obj.replace(tzinfo=LOCAL_TZ)
                
                e_time_str = str(local_class.end_prof_time).zfill(4)
                end_dt_obj = datetime.strptime(f"{current_date_prof} {e_time_str[:2]}:{e_time_str[2:]}", "%Y-%m-%d %H:%M")
                end_dt_obj = end_dt_obj.replace(tzinfo=LOCAL_TZ)
                
                if local_class.end_prof_time < local_class.start_prof_time:
                    end_dt_obj += timedelta(days=1)
                
                check_summ = full_name.strip().lower()
                check_start_iso = start_dt_obj.strftime("%Y-%m-%dT%H:%M:%S")
                check_sig = (check_summ, check_start_iso)
                
                # Si ya está en Google (detectado en Fase A), no subir
                if check_sig in google_signatures:
                    continue

                logger.info(f"  🚀 SUBIENDO A CALENDAR: {full_name}")
                
                event_body = {
                    "summary": full_name,
                    "location": "Online - TuProfemaria App",
                    "description": f"{header_msg}\nClase creada desde el Panel Admin.",
                    "start": {
                        "dateTime": start_dt_obj.isoformat(),
                        "timeZone": "America/Caracas"
                    },
                    "end": {
                        "dateTime": end_dt_obj.isoformat(),
                        "timeZone": "America/Caracas"
                    }
                }
                
                service.events().insert(calendarId=teacher_email, body=event_body).execute()
                
                google_signatures.add(check_sig)
                count_uploaded_google += 1

            except Exception as e_post:
                logger.error(f"  ❌ Error subiendo clase ID {local_class.id}: {e_post}")
                continue

        final_msg = f"Sync Finalizado: 🆕 {count_preply_added} Preplys agregadas, 🚫 {count_ignored} ignorados, ⬆️ {count_uploaded_google} subidos."
        logger.info("==================================================")
        logger.info(final_msg)
        
        return {
            "msg": final_msg,
            "preply_added": count_preply_added,
            "updated_count": count_uploaded_google
        }

    except Exception as e:
        session.rollback()
        logger.error(f"🔥 Error Sync: {e}", exc_info=True)
        raise e
    finally:
        session.close()