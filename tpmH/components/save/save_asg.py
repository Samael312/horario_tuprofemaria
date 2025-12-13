from nicegui import ui, app
import logging
import re
from datetime import datetime, timedelta

# --- IMPORTS BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import AsignedClasses, User
from components.share_data import *

# --- IMPORTAMOS TU LÓGICA DE TIEMPO EXISTENTE ---
# Asegúrate de que este archivo exista y la ruta sea correcta
from components.timezone_converter import  convert_student_to_teacher, get_slots_in_student_tz, from_int_time
# ----------------------------------------------

logger = logging.getLogger(__name__)

def get_minutes_str(duration_text):
    """Convierte texto como '1 hora' a '60'."""
    if not duration_text: return "60"
    text_lower = duration_text.lower()
    if "1 hora" in text_lower or "60" in text_lower: return "60"
    if "45" in text_lower: return "45"
    if "30" in text_lower: return "30"
    if "90" in text_lower or "1.5" in text_lower: return "90"
    nums = re.findall(r'\d+', duration_text)
    return nums[0] if nums else "60"

def create_save_asgn_classes(button, user, table_clases, table_rangos, duration_selector, days_of_week, package_selector):

    async def save_tables_to_db():
        # 1. Obtener Usuario Estudiante y su Zona Horaria
        if isinstance(user, dict):
            student_username = user.get("username")
        else:
            student_username = str(user)

        pg_session = PostgresSession()
        try:
            student_db = pg_session.query(User).filter_by(username=student_username).first()
            if not student_db:
                ui.notify("Error: No se encontró al estudiante.", type="negative")
                pg_session.close()
                return
            
            # Obtenemos la zona horaria del alumno
            student_tz = student_db.time_zone 
            if not student_tz: 
                student_tz = "UTC" # Fallback

            # Datos para actualizar
            package_val = package_selector.value or ""
            student_db.package = package_val
            student_name = student_db.name
            student_surname = student_db.surname
            
            # Lógica del paquete (X/Y)
            limit_int = PACKAGE_LIMITS.get(package_val, 0)
            if limit_int == 0:
                try:
                    limit_int = int(re.search(r'\d+', package_val).group())
                except: limit_int = 0

            current_count = pg_session.query(AsignedClasses).filter_by(username=student_username).count()
            pg_session.commit()

        except Exception as e:
            pg_session.rollback()
            ui.notify(f"Error DB Inicial: {e}", type="negative")
            pg_session.close()
            return

        # 2. Procesar filas de la tabla
        clases_data = []
        duration_val = duration_selector.value
        
        logger.info(f"--- INICIO GUARDADO ---")
        logger.info(f"Alumno: {student_username} | Zona: {student_tz}")

        if table_clases:
            for row in table_clases.rows:
                raw_hora = row.get("hora", "")   # Ej: "06:00-07:00"
                fecha = row.get("fecha", "")     # Ej: "2024-01-20"
                dia = row.get("dia", "")
                
                if not raw_hora or not fecha: continue

                # A. Obtener duración en minutos
                raw_duration = row.get("duration", duration_val)
                final_duration_str = get_minutes_str(raw_duration)
                duration_minutes = int(final_duration_str)

                # B. Parsear Hora Inicio Alumno (String -> Int)
                # "06:00-07:00" -> Tomamos "06:00" -> Quitamos ":" -> 600
                start_str_only = raw_hora.split('-')[0].strip()
                start_int_stu = int(start_str_only.replace(":", ""))

                # C. Calcular Hora Fin Alumno (Int) 
                # Calculamos end time simple para el alumno (local)
                # OJO: convert_student_to_teacher nos devuelve lo del profe, 
                # pero necesitamos guardar también lo del alumno.
                # Lo hacemos simple sumando minutos al datetime local.
                try:
                    dt_stu_start = datetime.strptime(f"{fecha} {start_str_only}", "%Y-%m-%d %H:%M")
                    dt_stu_end = dt_stu_start + timedelta(minutes=duration_minutes)
                    end_int_stu = int(dt_stu_end.strftime("%H%M"))
                except:
                    end_int_stu = start_int_stu + (duration_minutes // 60 * 100) # Fallback básico

                # D. USAR TU FUNCIÓN IMPORTADA PARA CALCULAR HORA PROFESORA
                # Esta función usa TEACHER_TIMEZONE="America/Caracas" internamente
                prof_start, prof_end, prof_date = convert_student_to_teacher(
                    fecha, 
                    start_int_stu, 
                    duration_minutes, 
                    student_tz
                )

                logger.info(f"Conversión: {start_int_stu} ({student_tz}) -> {prof_start} (Prof)")

                clases_data.append({
                    'username': student_username,
                    'name': student_name,
                    'surname': student_surname,
                    'package': package_val,
                    'days': dia,
                    'duration': final_duration_str,
                    
                    # DATOS ALUMNO
                    'date': fecha,
                    'start_time': start_int_stu,
                    'end_time': end_int_stu,
                    
                    # DATOS PROFESOR (Calculados por tu función)
                    'date_prof': prof_date,
                    'start_prof_time': prof_start,
                    'end_prof_time': prof_end
                })

        pg_session.close()

        if not clases_data:
             ui.notify("No hay datos válidos", type="warning")
             return

        # 3. Guardar en Postgres
        pg_session = PostgresSession()
        try:
            for i, item in enumerate(clases_data):
                class_num = current_count + i + 1
                count_str = f"{class_num}/{limit_int}" if limit_int > 0 else f"{class_num}"

                new_class = AsignedClasses(
                    username=item['username'],
                    name=item['name'],
                    surname=item['surname'],
                    
                    date=item['date'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    
                    date_prof=item['date_prof'],
                    start_prof_time=item['start_prof_time'],
                    end_prof_time=item['end_prof_time'],
                    
                    duration=item['duration'],
                    days=item['days'],
                    package=item['package'],
                    status="Pendiente",
                    total_classes=0,
                    class_count=count_str,
                    payment_info={}
                )
                pg_session.add(new_class)
            
            pg_session.commit()
            ui.notify("Clases guardadas correctamente", type="positive")
            logger.info("✅ Guardado exitoso.")

        except Exception as e:
            pg_session.rollback()
            ui.notify(f"Error guardando: {e}", type="negative")
        finally:
            pg_session.close()

        # 4. Backup SQLite (Opcional, misma lógica)
        try:
            sq = BackupSession()
            for i, item in enumerate(clases_data):
                class_num = current_count + i + 1
                count_str = f"{class_num}/{limit_int}" if limit_int > 0 else f"{class_num}"
                sq.add(AsignedClasses(
                    username=item['username'], name=item['name'], surname=item['surname'],
                    date=item['date'], start_time=item['start_time'], end_time=item['end_time'],
                    date_prof=item['date_prof'], start_prof_time=item['start_prof_time'], end_prof_time=item['end_prof_time'],
                    duration=item['duration'], days=item['days'], package=item['package'],
                    status="Pendiente", total_classes=0, class_count=count_str, payment_info={}
                ))
            sq.commit()
            sq.close()
        except: pass

    button.on("click", save_tables_to_db)
    return save_tables_to_db