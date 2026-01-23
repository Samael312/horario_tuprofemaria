from datetime import datetime, timedelta
from db.postgres_db import PostgresSession
# ---------------------------------------------------------------
from db.models import User, ScheduleProf, AsignedClasses, ScheduleProfEsp
from zoneinfo import ZoneInfo
import logging
import httpx

# Configura aquí la zona horaria base de la profesora
session = PostgresSession()
teacher = session.query(User).filter(User.role == 'admin').first()
TEACHER_TIMEZONE = teacher.time_zone if teacher and teacher.time_zone else "America/Caracas"


TEACHER_TIMEZONE = "America/Caracas" 

# Logger local
logger = logging.getLogger(__name__)

def to_int_time(dt_obj):
    """Convierte datetime a entero HHMM"""
    return int(dt_obj.strftime("%H%M"))

def from_int_time(time_int):
    """Convierte entero HHMM a (hora, minuto)"""
    s = str(time_int).zfill(4)
    return int(s[:2]), int(s[2:])

def convert_student_to_teacher(date_str, start_time_int, duration_mins, student_tz_str):
    """
    Toma la hora/fecha elegida por el estudiante y calcula 
    cuándo es eso para la profesora.
    
    Retorna: (start_prof_int, end_prof_int, date_prof_str)
    """
    try:
        if not student_tz_str:
            student_tz_str = "UTC" # Fallback por seguridad

        # 1. Crear fecha/hora "aware" del estudiante
        sh, sm = from_int_time(start_time_int)
        dt_student_naive = datetime.strptime(f"{date_str} {sh}:{sm}", "%Y-%m-%d %H:%M")
        dt_student = dt_student_naive.replace(tzinfo=ZoneInfo(student_tz_str))

        # 2. Convertir a zona de profesora
        dt_prof = dt_student.astimezone(ZoneInfo(TEACHER_TIMEZONE))
        
        # 3. Calcular fin de clase (en tiempo profesora para consistencia)
        dt_prof_end = dt_prof + timedelta(minutes=duration_mins)

        # 4. Formatear resultados
        prof_start_int = to_int_time(dt_prof)
        prof_end_int = to_int_time(dt_prof_end)
        prof_date_str = dt_prof.strftime("%Y-%m-%d")

        return prof_start_int, prof_end_int, prof_date_str

    except Exception as e:
        logger.error(f"Error conversión zona horaria (S->T): {e}")
        # En caso de error crítico, devolvemos los mismos valores (fallback)
        # Calcula el end_time simple
        sh, sm = from_int_time(start_time_int)
        end_dt = datetime.strptime(f"{date_str} {sh}:{sm}", "%Y-%m-%d %H:%M") + timedelta(minutes=duration_mins)
        return start_time_int, to_int_time(end_dt), date_str

def get_slots_in_student_tz(teacher_slots, date_str, student_tz_str):
    """
    Convierte una lista de slots (enteros) disponibles de la profesora 
    a la hora local del estudiante para mostrarlos en la grilla.
    """
    student_slots = []
    try:
        if not student_tz_str:
            return teacher_slots # Si no tiene zona, mostramos la de la profe (o UTC)

        teacher_tz = ZoneInfo(TEACHER_TIMEZONE)
        student_tz = ZoneInfo(student_tz_str)

        for slot in teacher_slots:
            sh, sm = from_int_time(slot)
            # Creamos el tiempo en zona profe
            dt_prof = datetime.strptime(f"{date_str} {sh}:{sm}", "%Y-%m-%d %H:%M").replace(tzinfo=teacher_tz)
            
            # Convertimos a estudiante
            dt_student = dt_prof.astimezone(student_tz)
            
            # Solo agregamos si sigue siendo el mismo día (opcional, depende de tu lógica de UI)
            # Si permites ver horas de madrugada del día siguiente, quita este if
            if dt_student.strftime("%Y-%m-%d") == date_str:
                student_slots.append(to_int_time(dt_student))
            
    except Exception as e:
        logger.error(f"Error conversión slots (T->S): {e}")
        return teacher_slots
        
    return sorted(list(set(student_slots)))

# --- NUEVO: Caché para guardar IPs y no consultar la API repetidamente ---
_tz_cache = {}

async def get_timezone_from_ip(ip_address: str) -> str:
    """
    Consulta asíncrona a ip.guide para detectar zona horaria.
    Incluye caché y manejo de localhost.
    Retorna la zona horaria (str) o 'UTC' si falla.
    """
    # 1. Verificar Caché
    if ip_address in _tz_cache:
        return _tz_cache[ip_address]

    # 2. Verificar Localhost (GeoIP falla en local)
    if not ip_address or ip_address in ('127.0.0.1', 'localhost', '::1'):
        logger.warning("IP local detectada, usando UTC por defecto.")
        return "UTC"

    # 3. Consultar API
    url = f"https://ip.guide/{ip_address}"
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(url)
            
            if response.status_code == 200:
                data = response.json()

                logger.info(f"RESPUESTA IP.GUIDE: {data}")

                location = data.get('location', {})
                detected_tz = location.get('timezone')
                
                # Si no está en location, intentamos en la raíz por si acaso
                if not detected_tz:
                    detected_tz = data.get('timezone')

                if detected_tz:
                    _tz_cache[ip_address] = detected_tz
                    return detected_tz
            
            logger.warning(f"ip.guide retornó status {response.status_code}")

    except Exception as e:
        logger.error(f"Error conectando con ip.guide: {e}")

    # Fallback si todo falla
    return "UTC"