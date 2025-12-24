import os
import json
import logging
import random
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo  # IMPORTANTE: Para normalizar zonas
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
    Sincronización con LOGS DETALLADOS para depuración.
    Normaliza todo a 'America/Caracas' antes de comparar.
    """
    logger.info("==================================================")
    logger.info("🚀 INICIANDO SYNC CON MODO DEBUG DETALLADO")
    logger.info("==================================================")
    
    # Define la zona horaria base de tu aplicación
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
    
    # A. Snapshot de BD
    # Guardamos: (nombre_normalizado, apellido_normalizado, fecha_str, hora_inicio_int)
    # Nota: Quitamos el end_time de la firma estricta por ahora para evitar duplicados por errores de duración
    db_signatures = set()
    
    try:
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
                # DEBUG OCASIONAL (Descomentar si necesitas ver todo lo que hay en BD)
                logger.info(f"[DB LOAD] {signature}")
                
        logger.info(f"💾 Snapshot BD cargado: {len(db_signatures)} firmas únicas.")
        
    except Exception as e:
        logger.error(f"⚠️ Error cargando snapshot de BD: {e}")

    # --- 3. OBTENER EVENTOS DE GOOGLE ---
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat().replace("+00:00", "Z")
    
    google_events = []
    page_token = None
    
    try:
        logger.info(f"📥 Solicitando eventos a Google desde {now_iso}...")
        while True:
            events_result = service.events().list(
                calendarId=teacher_email, 
                timeMin=now_iso,
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
    
    count_added_db = 0
    count_uploaded_google = 0
    header_msg = "📅 Clase gestionada por Tuprofemaria"
    
    # Snapshot de firmas de Google para evitar resubida
    # (summary_lower, start_iso_local_str)
    google_signatures = set()

    try:
        # =========================================================================
        # FASE A: GOOGLE -> BASE DE DATOS
        # =========================================================================
        logger.info("--- 🔽 FASE A: PROCESANDO DESCARGAS (GOOGLE -> BD) ---")

        for event in google_events:
            summary = event.get('summary', 'Sin Nombre')
            start_raw = event['start'].get('dateTime')
            end_raw = event['end'].get('dateTime')
            
            if not start_raw: continue 
            
            try:
                # 1. Parsear y NORMALIZAR a Timezone LOCAL (Caracas)
                dt_start_gcal = parser.parse(start_raw).astimezone(LOCAL_TZ)
                dt_end_gcal = parser.parse(end_raw).astimezone(LOCAL_TZ)
                
                # --- LOG DE DIAGNÓSTICO ---
                # Ver qué hora cree Python que es vs qué mandó Google
                logger.info(f"[DEBUG TIME] Raw: {start_raw} -> Local: {dt_start_gcal}")

                # 2. Preparar Firma para evitar Re-Subida (Fase B)
                # Guardamos la fecha/hora en formato ISO limpio sin offset para comparación estricta de string
                g_summ_norm = summary.strip().lower()
                g_start_iso_clean = dt_start_gcal.strftime("%Y-%m-%dT%H:%M:%S")
                
                google_signatures.add((g_summ_norm, g_start_iso_clean))
                
                # 3. Preparar datos para comparar con BD existente
                date_str = dt_start_gcal.strftime("%Y-%m-%d")
                start_int = int(dt_start_gcal.strftime("%H%M"))
                
                # Cálculo de End Time integer
                raw_end_int = int(dt_end_gcal.strftime("%H%M"))
                if dt_end_gcal.minute >= 45: # Redondeo de horas
                    next_h = dt_end_gcal + timedelta(hours=1)
                    end_int = int(next_h.replace(minute=0).strftime("%H%M"))
                else:
                    end_int = raw_end_int

                # Separar nombre/apellido
                parts = summary.strip().split(' ')
                name_val = parts[0]
                surname_val = " ".join(parts[1:]) if len(parts) > 1 else ""
                
                name_check = name_val.strip().lower()
                surname_check = surname_val.strip().lower()
                
                # FIRMA CANDIDATA (Debe coincidir con la estructura de db_signatures)
                candidate_sig = (name_check, surname_check, date_str, start_int)
                
                # --- LOG DE DECISIÓN ---
                if candidate_sig in db_signatures:
                    logger.info(f"  [SKIP BAJADA] Ya existe en BD: {candidate_sig}")
                    continue
                
                # Si llegamos aquí, NO está en la BD
                logger.info(f"  [NUEVO ENCONTRADO] Google trae: {summary} el {date_str} a las {start_int}")
                logger.info(f"     -> Buscamos firma: {candidate_sig}")
                logger.info(f"     -> ¿Estaba en DB?: NO")

                # INSERCIÓN
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
                    days=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][dt_start_gcal.weekday()],
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
                # Agregar a la firma local para no duplicar en este mismo loop
                db_signatures.add(candidate_sig)
                count_added_db += 1
                logger.info(f"  ✅ AGREGADO A BD: {summary}")

            except Exception as e:
                logger.error(f"  ❌ Error procesando evento Google '{summary}': {e}")
                continue

        session.commit()
        
        # =========================================================================
        # FASE B: BD -> GOOGLE
        # =========================================================================
        logger.info("--- 🔼 FASE B: PROCESANDO SUBIDAS (BD -> GOOGLE) ---")
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        local_classes = session.query(AsignedClasses).filter(
            AsignedClasses.date_prof >= today_str,
            AsignedClasses.status != 'Cancelada'
        ).all()
        
        for local_class in local_classes:
            full_name = f"{local_class.name} {local_class.surname}"
            
            # Filtro Preply
            if "- preply lesson" in full_name.lower() or local_class.package == "Preply":
                continue

            current_date_prof = local_class.date_prof if local_class.date_prof else local_class.date
            
            try:
                # Construir objetos datetime LOCALES
                s_time_str = str(local_class.start_prof_time).zfill(4)
                start_dt_obj = datetime.strptime(f"{current_date_prof} {s_time_str[:2]}:{s_time_str[2:]}", "%Y-%m-%d %H:%M")
                start_dt_obj = start_dt_obj.replace(tzinfo=LOCAL_TZ) # Asignar zona explicita
                
                e_time_str = str(local_class.end_prof_time).zfill(4)
                end_dt_obj = datetime.strptime(f"{current_date_prof} {e_time_str[:2]}:{e_time_str[2:]}", "%Y-%m-%d %H:%M")
                end_dt_obj = end_dt_obj.replace(tzinfo=LOCAL_TZ)
                
                if local_class.end_prof_time < local_class.start_prof_time:
                    end_dt_obj += timedelta(days=1)
                
                # Generar Firma para verificar con Google (Debe ser idéntica a la generada en Fase A punto 2)
                check_summ = full_name.strip().lower()
                check_start_iso = start_dt_obj.strftime("%Y-%m-%dT%H:%M:%S")
                
                check_sig = (check_summ, check_start_iso)
                
                # --- LOG DE COMPARACIÓN ---
                # Descomentar para ver detalle clase por clase
                logger.info(f"[CHECK UPLOAD] Buscando: {check_summ} @ {check_start_iso}")
                
                if check_sig in google_signatures:
                    # logger.info(f"   -> [SKIP] Ya existe en Google")
                    continue

                logger.info(f"  🚀 SUBIENDO A CALENDAR: {full_name}")
                logger.info(f"     -> Fecha Local: {start_dt_obj}")
                logger.info(f"     -> Firma generada: {check_sig}")
                
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

        final_msg = f"Sync Finalizado: ⬇️ {count_added_db} bajadas, ⬆️ {count_uploaded_google} subidas."
        logger.info("==================================================")
        logger.info(final_msg)
        
        return {
            "msg": final_msg,
            "new_count": count_added_db,
            "updated_count": count_uploaded_google
        }

    except Exception as e:
        session.rollback()
        logger.error(f"🔥 Error Sync: {e}", exc_info=True)
        raise e
    finally:
        session.close()