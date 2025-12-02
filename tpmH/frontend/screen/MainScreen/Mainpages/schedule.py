from nicegui import ui, app
from datetime import datetime, timedelta
import logging

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import User, ScheduleProf, ScheduleProfEsp, AsignedClasses, SchedulePref
from components.header import create_main_screen
from components.share_data import days_of_week, PACKAGE_LIMITS

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

@ui.page('/ScheduleMaker')
def scheduleMaker():
    # Estilos globales: Fondo gris muy suave
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_main_screen()
    
    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # 2. ESTADO REACTIVO
    state = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'loading': False
    }

    # =================================================================
    # LÓGICA DE NEGOCIO (MODEL)
    # =================================================================

    def get_time_icon(minutes):
        """Devuelve un icono basado en la hora del día"""
        if minutes < 720: return 'wb_sunny'      # < 12:00
        elif minutes < 1020: return 'wb_twilight' # < 17:00
        else: return 'nights_stay'               # > 17:00

    def get_user_preferred_ranges(user_id, date_str):
        session = PostgresSession()
        ranges = []
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
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

    def get_user_usage(session, user_id):
        user = session.query(User).filter(User.username == user_id).first()
        if not user: return "Sin Plan", 0, 0
        pkg_name = user.package or "None"
        limit = PACKAGE_LIMITS.get(pkg_name, 0)
        now = datetime.now()
        start_date_str = f"{now.year}-{str(now.month).zfill(2)}"
        count = session.query(AsignedClasses).filter(
            AsignedClasses.username == user_id,
            AsignedClasses.status != 'Cancelled',
            AsignedClasses.date.startswith(start_date_str)
        ).count()
        return pkg_name, limit, count

    def get_available_slots(date_str):
        session = PostgresSession()
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = days_of_week[dt.weekday()]
            
            # Disponibilidad del Profesor
            rules = session.query(ScheduleProfEsp).filter_by(date=date_str).all()
            if not rules:
                rules = session.query(ScheduleProf).filter_by(days=day_name).all()

            available_ranges = []
            for r in rules:
                status_bd = str(r.avai if hasattr(r, 'avai') else r.availability)
                if status_bd in POSITIVE_STATUS:
                    available_ranges.append((r.start_time, r.end_time))
            
            if not available_ranges: return [] 

            # Clases ocupadas
            busy_classes = session.query(AsignedClasses).filter(
                AsignedClasses.date == date_str,
                AsignedClasses.status != 'Cancelled'
            ).all()
            blocked_intervals = [(c.start_time, c.end_time) for c in busy_classes]

            # Generar Slots
            def to_min(t): return int(str(t).zfill(4)[:2]) * 60 + int(str(t).zfill(4)[2:])
            def to_hhmm(mins): return int(f"{mins // 60}{str(mins % 60).zfill(2)}")

            final_slots = []
            for r_start, r_end in available_ranges:
                curr_min = to_min(r_start)
                end_min = to_min(r_end)
                while curr_min + 60 <= end_min:
                    slot_start = curr_min
                    slot_end = curr_min + 60
                    is_blocked = False
                    for b_start, b_end in blocked_intervals:
                        bs, be = to_min(b_start), to_min(b_end)
                        if (slot_start < be) and (slot_end > bs):
                            is_blocked = True; break
                    if not is_blocked: final_slots.append(to_hhmm(slot_start))
                    curr_min += 60 
            return sorted(list(set(final_slots)))
        except Exception as e:
            logger.error(f"Error slots: {e}")
            return []
        finally:
            session.close()

    async def book_class(slot_int):
        session = PostgresSession()
        try:
            pkg, limit, used = get_user_usage(session, username)
            if limit > 0 and used >= limit:
                ui.notify(f"Límite alcanzado ({used}/{limit})", type='negative')
                return

            user_db = session.query(User).filter_by(username=username).first()
            s_str = str(slot_int).zfill(4)
            end_dt = datetime(2000, 1, 1, int(s_str[:2]), int(s_str[2:])) + timedelta(minutes=60)
            end_int = int(end_dt.strftime("%H%M"))
            
            dt_obj = datetime.strptime(state['date'], '%Y-%m-%d')
            day_name = days_of_week[dt_obj.weekday()]

            new_class = AsignedClasses(
                username=username, name=user_db.name, surname=user_db.surname,
                date=state['date'], days=day_name, start_time=slot_int,
                end_time=end_int, duration="60", package=pkg, status="Agendada"
            )
            session.add(new_class)
            session.commit()
            
            # Backup SQLite
            try:
                bk_sess = BackupSession()
                bk_sess.add(AsignedClasses(
                    username=username, name=user_db.name, surname=user_db.surname,
                    date=state['date'], days=day_name, start_time=slot_int,
                    end_time=end_int, duration="60", package=pkg, status="Agendada"
                ))
                bk_sess.commit(); bk_sess.close()
            except: pass

            ui.notify("Clase agendada correctamente", type='positive', icon='check')
            update_dashboard()
            
        except Exception as e:
            ui.notify(f"Error: {e}", type='negative')
        finally:
            session.close()

    # =================================================================
    # COMPONENTES DE INTERFAZ (VIEW)
    # =================================================================

    def render_booking_dialog(slot):
        """Dialogo de confirmación limpio"""
        t_str = str(slot).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        date_nice = datetime.strptime(state['date'], '%Y-%m-%d').strftime('%d %B %Y')
        
        with ui.dialog() as d, ui.card().classes('w-80 p-0 rounded-2xl overflow-hidden shadow-xl'):
            # Header Imagen/Color
            with ui.column().classes('w-full bg-slate-800 p-6 items-center'):
                ui.icon('calendar_today', color='white', size='lg')
                ui.label('Confirmar Reserva').classes('text-white font-bold mt-2')
            
            # Body
            with ui.column().classes('p-6 w-full items-center bg-white'):
                ui.label(date_nice).classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                ui.label(fmt_time).classes('text-4xl font-white text-slate-800 my-2')
                ui.label('Duración: 60 min').classes('text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full')

            # Footer
            with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 gap-2'):
                ui.button('Cancelar', on_click=d.close).props('flat text-color=slate').classes('flex-1')
                async def do_book():
                    d.close()
                    await book_class(slot)
                ui.button('Reservar', on_click=do_book).props('unelevated color=rose').classes('flex-1')
        d.open()

    @ui.refreshable
    def render_slots_area():
        """Renderiza la grilla de slots sin divisiones de texto"""
        
        # 1. Validación de fecha
        try:
            sel_dt = datetime.strptime(state['date'], '%Y-%m-%d')
            if sel_dt.date() < datetime.now().date():
                with ui.column().classes('w-full items-center py-12 opacity-60'):
                    ui.icon('history', size='3xl', color='slate-300')
                    ui.label("Esta fecha ya pasó").classes('text-slate-400 font-medium mt-2')
                return
        except: return

        # 2. Carga de datos
        all_slots = get_available_slots(state['date'])
        pref_ranges = get_user_preferred_ranges(username, state['date'])
        
        if not all_slots:
            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                ui.icon('event_busy', size='4xl', color='slate-300')
                ui.label("No hay disponibilidad").classes('text-slate-500 font-medium mt-3')
            return

        # 3. Renderizado de Grilla Unificada
        with ui.column().classes('w-full gap-4'):
            
            # Mensaje informativo sutil (si hay preferencias)
            has_prefs = any(is_in_user_range(s, pref_ranges) for s in all_slots)
            if has_prefs:
                with ui.row().classes('items-center gap-2 text-xs text-amber-600 bg-amber-50 px-3 py-1.5 rounded-lg self-start border border-amber-100'):
                    ui.icon('star', size='xs')
                    ui.label('Horarios sugeridos según tu historial')

            # Contenedor Grid (Responsive)
            # Grid-cols-3 en movil, cols-4 en tablet, cols-6 en desktop
            with ui.grid().classes('w-full grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3'):
                
                for slot in all_slots:
                    t_str = str(slot).zfill(4)
                    fmt_time = f"{t_str[:2]}:{t_str[2:]}"
                    is_preferred = is_in_user_range(slot, pref_ranges)
                    time_icon = get_time_icon(slot)

                    # Estilos condicionales
                    if is_preferred:
                        # Estilo "Premium" para preferidos
                        base_class = "bg-rose-50 border-rose-200 text-rose-900 shadow-sm ring-1 ring-rose-200 hover:bg-rose-100"
                        icon_color = "text-rose-500"
                    else:
                        # Estilo "Clean" estándar
                        base_class = "bg-white border-gray-300 text-gray-900 shadow-sm hover:border-gray-500 hover:text-gray-900"
                        icon_color = "text-slate-400"

                    # Botón
                    btn = ui.button(on_click=lambda s=slot: render_booking_dialog(s))
                    btn.props('unelevated').classes(f"{base_class} border rounded-xl py-3 px-0 transition-all duration-200 flex flex-col gap-1 items-center h-auto")
                    
                    with btn:
                        # Icono pequeño arriba o al lado
                        ui.icon(time_icon, size='xs').classes(f"{icon_color} opacity-80")
                        ui.label(fmt_time).classes('font-bold text-sm tracking-wide')

    @ui.refreshable
    def render_my_classes():
        session = PostgresSession()
        now_int = int(datetime.now().strftime("%Y%m%d"))
        classes = session.query(AsignedClasses).filter(
            AsignedClasses.username == username, AsignedClasses.status != 'Cancelled'
        ).all()
        
        future_classes = [c for c in classes if int(c.date.replace('-', '')) >= now_int]
        future_classes.sort(key=lambda x: (x.date, x.start_time))
        session.close()

        if not future_classes:
            with ui.column().classes('w-full items-center py-8 text-slate-400 italic'):
                ui.label('No tienes clases agendadas.')
            return

        with ui.column().classes('w-full gap-3'):
            for c in future_classes:
                dt = datetime.strptime(c.date, '%Y-%m-%d')
                t_str = str(c.start_time).zfill(4)
                fmt = f"{t_str[:2]}:{t_str[2:]}"
                
                # Tarjeta de clase
                with ui.row().classes('w-full bg-rose border-l-4 border-rose-500 shadow-sm rounded-r-lg p-3 justify-between items-center group transition-all hover:shadow-md'):
                    
                    # Columna Fecha
                    with ui.row().classes('items-center gap-4'):
                        with ui.column().classes('items-center leading-none px-2'):
                            ui.label(dt.strftime('%d')).classes('text-xl font-white text-slate-700')
                            ui.label(dt.strftime('%b')).classes('text-[10px] font-bold uppercase text-slate-400')
                        
                        # Columna Info
                        with ui.column().classes('gap-0'):
                            ui.label(f"{days_of_week[dt.weekday()]} - {fmt}").classes('font-bold text-slate-800 text-sm')
                            ui.label('Inglés General').classes('text-xs text-slate-500')
                    
                    # Botón Eliminar (discreto)
                    ui.button(icon='close', on_click=lambda x=c: delete_class_dialog(x)).props('flat round dense color=slate size=sm').classes('opacity-0 group-hover:opacity-100 transition-opacity')

    def delete_class_dialog(c_obj):
        with ui.dialog() as d, ui.card().classes('rounded-xl'):
            ui.label('¿Cancelar clase?').classes('font-bold text-lg')
            ui.label(f"{c_obj.date} a las {c_obj.start_time} hrs").classes('text-sm text-slate-500')
            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('No', on_click=d.close).props('flat')
                async def do_del():
                    d.close()
                    sess = PostgresSession()
                    try:
                        sess.query(AsignedClasses).filter(AsignedClasses.id == c_obj.id).delete()
                        sess.commit()
                        ui.notify('Clase cancelada', type='info')
                        update_dashboard()
                    except: pass
                    finally: sess.close()
                ui.button('Sí, Cancelar', on_click=do_del).props('unelevated color=red')
        d.open()

    @ui.refreshable
    def render_stats_widget():
        """Widget lateral de estadísticas"""
        session = PostgresSession()
        pkg, limit, used = get_user_usage(session, username)
        session.close()
        
        percent = min(used/limit, 1.0) if limit > 0 else 0
        
        with ui.card().classes('w-full p-5 rounded-2xl bg-white shadow-sm border border-slate-100'):
            ui.label("Mi Plan").classes('text-xs font-bold text-slate-400 uppercase tracking-widest mb-4')
            
            with ui.row().classes('items-center gap-4 w-full'):
                with ui.circular_progress(value=percent, show_value=False, color='rose', size='50px').props('thickness=0.2 track-color=grey-2'):
                    ui.icon('school', color='rose', size='xs')
                
                with ui.column().classes('gap-0 flex-1'):
                    ui.label(pkg).classes('font-bold text-slate-800 text-lg leading-tight')
                    ui.label(f"{used} de {limit} clases").classes('text-xs text-slate-500')

    # =================================================================
    # LAYOUT SYSTEM (ESTRUCTURA FÁCIL DE MODIFICAR)
    # =================================================================

    def update_dashboard():
        render_slots_area.refresh()
        render_my_classes.refresh()
        render_stats_widget.refresh()

    def render_sidebar():
        """Contenido de la barra lateral (o superior en móvil)"""
        with ui.column().classes('w-full gap-6'):
            # Calendario
            with ui.card().classes('w-full p-4 rounded-2xl shadow-sm border border-slate-100 bg-white'):
                ui.date(value=state['date']).bind_value(state, 'date') \
                    .on('update:model-value', render_slots_area.refresh) \
                    .props('flat color=rose class="w-full"')
            
            # Estadísticas
            render_stats_widget()

    def render_main_content():
        """Contenido principal"""
        with ui.column().classes('w-full gap-8'):
            
            # Header del contenido
            with ui.row().classes('items-baseline justify-between w-full'):
                with ui.column().classes('gap-0'):
                    ui.label('Reservar Horario').classes('text-2xl font-bold text-slate-800')
                    ui.label().bind_text_from(state, 'date', 
                        backward=lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%A, %d de %B')
                    ).classes('text-rose-500 font-medium')
                
                ui.button(icon='refresh', on_click=update_dashboard).props('flat round color=slate')

            # Area de Slots (La grilla)
            render_slots_area()

            ui.separator().classes('my-2 bg-slate-200')

            # Sección "Mis Clases"
            with ui.column().classes('w-full gap-4'):
                ui.label('Mis Próximas Sesiones').classes('text-lg font-bold text-slate-800')
                render_my_classes()

    # --- ENSAMBLAJE DE LA PÁGINA ---
    # Usamos un Grid CSS. Si quieres cambiar la distribución, 
    # solo cambias los 'col-span' aquí.
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8'):
        
        # Grid Principal
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-12 gap-8 items-start'):
            
            # 1. Sidebar (Calendario + Stats) -> Ocupa 4 de 12 columnas
            with ui.column().classes('lg:col-span-4 w-full order-2 lg:order-1'):
                render_sidebar()
            
            # 2. Main Content (Slots + Clases) -> Ocupa 8 de 12 columnas
            with ui.column().classes('lg:col-span-8 w-full order-1 lg:order-2'):
                render_main_content()

# Ejecutar
if __name__ in {"__main__", "__mp_main__"}:
    ui.run()