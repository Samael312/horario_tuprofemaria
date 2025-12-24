from nicegui import ui, app
from datetime import datetime, timedelta
import logging
import asyncio

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import User, ScheduleProf, ScheduleProfEsp, AsignedClasses, SchedulePref
from components.header import create_main_screen
from components.share_data import days_of_week, PACKAGE_LIMITS
from prompts.chatbot import render_floating_chatbot
# IMPORTAMOS EL CONVERSOR
from components.timezone_converter import convert_student_to_teacher, get_slots_in_student_tz, from_int_time

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

@ui.page('/ScheduleMaker')
def scheduleMaker():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_main_screen()
    
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
    
    def get_renovations():
        session = PostgresSession()
        try:
            user = (
                session.query(User)
                .filter(User.username == username)
                .first()
            )
            return user.renovations if user else 0
        except Exception as e:
            logger.error(f"Error obteniendo renovaciones: {e}")
            return 0
        finally:
            session.close()


    # Inicializamos estado
    lifetime_count = get_all_time_classes()
    reno = get_renovations()

    is_trial = (lifetime_count == 0 and reno == 0)

    # 3. ESTADO REACTIVO
    state = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'loading': False,
        'is_trial': is_trial,
        'duration': 30 if is_trial else 60
    }
    
    # === NUEVO: DIÁLOGO INFORMATIVO SI ES MODO PRUEBA ===
    if is_trial:
        with ui.dialog() as trial_dialog, ui.card().classes('w-[400px] items-center p-6 text-center'):
            ui.icon('school', size='xl', color='purple-500').classes('mb-2')
            ui.label('¡Bienvenido/a!').classes('text-xl font-bold text-slate-700')
            ui.label('Agenda tu clase de prueba, luego de agendar dicha clase las siguientes contaran como parte de tu paquete.').classes('text-sm text-slate-500 my-4')
            ui.button('Entendido', on_click=trial_dialog.close).props('unelevated color=purple')
        
        # Abrimos el dialog después de una pequeña pausa para asegurar que la UI cargó
        ui.timer(0.5, trial_dialog.open, once=True)
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
        if not user: return "Sin Plan", 0, 0
        pkg_name = user.package or "None"
        limit = PACKAGE_LIMITS.get(pkg_name, 0)
        now = datetime.now()
        start_date_str = f"{now.year}-{str(now.month).zfill(2)}"
        
        # MODIFICACIÓN: Excluir status que contengan "Prueba"
        current_usage = session.query(AsignedClasses).filter(
            AsignedClasses.username == user_id,
            AsignedClasses.status != 'Cancelled',
            AsignedClasses.status.notlike('Prueba_Pendiente'), # NO contar pruebas
            AsignedClasses.date.startswith(start_date_str)
        ).count()
        return pkg_name, limit, current_usage

    def get_available_slots(date_str, duration_mins):
        session = PostgresSession()
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%d')
            day_name = days_of_week[dt.weekday()]
            
            # 1. Reglas Generales y Específicas
            general_rules = session.query(ScheduleProf).filter_by(days=day_name).all()
            specific_rules = session.query(ScheduleProfEsp).filter_by(date=date_str).all()

            available_ranges_prof = []

            # Disponibilidad General
            for r in general_rules:
                if str(getattr(r, 'availability', '')) in POSITIVE_STATUS:
                    available_ranges_prof.append((r.start_time, r.end_time))
            
            # Disponibilidad Específica (Extra)
            for r in specific_rules:
                if str(getattr(r, 'avai', '')) in POSITIVE_STATUS:
                    available_ranges_prof.append((r.start_time, r.end_time))

            if not available_ranges_prof: return [] 

            # 2. Bloqueos (Clases ya agendadas + Bloqueos específicos)
            busy_classes = session.query(AsignedClasses).filter(
                AsignedClasses.date == date_str, 
                AsignedClasses.status != 'Cancelled'
            ).all()
            
            blocked_intervals_prof = []
            
            for c in busy_classes:
                # Usar hora profesor si existe, si no hora local
                sp = c.start_prof_time if c.start_prof_time is not None else c.start_time
                ep = c.end_prof_time if c.end_prof_time is not None else c.end_time
                blocked_intervals_prof.append((sp, ep))

            for r in specific_rules:
                if str(getattr(r, 'avai', '')) not in POSITIVE_STATUS:
                    blocked_intervals_prof.append((r.start_time, r.end_time))

            # Helpers de conversión
            def to_min(t): return int(str(t).zfill(4)[:2]) * 60 + int(str(t).zfill(4)[2:])
            def to_hhmm(mins): return int(f"{mins // 60}{str(mins % 60).zfill(2)}")

            prof_slots_free = []
            prof_slots_busy = []

            # 3. Generar Slots y Clasificar
            for r_start, r_end in available_ranges_prof:
                curr_min = to_min(r_start)
                end_min = to_min(r_end)
                
                while curr_min + duration_mins <= end_min:
                    slot_start = curr_min
                    slot_end = curr_min + duration_mins
                    
                    # Checar colisión
                    is_blocked = False
                    for b_start, b_end in blocked_intervals_prof:
                        bs, be = to_min(b_start), to_min(b_end)
                        if (slot_start < be) and (slot_end > bs):
                            is_blocked = True; break
                    
                    if is_blocked:
                        prof_slots_busy.append(to_hhmm(slot_start))
                    else: 
                        prof_slots_free.append(to_hhmm(slot_start))
                    
                    curr_min += duration_mins 
            
            # 4. Convertir a Hora Estudiante
            student_tz = get_user_timezone()
            final_free = get_slots_in_student_tz(prof_slots_free, date_str, student_tz)
            final_busy = get_slots_in_student_tz(prof_slots_busy, date_str, student_tz)
            
            # 5. Unificar con etiqueta
            combined_slots = []
            for t in final_free:
                combined_slots.append({'time': t, 'status': 'free'})
            for t in final_busy:
                combined_slots.append({'time': t, 'status': 'busy'})
            
            combined_slots.sort(key=lambda x: x['time'])
            
            return combined_slots

        except Exception as e:
            logger.error(f"Error slots: {e}")
            return []
        finally:
            session.close()

    # --- BOOK CLASS ---
    async def book_class(slot_int):
        session = PostgresSession()
        try:
            pkg, limit, used = get_current_package_usage(session, username)
            
            # Solo validamos límite si NO es prueba
            if not state['is_trial'] and limit > 0 and used >= limit:
                ui.notify(f"Límite mensual alcanzado ({used}/{limit})", type='negative')
                return False
            
            # Cálculo de histórico (Excluyendo pruebas)
            total_lifetime_used = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status != 'Cancelled',
                AsignedClasses.status.notlike('Prueba_Prueba') # NO contar pruebas
            ).count()

            user_db = session.query(User).filter_by(username=username).first()
            student_tz = user_db.time_zone or "UTC"
            duration = state['duration']
            
            # Cálculos de tiempo
            s_str = str(slot_int).zfill(4)
            sh, sm = int(s_str[:2]), int(s_str[2:])
            start_dt_obj = datetime(2000, 1, 1, sh, sm)
            end_dt = start_dt_obj + timedelta(minutes=duration)
            end_int = int(end_dt.strftime("%H%M"))
            
            dt_obj = datetime.strptime(state['date'], '%Y-%m-%d')
            day_name = days_of_week[dt_obj.weekday()]

            sp_time, ep_time, prof_date = convert_student_to_teacher(
                state['date'], slot_int, duration, student_tz
            )

            status_to_save = "Prueba_Pendiente" if state['is_trial'] else "Pendiente"
            
            # --- LÓGICA DE CONTADORES ---
            if state['is_trial']:
                # Si es prueba, NO asignamos contadores numéricos
                count_label = None 
                new_total_classes_seq = None
            else:
                # Si es normal, incrementamos
                if pkg == "Flexible":
                    current_class_num = total_lifetime_used + 1
                    count_label = f"{current_class_num}/inf"
                else:
                    current_class_num = used + 1
                    count_label = f"{current_class_num}/{limit}"
                new_total_classes_seq = total_lifetime_used + 1

            new_class = AsignedClasses(
                username=username, name=user_db.name, surname=user_db.surname,
                date=state['date'], days=day_name, 
                start_time=slot_int, end_time=end_int, 
                start_prof_time=sp_time, end_prof_time=ep_time,
                date_prof=prof_date, duration=str(duration), package=pkg, 
                status=status_to_save,
                class_count=count_label,          # Será None si es prueba
                total_classes=new_total_classes_seq # Será None si es prueba
            )
            session.add(new_class)
            session.commit()
            
            # Backup SQLite
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

            return True
            
        except Exception as e:
            ui.notify(f"Error al guardar: {e}", type='negative')
            return False
        finally:
            session.close()

    # =================================================================
    # COMPONENTES DE INTERFAZ (VIEW)
    # =================================================================

    def render_booking_dialog(slot):
        t_str = str(slot).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        date_nice = datetime.strptime(state['date'], '%Y-%m-%d').strftime('%d %B %Y')
        duration = state['duration']
        tipo_clase = "Clase de Prueba" if state['is_trial'] else "Clase Regular"

        with ui.dialog() as d, ui.card().classes('w-80 p-0 rounded-2xl overflow-hidden shadow-xl'):
            with ui.column().classes('w-full bg-slate-800 p-6 items-center'):
                ui.icon('calendar_today', color='white', size='lg')
                ui.label(f'Confirmar {tipo_clase}').classes('text-white font-bold mt-2')
            
            with ui.column().classes('p-6 w-full items-center bg-white'):
                ui.label(date_nice).classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                ui.label(fmt_time).classes('text-4xl font-white text-slate-800 my-2')
                ui.label(f'Duración: {duration} min').classes('text-sm text-slate-500 bg-slate-100 px-3 py-1 rounded-full')

            with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 gap-2'):
                ui.button('Cancelar', on_click=d.close).props('unelevated color=red').classes('flex-1')
                confirm_btn = ui.button('Reservar').props('unelevated color=green').classes('flex-1')
                
                async def do_book():
                    # 1. Feedback visual
                    confirm_btn.props('loading')
                    confirm_btn.disable()
                    
                    # CORRECCIÓN 1: Pausa para renderizar la UI antes de bloquear
                    await asyncio.sleep(0.1) 
                    
                    try:
                        # 2. Guardar en DB (Bloqueante)
                        success = await book_class(slot)
                        
                        if success:
                            # 3. Éxito
                            d.close()
                            ui.notify("Clase agendada correctamente", type='positive', icon='check')
                            await update_dashboard() 
                        else:
                            # 4. Fallo lógico
                            confirm_btn.props(remove='loading')
                            confirm_btn.enable()

                    except Exception as e:
                        # 5. Excepción
                        confirm_btn.props(remove='loading')
                        confirm_btn.enable()
                        ui.notify(str(e), type='negative')
                
                confirm_btn.on('click', do_book)
        d.open()

    @ui.refreshable
    def render_slots_area():
         # Si estamos cargando, mostrar spinner
        if state.get('loading', False):
            with ui.column().classes('w-full items-center justify-center py-12'):
                ui.spinner('dots', size='lg', color='rose')
                ui.label('Actualizando disponibilidad...').classes('text-slate-400 text-sm animate-pulse')
            return

        try:
            sel_dt = datetime.strptime(state['date'], '%Y-%m-%d')
            now = datetime.now()
            current_hhmm = int(now.strftime("%H%M"))
            is_today = (sel_dt.date() == now.date())

            if sel_dt.date() < now.date():
                with ui.column().classes('w-full items-center py-12 opacity-60'):
                    ui.icon('history', size='3xl', color='slate-300')
                    ui.label("Esta fecha ya pasó").classes('text-slate-400 font-medium mt-2')
                return
        except: return

        current_duration = state['duration']
        all_slots_data = get_available_slots(state['date'], current_duration)
        pref_ranges = get_user_preferred_ranges(username, state['date'])
        

        if not all_slots_data:
            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                ui.icon('event_busy', size='4xl', color='slate-300')
                ui.label("No hay disponibilidad").classes('text-slate-500 font-medium mt-3')
            return

        with ui.column().classes('w-full gap-4'):

           

            # Leyenda si hay preferentes
            has_prefs = any((item['status'] == 'free' and is_in_user_range(item['time'], pref_ranges)) for item in all_slots_data)
            if has_prefs:
                with ui.row().classes('items-center gap-2 text-xs text-purple-700 bg-purple-50 px-3 py-1.5 rounded-lg self-start border border-purple-100'):
                    ui.icon('star', size='xs', color='purple-700')
                    ui.label('Horarios preferenciales (Morado)')

            # --- GRID DE HORARIOS ---
            with ui.grid().classes('w-full grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3'):
                
                for item in all_slots_data:
                    slot = item['time']
                    status = item['status']
                    
                    # Formato de hora
                    t_str = str(slot).zfill(4)
                    fmt_time = f"{t_str[:2]}:{t_str[2:]}"
                    
                    is_preferred = is_in_user_range(slot, pref_ranges)
                    is_past_hour = is_today and (slot < current_hhmm)

                    # --- LÓGICA DE ESTILOS ---
                    
                    # 1. HORA PASADA (Gris muy claro, deshabilitado)
                    if is_past_hour:
                        btn_color_class = (
                        "!bg-slate-100 "           # Fondo gris muy pálido
                        "!text-slate-300 "          # Texto gris medio
                        "border border-slate-200 " # Borde muy sutil de 1px (plano)
                        "cursor-not-allowed "      # Cursor de prohibido
                        "hover:!bg-slate-100"      # Sin efecto hover
                    ) 
                        btn_props = "unelevated"
                        icon_name = "schedule"

                        # Al hacer click, solo notifica
                        def notify_busy():
                            ui.notify('Horario ya pasado', type='warning', icon='clock', position='center')
                        click_handler = notify_busy
                    
                    # 2. OCUPADO (Gris sólido, "No disponible")
                    elif status == 'busy':
                        # Gris medio, sin relieve (flat), cursor de prohibido
                        btn_color_class = (
                        "!bg-slate-100 "           # Fondo gris muy pálido
                        "!text-slate-300 "          # Texto gris medio
                        "border border-slate-200 " # Borde muy sutil de 1px (plano)
                        "cursor-not-allowed "      # Cursor de prohibido
                        "hover:!bg-slate-100"      # Sin efecto hover
                    ) 
                        btn_props = "unelevated"
                        icon_name = "lock"
                        
                        # Al hacer click, solo notifica
                        def notify_busy():
                            ui.notify('Horario no disponible o reservado.', type='warning', icon='lock', position='center')
                        click_handler = notify_busy

                    # 3. DISPONIBLE (Lógica de colores Rosado vs Morado)
                    else:
                        btn_props = "unelevated"
                        icon_name = "schedule" # O 'star' si prefieres distinguir icono también
                        click_handler = lambda s=slot: render_booking_dialog(s)

                        if is_preferred:
                            # MORADO (Estilo 3D)
                            btn_color_class = "!bg-purple-600 hover:bg-purple-700 text-white border-purple-800"
                            icon_name = "star" # Icono estrella para preferidos
                        else:
                            # ROSADO (Estilo 3D)
                            btn_color_class = "!bg-rose-600 hover:bg-rose-700 text-white border-rose-800"

                    # RENDERIZAR BOTÓN
                    btn = ui.button(on_click=click_handler)
                    btn.props(btn_props).classes(
                        f"{btn_color_class} shadow-md border-b-4 rounded-xl py-3 px-0 "
                        "transition-all active:border-b-0 active:translate-y-1 h-auto flex flex-col gap-1"
                    )
                    with btn:
                        ui.icon(icon_name, size='xs').classes('opacity-90')
                        ui.label(fmt_time).classes('font-bold text-sm tracking-wide')

    @ui.refreshable
    def render_my_classes():
        session = PostgresSession()
        now = datetime.now()
        now_int = int(now.strftime("%Y%m%d%H%M"))
        
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
                ui.label('No tienes clases agendadas.')
            return

        with ui.column().classes('w-full gap-3'):
            for c in classes:
                dt = datetime.strptime(c.date, '%Y-%m-%d')
                t_str = str(c.start_time).zfill(4)
                fmt = f"{t_str[:2]}:{t_str[2:]}"
                dur_text = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"

                with ui.row().classes('w-full bg-rose border-l-4 border-rose-500 shadow-sm rounded-r-lg p-3 justify-between items-center group transition-all hover:shadow-md'):
                    with ui.row().classes('items-center gap-4'):
                        with ui.column().classes('items-center leading-none px-2'):
                            ui.label(dt.strftime('%d')).classes('text-xl font-white text-slate-700')
                            ui.label(dt.strftime('%b')).classes('text-[10px] font-bold uppercase text-slate-400')
                        
                        with ui.column().classes('gap-0'):
                            with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                                ui.label(f"{days_of_week[dt.weekday()]} - {fmt}").classes('font-bold text-slate-800 text-sm')
                                if c.status == 'Prueba_Pendiente':
                                    ui.label('Clase de Prueba').classes('mt-1 text-[10px] font-bold text-purple-600 uppercase bg-purple-100 px-2 py-0.5 rounded-full')   
                                else:
                                    ui.label('Clase Regular').classes('mt-1 text-[10px] font-bold text-rose-600 uppercase bg-rose-100 px-2 py-0.5 rounded-full')
                                
                                if getattr(c, 'class_count', None):
                                    ui.label(f"Clase {c.class_count}").classes('text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100')

                            ui.label(f'Inglés General ({dur_text})').classes('text-xs text-slate-500')
                    
                    ui.button(icon='close', on_click=lambda x=c: delete_class_dialog(x)).props('flat round dense color=slate size=sm').classes('opacity-0 group-hover:opacity-100 transition-opacity')

    def delete_class_dialog(c_obj):
        with ui.dialog() as d, ui.card().classes('rounded-xl'):
            ui.label('¿Cancelar clase?').classes('font-bold text-lg')
            ui.label(f"{c_obj.date} a las {c_obj.start_time} hrs").classes('text-sm text-slate-500')
            with ui.row().classes('w-full justify-end mt-4 gap-2'):
                ui.button('No', on_click=d.close).props('flat text-color=slate')
                del_btn = ui.button('Sí, Cancelar').props('unelevated color=red')
                async def do_del():
                    del_btn.props('loading')
                    sess = PostgresSession()
                    try:
                        sess.query(AsignedClasses).filter(AsignedClasses.id == c_obj.id).delete()
                        sess.commit()
                        ui.notify('Clase cancelada', type='info')
                        d.close()
                        await update_dashboard() 
                    except: pass
                    finally: sess.close()
                del_btn.on('click', do_del)
        d.open()

    @ui.refreshable
    def render_stats_widget():
        session = PostgresSession()
        pkg, limit, used_curr = get_current_package_usage(session, username)
        
        total_lifetime = session.query(AsignedClasses).filter(
            AsignedClasses.username == username,
            AsignedClasses.status != 'Cancelled'
        ).count()
        session.close()
        
        percent = min(used_curr/limit, 1.0) if limit > 0 else 0

        # Contenedor de la tarjeta con degradado sutil y borde suave
        with ui.card().classes('w-full rounded-2xl p-1 bg-gradient-to-br from-white to-pink-50 border border-pink-100 shadow-sm hover:shadow-md transition-all duration-300 cursor-pointer group'):
            with ui.row().classes('items-center no-wrap px-4 py-3 gap-4'):
                
                # 1. AVATAR (Con anillo y efecto de brillo)
                with ui.element('div').classes('relative'):
                    # El contenedor de la imagen
                    with ui.element('div').classes('w-12 h-12 rounded-full p-0.5 bg-gradient-to-tr from-rose-400 to-purple-400 shadow-lg group-hover:scale-105 transition-transform'):
                        with ui.element('div').classes('w-full h-full rounded-full bg-white overflow-hidden p-0.5'):
                            ui.image('/static/icon/logo.png').classes('w-full h-full object-cover rounded-full')
                    
                    # Indicador de "En línea" (Punto verde)
                    ui.element('div').classes('absolute bottom-0 right-0 w-3 h-3 bg-emerald-400 border-2 border-white rounded-full')

                # 2. TEXTO (Mejor estructurado)
                with ui.column().classes('gap-0.5 flex-1'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('¿Necesitas ayuda?').classes('text-sm font-bold text-slate-800')
                        # Pequeña etiqueta "AI"
                        ui.label('AI').classes('text-[10px] font-black bg-rose-100 text-rose-600 px-1.5 rounded')
                    
                    ui.label('Pregúntale a Chipi AI si tienes alguna duda sobre como crear tu horario.').classes('text-xs text-slate-500 leading-tight')

                # 3. ICONO DE ACCIÓN (Flecha sutil)
                ui.icon('chat_bubble_outline', size='sm').classes('text-rose-300 group-hover:text-rose-500 transition-colors duration-100')
            
        with ui.card().classes('w-full p-5 rounded-2xl bg-white shadow-sm border border-slate-100 gap-4'):
            with ui.column().classes('w-full gap-2'):
                ui.label("Plan Actual (Mes)").classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                with ui.row().classes('items-center gap-4 w-full'):
                    with ui.circular_progress(value=percent, show_value=False, color='rose', size='50px').props('thickness=0.2 track-color=grey-2'):
                        ui.icon('school', color='rose', size='xs')
                    with ui.column().classes('gap-0 flex-1'):
                        ui.label(pkg).classes('font-bold text-slate-800 text-lg leading-tight')
                        ui.label(f"{used_curr} de {limit} clases").classes('text-xs text-slate-500')

            ui.separator()

            with ui.column().classes('w-full gap-1'):
                ui.label("Trayectoria").classes('text-xs font-bold text-slate-400 uppercase tracking-widest')
                with ui.row().classes('items-center gap-3 mt-1'):
                    ui.icon('emoji_events', color='amber-500', size='sm')
                    with ui.column().classes('gap-0'):
                        ui.label(f"{total_lifetime} Clases").classes('font-bold text-slate-700')
                        ui.label("Agendadas en total").classes('text-[10px] text-slate-400')
        

            # === ZONA DE INFORMACIÓN (Estilo Moderno/Premium) ===
            user_tz = get_user_timezone()

        with ui.row().classes('w-full p-3 rounded-2xl bg-gradient-to-br from-white to-gray-50 border border-blue-100 shadow-sm items-center gap-3'):
                
                # 1. ICONO (Estilo "Glass" azulado)
                # Contenedor con fondo suave y anillo sutil
                with ui.element('div').classes('p-2.5 bg-blue-50 rounded-xl flex items-center justify-center ring-1 ring-blue-100'):
                    ui.icon('public', color='gray-600', size='xs')
                
                # 2. TEXTO
                with ui.column().classes('gap-0.5 flex-1'):
                    # Cabecera con Título y la Zona Horaria destacada
                    with ui.row().classes('items-center gap-2'):
                        ui.label('Sincronización Activa').classes('text-xs font-bold text-blue-900 uppercase tracking-wide')
                        # Badge para la zona horaria
                        ui.label(user_tz).classes('text-[10px] font-bold bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-md border border-blue-200')

                    # Cuerpo del mensaje (Markdown limpio)
                    ui.markdown(
                        "Ves la **disponibilidad real de la profesora** convertida automáticamente a tu hora local. "
                        "<span class='text-blue-500 italic'>No necesitas calcular diferencias.</span>"
                    ).classes('text-xs text-slate-600 leading-snug')

    # CORRECCIÓN 2: Lógica de dashboard optimizada para feedback visual inmediato
    async def update_dashboard():
        # 1. Activamos carga
        state['loading'] = True
        
        # 2. Refrescamos UI inmediatamente (Bloquea sidebar, Muestra spinner)
        render_sidebar.refresh()
        render_slots_area.refresh()
        
        # 3. Pausa para permitir repintado de UI
        await asyncio.sleep(0.1)

        # 4. Cálculos pesados
        lifetime_count = get_all_time_classes()
        is_trial_now = (lifetime_count == 0)
        
        if state['is_trial'] != is_trial_now:
            state['is_trial'] = is_trial_now
            state['duration'] = 30 if is_trial_now else 60

        render_header_area.refresh()
        render_my_classes.refresh()
        render_stats_widget.refresh()

        # 5. Finalizamos carga y desbloqueamos
        state['loading'] = False
        render_sidebar.refresh()
        render_slots_area.refresh()

    async def on_date_change(e):
        await update_dashboard()

    # CORRECCIÓN 3: Decorador y propiedad disable dinámica
    @ui.refreshable
    def render_sidebar():
        with ui.column().classes('w-full gap-6'):
            with ui.card().classes('w-full p-4 rounded-2xl shadow-sm border border-slate-100 bg-white'):
                is_disabled = state.get('loading', False)
                ui.date(value=state['date']) \
                    .bind_value(state, 'date') \
                    .on('update:model-value', on_date_change) \
                    .props(f'flat color=rose class="w-full" {"disable" if is_disabled else ""}')
            
            render_stats_widget()

    @ui.refreshable
    def render_header_area():
        if state['is_trial']:
            main_title = "Selecciona tu clase de prueba"
            sub_color = "text-purple-600"
        else:
            main_title = "Reservar Horario"
            sub_color = "text-rose-500"
        
        async def on_duration_change(e):
            await update_dashboard()

        with ui.row().classes('items-center justify-between w-full'):
            with ui.column().classes('gap-0'):
                with ui.row().classes('w-full items-center justify-between mb-2 relative'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('book', size='lg', color='pink-600')
                        with ui.column().classes('gap-0'):
                            ui.label(main_title).classes('text-2xl font-bold text-slate-800')
                            ui.label().bind_text_from(state, 'date', 
                                backward=lambda d: datetime.strptime(d, '%Y-%m-%d').strftime('%A, %d de %B') if d else "Cargando..."
                            ).classes(f'{sub_color} font-medium')
                          
            with ui.row().classes('items-center gap-4'):
                if not state['is_trial']:
                    ui.toggle({30: '30 min', 60: '1 Hora'}, value=60).bind_value(state, 'duration') \
                        .on('update:model-value', on_duration_change) \
                        .props('no-caps push color=white text-color=rose-600 toggle-color=rose-600 toggle-text-color=white')

                refresh_btn = ui.button(icon='refresh').props('flat round color=slate')
                async def do_refresh():
                    refresh_btn.props('loading')
                    await update_dashboard()
                    refresh_btn.props(remove='loading')
                refresh_btn.on('click', do_refresh)

    def render_main_content():
        with ui.column().classes('w-full gap-8'):
            render_header_area()
            render_slots_area()
            ui.separator().classes('my-2 bg-slate-200')
            with ui.column().classes('w-full gap-4'):
                ui.label('Mis Próximas Sesiones').classes('text-lg font-bold text-slate-800')
                render_my_classes()

    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8'):
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-12 gap-8 items-start'):
            with ui.column().classes('lg:col-span-4 w-full order-2 lg:order-1'):
                render_sidebar()
            with ui.column().classes('lg:col-span-8 w-full order-1 lg:order-2'):
                render_main_content()
        
    render_floating_chatbot('schedule')