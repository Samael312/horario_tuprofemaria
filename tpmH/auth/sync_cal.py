import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from db.models import User, AsignedClasses
from db.postgres_db import PostgresSession
from dateutil import parser
import random
from dotenv import load_dotenv # Importamos dotenv

# Cargar variables del archivo .env si existe (para local)
load_dotenv()

def sync_google_calendar_logic(teacher_email):
    """Lógica que se ejecuta en segundo plano para sincronizar."""
    
    # 1. INTENTAR CARGAR CREDENCIALES
    creds = None
    
    # OPCIÓN A: Variable de entorno (Para Render)
    json_creds_env = os.getenv('GOOGLE_CREDENTIALS_JSON')
    
    if json_creds_env:
        print("--- Usando credenciales desde Variable de Entorno (Render) ---")
        creds_dict = json.loads(json_creds_env)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/calendar.readonly'])
            
    # OPCIÓN B: Archivo local (Para tu PC)
    elif os.path.exists('credentials.json'):
        print("--- Usando credenciales desde archivo credentials.json (Local) ---")
        creds = service_account.Credentials.from_service_account_file(
            'credentials.json', scopes=['https://www.googleapis.com/auth/calendar.readonly'])
            
    else:
        raise Exception("ERROR FATAL: No se encontraron credenciales. \n"
                        "1. En Render: Configura GOOGLE_CREDENTIALS_JSON. \n"
                        "2. En Local: Pon el archivo credentials.json en la raíz.")

    # Conectar con Google
    service = build('calendar', 'v3', credentials=creds)
    
    # Buscar eventos desde AHORA
    now_iso = datetime.utcnow().isoformat() + 'Z'
    
    print(f"Buscando eventos en el calendario: {teacher_email}")
    
    try:
        events_result = service.events().list(
            calendarId=teacher_email, timeMin=now_iso,
            maxResults=50, singleEvents=True,
            orderBy='startTime').execute()
    except Exception as e:
        raise Exception(f"Error accediendo al calendario '{teacher_email}'. "
                        f"¿Invitaste al bot (client_email del JSON) a este calendario? Error: {e}")

    events = events_result.get('items', [])
    
    session = PostgresSession()
    count_added = 0
    
    try:
        for event in events:
            summary = event.get('summary', 'Sin Nombre')
            start_raw = event['start'].get('dateTime', event['start'].get('date'))
            end_raw = event['end'].get('dateTime', event['end'].get('date'))
            
            # Parsear fechas
            start_dt = parser.parse(start_raw)
            end_dt = parser.parse(end_raw)
            
            # --- CALCULO DURACIÓN ---
            duration_delta = end_dt - start_dt
            duration_minutes = duration_delta.total_seconds() / 60
            
            if 20 <= duration_minutes <= 40:
                str_duration = "30"
            elif 45 <= duration_minutes <= 60:
                str_duration = "50"
            else:
                str_duration = str(int(duration_minutes))

            # --- FORMATO INTEGER Y REDONDEO ---
            def get_hhmm(dt_obj, round_up=False):
                if round_up and dt_obj.minute >= 45:
                    dt_obj = dt_obj + timedelta(hours=1)
                    dt_obj = dt_obj.replace(minute=0)
                return int(dt_obj.strftime("%H%M"))

            start_int = get_hhmm(start_dt)
            end_int = get_hhmm(end_dt, round_up=True) 
            
            date_str = start_dt.strftime("%Y-%m-%d")
            # Mapeo de días (Asegúrate de importar days_of_week correctamente o definirlo aquí si falla)
            # Para evitar error de importación circular, lo defino safe aquí:
            days_map = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            day_name = days_map[start_dt.weekday()] 

            # --- EXTRACCIÓN NOMBRE ---
            parts = summary.split(' ')
            name_val = parts[0]
            surname_val = " ".join(parts[1:]) if len(parts) > 1 else ""

            # --- GENERACIÓN DE USUARIO (Name + Numero) ---
            clean_name = "".join(c for c in name_val if c.isalnum())
            clean_surname = "".join(c for c in surname_val if c.isalnum())
            rand_num = random.randint(100, 999)
            generated_username = f"{clean_name}{clean_surname}{rand_num}"

            # --- EVITAR DUPLICADOS ---
            slot_occupied = session.query(AsignedClasses).filter(
                AsignedClasses.date == date_str,
                AsignedClasses.start_time == start_int,
                AsignedClasses.status.notin_(['Cancelada', 'Cancelled', 'No Asistió'])
            ).first()

            if slot_occupied:
                continue 

            # --- CREAR CLASE ---
            new_class = AsignedClasses(
                username=generated_username,
                name=name_val,
                surname=surname_val,
                date=date_str,
                days=day_name,
                duration=str_duration,
                
                start_time=start_int,
                end_time=end_int,
                
                start_prof_time=start_int,
                end_prof_time=end_int,
                date_prof=date_str,
                
                package="Preply",
                status="Pendiente",
                class_count="1/1",
                total_classes=0,
                payment_info={}
            )
            session.add(new_class)
            count_added += 1
        
        session.commit()
        return count_added
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()