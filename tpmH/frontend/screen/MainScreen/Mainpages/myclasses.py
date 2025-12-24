from nicegui import ui, app
from datetime import datetime
import logging
from db.sqlite_db import BackupSession

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.models import AsignedClasses, User, ScheduleProf, ScheduleProfEsp, SchedulePref
from components.header import create_main_screen
from components.share_data import days_of_week, PACKAGE_LIMITS, pack_of_classes
from zoneinfo import ZoneInfo # Para manejo preciso de zonas al reagendar
from datetime import datetime, timedelta
import asyncio  # Importamos asyncio para corregir el error del loop
from prompts.chatbot import render_floating_chatbot

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@ui.page('/myclasses')
def my_classes():
    # Estilos globales consistentes
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_main_screen()

    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # Estados que obligan a mover la clase al historial
    HISTORY_STATUSES = {'Finalizada', 'Completada', 'No Asistió', 'Cancelada'}

    # Variable para almacenar info del usuario (se llena en get_user_classes)
    user_state = {
        'package': 'None', 
        'class_count_str': '0/0', 
        'current': 0, 
        'limit': 0,
        'total_classes': 0
    }

    # 2. LOGICA DE DATOS
    def get_user_classes():
        session = PostgresSession()
        try:
            # A. Obtener Datos del Usuario
            user = session.query(User).filter(User.username == username).first()
            if user:
                user_state['package'] = user.package
                user_state['class_count_str'] = user.class_count or "0/0"
                user_state['total_classes'] = user.total_classes or '0'
                # Guardamos la zona horaria para usarla en las comparaciones
                user_state['timezone'] = user.time_zone if user.time_zone else 'America/Caracas'
                
                # Parsear "X/Y"
                try:
                    curr, lim = map(int, str(user_state['class_count_str']).split('/'))
                    user_state['current'] = curr
                    user_state['limit'] = lim
                except:
                    user_state['current'] = 0
                    user_state['limit'] = PACKAGE_LIMITS.get(user.package, 0)

            # --- CORRECCIÓN CRÍTICA DE TIEMPO ---
            # 1. Definir "Ahora" según la zona del usuario, no la del servidor (UTC)
            try:
                user_tz = ZoneInfo(user_state['timezone'])
            except:
                user_tz = ZoneInfo('America/Caracas')

            # Obtenemos la hora actual en la zona del usuario y quitamos la info de zona
            # para poder comparar con las fechas 'naive' de la base de datos.
            now_user_local = datetime.now(user_tz).replace(tzinfo=None)

            # B. Actualizar estados (Auto-Finalizar clases pasadas)
            active_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status.in_(['Pendiente', 'Prueba_Pendiente'])
            ).all()
            
            updates = False
            for c in active_classes:
                try:
                    # Convertir fecha y hora de la clase a objeto datetime
                    # start_time viene como entero (ej: 1200) -> string "1200"
                    t_str = str(c.start_time).zfill(4) 
                    c_start = datetime.strptime(f"{c.date} {t_str}", "%Y-%m-%d %H%M")
                    
                    # Calcular hora de FIN (Inicio + Duración)
                    # Si no tiene duración, asumimos 60 min
                    dur = int(c.duration) if c.duration else 60
                    c_end = c_start + timedelta(minutes=dur)

                    # Si la hora actual (usuario) es mayor que la hora de FIN de la clase
                    if now_user_local > c_end:
                        c.status = 'Finalizada'
                        updates = True
                except Exception as e:
                    logger.error(f"Error procesando fecha clase {c.id}: {e}")
            
            if updates:
                session.commit()

            # C. Obtener listas para mostrar
            all_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username
            ).all()
            
            upcoming = []
            history = []
            
            for c in all_classes:
                # Reutilizamos lógica de comparación para consistencia visual
                is_history_status = c.status in HISTORY_STATUSES
                
                # Calcular si ya pasó en el tiempo (lógica visual)
                is_past_time = False
                try:
                    t_str = str(c.start_time).zfill(4)
                    c_start = datetime.strptime(f"{c.date} {t_str}", "%Y-%m-%d %H%M")
                    dur = c.duration if c.duration else 60
                    c_end = c_start + timedelta(minutes=dur)
                    
                    if now_user_local > c_end:
                        is_past_time = True
                except:
                    is_past_time = False

                if is_history_status or is_past_time:
                    history.append(c)
                else:
                    if c.status != 'Cancelada':
                        upcoming.append(c)
            
            upcoming.sort(key=lambda x: (x.date, x.start_time))
            history.sort(key=lambda x: (x.date, x.start_time), reverse=True)
            
            return upcoming, history
        except Exception as e:
            logger.error(f"Error fetching classes: {e}")
            return [], []
        finally:
            session.close()

    async def cancel_class(c_id, dialog):
        session = PostgresSession()
        try:
            class_to_delete = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            
            if class_to_delete:
                c_username = class_to_delete.username
                c_date = class_to_delete.date
                c_start_time = class_to_delete.start_time
                
                session.delete(class_to_delete)
                session.commit()

                # Backup SQLite
                try:
                    bk_sess = BackupSession()
                    bk_cls = bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == c_username,
                        AsignedClasses.date == c_date,
                        AsignedClasses.start_time == c_start_time
                    ).first()
                    if bk_cls:
                        bk_sess.delete(bk_cls)
                        bk_sess.commit()
                    bk_sess.close()
                except Exception as e:
                    logger.error(f"Error backup sqlite delete: {e}")

                ui.notify('Clase cancelada exitosamente', type='positive', icon='check')
                dialog.close()
                refresh_ui() 
            else:
                ui.notify("No se encontró la clase a cancelar.", type='warning')
                
        except Exception as e:
            ui.notify(f"Error al cancelar: {e}", type='negative')
        finally:
            session.close()
    
    POSITIVE_STATUS = ["Libre", "Available", "Disponible"]

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

    # --- LÓGICA DE RENOVACIÓN DE SUSCRIPCIÓN (ACTUALIZADA) ---
    async def renew_subscription(new_plan_name):
        session = PostgresSession()
        try:
            u = session.query(User).filter(User.username == username).first()
            if u:
                # 1. Actualizar Plan
                u.package = new_plan_name
                
                # 2. Obtener nuevo límite
                new_limit = PACKAGE_LIMITS.get(new_plan_name, 0)
                new_count_str = f"0/{new_limit}"
                
                # 3. RESETEAR CONTADORES A 0 EN USER
                u.class_count = new_count_str
                u.total_classes = 0 
                
                # --- ACTUALIZAR payment_info (solo Clases_paquete) ---
                if u.payment_info:
                    try:
                        pi = u.payment_info.copy()
                        pi["Clases_paquete"] = f"0/{new_limit}"
                        u.payment_info = pi
                    except Exception as json_err:
                        logger.error(f"Error actualizando payment_info: {json_err}")

                # --- NUEVA LÓGICA: INCREMENTAR RENOVACIONES ---
                current_renovations = u.renovations if u.renovations is not None else 0
                u.renovations = current_renovations + 1
                logger.info(f"Usuario {username} renovado. Renovaciones totales: {u.renovations}")
                
                # 4. ELIMINAR TODAS LAS CLASES (Reset total)
                session.query(AsignedClasses).filter(
                    AsignedClasses.username == username
                ).delete(synchronize_session=False)

                session.commit()

                # Backup SQLite
                try:
                    bk_sess = BackupSession()
                    
                    # Update User in Backup
                    bk_u = bk_sess.query(User).filter(User.username == username).first()
                    if bk_u:
                        bk_u.package = new_plan_name
                        bk_u.class_count = new_count_str
                        bk_u.total_classes = 0

                        # --- ACTUALIZAR payment_info EN BACKUP ---
                    if bk_u.payment_info:
                        try:
                            bk_pi = bk_u.payment_info.copy()
                            bk_pi["Clases_paquete"] = f"0/{new_limit}"
                            bk_u.payment_info = bk_pi
                        except Exception as json_err_bk:
                            logger.error(f"Error actualizando payment_info en backup: {json_err_bk}")
                        
                        # --- ACTUALIZAR BACKUP (Renovations) ---
                        bk_renovations = bk_u.renovations if bk_u.renovations is not None else 0
                        bk_u.renovations = bk_renovations + 1
                    
                    # Delete Classes in Backup
                    bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == username
                    ).delete(synchronize_session=False)
                    
                    bk_sess.commit()
                    bk_sess.close()
                except Exception as ex_bk:
                    logger.error(f"Error backup update: {ex_bk}")

                ui.notify(f"Suscripción actualizada a {new_plan_name}. Historial reiniciado.", type='positive', icon='verified')
                refresh_ui()
            else:
                ui.notify("Usuario no encontrado", type='negative')
        except Exception as e:
            ui.notify(f"Error renovando: {e}", type='negative')
        finally:
            session.close()

    def open_renewal_dialog():
        current_plan = user_state['package']
        
        with ui.dialog() as d, ui.card().classes('w-96 p-6 rounded-2xl'):
            ui.label('Actualizar Suscripción').classes('text-xl font-bold text-slate-800 mb-2')
            ui.label('Has completado todas las clases de tu paquete actual.').classes('text-sm text-slate-500 mb-4')
            
            # --- MANEJADORES ASÍNCRONOS ---
            async def handle_repeat():
                d.close()
                await renew_subscription(current_plan)

            # Opción 1: Repetir
            ui.button(f'Repetir {current_plan}', 
                      icon='replay', 
                      on_click=handle_repeat
            ).props('unelevated color=blue-600 w-full').classes('mb-3')
            
            ui.separator().classes('mb-3')
            
            # Opción 2: Cambiar
            ui.label('O cambiar a otro plan:').classes('text-xs font-bold text-slate-400 uppercase mb-2')
            
            available_plans = sorted([p for p in pack_of_classes if p != 'None'])
            select_plan = ui.select(available_plans, label='Seleccionar Plan').props('outlined dense w-full').classes('w-full mb-4')
            
            async def handle_change():
                if select_plan.value:
                    d.close()
                    await renew_subscription(select_plan.value)
                else:
                    ui.notify('Selecciona un plan', type='warning')

            ui.button('Cambiar Plan', 
                      icon='switch_access_shortcut', 
                      on_click=handle_change
            ).props('outline color=slate w-full')

        d.open()

    # 3. COMPONENTES VISUALES
    
    def render_stat_card(icon, label, value, color_class, text_color):
        """Tarjeta pequeña de estadísticas"""
        with ui.card().classes('flex-1 p-4 rounded-xl shadow-sm border border-slate-100 items-center justify-between flex-row min-w-[150px]'):
            with ui.column().classes('gap-1'):
                ui.label(str(value)).classes(f'text-3xl font-bold {text_color} leading-none')
                ui.label(label).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
            
            with ui.element('div').classes(f'p-3 rounded-full {color_class}'):
                ui.icon(icon, color='white', size='sm')

    def render_class_card(c, is_history=False):
        """Renderiza una tarjeta de clase individual"""
        dt = datetime.strptime(c.date, '%Y-%m-%d')
        t_str = str(c.start_time).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        duration_txt = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
        
        # Lógica de Colores y Etiquetas
        if is_history:
            border_color = "border-slate-300"
            bg_badge = "bg-slate-100 text-slate-500"
            status_txt = c.status.replace('_', ' ')
            type_txt = "Historial"
            opacity = "opacity-75 hover:opacity-100 transition-opacity"
            
            if c.status == 'Completada':
                status_txt = "Completada"
                bg_badge = "bg-green-100 text-green-700"
                border_color = "border-green-500"
            elif c.status == 'No Asistió':
                bg_badge = "bg-gray-200 text-gray-700"
                border_color = "border-gray-400"
            elif c.status == 'Cancelada':
                bg_badge = "bg-red-100 text-red-700"
                border_color = "border-red-400"

        else:
            opacity = ""
            status_txt = "Agendada"
            
            if c.status == 'Prueba_Pendiente':
                type_txt = "Clase de Prueba"
                bg_badge = "bg-purple-100 text-purple-700"
                border_color = "border-purple-500"
            else:
                type_txt = "Clase Regular"
                bg_badge = "bg-rose-100 text-rose-700"
                border_color = "border-rose-500"

        with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-row overflow-hidden group {opacity}'):
            
            with ui.column().classes(f'w-24 justify-center items-center bg-slate-50 border-r-4 {border_color} p-4 gap-0'):
                ui.label(dt.strftime('%d')).classes('text-3xl font-bold text-slate-700 leading-none')
                ui.label(dt.strftime('%b')).classes('text-xs font-bold uppercase text-slate-400 mt-1')
                ui.label(dt.strftime('%Y')).classes('text-[10px] text-slate-300')

            with ui.column().classes('flex-1 p-4 justify-center gap-1'):
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    ui.label(f"{days_of_week[dt.weekday()]} • {fmt_time}").classes('text-lg font-bold text-slate-800')
                    
                    ui.label(status_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')
                    
                    if not is_history:
                        ui.label(type_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')

                    if hasattr(c, 'class_count') and c.class_count:
                        ui.label(f"Clase {c.class_count}").classes('text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100')

                    if hasattr(c, 'total_classes') and c.total_classes:
                        ui.label(f"Total #{c.total_classes}").classes('text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100')

                with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('schedule', size='xs')
                        ui.label(duration_txt)
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('school', size='xs')
                        ui.label('Inglés General')
                    if not is_history:
                        ui.button('Reagendar', icon='edit_calendar', on_click=lambda: open_reschedule_dialog(c)) \
                            .props('flat dense color=blue-600 size=sm').classes('mt-2')

            if not is_history:
                with ui.column().classes('h-full items-center justify-center pr-4'):
                    btn = ui.button(icon='delete_outline', color='slate').props('flat round')
                    btn.classes('my-auto text-slate-400 hover:text-red-500 transition-colors')
                    
                    def open_confirm(c_id=c.id):
                        with ui.dialog() as d, ui.card().classes('rounded-xl p-6 w-80'):
                            ui.label('¿Cancelar esta clase?').classes('text-lg font-bold text-slate-800')
                            ui.label('Esta acción no se puede deshacer.').classes('text-sm text-slate-500 mb-4')
                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Volver', on_click=d.close).props('flat text-color=slate')
                                cancel_btn = ui.button('Confirmar Cancelación', on_click=lambda: cancel_class(c_id, d))
                                cancel_btn.props('unelevated color=red')
                        d.open()
                    
                    btn.on('click', open_confirm)

    @ui.refreshable
    def render_content():
        upcoming, history = get_user_classes()
        
        curr = user_state['current']
        limit = user_state['limit']
        pkg_name = user_state['package']
        total_classes = user_state['total_classes']


        raw_package = str(user_state.get('package', 'None'))
        pkg_name_clean = raw_package.strip()
        total_classes_raw = user_state.get('total_classes', 0)
        int_total_clases = int(total_classes_raw)
        flex_limit = 5

        print(f"DEBUG -> Paquete DB: '{raw_package}' | Limpio: '{pkg_name_clean}' | Total Clases: {int_total_clases}")

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
            
            with ui.row().classes('w-full justify-between items-end'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('book', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Mis Clases').classes('text-3xl font-bold text-slate-800')
                        ui.label(f'Bienvenido, {username}').classes('text-slate-500 font-medium')
                    
                # LÓGICA DE BOTÓN
                if pkg_name_clean == 'Flexible' and int_total_clases >= flex_limit:
                    
                    with ui.row().classes('items-center gap-2'):
                        # Botón 1: Agendar
                        ui.button('Agendar Nueva', icon='add', on_click=lambda: ui.navigate.to('/ScheduleMaker')) \
                            .props('unelevated color=rose-600').classes('rounded-xl px-4 py-2 shadow-md shadow-rose-200 hover:shadow-lg transition-all')
                        
                        # Botón 2: Actualizar (Ahora con estilo visible)
                        ui.button('Actualizar Suscripción', icon='published_with_changes', on_click=open_renewal_dialog) \
                            .props('unelevated color=amber-600').classes('rounded-xl px-4 py-2 shadow-md shadow-amber-200 hover:shadow-lg transition-all')
                elif limit > 0 and curr >= limit:
                    ui.button('Actualizar Suscripción', icon='published_with_changes', on_click=open_renewal_dialog) \
                        .props('unelevated color=amber-600').classes('rounded-xl px-4 py-2 shadow-md shadow-amber-200 hover:shadow-lg transition-all animate-bounce')
                else:
                    ui.button('Agendar Nueva', icon='add', on_click=lambda: ui.navigate.to('/ScheduleMaker')) \
                        .props('unelevated color=rose-600').classes('rounded-xl px-4 py-2 shadow-md shadow-rose-200 hover:shadow-lg transition-all')

            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('event', 'Próximas', len(upcoming), 'bg-rose-500', 'text-rose-600')
                render_stat_card('history', 'Historial', len(history), 'bg-purple-500', 'text-purple-600')
                
                if limit > 0:
                    prog_color = 'bg-green-500' if curr < limit else 'bg-amber-500'
                    text_prog = 'text-green-600' if curr < limit else 'text-amber-600'
                    render_stat_card('inventory_2', f'Plan {pkg_name}', f"{curr}/{limit}", prog_color, text_prog)
                else:
                    render_stat_card('school', 'COMPLETADAS', total_classes , 'bg-slate-500', 'text-slate-600')

            with ui.card().classes('w-full rounded-2xl shadow-sm border border-slate-100 p-0 overflow-hidden bg-transparent shadow-none border-none'):
                
                with ui.tabs().classes('w-full justify-start text-slate-500 bg-transparent') \
                        .props('active-color=rose indicator-color=rose align=left narrow') as tabs:
                    t_upcoming = ui.tab('Próximas').classes('capitalize font-bold')
                    t_history = ui.tab('Historial').classes('capitalize font-bold')

                ui.separator().classes('mb-4')

                with ui.tab_panels(tabs, value=t_upcoming).classes('w-full bg-transparent'):
                    
                    with ui.tab_panel(t_upcoming).classes('p-0 gap-4 flex flex-col'):
                        if not upcoming:
                            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                                ui.icon('event_available', size='4xl', color='slate-300')
                                ui.label("Todo despejado").classes('text-slate-500 font-bold mt-4')
                                ui.label("No tienes clases agendadas próximamente.").classes('text-sm text-slate-400')
                        else:
                            for c in upcoming:
                                render_class_card(c, is_history=False)

                    with ui.tab_panel(t_history).classes('p-0 gap-4 flex flex-col'):
                        if not history:
                            with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                                ui.label("Aún no tienes historial de clases.").classes('text-sm italic')
                        else:
                            for c in history:
                                render_class_card(c, is_history=True)

    
    

    def refresh_ui():
        render_content.refresh()

    render_content()
    render_floating_chatbot('my_classes')