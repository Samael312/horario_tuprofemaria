from nicegui import ui, app
from datetime import datetime, timedelta
import logging
import asyncio  # Importamos asyncio para corregir el error del loop
from zoneinfo import ZoneInfo # Para manejo preciso de zonas al reagendar
from dateutil import parser # Necesario para parsear fechas de Google
from google.oauth2 import service_account
from googleapiclient.discovery import build
from auth.sync_cal import sync_google_calendar_logic
import os
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import AsignedClasses, User, ScheduleProf, ScheduleProfEsp, SchedulePref
from components.headerAdmin import create_admin_screen
from components.db_migration import backup_entire_database


from components.share_data import days_of_week, PACKAGE_LIMITS 

from components.timezone_converter import convert_student_to_teacher

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- SISTEMA DE CACHÉ GLOBAL ---
class DataCache:
    def __init__(self):
        self.classes = None    # Almacenará la lista de clases
        self.users = None      # Almacenará la lista de usuarios
        self.last_fetch = None
        self.ttl = timedelta(hours=2) # 2 Horas de vida

    def get(self):
        """Retorna (classes, users) si son válidos, sino None"""
        if self.classes is None or self.last_fetch is None:
            return None
        
        if datetime.now() - self.last_fetch > self.ttl:
            logger.info("Caché expirada. Se requiere recarga DB.")
            return None
            
        return self.classes, self.users

    def set(self, classes, users):
        self.classes = classes
        self.users = users
        self.last_fetch = datetime.now()
        logger.info(f"Datos guardados en Caché RAM ({len(classes)} registros).")

    def invalidate(self):
        self.classes = None
        self.users = None
        logger.info("Caché invalidada manualmente.")

# Instancia global (vive mientras corre la app)
global_cache = DataCache()

# Opciones de Estado para el Profesor
STATUS_OPTIONS = {
    'Pendiente': {'color': 'orange', 'icon': 'schedule'},
    'Prueba_Pendiente': {'color': 'purple', 'icon': 'science'}, 
    'Finalizada': {'color': 'teal', 'icon': 'task_alt'},
    'Completada': {'color': 'green', 'icon': 'check_circle'},
    'Cancelada': {'color': 'red', 'icon': 'cancel'},
    'No Asistió': {'color': 'grey', 'icon': 'person_off'}
}

# Estados que se consideran "Finalizados" para el historial general
FINALIZED_STATUSES = {'Completada', 'Cancelada', 'No Asistió', 'Finalizada'}

# Estados que CONSUMEN una clase del paquete (para class_count)
CONSUMED_STATUSES = {'Completada', 'No Asistió'}

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

