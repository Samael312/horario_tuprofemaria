from nicegui import ui, app
from datetime import datetime, timedelta
import logging
import asyncio  # Importamos asyncio para corregir el error del loop
from zoneinfo import ZoneInfo # Para manejo preciso de zonas al reagendar


from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import AsignedClasses, User, ScheduleProf, ScheduleProfEsp, SchedulePref
from components.headerAdmin import create_admin_screen

from components.share_data import days_of_week, PACKAGE_LIMITS 

from components.timezone_converter import convert_student_to_teacher

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Opciones de Estado para el Profesor
STATUS_OPTIONS = {
    'Pendiente': {'color': 'orange', 'icon': 'schedule'},
    'Prueba_Pendiente': {'color': 'purple', 'icon': 'science'}, 
    'Completada': {'color': 'green', 'icon': 'check_circle'},
    'Cancelada': {'color': 'red', 'icon': 'cancel'},
    'No Asistió': {'color': 'grey', 'icon': 'person_off'}
}

# Estados que se consideran "Finalizados" para el historial general
FINALIZED_STATUSES = {'Completada', 'Cancelada', 'No Asistió'}

# Estados que CONSUMEN una clase del paquete (para class_count)
CONSUMED_STATUSES = {'Completada', 'No Asistió', 'Finalizada'}

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

