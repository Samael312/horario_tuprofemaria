from nicegui import ui, app
from datetime import datetime, timedelta
import logging
import asyncio

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import User, ScheduleProf, ScheduleProfEsp, AsignedClasses, SchedulePref
from components.header import create_main_screen
# --- IMPORTS SHARE DATA & ALCABALA ---
from components.share_data import days_of_week, PACKAGE_LIMITS, t_val
# -------------------------------------
from components.timezone_converter import convert_student_to_teacher, get_slots_in_student_tz

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

# =====================================================
# 1. TRADUCCIONES (ScheduleMaker)
# =====================================================
SM_TRANSLATIONS = {
    'es': {
        # Títulos
        'title_trial': 'Selecciona tu clase de prueba',
        'title_regular': 'Reservar Horario',
        'my_sessions': 'Mis Próximas Sesiones',
        # Stats Widget
        'plan_current': 'Plan Actual (Mes)',
        'no_plan': 'Sin Plan',
        'trajectory': 'Trayectoria',
        'total_booked': 'Agendadas en total',
        'classes_label': 'Clases',
        # Mensajes de Estado
        'loading_slots': 'Buscando horarios disponibles...',
        'date_passed': 'Esta fecha ya pasó',
        'no_availability': 'No hay disponibilidad',
        'pref_slots': 'Horarios preferenciales (Morado)',
        'no_classes_scheduled': 'No tienes clases agendadas.',
        # Clases Lista
        'class_trial': 'Clase de Prueba',
        'class_regular': 'Clase Regular',
        'general_english': 'Inglés General',
        # Dialogos
        'confirm_title': 'Confirmar',
        'date_label': 'FECHA',
        'duration_label': 'Duración',
        'btn_cancel': 'Cancelar',
        'btn_book': 'Reservar',
        'btn_yes_cancel': 'Sí, Cancelar',
        'dialog_cancel_title': '¿Cancelar clase?',
        # Notificaciones
        'limit_reached': 'Límite mensual alcanzado ({used}/{limit})',
        'booked_ok': 'Clase agendada correctamente',
        'cancelled_ok': 'Clase cancelada',
        'error_generic': 'Error: {}',
        # Botones / UI
        'toggle_30': '30 min',
        'toggle_60': '1 Hora'
    },
    'en': {
        # Titles
        'title_trial': 'Select your trial class',
        'title_regular': 'Book Schedule',
        'my_sessions': 'My Upcoming Sessions',
        # Stats Widget
        'plan_current': 'Current Plan (Month)',
        'no_plan': 'No Plan',
        'trajectory': 'Track Record',
        'total_booked': 'Total booked',
        'classes_label': 'Classes',
        # Status Messages
        'loading_slots': 'Searching available slots...',
        'date_passed': 'This date has passed',
        'no_availability': 'No availability',
        'pref_slots': 'Preferred slots (Purple)',
        'no_classes_scheduled': 'You have no scheduled classes.',
        # Classes List
        'class_trial': 'Trial Class',
        'class_regular': 'Regular Class',
        'general_english': 'General English',
        # Dialogs
        'confirm_title': 'Confirm',
        'date_label': 'DATE',
        'duration_label': 'Duration',
        'btn_cancel': 'Cancel',
        'btn_book': 'Book',
        'btn_yes_cancel': 'Yes, Cancel',
        'dialog_cancel_title': 'Cancel class?',
        # Notifications
        'limit_reached': 'Monthly limit reached ({used}/{limit})',
        'booked_ok': 'Class booked successfully',
        'cancelled_ok': 'Class cancelled',
        'error_generic': 'Error: {}',
        # UI
        'toggle_30': '30 min',
        'toggle_60': '1 Hour'
    }
}