@ui.page('/myclassesAdmin')
def my_classesAdmin():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_admin_screen()

    # Almacenamos los valores de los filtros aquí
    filters = {
        'student': None,       # Texto libre (Nombre/Apellido)
        'region': None,     # Zona horaria seleccionada
        'time_of_day': None, # 'Mañana', 'Tarde', 'Noche'
        'date': None  # Fecha específica
    }

    # ==============================================================================
    # 1. FUNCIÓN DE SINCRONIZACIÓN Y RESPALDO (INTEGRADA)
    # ==============================================================================
    async def run_sync():
        """
        Ejecuta secuencialmente:
        1. Sincronización Bidireccional Google Calendar <-> Neon
        2. Respaldo total Neon -> Supabase
        """
        # --- CONFIGURACIÓN DE UI ---
        notification = ui.notification(timeout=None)
        notification.spinner = True
        
        try:
            teacher_email = os.getenv('CALENDAR_ID')
            if not teacher_email:
                notification.dismiss()
                ui.notify('Error: Falta CALENDAR_ID en .env', type='negative')
                return

            # ==========================================
            # FASE 1: GOOGLE CALENDAR SYNC
            # ==========================================
            notification.message = 'Fase 1/2: Sincronizando Google Calendar...'
            
            # Ejecutamos en hilo aparte para no congelar la UI
            google_result = await asyncio.to_thread(sync_google_calendar_logic, teacher_email)
            
            # Extraemos resultados de Google
            g_msg = google_result.get('msg', 'Google Sync OK')
            g_new = google_result.get('new_count', 0)
            g_upd = google_result.get('updated_count', 0)

            # ==========================================
            # FASE 2: RESPALDO A SUPABASE
            # ==========================================
            notification.message = 'Fase 2/2: Clonando Base de Datos a Supabase...'
            
            # Ejecutamos el respaldo también en hilo aparte (es pesado)
            backup_result = await asyncio.to_thread(backup_entire_database)

            notification.dismiss()

            # ==========================================
            # REPORTE FINAL
            # ==========================================
            
            # Construir mensaje de éxito/error del respaldo
            if backup_result.get("success"):
                db_status = "✅ Respaldo Supabase OK"
            else:
                db_error = backup_result.get("error", "Error desconocido")
                db_status = f"⚠️ Falló Respaldo: {db_error}"
                logger.error(f"Error Backup: {db_error}")

            # Notificación combinada para el usuario
            final_message = (
                f"Sincronización Completa:\n"
                f"⬇️ {g_new} bajadas | ⬆️ {g_upd} subidas\n"
                f"{db_status}"
            )
            
            # Si hubo error en respaldo, usamos warning, si no positive
            notif_type = 'warning' if not backup_result.get("success") else 'positive'
            
            ui.notify(final_message, type=notif_type, icon='cloud_done', multi_line=True, close_button=True)

            # Refrescar la UI para mostrar los nuevos datos traídos de Google
            global_cache.invalidate()
            refresh_ui()

        except Exception as e:
            if notification:
                notification.dismiss()
            logger.error(f"Error crítico en run_sync: {e}")
            ui.notify(f'Error crítico: {str(e)}', type='negative')
    
    # 1. LOGICA DE DATOS
    def get_all_classes():
        """
        Versión OPTIMIZADA con Caché.
        """
        session = PostgresSession()
        try:
            # 1. Obtener Usuario Admin (Rápido, no cacheamos esto por si cambia de usuario)
            username = app.storage.user.get("username")
            admin_user = session.query(User).filter(User.username == username).first()
            admin_tz_str = admin_user.time_zone if admin_user and admin_user.time_zone else 'America/Caracas'
            try:
                admin_tz = ZoneInfo(admin_tz_str)
            except:
                admin_tz = ZoneInfo('America/Caracas') 
            
            now_admin_local = datetime.now(admin_tz).replace(tzinfo=None)
            now_date_str = now_admin_local.strftime('%Y-%m-%d')

            # ======================================================
            # 2. LOGICA DE CACHÉ (AQUÍ ESTÁ LA MAGIA)
            # ======================================================
            cached_data = global_cache.get()
            
            if cached_data:
                # HIT: Usamos datos de memoria
                all_classes, users = cached_data
            else:
                # MISS: Consultamos BD (Lento)
                logger.info("⏳ Consultando Base de Datos Completa...")
                all_classes = session.query(AsignedClasses).all()
                users = session.query(User).all()
                
                # CRÍTICO: Desconectar objetos de la sesión para que vivan en caché
                session.expunge_all() 
                
                # Guardamos en caché
                global_cache.set(all_classes, users)

            # Mapeo de zonas horarias (Procesamiento Python rápido)
            user_tz_map = {u.username: (u.time_zone or 'UTC') for u in users}
            
            today_classes = []
            upcoming_platform = [] 
            upcoming_preply = []   
            history_classes = []
            
            unique_regions = set()
            unique_students = set()
            
            ids_to_finalize = [] # Para actualización batch en DB

            for c in all_classes:
                # Adjuntar TimeZone y Datos para Filtros
                c.student_tz = user_tz_map.get(c.username, 'UTC')
                unique_regions.add(c.student_tz)
                full_name = f"{c.name} {c.surname}".strip()
                unique_students.add(full_name)

                # Datos de Tiempo (Profesor)
                p_date = getattr(c, 'date_prof', None) or c.date
                
                # --- AUTO-FINALIZACIÓN (Adaptada para Caché) ---
                if c.status in ['Pendiente', 'Prueba_Pendiente']:
                    try:
                         if c.date_prof and c.start_prof_time:
                            t_str = str(c.start_prof_time).zfill(4)
                            c_start_prof = datetime.strptime(f"{c.date_prof} {t_str}", "%Y-%m-%d %H%M")
                            dur = int(c.duration) if c.duration else 60
                            c_end_prof = c_start_prof + timedelta(minutes=dur)

                            if now_admin_local > c_end_prof:
                                # Actualizamos objeto en memoria (para que se vea ya)
                                c.status = 'Finalizada'
                                # Guardamos ID para actualizar DB real
                                ids_to_finalize.append(c.id)
                    except Exception: pass
                
                # --- CLASIFICACIÓN (Igual que antes) ---
                is_future = False
                try:
                    if c.date_prof and c.start_prof_time:
                        t_str = str(c.start_prof_time).zfill(4)
                        c_start = datetime.strptime(f"{c.date_prof} {t_str}", "%Y-%m-%d %H%M")
                        if c_start > now_admin_local: is_future = True
                except: pass

                if c.status in FINALIZED_STATUSES or c.status == 'Finalizada':
                    history_classes.append(c)
                elif p_date == now_date_str:
                    today_classes.append(c)
                elif is_future or (p_date > now_date_str and c.status not in FINALIZED_STATUSES):
                    if "- Preply lesson" in full_name: upcoming_preply.append(c)
                    else: upcoming_platform.append(c)
                else:
                    history_classes.append(c)

            # --- ESCRITURA EN DB DE CAMBIOS AUTOMÁTICOS ---
            # Si detectamos clases vencidas, las actualizamos en DB sin borrar caché
            if ids_to_finalize:
                try:
                    # Usamos una query UPDATE masiva que es muy eficiente
                    session.query(AsignedClasses).filter(AsignedClasses.id.in_(ids_to_finalize)).update({AsignedClasses.status: 'Finalizada'}, synchronize_session=False)
                    session.commit()
                    logger.info(f"✅ Se auto-finalizaron {len(ids_to_finalize)} clases en DB.")
                except Exception as e:
                    logger.error(f"Error auto-finalizando: {e}")
                    session.rollback()

            # Ordenamiento (Rápido en Python)
            def sort_key_prof(x):
                d = getattr(x, 'date_prof', None) or x.date or "9999-99-99"
                t = x.start_prof_time if getattr(x, 'start_prof_time', None) is not None else x.start_time or 0
                return (d, t)

            today_classes.sort(key=sort_key_prof)
            upcoming_platform.sort(key=sort_key_prof)
            upcoming_preply.sort(key=sort_key_prof)
            history_classes.sort(key=sort_key_prof, reverse=True)
            
            return today_classes, upcoming_platform, upcoming_preply, history_classes, sorted(list(unique_regions)), sorted(list(unique_students)), all_classes
            
        except Exception as e:
            logger.error(f"Error fetching admin classes: {e}")
            return [], [], [], [], [], [], []
        finally:
            session.close()
    
    def filter_list(class_list):
        """Aplica los filtros activos a una lista."""
        filtered = []
        # Obtenemos valores limpios de los filtros
        f_student = filters['student']
        f_region = filters['region']
        f_time = filters['time_of_day']
        f_date = filters['date']

        for c in class_list:
            # 1. Filtro Estudiante (Selector)
            if f_student and f_student != 'Todos':
                full_name = f"{c.name} {c.surname}".strip()
                if full_name != f_student:
                    continue
            
            # 2. Filtro Región
            if f_region and f_region != 'Todas':
                if c.student_tz != f_region:
                    continue
            
            # 3. Filtro Hora
            if f_time and f_time != 'Todos':
                t = c.start_prof_time if c.start_prof_time is not None else c.start_time
                if t is None: t = 0
                
                if f_time == 'Mañana' and t >= 1200: continue
                if f_time == 'Tarde' and not (1200 <= t < 1900): continue
                if f_time == 'Noche' and t < 1900: continue
            
            if f_date:
                # Obtenemos la fecha real (Profesor o base)
                c_date = getattr(c, 'date_prof', None) or c.date
                if c_date != f_date:
                    continue

            filtered.append(c)
        return filtered

    async def update_status(c_id, new_status):
        session = PostgresSession()
        try:
            cls = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            if cls:
                cls.status = new_status
                
                # --- ACTUALIZACIÓN DE USER (Contadores DB) ---
                session.flush() 

                user = session.query(User).filter(User.username == cls.username).first()
                if user:
                    # 1. TOTAL CLASSES (Histórico) - NO contamos pruebas
                    finalized_count = session.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        AsignedClasses.status.in_(['Completada', 'Cancelada', 'No Asistió', 'Finalizada']),
                        AsignedClasses.status.notlike('%Prueba_Pendiente%')
                    ).count()
                    user.total_classes = finalized_count

                    # 2. CLASS COUNT (Paquete Mensual) - NO contamos pruebas
                    #try:
                    #    c_date_obj = datetime.strptime(cls.date, '%Y-%m-%d')
                    #    month_prefix = c_date_obj.strftime('%Y-%m')
                    #except:
                    #    month_prefix = datetime.now().strftime('%Y-%m')

                    month_consumed = session.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        #AsignedClasses.date.startswith(month_prefix),
                        AsignedClasses.status.in_(CONSUMED_STATUSES),
                        AsignedClasses.status.notlike('%Prueba_Pendiente%')
                    ).count()

                    pkg_limit = PACKAGE_LIMITS.get(user.package, 0)
                    user.class_count = f"{month_consumed}/{pkg_limit}" if pkg_limit > 0 else f"{month_consumed}"

                    session.add(user)

                session.commit()
                global_cache.invalidate()
                
                # Backup SQLite (Misma lógica)
                try:
                    bk_sess = BackupSession()
                    bk_cls = bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        AsignedClasses.date == cls.date,
                        AsignedClasses.start_time == cls.start_time
                    ).first()
                    
                    if bk_cls:
                        bk_cls.status = new_status
                    else:
                        # Si no existe, lo creamos (manteniendo lógica de nulos si es prueba)
                        bk_sess.add(AsignedClasses(
                            username=cls.username, name=cls.name, surname=cls.surname,
                            date=cls.date, days=cls.days, start_time=cls.start_time,
                            end_time=cls.end_time, duration=cls.duration, 
                            package=cls.package, status=new_status,
                            start_prof_time=getattr(cls, 'start_prof_time', None),
                            end_prof_time=getattr(cls, 'end_prof_time', None),
                            date_prof=getattr(cls, 'date_prof', None),
                            class_count=getattr(cls, 'class_count', None),
                            total_classes=getattr(cls, 'total_classes', None)
                        ))
                    
                    if user:
                        bk_user = bk_sess.query(User).filter(User.username == cls.username).first()
                        if bk_user:
                            bk_user.total_classes = user.total_classes
                            bk_user.class_count = user.class_count

                    bk_sess.commit()
                    bk_sess.close()
                except Exception as e:
                    logger.error(f"Error backup sqlite: {e}")

                ui.notify(f'Clase actualizada a: {new_status}', type='positive', icon='check')
                refresh_ui()
        except Exception as e:
            ui.notify(f"Error al actualizar: {e}", type='negative')
        finally:
            session.close()

    # --- LÓGICA DE REAGENDAMIENTO ---
    async def reschedule_class(c_id, new_prof_date, new_prof_time_int, new_student_date, new_student_time_int, dialog):
        session = PostgresSession()
        try:
            cls = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            if cls:
                # Guardar valores viejos para buscar en Backup
                old_date = cls.date
                old_start = cls.start_time
                username = cls.username

                # Calcular Duración y End Times
                duration = int(cls.duration) if cls.duration else 60
                
                # Calcular end_time Estudiante
                s_h = new_student_time_int // 100
                s_m = new_student_time_int % 100
                s_start_dt = datetime.strptime(f"{new_student_date} {s_h}:{s_m}", "%Y-%m-%d %H:%M")
                s_end_dt = s_start_dt + timedelta(minutes=duration)
                new_student_end_int = int(s_end_dt.strftime("%H%M"))
                
                # Calcular end_time Profesor
                p_h = new_prof_time_int // 100
                p_m = new_prof_time_int % 100
                p_start_dt = datetime.strptime(f"{new_prof_date} {p_h}:{p_m}", "%Y-%m-%d %H:%M")
                p_end_dt = p_start_dt + timedelta(minutes=duration)
                new_prof_end_int = int(p_end_dt.strftime("%H%M"))

                # Nombre del día (basado en fecha estudiante)
                dt_obj = datetime.strptime(new_student_date, '%Y-%m-%d')
                new_day_name = days_of_week[dt_obj.weekday()]

                # 4. Actualizar en BD (Postgres)
                cls.date = new_student_date
                cls.start_time = new_student_time_int
                cls.end_time = new_student_end_int
                cls.days = new_day_name
                cls.date_prof = new_prof_date
                cls.start_prof_time = new_prof_time_int
                cls.end_prof_time = new_prof_end_int
                session.commit()
                global_cache.invalidate()

                # 5. Actualizar Backup SQLite
                try:
                    bk_sess = BackupSession()
                    bk_cls = bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == username,
                        AsignedClasses.date == old_date,
                        AsignedClasses.start_time == old_start
                    ).first()
                    
                    if bk_cls:
                        bk_cls.date = new_student_date
                        bk_cls.start_time = new_student_time_int
                        bk_cls.end_time = new_student_end_int
                        bk_cls.days = new_day_name
                        bk_cls.date_prof = new_prof_date
                        bk_cls.start_prof_time = new_prof_time_int
                        bk_cls.end_prof_time = new_prof_end_int
                        bk_sess.commit()
                    bk_sess.close()
                except Exception as e:
                    logger.error(f"Error backup reschedule: {e}")

                ui.notify(f"Clase reagendada correctamente.", type='positive')
                dialog.close()
                refresh_ui()
            else:
                ui.notify("Clase no encontrada", type='negative')
        except Exception as e:
            ui.notify(f"Error al reagendar: {e}", type='negative')
        finally:
            session.close()


    def open_reschedule_dialog(c, on_success=None):
   
        # Obtener el usuario admin actual (o forzar el que se esté usando)
        admin_username = app.storage.user.get("username")

        # === 1. LÓGICA DE BÚSQUEDA (Misma lógica Admin, estructura limpia) ===
        def get_slots_data(date_str):
            session = PostgresSession()
            slots_data = []
            try:
                if not date_str: return []
                
                # Normalizar fecha
                d_clean = date_str.replace('/', '-')
                try: dt = datetime.strptime(d_clean, '%Y-%m-%d')
                except ValueError: return []
                
                query_date = dt.strftime('%Y-%m-%d')
                day_name = days_of_week[dt.weekday()]
                
                # A) Disponibilidad (Tus reglas)
                rules = session.query(ScheduleProfEsp).filter_by(date=query_date).all()
                if not rules:
                    rules = session.query(ScheduleProf).filter_by(days=day_name).all()
                
                avail_ranges = []
                POSITIVE_STATUS = ["Libre", "Available", "Disponible"]
                for r in rules:
                    status = str(r.avai if hasattr(r, 'avai') else r.availability)
                    if status in POSITIVE_STATUS:
                        avail_ranges.append((r.start_time, r.end_time))
                
                # B) Ocupado (Tus clases, EXCLUYENDO la actual c.id)
                busy = session.query(AsignedClasses).filter(
                    AsignedClasses.date_prof == query_date,
                    AsignedClasses.status.notin_(['Cancelled', 'Cancelada']),
                    AsignedClasses.id != c.id 
                ).all()
                busy_ranges = [(b.start_prof_time, b.end_prof_time) for b in busy if b.start_prof_time]

                # C) Zonas Horarias
                # 1. Alumno
                student_user = session.query(User).filter(User.username == c.username).first()
                student_tz_str = student_user.time_zone if student_user and student_user.time_zone else 'UTC'
                
                # 2. Profesora (Tú)
                admin_user = session.query(User).filter(User.username == admin_username).first()
                teacher_tz_str = admin_user.time_zone if admin_user and admin_user.time_zone else 'America/Caracas'

                # D) Cálculo Slots
                try: duration = int(float(c.duration)) if c.duration else 60
                except: duration = 60
                step = 60 
                
                def to_minutes(hhmm): return (hhmm // 100) * 60 + (hhmm % 100)
                def to_hhmm_int(minutes): return ((minutes // 60) * 100) + (minutes % 60)
                busy_ranges_min = [(to_minutes(bs), to_minutes(be)) for bs, be in busy_ranges]

                valid_slots = []
                for start, end in avail_ranges:
                    curr_m = to_minutes(start)
                    end_m = to_minutes(end)
                    while curr_m + duration <= end_m:
                        s_end_m = curr_m + duration
                        is_busy = False
                        for b_s_m, b_e_m in busy_ranges_min:
                            if (curr_m < b_e_m) and (s_end_m > b_s_m): is_busy = True; break
                        if not is_busy: valid_slots.append(to_hhmm_int(curr_m))
                        curr_m += step 
                
                unique_slots = sorted(list(set(valid_slots)))
                
                # E) Conversión y Formato
                for slot in unique_slots:
                    t_h, t_m = slot // 100, slot % 100
                    t_str = f"{str(t_h).zfill(2)}:{str(t_m).zfill(2)}"
                    try:
                        prof_tz = ZoneInfo(teacher_tz_str)
                        stud_tz = ZoneInfo(student_tz_str)
                        
                        # Creado en Zona Profe
                        dt_prof = datetime.strptime(f"{query_date} {t_str}", "%Y-%m-%d %H:%M").replace(tzinfo=prof_tz)
                        dt_stud = dt_prof.astimezone(stud_tz)
                        
                        dt_prof_end = dt_prof + timedelta(minutes=duration)
                        dt_stud_end = dt_stud + timedelta(minutes=duration)
                        
                        s_time_str = dt_stud.strftime("%H:%M")
                        s_date_str = dt_stud.strftime("%Y-%m-%d")
                        s_time_int = int(dt_stud.strftime("%H%M"))
                        s_end_int = int(dt_stud_end.strftime("%H%M"))
                        s_weekday = days_of_week[dt_stud.weekday()]
                        
                        # Preferencias del Alumno
                        is_preferred = False
                        prefs = session.query(SchedulePref).filter(SchedulePref.username == c.username, SchedulePref.days == s_weekday).all()
                        for p in prefs:
                            if p.start_time <= s_time_int < p.end_time: is_preferred = True; break
                        
                        day_diff = f"({s_weekday})" if s_date_str != query_date else ""

                        slots_data.append({
                            't_time_int': slot, 
                            't_end_int': int(dt_prof_end.strftime("%H%M")), 
                            't_date': query_date, 
                            't_time_str': t_str,
                            
                            's_time_int': s_time_int, 
                            's_end_int': s_end_int, 
                            's_date': s_date_str, 
                            's_weekday': s_weekday,
                            's_time_str': s_time_str, 
                            's_day_diff': day_diff, 
                            'is_preferred': is_preferred
                        })
                    except Exception: pass
            except Exception as e: 
                logger.error(f"Error slots admin: {e}")
            finally: 
                session.close()
            return slots_data

        # === 2. INTERFAZ GRÁFICA (Estilo Alumno adaptado a Admin) ===
        with ui.dialog() as d, ui.card().classes('w-full max-w-[900px] h-[85vh] p-0 rounded-2xl flex flex-col overflow-hidden shadow-2xl'):
            
            # Header (Admin Style - Darker)
            with ui.row().classes('w-full bg-slate-900 text-white p-6 justify-between items-center shrink-0'):
                with ui.column().classes('gap-1'):
                    ui.label('Reagendar Clase (Admin)').classes('text-xl font-bold tracking-wide')
                    with ui.row().classes('items-center gap-2 text-sm text-slate-400'):
                        ui.icon('person', size='xs')
                        ui.label(f'Alumno: {c.name} {c.surname}')
                ui.button(icon='close', on_click=d.close).props('flat round dense color=white')

            # Contenido Scrollable
            with ui.column().classes('w-full flex-1 p-6 gap-6 overflow-hidden bg-slate-50'):
                
                # Selector Fecha (TU CALENDARIO)
                with ui.row().classes('w-full items-end gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm'):
                    default_date = c.date_prof if c.date_prof else c.date
                    
                    date_input = ui.input('Fecha (Tu Calendario)', value=default_date).props('outlined dense mask="####-##-##"').classes('flex-1')
                    with ui.menu().props('no-parent-event') as menu:
                            ui.date().bind_value(date_input).props('mask="YYYY-MM-DD"')
                    with date_input.add_slot('append'):
                        ui.icon('event').classes('cursor-pointer text-indigo-600').on('click', menu.open)
                    
                    search_btn = ui.button('Ver Disponibilidad', icon='search') \
                        .props('unelevated color=indigo-600') \
                        .classes('h-[40px] px-6 font-bold')
                
                # Resultados Grid
                results_container = ui.column().classes('w-full flex-1 overflow-y-auto pr-2 gap-4')
                spinner = ui.spinner('dots', size='3em', color='indigo').classes('self-center hidden')

                async def show_slots():
                    results_container.clear()
                    spinner.classes(remove='hidden')
                    
                    date_val = date_input.value
                    # Ejecutar lógica DB en hilo separado
                    slots = await asyncio.to_thread(get_slots_data, date_val)
                    
                    spinner.classes(add='hidden')
                    
                    if not slots:
                        with results_container:
                            with ui.column().classes('w-full items-center justify-center py-10 opacity-50'):
                                ui.icon('event_busy', size='4xl', color='slate')
                                ui.label('Sin huecos disponibles.').classes('text-lg')
                        return

                    with results_container:
                        ui.label(f'Huecos libres el {date_val}:').classes('text-xs font-bold text-slate-500 uppercase tracking-widest mb-2')
                        
                        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for slot in slots:
                                # Estilos condicionales: Resaltamos si es horario preferido del alumno
                                card_bg = 'bg-emerald-50 border-emerald-200' if slot['is_preferred'] else 'bg-white border-slate-200'
                                
                                with ui.card().classes(f'p-4 border rounded-xl gap-2 {card_bg} hover:shadow-lg hover:border-indigo-500 cursor-pointer transition-all group') \
                                        .on('click', lambda s=slot: confirm_reschedule(s)):
                                    
                                    # Badge Preferencia Alumno
                                    if slot['is_preferred']:
                                        with ui.row().classes('w-full justify-end absolute top-2 right-2'): 
                                            ui.badge('Prefiere Alumno', color='emerald').props('dense flat')

                                    with ui.row().classes('w-full justify-between items-center mt-2'):
                                        
                                        # 1. TU HORA (Principal - Grande)
                                        with ui.column().classes('gap-0 items-start'):
                                            ui.label('TU HORA').classes('text-[10px] font-bold text-slate-400 tracking-wider')
                                            ui.label(slot['t_time_str']).classes('text-2xl font-black text-slate-700 group-hover:text-indigo-600')
                                        
                                        ui.icon('arrow_forward', color='slate-300')
                                        
                                        # 2. HORA ALUMNO (Secundaria - Derecha)
                                        with ui.column().classes('gap-0 items-end'):
                                            ui.label('ALUMNO').classes('text-[10px] font-bold text-slate-400 tracking-wider')
                                            ui.label(slot['s_time_str']).classes('text-lg font-medium text-slate-600')
                                            if slot['s_day_diff']: 
                                                ui.label(f"{slot['s_day_diff']}").classes('text-[10px] font-bold text-orange-500')

                # === 3. CONFIRMACIÓN Y GUARDADO ===
                def confirm_reschedule(slot_data):
                    with ui.dialog() as confirm_d, ui.card().classes('w-96 p-6 rounded-xl'):
                        ui.label('Confirmar Cambio').classes('text-xl font-bold text-slate-800')
                        
                        with ui.column().classes('my-4 gap-2 bg-slate-50 p-3 rounded border border-slate-100'):
                            ui.label('Se moverá la clase a:').classes('text-xs text-slate-400 uppercase font-bold')
                            ui.label(f"{slot_data['t_date']} a las {slot_data['t_time_str']}").classes('text-lg font-bold text-indigo-700')
                            ui.label('(Tu Horario)').classes('text-xs text-slate-400')
                            
                            ui.separator().classes('bg-slate-200')
                            
                            ui.label(f"Alumno: {slot_data['s_date']} - {slot_data['s_time_str']}").classes('text-sm text-slate-600 italic')

                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Cancelar', on_click=confirm_d.close).props('flat color=slate')
                            
                            async def execute_save():
                                session = PostgresSession()
                                try:
                                    class_db = session.query(AsignedClasses).filter(AsignedClasses.id == c.id).first()
                                    if not class_db: ui.notify("Error: Clase no encontrada", type='negative'); return

                                    # Actualizar DB (Ambos lados)
                                    class_db.date = slot_data['s_date']; class_db.days = slot_data['s_weekday']
                                    class_db.start_time = slot_data['s_time_int']; class_db.end_time = slot_data['s_end_int']
                                    
                                    class_db.date_prof = slot_data['t_date']
                                    class_db.start_prof_time = slot_data['t_time_int']; class_db.end_prof_time = slot_data['t_end_int']
                                    
                                    class_db.status = 'Pendiente'

                                    session.commit()
                                    ui.notify(f"Clase reagendada correctamente.", type='positive')
                                    
                                    confirm_d.close()
                                    d.close()
                                    
                                    # Callback de refresco
                                    if on_success: on_success()
                                    else: ui.navigate.reload() # Fallback si no hay callback
                                    
                                except Exception as e:
                                    session.rollback(); ui.notify(f"Error: {e}", type='negative')
                                finally: session.close()
                                    
                            ui.button('Confirmar', on_click=execute_save).props('unelevated color=indigo')
                    confirm_d.open()

                # Listeners
                search_btn.on('click', show_slots)
                if default_date: ui.timer(0.1, show_slots, once=True)

        d.open()

    # 2. COMPONENTES VISUALES
    
    def render_stat_card(label, value, color):
        with ui.card().classes('flex-1 min-w-[140px] p-4 rounded-xl shadow-sm border border-slate-100 bg-white items-center justify-between flex-row'):
            with ui.column().classes('gap-0'):
                ui.label(str(value)).classes(f'text-3xl font-bold text-{color}-600 leading-none')
                ui.label(label).classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider')
            ui.icon('bar_chart', color=f'{color}-200', size='md')

    def render_admin_class_card(c, is_history=False):
        # Datos Temporales
        p_start = getattr(c, 'start_prof_time', None)
        use_prof_time = p_start is not None
        
        raw_start = p_start if use_prof_time else c.start_time
        raw_date = (getattr(c, 'date_prof', None) or c.date)
        
        t_str = str(raw_start).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        
        try:
            dt = datetime.strptime(raw_date, '%Y-%m-%d')
            date_nice = dt.strftime('%d %b')
            day_str = days_of_week[dt.weekday()][:3]
        except:
            date_nice = raw_date
            day_str = "---"

        dur_text = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
        
        tz_icon = 'public' if use_prof_time else 'warning'
        tz_tooltip = 'Hora Local Profesora' if use_prof_time else 'Hora Alumno (Sin conversión)'

        current_status = c.status
        status_config = STATUS_OPTIONS.get(current_status, {'color': 'gray', 'icon': 'help'})
        
        # --- ESTILO DISTINTIVO PREPLY ---
        full_name = f"{c.name} {c.surname}"
        if "- Preply lesson" in full_name and not is_history:
             border_l = "border-teal-400" # Distintivo Preply
        elif not is_history:
             border_l = f"border-{status_config['color']}-500" # Distintivo Plataforma
        else:
             border_l = "border-slate-300" # Historial

        card_opacity = "opacity-60 hover:opacity-100" if is_history or current_status == 'Cancelada' else "opacity-100"

        with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-col md:flex-row overflow-hidden transition-all {card_opacity}'):
            
            # 1. Bloque Izquierdo (Hora Prof)
            with ui.row().classes(f'md:w-32 w-full justify-between md:justify-center items-center bg-slate-50 md:border-r-4 md:border-b-0 border-b-4 {border_l} p-3 gap-2'):
                with ui.column().classes('items-center gap-0'):
                    ui.label(fmt_time).classes('text-2xl font-bold text-slate-700 leading-none')
                    with ui.row().classes('items-center gap-1'):
                        ui.icon(tz_icon, size='xs', color='slate-400').tooltip(tz_tooltip)
                        ui.label(dur_text).classes('text-[10px] font-medium text-slate-400')
                
                with ui.column().classes('items-end md:items-center gap-0'):
                    ui.label(date_nice).classes('text-xs font-bold uppercase text-slate-500')
                    ui.label(day_str).classes('text-[10px] text-slate-400')

            # 2. Bloque Central (Info Estudiante)
            with ui.column().classes('flex-1 p-3 md:p-4 justify-center gap-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('person', size='xs', color='slate-400')
                    ui.label(full_name).classes('text-lg font-bold text-slate-800 leading-tight')
                    
                    # --- BOTÓN REAGENDAR ---
                    if not c.status == ('Cancelada', 'No Asistió', 'Completada'):
                        ui.button('Reagendar', icon='edit_calendar', on_click=lambda: open_reschedule_dialog(c)) \
                            .props('flat dense color=blue-600 size=sm').classes('mt-2')
                
                # Etiquetas (Chips)
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    # Hora Alumno
                    s_time_str = str(c.start_time).zfill(4)
                    s_fmt = f"{s_time_str[:2]}:{s_time_str[2:]}"
                    ui.label(f"Alumno: {s_fmt}").classes('text-[10px] font-bold bg-slate-100 text-slate-600 px-2 py-0.5 rounded')
                    
                    # Plan
                    if c.package:
                        ui.label(f"{c.package}").classes('text-[10px] font-bold bg-gray-100 text-gray-600 px-2 py-0.5 rounded')

                    # ETIQUETA: ZONA HORARIA ESTUDIANTE
                    st_tz = getattr(c, 'student_tz', 'UTC')
                    ui.label(f"{st_tz}").classes('text-[10px] font-bold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-100').tooltip('Zona horaria del estudiante')

                    # ETIQUETA: TIPO DE CLASE
                    if c.status == 'Prueba_Pendiente':
                        ui.label('PRUEBA').classes('text-[10px] font-bold bg-purple-100 text-purple-700 px-2 py-0.5 rounded border border-purple-200')
                    else:
                        ui.label('REGULAR').classes('text-[10px] font-bold bg-rose-50 text-rose-700 px-2 py-0.5 rounded border border-rose-100')

                    # ETIQUETA: CONTEO PAQUETE (class_count)
                    if getattr(c, 'class_count', None):
                        ui.label(f"Clase {c.class_count}").classes('text-[10px] font-bold bg-yellow-50 text-yellow-700 px-2 py-0.5 rounded border border-yellow-100').tooltip('Progreso del paquete')

                    # ETIQUETA: TOTAL HISTÓRICO (total_classes)
                    if getattr(c, 'total_classes', None):
                        ui.label(f"Total #{c.total_classes}").classes('text-[10px] font-bold bg-cyan-50 text-cyan-700 px-2 py-0.5 rounded border border-cyan-100').tooltip('Total histórico de clases')

            # 3. Bloque Derecho (Acciones)
            with ui.column().classes('p-3 md:p-4 justify-center items-end md:w-64 bg-white border-t md:border-t-0 md:border-l border-slate-50'):
                
                # Selector de Estado
                display_options = [k for k in STATUS_OPTIONS.keys() if k != 'Prueba_Pendiente']
                if current_status == 'Prueba_Pendiente' and current_status not in display_options:
                    display_options.insert(0, current_status)

                status_select = ui.select(
                    options=display_options,
                    value=current_status,
                    on_change=lambda e, cid=c.id: update_status(cid, e.value)
                ).props('outlined dense options-dense behavior="menu"').classes('w-full')
                
                # Estado visual
                with ui.row().classes('w-full justify-between items-center mt-1'):
                    ui.label('Estado:').classes('text-[10px] text-slate-400')
                    with ui.row().classes('items-center gap-1'):
                        ui.icon(status_config['icon'], size='xs', color=status_config['color'])
                        ui.label(current_status.replace('_', ' ')).classes(f'text-xs font-bold text-{status_config["color"]}-600')

    @ui.refreshable
    def render_content():
        # 1. Obtener Datos
        # Nota: Agregamos las listas separadas al retorno de get_all_classes
        today_raw, up_platform, up_preply, history_raw, available_regions, available_students, all_classes_raw = get_all_classes()
        
        # 2. Filtrar Datos (Aplicar filtros a cada lista)
        filtered_today = filter_list(today_raw)
        filtered_platform = filter_list(up_platform)
        filtered_preply = filter_list(up_preply)
        filtered_history = filter_list(history_raw)

        # 3. CÁLCULO DE KPIs
        
        # --- A. Métricas Generales (Todo el historial de la BD) ---
        gen_total = len(all_classes_raw)
        gen_pending = sum(1 for c in all_classes_raw if c.status in ['Pendiente', 'Prueba_Pendiente'])
        gen_completed = sum(1 for c in all_classes_raw if c.status == 'Completada') 
        
        # --- B. Métricas de Hoy ---
        now_str = datetime.now().strftime('%Y-%m-%d')
        # Buscamos clases que sean de HOY en cualquiera de las listas (incluso historial si ya pasaron hoy)
        all_today_candidates = today_raw + [c for c in history_raw if (getattr(c, 'date_prof', None) or c.date) == now_str]
        
        day_total = len(all_today_candidates)
        day_pending = sum(1 for c in all_today_candidates if c.status in ['Pendiente', 'Prueba_Pendiente'])
        day_completed = sum(1 for c in all_today_candidates if c.status == 'Completada')

        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
            
            # HEADER
            with ui.row().classes('w-full justify-between items-center py-4 border-b border-slate-100'):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes('p-2 bg-pink-50 rounded-lg flex items-center justify-center'):
                        ui.icon('local_library', size='md', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Gestión de Clases').classes('text-xl font-bold text-slate-800 tracking-tight')
                        ui.label('Panel de Administración').classes('text-xs text-slate-500 font-medium')

                with ui.row().classes('items-center gap-3'):
                    ui.button('Sincronizar', on_click=run_sync, icon='sync_alt') \
                        .props('flat no-caps').classes('text-slate-700 bg-white border border-slate-200 rounded-full px-5 py-2 text-sm font-semibold shadow-sm')
                    ui.button(icon='refresh', on_click=lambda: (global_cache.invalidate(), refresh_ui())).props('flat round dense').tooltip('Recargar desde la Nube')

            # --- SECCIÓN DE KPIs (TABS) ---
            with ui.card().classes('w-full p-0 rounded-xl bg-white border border-slate-100 shadow-sm overflow-hidden'):
                # Header de Tabs
                with ui.tabs().classes('w-full text-slate-600 bg-slate-50 border-b border-slate-100') as tabs:
                    t_day = ui.tab('Métricas Hoy').classes('flex-1')
                    t_gen = ui.tab('Métricas Generales').classes('flex-1')

                # Paneles
                with ui.tab_panels(tabs, value=t_day).classes('w-full p-4 bg-white'):
                    
                    # PANEL 1: MÉTRICAS DE HOY
                    with ui.tab_panel(t_day).classes('p-0'):
                        with ui.row().classes('w-full gap-4 flex-nowrap'):
                            render_stat_card('Total Hoy', day_total, 'blue')
                            render_stat_card('Pendientes Hoy', day_pending, 'orange')
                            render_stat_card('Completadas Hoy', day_completed, 'green')
                    
                    # PANEL 2: MÉTRICAS GENERALES
                    with ui.tab_panel(t_gen).classes('p-0'):
                        with ui.row().classes('w-full gap-4 flex-nowrap'):
                            render_stat_card('Total Histórico', gen_total, 'indigo')
                            render_stat_card('Total Pendientes', gen_pending, 'orange')
                            render_stat_card('Total Completadas', gen_completed, 'green')

            # --- FILTROS ---
            with ui.card().classes('w-full p-4 rounded-xl bg-white border border-slate-100 shadow-sm mt-2'):
                with ui.row().classes('w-full items-center gap-4 flex-wrap'):
                    ui.icon('filter_list', color='slate-400')
                    
                    # 1. FILTRO DE FECHA (Mejorado)
                    # Usamos 'outlined' y 'dense' para que se vea como una caja, no una línea
                   # --- FILTRO FECHA CORREGIDO ---
                    with ui.input('Fecha').bind_value(filters, 'date').props('outlined dense mask="####-##-##"').classes('w-56') as date_input:
                        
                        # 1. Definimos el menú PRIMERO para evitar errores de referencia
                        with ui.menu().props('no-parent-event') as menu_date:
                            ui.date().bind_value(filters, 'date').on('update:model-value', lambda: (refresh_ui(), menu_date.close()))

                        # 2. Agregamos AMBOS iconos en un solo bloque 'append'
                        with date_input.add_slot('append'):
                            # Icono Calendario
                            ui.icon('event').classes('cursor-pointer text-slate-500 hover:text-indigo-600').on('click', menu_date.open)
                            
                            # Botón X para borrar (Visible solo si hay fecha seleccionada)
                            def clear_date():
                                filters['date'] = None
                                date_input.set_value(None) # Forzamos limpieza visual inmediata
                                refresh_ui()
                                
                            ui.button(icon='cancel', on_click=clear_date) \
                                .props('flat round dense size=xs color=slate') \
                                .bind_visibility_from(filters, 'date')

                    # 2. OTROS FILTROS (Asegurando estilo consistente)
                    
                    stud_opts = ['Todos'] + available_students
                    ui.select(options=stud_opts, value=filters['student'] or 'Todos', label='Estudiante', with_input=True) \
                        .props('outlined dense') \
                        .bind_value(filters, 'student').on('update:model-value', refresh_ui).classes('flex-1 min-w-[200px]')
                    
                    region_opts = ['Todas'] + available_regions
                    ui.select(options=region_opts, value=filters['region'] or 'Todas', label='Región') \
                        .props('outlined dense') \
                        .bind_value(filters, 'region').on('update:model-value', refresh_ui).classes('w-48')
                    
                    time_opts = ['Todos', 'Mañana', 'Tarde', 'Noche']
                    ui.select(options=time_opts, value=filters['time_of_day'] or 'Todos', label='Horario') \
                        .props('outlined dense') \
                        .bind_value(filters, 'time_of_day').on('update:model-value', refresh_ui).classes('w-40')
                

            # --- LISTAS DE CLASES ---
            
            # 1. AGENDA DE HOY
            if filtered_today:
                with ui.column().classes('w-full gap-3 mt-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('today', color='rose', size='sm')
                        ui.label('Agenda de Hoy').classes('text-lg font-bold text-slate-800')
                    for c in filtered_today:
                        render_admin_class_card(c)
            elif not any(filters.values()): 
                ui.label('No hay clases pendientes para hoy.').classes('text-slate-400 italic mt-4')

            ui.separator().classes('bg-slate-200 my-2')

            # 2. PRÓXIMAS SESIONES (CON TABS PLATAFORMA VS PREPLY)
            with ui.card().classes('w-full p-0 rounded-xl bg-white border border-slate-100 shadow-sm'):
                
                # Header Tabs Próximas
                with ui.tabs().classes('w-full text-slate-500 bg-slate-50 border-b border-slate-100').props('active-color=primary indicator-color=primary align=left narrow') as tabs_up:
                    t_plat = ui.tab('Plataforma', icon='school')
                    t_prep = ui.tab('Preply', icon='language')

                with ui.tab_panels(tabs_up, value=t_plat).classes('w-full bg-transparent p-4'):
                    
                    # PANEL PLATAFORMA
                    with ui.tab_panel(t_plat).classes('p-0 gap-3 flex flex-col'):
                        if not filtered_platform:
                             ui.label('No hay clases de Plataforma futuras.').classes('text-slate-400 italic')
                        for c in filtered_platform:
                            render_admin_class_card(c)

                    # PANEL PREPLY
                    with ui.tab_panel(t_prep).classes('p-0 gap-3 flex flex-col'):
                         if not filtered_preply:
                             ui.label('No hay clases de Preply futuras.').classes('text-slate-400 italic')
                         for c in filtered_preply:
                            render_admin_class_card(c)

            # 3. HISTORIAL
            with ui.expansion('Historial', icon='history').classes('w-full bg-slate-50 border border-slate-100 rounded-xl'):
                with ui.column().classes('w-full p-4 gap-3'):
                    if not filtered_history:
                        ui.label('Historial vacío.').classes('text-slate-400 italic')
                    for c in filtered_history:
                        render_admin_class_card(c, is_history=True)

    def refresh_ui():
        render_content.refresh()

    render_content()