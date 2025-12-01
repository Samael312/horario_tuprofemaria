from nicegui import ui, app
from datetime import datetime, timedelta
import logging

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
# Importamos tus modelos reales incluyendo SchedulePref
from db.models import User, ScheduleProf, ScheduleProfEsp, AsignedClasses, SchedulePref
from components.header import create_main_screen
from components.share_data import days_of_week, PACKAGE_LIMITS

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

@ui.page('/ScheduleMaker')
def scheduleMaker():
    # Estilos globales: Fondo gris suave para resaltar las tarjetas blancas
    ui.query('body').style('background-color: #f8fafc; margin: 0; padding: 0;')
    
    create_main_screen()
    
    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # Estado reactivo
    state = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'slot': None
    }
    
    # Contenedores UI
    slots_area = ui.element('div').classes('w-full flex flex-col gap-6 transition-all')
    stats_container = ui.element('div')

    # =================================================================
    # LÓGICA DE NEGOCIO Y BASE DE DATOS
    # =================================================================

    def get_user_preferred_ranges(user_id, date_str):
        """
        Consulta SchedulePref (rangos_horarios) para el usuario y el DÍA de la semana seleccionado.
        """
        session = PostgresSession()
        ranges = []
        try:
            # 1. Obtener el nombre del día (ej: "Monday")
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = days_of_week[dt.weekday()]
            
            # 2. Consultar la tabla SchedulePref
            # Filtramos por usuario y por el día de la semana específico
            prefs = session.query(SchedulePref).filter(
                SchedulePref.username == user_id,
                SchedulePref.days == day_name
            ).all()

            # 3. Extraer tuplas (inicio, fin)
            for p in prefs:
                # Aseguramos que existan datos válidos
                if p.start_time is not None and p.end_time is not None:
                    ranges.append((p.start_time, p.end_time))
            
            if ranges:
                logger.info(f"Preferencias encontradas para {day_name}: {ranges}")
            
        except Exception as e:
            logger.error(f"Error obteniendo preferencias: {e}")
        finally:
            session.close()
        return ranges

    def is_in_user_range(slot_int, ranges):
        """Verifica si el slot (entero) está dentro de alguno de los rangos preferidos."""
        # El slot dura 60 min. Consideramos "preferido" si el inicio del slot
        # está dentro del rango definido por el usuario.
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
            
            # A. REGLAS DE PROFESOR
            rules = session.query(ScheduleProfEsp).filter_by(date=date_str).all()
            if not rules:
                rules = session.query(ScheduleProf).filter_by(days=day_name).all()

            available_ranges = []
            for r in rules:
                status_bd = str(r.avai if hasattr(r, 'avai') else r.availability)
                if status_bd in POSITIVE_STATUS:
                    available_ranges.append((r.start_time, r.end_time))
            
            if not available_ranges: return [] 

            # B. CLASES OCUPADAS
            busy_classes = session.query(AsignedClasses).filter(
                AsignedClasses.date == date_str,
                AsignedClasses.status != 'Cancelled'
            ).all()
            blocked_intervals = [(c.start_time, c.end_time) for c in busy_classes]

            # C. CÁLCULO DE SLOTS
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
                ui.notify(f"Límite alcanzado ({used}/{limit})", type='negative', icon='lock')
                return

            user_db = session.query(User).filter_by(username=username).first()
            s_str = str(slot_int).zfill(4)
            start_dt = datetime(2000, 1, 1, int(s_str[:2]), int(s_str[2:]))
            end_dt = start_dt + timedelta(minutes=60)
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
            
            ui.notify("¡Clase agendada con éxito!", type='positive', icon='check_circle')
            
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

            refresh_dashboard()
            
        except Exception as e:
            ui.notify(f"Error al agendar: {e}", type='negative')
        finally:
            session.close()

    # =================================================================
    # COMPONENTES DE UI (MODERNIZADOS & RESALTADOS)
    # =================================================================

    def render_slot_group(title, slots, icon, preferred_ranges):
        """Renderiza botones, resaltando los que coinciden con preferred_ranges"""
        if not slots: return
        
        with ui.column().classes('w-full gap-2'):
            # Título de la sección (Mañana/Tarde/Noche)
            with ui.row().classes('items-center gap-2 text-slate-500 mb-1'):
                ui.icon(icon, size='xs')
                ui.label(title).classes('text-xs font-bold uppercase tracking-wider')
            
            with ui.row().classes('w-full flex-wrap gap-3'):
                for slot in slots:
                    t_str = str(slot).zfill(4)
                    fmt_time = f"{t_str[:2]}:{t_str[2:]}"
                    
                    # --- LÓGICA DE RESALTADO ---
                    is_preferred = is_in_user_range(slot, preferred_ranges)
                    
                    if is_preferred:
                        # ESTILO DESTACADO (Gold/Amber)
                        # Borde dorado, fondo suave amarillo, icono de estrella
                        btn_classes = (
                            'bg-amber-50 text-amber-900 border border-amber-400 shadow-sm rounded-lg px-4 py-2 '
                            'hover:bg-amber-100 transition-all font-bold ring-2 ring-amber-100'
                        )
                        tooltip_text = "✨ Horario habitual"
                        icon_btn = 'star'
                    else:
                        # ESTILO ESTÁNDAR (Slate/Rose)
                        btn_classes = (
                            'bg-white text-slate-600 border border-slate-200 shadow-sm rounded-lg px-4 py-2 '
                            'hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 transition-all font-medium'
                        )
                        tooltip_text = None
                        icon_btn = None

                    # Render del Botón
                    btn = ui.button(on_click=lambda s=slot: confirm_booking(s))
                    btn.props('unelevated').classes(btn_classes)
                    
                    with btn:
                        if icon_btn:
                            ui.icon(icon_btn, size='xs').classes('mr-1 text-amber-600')
                        ui.label(fmt_time)
                    
                    if tooltip_text:
                        btn.tooltip(tooltip_text)

    def update_slots_ui():
        slots_area.clear()
        
        # 1. Validar fecha pasada
        try:
            sel_dt = datetime.strptime(state['date'], '%Y-%m-%d')
            if sel_dt.date() < datetime.now().date():
                with slots_area:
                    with ui.column().classes('w-full items-center py-8 opacity-50'):
                        ui.icon('history', size='3xl', color='slate-300')
                        ui.label("Fecha pasada").classes('text-slate-400')
                return
        except: return

        # 2. Obtener datos (Slots disponibles y Preferencias del usuario para ESTA fecha)
        all_slots = get_available_slots(state['date'])
        pref_ranges = get_user_preferred_ranges(username, state['date'])
        
        with slots_area:
            # Leyenda informativa si hay coincidencias
            if all_slots and pref_ranges:
                with ui.row().classes('w-full bg-blue-50 border border-blue-100 p-3 rounded-lg items-center gap-3 mb-2'):
                    ui.icon('recommend', color='blue-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Horarios Recomendados').classes('text-xs font-bold text-blue-800 uppercase')
                        ui.label('Las opciones resaltadas (✨) coinciden con tu disponibilidad configurada.').classes('text-xs text-blue-700')

            if not all_slots:
                with ui.column().classes('w-full items-center py-12 bg-white rounded-xl border border-dashed border-slate-300'):
                    ui.icon('event_busy', size='4xl', color='slate-300')
                    ui.label("No hay horarios disponibles").classes('text-slate-500 mt-2')
            else:
                # Agrupar por franja horaria
                morning = [s for s in all_slots if s < 1200]
                afternoon = [s for s in all_slots if 1200 <= s < 1700]
                evening = [s for s in all_slots if s >= 1700]

                if morning: render_slot_group("Mañana", morning, 'wb_sunny', pref_ranges)
                if afternoon: render_slot_group("Tarde", afternoon, 'wb_twilight', pref_ranges)
                if evening: render_slot_group("Noche", evening, 'nights_stay', pref_ranges)

    def confirm_booking(slot):
        t_str = str(slot).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        
        with ui.dialog() as dialog, ui.card().classes('p-0 w-80 rounded-2xl overflow-hidden'):
            # Header del Dialog
            with ui.column().classes('w-full bg-slate-900 p-6 items-center'):
                ui.icon('event_available', size='xl', color='white')
                ui.label('Confirmar Reserva').classes('text-white font-bold text-lg mt-2')
            
            # Body del Dialog
            with ui.column().classes('p-6 items-center w-full bg-white'):
                date_pretty = datetime.strptime(state['date'], '%Y-%m-%d').strftime('%d %b %Y')
                ui.label(date_pretty).classes('text-sm uppercase tracking-widest text-slate-500')
                ui.label(f"{fmt_time}").classes('text-4xl font-black text-slate-800 my-2')
                ui.label("¿Confirmar esta clase?").classes('text-slate-600')

            # Footer con botones
            with ui.row().classes('w-full p-4 bg-slate-50 gap-2 border-t border-slate-100'):
                ui.button('Cancelar', on_click=dialog.close).props('flat color=slate').classes('flex-1')
                async def on_confirm():
                    dialog.close()
                    await book_class(slot)
                ui.button('Reservar', on_click=on_confirm).props('unelevated color=rose').classes('flex-1')
        dialog.open()

    def update_stats_ui():
        stats_container.clear()
        sess_info = PostgresSession()
        pkg, limit, used = get_user_usage(sess_info, username)
        sess_info.close()
        
        percent = min(used / limit, 1.0) if limit > 0 else 0
        color = 'rose' if percent >= 0.9 else 'emerald'
        
        with stats_container:
            with ui.card().classes('w-full p-0 shadow-sm border border-slate-200 rounded-xl overflow-hidden'):
                with ui.row().classes('w-full bg-slate-50 px-4 py-3 border-b border-slate-100 justify-between items-center'):
                    ui.label("Mi Plan Actual").classes('font-bold text-slate-700 text-sm uppercase')
                    ui.icon('verified', color='blue-500', size='xs')

                with ui.row().classes('p-5 items-center gap-5'):
                    with ui.circular_progress(value=percent, show_value=False, color=color, size='65px').props('thickness=0.15 track-color=grey-2'):
                        ui.icon('person', color=color, size='md')
                    
                    with ui.column().classes('gap-1'):
                        ui.label(pkg).classes('text-xl font-black text-slate-800 leading-none')
                        ui.label(f'{used} / {limit} Clases').classes('text-sm font-bold text-slate-600')
                        ui.linear_progress(value=percent, size='6px', color=color).classes('w-24 rounded-full opacity-50')

    @ui.refreshable
    def my_classes_list():
        session = PostgresSession()
        now_int = int(datetime.now().strftime("%Y%m%d"))
        classes = session.query(AsignedClasses).filter(
            AsignedClasses.username == username, AsignedClasses.status != 'Cancelled'
        ).all()
        
        future_classes = []
        for c in classes:
            try:
                if int(c.date.replace('-', '')) >= now_int: future_classes.append(c)
            except: pass
        
        future_classes.sort(key=lambda x: (x.date, x.start_time))
        session.close()

        if not future_classes:
            with ui.column().classes('w-full items-center justify-center py-8 text-slate-400'):
                ui.icon('calendar_today', size='lg')
                ui.label('Sin clases futuras').classes('text-sm')
            return

        with ui.column().classes('w-full gap-3 max-h-[500px] overflow-y-auto pr-2'):
            for c in future_classes:
                dt = datetime.strptime(c.date, '%Y-%m-%d')
                t_str = str(c.start_time).zfill(4)
                fmt = f"{t_str[:2]}:{t_str[2:]}"

                with ui.row().classes('w-full bg-white border border-slate-200 p-3 rounded-xl shadow-sm hover:shadow-md transition-shadow items-center justify-between group'):
                    with ui.row().classes('items-center gap-4'):
                        # Badge Fecha
                        with ui.column().classes('bg-slate-100 px-3 py-2 rounded-lg items-center min-w-[60px] gap-0 border border-slate-200'):
                            ui.label(dt.strftime('%d')).classes('text-lg font-black text-slate-700 leading-none')
                            ui.label(dt.strftime('%b')).classes('text-[10px] font-bold text-slate-500 uppercase')
                        
                        # Info Clase
                        with ui.column().classes('gap-0'):
                            ui.label(f"{days_of_week[dt.weekday()]}").classes('font-bold text-slate-800')
                            ui.label(f"{fmt} hrs").classes('text-xs font-medium text-white bg-rose-500 px-2 py-0.5 rounded-full self-start mt-1')

                    # Menú contextual
                    with ui.button(icon='more_vert').props('flat round dense color=slate'):
                        with ui.menu().classes('bg-white shadow-lg border border-slate-100'):
                            ui.menu_item('Liberar Clase', on_click=lambda x=c: reschedule_dialog(x)) \
                                .props('active-class="bg-red-50 text-red-600"')

    def reschedule_dialog(class_obj):
        with ui.dialog() as d, ui.card().classes('w-96 p-0 rounded-xl overflow-hidden'):
            with ui.row().classes('w-full bg-amber-50 p-4 items-center gap-3 border-b border-amber-100'):
                ui.icon('warning', color='amber-700')
                ui.label('Gestionar Clase').classes('font-bold text-amber-900')
            
            with ui.column().classes('p-6 gap-2 bg-white'):
                ui.label("¿Deseas liberar este horario?").classes('font-medium text-slate-800')
                ui.label(f"Clase del {class_obj.date} a las {class_obj.start_time}").classes('text-sm text-slate-500')
            
            async def process_cancel():
                d.close()
                sess = PostgresSession()
                try:
                    sess.query(AsignedClasses).filter(AsignedClasses.id == class_obj.id).delete()
                    sess.commit()
                    # Backup logic
                    try:
                        bk = BackupSession()
                        bk.query(AsignedClasses).filter(
                            AsignedClasses.date == class_obj.date,
                            AsignedClasses.start_time == class_obj.start_time,
                            AsignedClasses.username == username
                        ).delete()
                        bk.commit(); bk.close()
                    except: pass
                    
                    ui.notify("Clase liberada correctamente", type='info')
                    refresh_dashboard()
                except Exception as e:
                    ui.notify(f"Error: {e}", type='negative')
                finally:
                    sess.close()

            with ui.row().classes('w-full bg-slate-50 p-3 justify-end gap-2 border-t border-slate-100'):
                ui.button('Cerrar', on_click=d.close).props('flat text-color=slate')
                ui.button('Sí, Liberar', on_click=process_cancel).props('unelevated color=negative')
        d.open()

    def refresh_dashboard():
        update_slots_ui()
        my_classes_list.refresh()
        update_stats_ui()

    # =================================================================
    # LAYOUT PRINCIPAL (GRID SYSTEM)
    # =================================================================
    
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        
        # Header
        with ui.row().classes('w-full items-center justify-between mb-2'):
            with ui.column().classes('gap-1'):
                ui.label('Hola, ' + username).classes('text-2xl md:text-3xl font-black text-slate-800')
                ui.label('Reserva tu próxima sesión de inglés').classes('text-slate-500 font-medium')
            ui.button(icon='refresh', on_click=refresh_dashboard).props('flat round color=slate').tooltip('Actualizar datos')

        # Grid Contenido
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-12 gap-8'):
            
            # --- COLUMNA IZQUIERDA (4 cols) ---
            with ui.column().classes('lg:col-span-4 gap-6'):
                # Stats
                stats_container
                update_stats_ui() 

                # Calendario
                with ui.card().classes('w-full p-4 shadow-sm border border-slate-200 rounded-xl'):
                    ui.label('Seleccionar Fecha').classes('font-bold text-slate-700 mb-2 ml-1')
                    # Calendario estilo "flat"
                    ui.date(value=state['date']).bind_value(state, 'date') \
                        .on('update:model-value', update_slots_ui) \
                        .props('minimal flat color=rose today-btn class="w-full"')

            # --- COLUMNA DERECHA (8 cols) ---
            with ui.column().classes('lg:col-span-8 gap-8'):
                
                # Panel Horarios
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('items-baseline gap-2'):
                        ui.label("Horarios Disponibles").classes('text-xl font-bold text-slate-800')
                        # Muestra la fecha formateada dinámica
                        ui.label().bind_text_from(state, 'date', backward=lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%d %B')).classes('text-rose-500 font-medium')
                    
                    slots_area
                    update_slots_ui()

                ui.separator().classes('bg-slate-200')

                # Panel Mis Clases
                with ui.column().classes('w-full gap-4'):
                    ui.label("Mis Próximas Clases").classes('text-xl font-bold text-slate-800')
                    my_classes_list()