@ui.page('/myclassesAdmin')
def my_classesAdmin():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_admin_screen()

    # 1. LOGICA DE DATOS
    def get_all_classes():
        session = PostgresSession()
        try:
            # Traemos TODAS las clases
            all_classes = session.query(AsignedClasses).all()
            
            # Mapa de TimeZones
            users = session.query(User).all()
            user_tz_map = {u.username: (u.time_zone or 'UTC') for u in users}
            
            now = datetime.now()
            now_date_str = now.strftime('%Y-%m-%d')
            
            today_classes = []
            upcoming_classes = []
            history_classes = []
            
            for c in all_classes:
                # Adjuntar TimeZone
                c.student_tz = user_tz_map.get(c.username, 'UTC')

                # Lógica de Tiempo Profesora
                p_start = c.start_prof_time if getattr(c, 'start_prof_time', None) is not None else c.start_time
                p_date = getattr(c, 'date_prof', None) or c.date
                
                if p_date and p_start is not None:
                    c_full_int = int(p_date.replace('-', '') + str(p_start).zfill(4))
                else:
                    c_full_int = 0 

                current_full_int = int(now.strftime("%Y%m%d%H%M"))

                # Prioridad a la fecha de HOY
                if p_date == now_date_str:
                    if c.status in FINALIZED_STATUSES:
                        history_classes.append(c)
                    else:
                        today_classes.append(c)
                elif c.status in FINALIZED_STATUSES:
                    history_classes.append(c)
                elif c_full_int > current_full_int:
                    upcoming_classes.append(c)
                else:
                    history_classes.append(c)
            
            def sort_key_prof(x):
                d = getattr(x, 'date_prof', None) or x.date or "9999-99-99"
                t = x.start_prof_time if getattr(x, 'start_prof_time', None) is not None else x.start_time or 0
                return (d, t)

            today_classes.sort(key=sort_key_prof)
            upcoming_classes.sort(key=sort_key_prof)
            history_classes.sort(key=sort_key_prof, reverse=True)
            
            return today_classes, upcoming_classes, history_classes
        except Exception as e:
            logger.error(f"Error fetching admin classes: {e}")
            return [], [], []
        finally:
            session.close()

    async def update_status(c_id, new_status):
        session = PostgresSession()
        try:
            cls = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            if cls:
                cls.status = new_status
                
                # --- ACTUALIZACIÓN DE USER ---
                session.flush() 

                user = session.query(User).filter(User.username == cls.username).first()
                if user:
                    # 1. TOTAL CLASSES
                    finalized_count = session.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        AsignedClasses.status.in_(['Completada', 'Cancelada', 'No Asistió', 'Finalizada'])
                    ).count()
                    user.total_classes = finalized_count

                    # 2. CLASS COUNT
                    try:
                        c_date_obj = datetime.strptime(cls.date, '%Y-%m-%d')
                        month_prefix = c_date_obj.strftime('%Y-%m')
                    except:
                        month_prefix = datetime.now().strftime('%Y-%m')

                    month_consumed = session.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        AsignedClasses.date.startswith(month_prefix),
                        AsignedClasses.status.in_(CONSUMED_STATUSES)
                    ).count()

                    pkg_limit = PACKAGE_LIMITS.get(user.package, 0)
                    user.class_count = f"{month_consumed}/{pkg_limit}" if pkg_limit > 0 else f"{month_consumed}"

                    session.add(user)

                session.commit()
                
                # Backup SQLite
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

    def open_reschedule_dialog(c):
        with ui.dialog() as d, ui.card().classes('w-[600px] rounded-xl p-0 overflow-hidden'):
            
            # Header Dialog
            with ui.row().classes('w-full bg-slate-50 p-4 border-b border-slate-100 justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Reagendar Clase').classes('text-lg font-bold text-slate-800')
                    ui.label(f'Alumno: {c.name} {c.surname}').classes('text-xs text-slate-500')
                ui.button(icon='close', on_click=d.close).props('flat round dense color=slate')

            # Content
            with ui.column().classes('w-full p-6 gap-4'):
                
                # 1. Selector de Fecha (Fecha Profesora) y Botón de Búsqueda
                # Usamos la fecha actual de la clase (prof) como default
                default_date = c.date_prof or c.date
                
                # Fila para el Input y el Botón
                with ui.row().classes('w-full items-start gap-4'):
                    
                    # INPUT DE FECHA
                    with ui.input('Fecha (Tu Horario)', value=default_date).props('outlined dense mask="####-##-##"').classes('flex-1') as date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            d_picker = ui.date().bind_value(date_input).props('mask="YYYY-MM-DD"')
                        with date_input.add_slot('append'):
                            ui.icon('event').classes('cursor-pointer text-slate-500 hover:text-slate-700').on('click', menu.open)
                    
                    # BOTÓN DE BÚSQUEDA
                    # Botón más elegante con estilo mejorado
                    search_btn = ui.button('Buscar Disponibilidad', icon='search') \
                        .props('unelevated color=blue-600') \
                        .classes('h-[40px] px-6 rounded-lg shadow-sm hover:shadow-md transition-shadow font-bold tracking-wide')

                # Contenedor de Slots
                slots_container = ui.column().classes('w-full gap-2')
                
                # --- Lógica de Slots ---
                def get_slots_data(date_str, admin_username):
                    session = PostgresSession()
                    slots_data = []
                    try:
                        # 0. Normalización de fecha para robustez
                        if not date_str: return []
                        
                        try:
                            # Reemplazar barras por guiones para estandarizar
                            d_clean = date_str.replace('/', '-')
                            
                            # Intentar ISO (YYYY-MM-DD)
                            dt = datetime.strptime(d_clean, '%Y-%m-%d')
                        except ValueError:
                            try:
                                # Intentar Formato Europeo/Latino (DD-MM-YYYY)
                                dt = datetime.strptime(d_clean, '%d-%m-%Y')
                            except ValueError:
                                logger.error(f"Formato de fecha inválido recibido: {date_str}")
                                return []
                        
                        # Fecha estandarizada para consultas DB
                        query_date = dt.strftime('%Y-%m-%d')
                        day_name = days_of_week[dt.weekday()]
                        
                        # 1. Disponibilidad Profesora (Teacher Time) - Usando query_date
                        rules = session.query(ScheduleProfEsp).filter_by(date=query_date).all()
                        if not rules:
                            rules = session.query(ScheduleProf).filter_by(days=day_name).all()
                        
                        avail_ranges = []
                        for r in rules:
                            status = str(r.avai if hasattr(r, 'avai') else r.availability)
                            if status in POSITIVE_STATUS:
                                avail_ranges.append((r.start_time, r.end_time))
                        
                        # 2. Ocupado Profesora (Busy Teacher Time) - Usando query_date
                        busy = session.query(AsignedClasses).filter(
                            AsignedClasses.date_prof == query_date,
                            AsignedClasses.status != 'Cancelled',
                            AsignedClasses.id != c.id # Excluir la clase actual para permitir moverla al mismo día
                        ).all()
                        busy_ranges = [(b.start_prof_time, b.end_prof_time) for b in busy if b.start_prof_time]

                        # 3. Preferencias Alumno
                        user = session.query(User).filter(User.username == c.username).first()
                        student_tz_str = user.time_zone if user and user.time_zone else 'UTC'
                        
                        # Obtener Zona de la Profesora (Admin)
                        admin_user = session.query(User).filter(User.username == admin_username).first()
                        teacher_tz_str = admin_user.time_zone if admin_user and admin_user.time_zone else 'Europe/Madrid'

                        # Generar Slots cada 30 min (o duración clase)
                        step = 60
                        duration = int(c.duration) if c.duration else 60
                        
                        # --- CÁLCULO DE SLOTS CORREGIDO (USANDO MINUTOS) ---
                        
                        # Helpers para conversión
                        def to_minutes(hhmm):
                            return (hhmm // 100) * 60 + (hhmm % 100)
                        
                        def to_hhmm_int(minutes):
                            h = minutes // 60
                            m = minutes % 60
                            return (h * 100) + m

                        # Convertir ocupado a minutos
                        busy_ranges_min = [(to_minutes(bs), to_minutes(be)) for bs, be in busy_ranges]

                        valid_slots = []
                        for start, end in avail_ranges:
                            # Iterar en minutos para evitar horas inválidas (ej 16:60)
                            curr_m = to_minutes(start)
                            end_m = to_minutes(end)
                            
                            while curr_m + duration <= end_m:
                                # Check busy (en minutos)
                                is_busy = False
                                s_end_m = curr_m + duration
                                
                                for b_s_m, b_e_m in busy_ranges_min:
                                    if (curr_m < b_e_m) and (s_end_m > b_s_m):
                                        is_busy = True
                                        break
                                
                                if not is_busy:
                                    # Convertir de nuevo a HHMM int para el resto de la lógica
                                    valid_slots.append(to_hhmm_int(curr_m))
                                
                                curr_m += step
                        
                        # Procesar para frontend
                        unique_slots = sorted(list(set(valid_slots)))
                        
                        for slot in unique_slots:
                            # Teacher Info
                            t_h, t_m = slot // 100, slot % 100
                            t_str = f"{str(t_h).zfill(2)}:{str(t_m).zfill(2)}"
                            
                            # Student Info (Cálculo)
                            try:
                                prof_tz = ZoneInfo(teacher_tz_str) # Usamos zona de DB
                                stud_tz = ZoneInfo(student_tz_str)
                                
                                dt_prof = datetime.strptime(f"{query_date} {t_str}", "%Y-%m-%d %H:%M")
                                dt_prof = dt_prof.replace(tzinfo=prof_tz)
                                
                                dt_stud = dt_prof.astimezone(stud_tz)
                                
                                s_time_str = dt_stud.strftime("%H:%M")
                                s_date_str = dt_stud.strftime("%Y-%m-%d")
                                s_time_int = int(dt_stud.strftime("%H%M"))
                                s_weekday = days_of_week[dt_stud.weekday()]
                                
                                # Check Prefs (Student Time)
                                prefs = session.query(SchedulePref).filter(
                                    SchedulePref.username == c.username,
                                    SchedulePref.days == s_weekday
                                ).all()
                                is_preferred = False
                                for p in prefs:
                                    if p.start_time <= s_time_int < p.end_time:
                                        is_preferred = True
                                        break
                                
                                slots_data.append({
                                    't_time_int': slot,
                                    't_time_str': t_str,
                                    's_time_str': s_time_str,
                                    's_date_str': s_date_str,
                                    's_time_int': s_time_int,
                                    'is_preferred': is_preferred
                                })
                                
                            except Exception as ex:
                                logger.error(f"Timezone error: {ex} (Slot: {slot})")
                                # Fallback sin conversión
                                slots_data.append({
                                    't_time_int': slot,
                                    't_time_str': t_str,
                                    's_time_str': "Err",
                                    's_date_str': query_date,
                                    's_time_int': slot,
                                    'is_preferred': False
                                })

                    except Exception as e:
                        logger.error(f"Error getting slots: {e}")
                    finally:
                        session.close()
                    return slots_data

                async def render_slots():
                    slots_container.clear()
                    if not date_input.value: return
                    
                    # Obtener username del admin logueado para sacar su zona horaria
                    current_admin = app.storage.user.get("username")

                    with slots_container:
                        ui.spinner('dots').classes('self-center text-slate-400')
                        
                        # CORRECCIÓN: Usar asyncio.get_running_loop() en lugar de app.loop
                        loop = asyncio.get_running_loop()
                        data = await loop.run_in_executor(None, get_slots_data, date_input.value, current_admin)
                        
                        slots_container.clear()

                        if not data:
                            ui.label('No hay horarios disponibles para esta fecha.').classes('text-sm text-slate-400 italic')
                            return

                        with ui.grid().classes('grid-cols-4 gap-2 w-full max-h-60 overflow-y-auto pr-2'):
                            for slot in data:
                                # Colores
                                if slot['is_preferred']:
                                    btn_color = 'purple-600'
                                    btn_bg = 'bg-purple-600'
                                    text_col = 'white'
                                else:
                                    btn_color = 'slate-200'
                                    btn_bg = 'bg-slate-100'
                                    text_col = 'slate-700'

                                # Botón Slot
                                btn = ui.button(slot['t_time_str'], on_click=lambda s=slot: confirm_reschedule(s)) \
                                    .props(f'unelevated color=None') \
                                    .classes(f'{btn_bg} text-{text_col} font-bold rounded-lg hover:bg-slate-300 transition-colors')
                                
                                # Tooltip con hora alumno
                                with btn:
                                    ui.tooltip(f"Alumno: {slot['s_time_str']} ({slot['s_date_str']})").classes('bg-slate-800 text-xs')

                async def confirm_reschedule(slot_data):
                    # Pasamos todos los datos calculados para evitar recálculos y errores
                    await reschedule_class(
                        c.id, 
                        date_input.value, # Teacher Date
                        slot_data['t_time_int'], # Teacher Time
                        slot_data['s_date_str'], # Student Date
                        slot_data['s_time_int'], # Student Time
                        d
                    )

                # Init & Event Listeners
                
                # Botón Buscar
                search_btn.on('click', render_slots)
                
                # Date Picker: Solo cerrar menú, NO buscar automáticamente
                d_picker.on('change', menu.close)

                # Carga Inicial: OPCIONAL. Comenta la siguiente línea si quieres que la lista empiece vacía.
                # render_slots() 

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
        
        card_opacity = "opacity-60 hover:opacity-100" if is_history or current_status == 'Cancelada' else "opacity-100"
        border_l = f"border-{status_config['color']}-500" if not is_history else "border-slate-300"

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
                    full_name = f"{c.name} {c.surname}"
                    ui.label(full_name).classes('text-lg font-bold text-slate-800 leading-tight')
                    
                    # --- BOTÓN REAGENDAR ---
                    # Solo habilitado si no es historial
                    if not is_history:
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
        today, upcoming, history = get_all_classes()
        
        today_pending = sum(1 for c in today if 'Pendiente' in c.status)
        today_done = sum(1 for c in today if c.status == 'Completada')

        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
            
            # HEADER
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('book', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Gestión de Clases').classes('text-2xl font-bold text-slate-800')
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('public', size='xs', color='rose')
                            ui.label('Horarios convertidos a tu zona local').classes('text-sm text-rose-500 font-medium')
                    
                ui.button(icon='refresh', on_click=refresh_ui).props('flat round color=slate')

            # STATS
            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('Clases Hoy', len(today), 'blue')
                render_stat_card('Pendientes Hoy', today_pending, 'orange')
                render_stat_card('Completadas Hoy', today_done, 'green')

            # SECCIONES
            if today:
                with ui.column().classes('w-full gap-3 mt-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('today', color='rose', size='sm')
                        ui.label('Agenda de Hoy').classes('text-lg font-bold text-slate-800')
                    for c in today:
                        render_admin_class_card(c)
            elif not upcoming:
                ui.label('No hay clases pendientes para hoy.').classes('text-slate-400 italic mt-4')

            ui.separator().classes('bg-slate-200 my-2')

            with ui.expansion('Próximas Sesiones', icon='calendar_month', value=True).classes('w-full bg-white border border-slate-100 rounded-xl shadow-sm'):
                with ui.column().classes('w-full p-4 gap-3'):
                    if not upcoming:
                        ui.label('No hay clases futuras pendientes.').classes('text-slate-400 italic')
                    for c in upcoming:
                        render_admin_class_card(c)

            with ui.expansion('Historial', icon='history').classes('w-full bg-slate-50 border border-slate-100 rounded-xl'):
                with ui.column().classes('w-full p-4 gap-3'):
                    if not history:
                        ui.label('Historial vacío.').classes('text-slate-400 italic')
                    for c in history:
                        render_admin_class_card(c, is_history=True)

    def refresh_ui():
        render_content.refresh()

    render_content()