@ui.page('/ScheduleMaker')
def scheduleMaker():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # 2. HELPER: CONTADOR HISTÓRICO
    def get_all_time_classes():
        session = PostgresSession()
        try:
            count = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status != 'Cancelled'
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error contando historial: {e}")
            return 0
        finally:
            session.close()

    # Inicializamos estado
    lifetime_count = get_all_time_classes()
    is_trial = (lifetime_count == 0)

    # 3. ESTADO REACTIVO
    state = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'loading': False,
        'is_trial': is_trial,
        'duration': 30 if is_trial else 60
    }

    # =================================================================
    # LÓGICA DE NEGOCIO (MODEL)
    # =================================================================

    def get_user_timezone():
        session = PostgresSession()
        tz = "UTC"
        try:
            u = session.query(User).filter(User.username == username).first()
            if u and u.time_zone:
                tz = u.time_zone
        finally:
            session.close()
        return tz

    def get_time_icon(minutes):
        if minutes < 720: return 'wb_sunny'
        elif minutes < 1020: return 'wb_twilight'
        else: return 'nights_stay'

    def get_user_preferred_ranges(user_id, date_str):
        session = PostgresSession()
        ranges = []
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            # USO INTERNO: days_of_week siempre devuelve español (Lunes, etc) para consultar DB
            day_name = days_of_week[dt.weekday()] 
            prefs = session.query(SchedulePref).filter(
                SchedulePref.username == user_id,
                SchedulePref.days == day_name
            ).all()
            for p in prefs:
                if p.start_time is not None and p.end_time is not None:
                    ranges.append((p.start_time, p.end_time))
        except Exception as e:
            logger.error(f"Error prefs: {e}")
        finally:
            session.close()
        return ranges

    def is_in_user_range(slot_int, ranges):
        for start, end in ranges:
            if start <= slot_int < end:
                return True
        return False

    def get_current_package_usage(session, user_id):
        user = session.query(User).filter(User.username == user_id).first()
        if not user: return "None", 0, 0
        pkg_name = user.package or "None"
        limit = PACKAGE_LIMITS.get(pkg_name, 0)
        now = datetime.now()
        start_date_str = f"{now.year}-{str(now.month).zfill(2)}"
        current_usage = session.query(AsignedClasses).filter(
            AsignedClasses.username == user_id,
            AsignedClasses.status != 'Cancelled',
            AsignedClasses.date.startswith(start_date_str)
        ).count()
        return pkg_name, limit, current_usage

    def get_available_slots(date_str, duration_mins):
        session = PostgresSession()
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = days_of_week[dt.weekday()] # Interno Español
            
            rules = session.query(ScheduleProfEsp).filter_by(date=date_str).all()
            if not rules:
                rules = session.query(ScheduleProf).filter_by(days=day_name).all()

            available_ranges_prof = []
            for r in rules:
                status_bd = str(r.avai if hasattr(r, 'avai') else r.availability)
                # POSITIVE_STATUS puede contener inglés y español, así que es seguro
                if status_bd in POSITIVE_STATUS:
                    available_ranges_prof.append((r.start_time, r.end_time))
            
            if not available_ranges_prof: return [] 

            busy_classes = session.query(AsignedClasses).filter(
                AsignedClasses.date == date_str, 
                AsignedClasses.status != 'Cancelled'
            ).all()
            
            blocked_intervals_prof = []
            for c in busy_classes:
                sp = c.start_prof_time if c.start_prof_time is not None else c.start_time
                ep = c.end_prof_time if c.end_prof_time is not None else c.end_time
                blocked_intervals_prof.append((sp, ep))

            def to_min(t): return int(str(t).zfill(4)[:2]) * 60 + int(str(t).zfill(4)[2:])
            def to_hhmm(mins): return int(f"{mins // 60}{str(mins % 60).zfill(2)}")

            prof_slots = []
            for r_start, r_end in available_ranges_prof:
                curr_min = to_min(r_start)
                end_min = to_min(r_end)
                
                while curr_min + duration_mins <= end_min:
                    slot_start = curr_min
                    slot_end = curr_min + duration_mins
                    
                    is_blocked = False
                    for b_start, b_end in blocked_intervals_prof:
                        bs, be = to_min(b_start), to_min(b_end)
                        if (slot_start < be) and (slot_end > bs):
                            is_blocked = True; break
                    
                    if not is_blocked: 
                        prof_slots.append(to_hhmm(slot_start))
                    
                    curr_min += duration_mins 
            
            student_tz = get_user_timezone()
            final_student_slots = get_slots_in_student_tz(prof_slots, date_str, student_tz)
            
            return sorted(list(set(final_student_slots)))

        except Exception as e:
            logger.error(f"Error slots: {e}")
            return []
        finally:
            session.close()

    async def book_class(slot_int, t):
        session = PostgresSession()
        success = False 
        try:
            pkg, limit, used = get_current_package_usage(session, username)
            
            if limit > 0 and used >= limit:
                # Usamos traduccion con formato
                msg = t['limit_reached'].format(used=used, limit=limit)
                ui.notify(msg, type='negative')
                return
            
            total_lifetime_used = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status != 'Cancelled'
            ).count()
            new_total_classes_seq = total_lifetime_used + 1

            user_db = session.query(User).filter_by(username=username).first()
            student_tz = user_db.time_zone or "UTC"
            duration = state['duration']
            
            s_str = str(slot_int).zfill(4)
            sh, sm = int(s_str[:2]), int(s_str[2:])
            start_dt_obj = datetime(2000, 1, 1, sh, sm)
            end_dt = start_dt_obj + timedelta(minutes=duration)
            end_int = int(end_dt.strftime("%H%M"))
            
            dt_obj = datetime.strptime(state['date'], '%Y-%m-%d')
            day_name = days_of_week[dt_obj.weekday()] # Guardamos en Español (Interno)

            sp_time, ep_time, prof_date = convert_student_to_teacher(
                state['date'], slot_int, duration, student_tz
            )

            status_to_save = "Prueba_Pendiente" if state['is_trial'] else "Pendiente" # Interno
            current_class_num = used + 1
            count_label = f"{current_class_num}/{limit}" if limit > 0 else f"{current_class_num}"

            new_class = AsignedClasses(
                username=username, name=user_db.name, surname=user_db.surname,
                date=state['date'], days=day_name, 
                start_time=slot_int,
                end_time=end_int, 
                start_prof_time=sp_time,
                end_prof_time=ep_time,
                date_prof=prof_date,
                duration=str(duration), package=pkg, 
                status=status_to_save,
                class_count=count_label,
                total_classes=new_total_classes_seq
            )
            session.add(new_class)
            session.commit()
            
            try:
                bk_sess = BackupSession()
                bk_sess.add(AsignedClasses(
                    username=username, name=user_db.name, surname=user_db.surname,
                    date=state['date'], days=day_name, start_time=slot_int,
                    end_time=end_int, duration=str(duration), package=pkg, 
                    status=status_to_save,
                    start_prof_time=sp_time, end_prof_time=ep_time, date_prof=prof_date,
                    class_count=count_label,
                    total_classes=new_total_classes_seq
                ))
                bk_sess.commit(); bk_sess.close()
            except: pass

            ui.notify(t['booked_ok'], type='positive', icon='check')
            success = True
            
        except Exception as e:
            ui.notify(t['error_generic'].format(e), type='negative')
            success = False
        finally:
            session.close()

        if success:
            await asyncio.sleep(0.1) 
            try:
                # Recargar UI
                render_page_content.refresh()
            except Exception as e:
                logger.error(f"Error actualizando dashboard: {e}")

    # =================================================================
    # COMPONENTES DE INTERFAZ (VIEW) - Ahora dentro de refreshable global
    # =================================================================

    # Wrapper principal refrescable para todo el contenido de la página
    @ui.refreshable
    def render_page_content():
        lang = app.storage.user.get('lang', 'es')
        t = SM_TRANSLATIONS[lang]

        # Funciones locales que necesitan 't' y 'lang'
        def render_booking_dialog(slot):
            t_str = str(slot).zfill(4)
            fmt_time = f"{t_str[:2]}:{t_str[2:]}"
            
            # Formateo de fecha ALCABALA (Fecha objeto -> Nombre día traducido)
            dt_obj = datetime.strptime(state['date'], '%Y-%m-%d')
            day_internal = days_of_week[dt_obj.weekday()] # Lunes
            day_translated = t_val(day_internal, lang)    # Monday
            date_nice = f"{day_translated}, {dt_obj.day} {dt_obj.strftime('%B')}" # Nota: Mes sale en inglés por defecto python, para full español necesitarías mapa de meses

            duration = state['duration']
            tipo_clase = t['class_trial'] if state['is_trial'] else t['class_regular']

            with ui.dialog() as d, ui.card().classes('w-80 p-0 rounded-2xl overflow-hidden shadow-xl'):
                with ui.column().classes('w-full bg-slate-800 p-6 items-center'):
                    ui.icon('calendar_today', color='white', size='lg')
                    ui.label(f"{t['confirm_title']} {tipo_clase}").classes('text-white font-bold mt-2 text-center')
                
                with ui.column().classes('p-6 w-full items-center bg-white'):
                    ui.label(date_nice).classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                    ui.label(fmt_time).classes('text-4xl font-white text-slate-800 my-2')
                    ui.label(f"{t['duration_label']}: {duration} min").classes('text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full')

                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 gap-2'):
                    ui.button(t['btn_cancel'], on_click=d.close).props('unelevated color=red').classes('flex-1')
                    confirm_btn = ui.button(t['btn_book']).props('unelevated color=green').classes('flex-1')
                    
                    async def do_book():
                        confirm_btn.props('loading')
                        try:
                            await book_class(slot, t)
                            d.close()
                        except Exception as e:
                            confirm_btn.props(remove='loading')
                            ui.notify(str(e), type='negative')
                    confirm_btn.on('click', do_book)
            d.open()

        def delete_class_dialog(c_obj):
            with ui.dialog() as d, ui.card().classes('rounded-xl'):
                ui.label(t['dialog_cancel_title']).classes('font-bold text-lg')
                ui.label(f"{c_obj.date} | {c_obj.start_time} hrs").classes('text-sm text-slate-500')
                with ui.row().classes('w-full justify-end mt-4 gap-2'):
                    ui.button(t['no'], on_click=d.close).props('flat text-color=slate') # Usa 'No' del share_data si está disponible o global, aquí hardcodeamos 'No' simple
                    del_btn = ui.button(t['btn_yes_cancel']).props('unelevated color=red')
                    async def do_del():
                        del_btn.props('loading')
                        sess = PostgresSession()
                        try:
                            sess.query(AsignedClasses).filter(AsignedClasses.id == c_obj.id).delete()
                            sess.commit()
                            ui.notify(t['cancelled_ok'], type='info')
                            render_page_content.refresh() # Recargar todo
                            d.close()
                        except: pass
                        finally: sess.close()
                    del_btn.on('click', do_del)
            d.open()

        # SUB-RENDER: Estadísticas
        def render_stats_widget():
            session = PostgresSession()
            pkg, limit, used_curr = get_current_package_usage(session, username)
            
            # ALCABALA: Traducir el nombre del paquete al mostrarlo
            pkg_display = t_val(pkg, lang) if pkg != "None" else t['no_plan']

            total_lifetime = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status != 'Cancelled'
            ).count()
            
            session.close()
            
            percent = min(used_curr/limit, 1.0) if limit > 0 else 0
            
            with ui.card().classes('w-full p-5 rounded-2xl bg-white shadow-sm border border-slate-100 gap-4'):
                with ui.column().classes('w-full gap-2'):
                    ui.label(t['plan_current']).classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                    with ui.row().classes('items-center gap-4 w-full'):
                        with ui.circular_progress(value=percent, show_value=False, color='rose', size='50px').props('thickness=0.2 track-color=grey-2'):
                            ui.icon('school', color='rose', size='xs')
                        with ui.column().classes('gap-0 flex-1'):
                            ui.label(pkg_display).classes('font-bold text-slate-800 text-lg leading-tight')
                            ui.label(f"{used_curr} / {limit}").classes('text-xs text-slate-500')

                ui.separator()

                with ui.column().classes('w-full gap-1'):
                    ui.label(t['trajectory']).classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                    with ui.row().classes('items-center gap-3 mt-1'):
                        ui.icon('emoji_events', color='amber-500', size='sm')
                        with ui.column().classes('gap-0'):
                            ui.label(f"{total_lifetime} {t['classes_label']}").classes('font-bold text-slate-700')
                            ui.label(t['total_booked']).classes('text-[10px] text-slate-400')

        # SUB-RENDER: Lista de Clases
        def render_my_classes():
            session = PostgresSession()
            now = datetime.now()
            now_int = int(now.strftime("%Y%m%d%H%M"))
            
            # Lógica de finalización automática (igual que antes)
            pending_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status.in_(['Pendiente', 'Prueba_Pendiente'])
            ).all()
            updates_made = False
            for c in pending_classes:
                class_dt_int = int(c.date.replace('-', '') + str(c.start_time).zfill(4))
                if class_dt_int < now_int:
                    c.status = 'Finalizada'
                    updates_made = True
            if updates_made: session.commit()

            classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username, 
                AsignedClasses.status.in_(['Pendiente', 'Prueba_Pendiente'])
            ).all()
            
            classes.sort(key=lambda x: (x.date, x.start_time))
            session.close()

            if not classes:
                with ui.column().classes('w-full items-center py-8 text-slate-400 italic'):
                    ui.label(t['no_classes_scheduled'])
                return

            with ui.column().classes('w-full gap-3'):
                for c in classes:
                    dt = datetime.strptime(c.date, '%Y-%m-%d')
                    t_str = str(c.start_time).zfill(4)
                    fmt = f"{t_str[:2]}:{t_str[2:]}"
                    dur_text = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
                    
                    # ALCABALA: Traducir nombre del día
                    day_display = t_val(days_of_week[dt.weekday()], lang)

                    with ui.row().classes('w-full bg-rose border-l-4 border-rose-500 shadow-sm rounded-r-lg p-3 justify-between items-center group transition-all hover:shadow-md'):
                        with ui.row().classes('items-center gap-4'):
                            with ui.column().classes('items-center leading-none px-2'):
                                ui.label(dt.strftime('%d')).classes('text-xl font-white text-slate-700')
                                # Mes corto. Lo dejamos en inglés por defecto o requeriría mapa extra.
                                ui.label(dt.strftime('%b')).classes('text-[10px] font-bold uppercase text-slate-400')
                            
                            with ui.column().classes('gap-0'):
                                with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                                    ui.label(f"{day_display} - {fmt}").classes('font-bold text-slate-800 text-sm')
                                    
                                    if c.status == 'Prueba_Pendiente':
                                        ui.label(t['class_trial']).classes('mt-1 text-[10px] font-bold text-purple-600 uppercase bg-purple-100 px-2 py-0.5 rounded-full')   
                                    else:
                                        ui.label(t['class_regular']).classes('mt-1 text-[10px] font-bold text-rose-600 uppercase bg-rose-100 px-2 py-0.5 rounded-full')
                                    
                                    if getattr(c, 'class_count', None):
                                        # class_count ya viene formateado "1/4", no necesita traducción
                                        ui.label(f"{c.class_count}").classes('text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100')

                                ui.label(f"{t['general_english']} ({dur_text})").classes('text-xs text-slate-500')
                        
                        ui.button(icon='close', on_click=lambda x=c: delete_class_dialog(x)).props('flat round dense color=slate size=sm').classes('opacity-0 group-hover:opacity-100 transition-opacity')

        # SUB-RENDER: Grilla de Horarios
        def render_slots_area():
            if state.get('loading', False):
                with ui.column().classes('w-full items-center justify-center py-12'):
                    ui.spinner('dots', size='lg', color='rose')
                    ui.label(t['loading_slots']).classes('text-slate-400 text-sm animate-pulse')
                return

            try:
                sel_dt = datetime.strptime(state['date'], '%Y-%m-%d')
                now = datetime.now()
                current_hhmm = int(now.strftime("%H%M"))
                is_today = (sel_dt.date() == now.date())

                if sel_dt.date() < now.date():
                    with ui.column().classes('w-full items-center py-12 opacity-60'):
                        ui.icon('history', size='3xl', color='slate-300')
                        ui.label(t['date_passed']).classes('text-slate-400 font-medium mt-2')
                    return
            except: return

            current_duration = state['duration']
            all_slots = get_available_slots(state['date'], current_duration)
            pref_ranges = get_user_preferred_ranges(username, state['date'])
            
            if not all_slots:
                with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                    ui.icon('event_busy', size='4xl', color='slate-300')
                    ui.label(t['no_availability']).classes('text-slate-500 font-medium mt-3')
                return

            with ui.column().classes('w-full gap-4'):
                has_prefs = any(is_in_user_range(s, pref_ranges) for s in all_slots)
                if has_prefs:
                    with ui.row().classes('items-center gap-2 text-xs text-purple-700 bg-purple-50 px-3 py-1.5 rounded-lg self-start border border-purple-100'):
                        ui.icon('star', size='xs', color='purple-700')
                        ui.label(t['pref_slots'])

                with ui.grid().classes('w-full grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3'):
                    for slot in all_slots:
                        t_str = str(slot).zfill(4)
                        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
                        is_preferred = is_in_user_range(slot, pref_ranges)
                        time_icon = get_time_icon(slot)
                        is_past_hour = is_today and (slot < current_hhmm)

                        if is_past_hour:
                            btn_classes = "bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed"
                            btn_props = "disabled flat color=grey"
                            click_handler = None
                        else:
                            click_handler = lambda s=slot: render_booking_dialog(s)
                            btn_props = "unelevated color=None"
                            if is_preferred:
                                btn_classes = "bg-purple-600 hover:bg-purple-700 text-white border-purple-800"
                            else:
                                btn_classes = "bg-rose-600 hover:bg-rose-700 text-white border-rose-800"

                        btn = ui.button(on_click=click_handler)
                        btn.props(btn_props).classes(
                            f"{btn_classes} shadow-md border-b-4 rounded-xl py-3 px-0 "
                            "transition-all active:border-b-0 active:translate-y-1 h-auto flex flex-col gap-1"
                        )
                        with btn:
                            ui.icon(time_icon, size='xs').classes('opacity-90')
                            ui.label(fmt_time).classes('font-bold text-sm tracking-wide')

        # SUB-RENDER: Header de Control
        def render_header_area():
            if state['is_trial']:
                main_title = t['title_trial']
                sub_color = "text-purple-600"
            else:
                main_title = t['title_regular']
                sub_color = "text-rose-500"
            
            async def on_duration_change(e):
                state['loading'] = True
                render_page_content.refresh() # Refrescar todo
                await asyncio.sleep(0.2)
                state['loading'] = False
                render_page_content.refresh()

            # ALCABALA FECHA HEADER
            dt_obj_h = datetime.strptime(state['date'], '%Y-%m-%d')
            day_trans = t_val(days_of_week[dt_obj_h.weekday()], lang)
            date_display = f"{day_trans}, {dt_obj_h.day} {dt_obj_h.strftime('%B')}"

            with ui.row().classes('items-center justify-between w-full'):
                with ui.column().classes('gap-0'):
                    with ui.row().classes('w-full items-center justify-between mb-2 relative'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('book', size='lg', color='pink-600')
                            with ui.column().classes('gap-0'):
                                ui.label(main_title).classes('text-2xl font-bold text-slate-800')
                                ui.label(date_display).classes(f'{sub_color} font-medium')
                
                with ui.row().classes('items-center gap-4'):
                    if not state['is_trial']:
                        # Toggle traducido
                        toggle_opts = {30: t['toggle_30'], 60: t['toggle_60']}
                        ui.toggle(toggle_opts, value=60).bind_value(state, 'duration') \
                            .on('update:model-value', on_duration_change) \
                            .props('no-caps push color=white text-color=rose-600 toggle-color=rose-600 toggle-text-color=white')

                    refresh_btn = ui.button(icon='refresh').props('flat round color=slate')
                    async def do_refresh():
                        refresh_btn.props('loading')
                        # Recalcular estado trial/regular
                        lifetime_count = get_all_time_classes()
                        state['is_trial'] = (lifetime_count == 0)
                        if state['is_trial']: state['duration'] = 30
                        else: state['duration'] = 60
                        
                        render_page_content.refresh()
                        await asyncio.sleep(0.5)
                        refresh_btn.props(remove='loading')
                    refresh_btn.on('click', do_refresh)

        # SUB-RENDER: Sidebar (Calendario + Stats)
        def render_sidebar():
            async def on_date_change_handler(e):
                state['loading'] = True
                render_page_content.refresh()
                await asyncio.sleep(0.1)
                state['loading'] = False
                render_page_content.refresh()

            with ui.column().classes('w-full gap-6'):
                with ui.card().classes('w-full p-4 rounded-2xl shadow-sm border border-slate-100 bg-white'):
                    ui.date(value=state['date']) \
                        .bind_value(state, 'date') \
                        .on('update:model-value', on_date_change_handler) \
                        .props('flat color=rose class="w-full"')
                render_stats_widget()

        # --- ENSAMBLAJE FINAL DEL CONTENIDO ---
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-12 gap-8 items-start'):
            with ui.column().classes('lg:col-span-4 w-full order-2 lg:order-1'):
                render_sidebar()
            with ui.column().classes('lg:col-span-8 w-full order-1 lg:order-2'):
                with ui.column().classes('w-full gap-8'):
                    render_header_area()
                    render_slots_area()
                    ui.separator().classes('my-2 bg-slate-200')
                    with ui.column().classes('w-full gap-4'):
                        ui.label(t['my_sessions']).classes('text-lg font-bold text-slate-800')
                        render_my_classes()

    # Iniciar Header con callback
    create_main_screen(page_refresh_callback=render_page_content.refresh)
    # Renderizar cuerpo
    render_page_content()