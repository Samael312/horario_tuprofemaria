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

   # --- LÓGICA DE REAGENDAMIENTO (VERSIÓN ESTUDIANTE) ---
    async def reschedule_class(c_id, new_student_date, new_student_time_int, dialog):
        session = PostgresSession()
        try:
            cls = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            if cls:
                # 1. Guardar valores viejos para Backup y Cálculos
                old_date = cls.date
                old_start = cls.start_time
                old_date_prof = cls.date_prof
                old_start_prof = cls.start_prof_time
                username = cls.username
                duration = int(cls.duration) if cls.duration else 60

                # 2. CALCULAR LA DIFERENCIA HORARIA (Time Delta)
                # Necesitamos saber la diferencia entre el horario del estudiante y el del profesor
                # para proyectar el nuevo horario del profesor automáticamente.
                
                # Convertimos horario actual a objetos datetime
                s_curr_str = str(old_start).zfill(4)
                curr_stu_dt = datetime.strptime(f"{old_date} {s_curr_str[:2]}:{s_curr_str[2:]}", "%Y-%m-%d %H:%M")
                
                p_curr_str = str(old_start_prof).zfill(4)
                curr_prof_dt = datetime.strptime(f"{old_date_prof} {p_curr_str[:2]}:{p_curr_str[2:]}", "%Y-%m-%d %H:%M")
                
                # Calculamos el desplazamiento (Offset)
                time_offset = curr_prof_dt - curr_stu_dt

                # 3. PROYECTAR NUEVOS HORARIOS
                # Creamos el datetime objetivo del estudiante
                s_new_str = str(new_student_time_int).zfill(4)
                new_stu_dt = datetime.strptime(f"{new_student_date} {s_new_str[:2]}:{s_new_str[2:]}", "%Y-%m-%d %H:%M")
                
                # Calculamos el fin del estudiante
                new_stu_end_dt = new_stu_dt + timedelta(minutes=duration)
                new_student_end_int = int(new_stu_end_dt.strftime("%H%M"))

                # Calculamos el nuevo inicio y fin del Profesor (Aplicando el offset)
                new_prof_dt = new_stu_dt + time_offset
                new_prof_end_dt = new_prof_dt + timedelta(minutes=duration)

                # Extraemos valores para la BD
                new_prof_date = new_prof_dt.strftime("%Y-%m-%d")
                new_prof_time_int = int(new_prof_dt.strftime("%H%M"))
                new_prof_end_int = int(new_prof_end_dt.strftime("%H%M"))

                # Nombre del día
                new_day_name = days_of_week[new_stu_dt.weekday()]

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
                    logger.error(f"Error backup reschedule student: {e}")

                ui.notify(f"Clase reagendada correctamente.", type='positive')
                if dialog: dialog.close()
                refresh_ui() # Asegúrate de tener acceso a esta función o pásala como callback
            else:
                ui.notify("Clase no encontrada", type='negative')
        except Exception as e:
            ui.notify(f"Error al reagendar: {e}", type='negative')
            logger.error(f"Error student reschedule: {e}")
        finally:
            session.close()


    def open_reschedule_dialog(c):
        
        
        # === 1. LÓGICA INTERNA PARA OBTENER HUECOS ===
        def get_slots_data(date_str):
            session = PostgresSession()
            slots_data = []
            try:
                if not date_str: return []
                
                # Normalizar fecha
                d_clean = date_str.replace('/', '-')
                try:
                    dt = datetime.strptime(d_clean, '%Y-%m-%d')
                except ValueError:
                    return []
                
                query_date = dt.strftime('%Y-%m-%d')
                day_name = days_of_week[dt.weekday()] # Asegúrate de importar days_of_week
                
                # A) Disponibilidad de la Profesora
                rules = session.query(ScheduleProfEsp).filter_by(date=query_date).all()
                if not rules:
                    rules = session.query(ScheduleProf).filter_by(days=day_name).all()
                
                avail_ranges = []
                POSITIVE_STATUS = ["Libre", "Available", "Disponible"] # O impórtalo de share_data
                
                for r in rules:
                    status = str(r.avai if hasattr(r, 'avai') else r.availability)
                    if status in POSITIVE_STATUS:
                        avail_ranges.append((r.start_time, r.end_time))
                
                # B) Ocupado Profesora (Excluyendo la clase actual 'c.id')
                busy = session.query(AsignedClasses).filter(
                    AsignedClasses.date_prof == query_date,
                    AsignedClasses.status.notin_(['Cancelled', 'Cancelada']),
                    AsignedClasses.id != c.id  # CLAVE: Ignoramos la clase actual para poder moverla al mismo día
                ).all()
                busy_ranges = [(b.start_prof_time, b.end_prof_time) for b in busy if b.start_prof_time]

                # C) Zonas Horarias (Automáticas)
                # 1. Alumno
                user = session.query(User).filter(User.username == c.username).first()
                student_tz_str = user.time_zone if user and user.time_zone else 'UTC'
                
                # 2. Profesora (Buscamos al primer admin)
                admin_user = session.query(User).filter(User.role == 'admin').first()
                teacher_tz_str = admin_user.time_zone if admin_user and admin_user.time_zone else 'America/Caracas'

                # D) Generar Slots
                try:
                    duration = int(float(c.duration)) if c.duration else 60
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
                            if (curr_m < b_e_m) and (s_end_m > b_s_m):
                                is_busy = True
                                break
                        
                        if not is_busy:
                            valid_slots.append(to_hhmm_int(curr_m))
                        
                        curr_m += step 
                
                unique_slots = sorted(list(set(valid_slots)))
                
                # E) Conversión Final
                for slot in unique_slots:
                    t_h, t_m = slot // 100, slot % 100
                    t_str = f"{str(t_h).zfill(2)}:{str(t_m).zfill(2)}"
                    
                    try:
                        prof_tz = ZoneInfo(teacher_tz_str)
                        stud_tz = ZoneInfo(student_tz_str)
                        
                        # Hora "maestra" (Profesor)
                        dt_prof = datetime.strptime(f"{query_date} {t_str}", "%Y-%m-%d %H:%M").replace(tzinfo=prof_tz)
                        
                        # Convertir a Alumno
                        dt_stud = dt_prof.astimezone(stud_tz)
                        
                        # Calcular fin para guardarlo bien luego
                        dt_prof_end = dt_prof + timedelta(minutes=duration)
                        dt_stud_end = dt_stud + timedelta(minutes=duration)
                        
                        s_time_str = dt_stud.strftime("%H:%M")
                        s_date_str = dt_stud.strftime("%Y-%m-%d")
                        s_time_int = int(dt_stud.strftime("%H%M"))
                        s_end_int = int(dt_stud_end.strftime("%H%M"))
                        s_weekday = days_of_week[dt_stud.weekday()]
                        
                        # Preferencias
                        is_preferred = False
                        prefs = session.query(SchedulePref).filter(
                            SchedulePref.username == c.username,
                            SchedulePref.days == s_weekday
                        ).all()
                        for p in prefs:
                            if p.start_time <= s_time_int < p.end_time:
                                is_preferred = True; break
                        
                        day_diff = ""
                        if s_date_str != query_date:
                            day_diff = f"({s_weekday})" 

                        slots_data.append({
                            't_time_int': slot,             # Inicio Prof (INT)
                            't_end_int': int(dt_prof_end.strftime("%H%M")), # Fin Prof (INT)
                            't_date': query_date,           # Fecha Prof (STR)
                            't_time_str': t_str,            # Inicio Prof (Visual)
                            
                            's_time_int': s_time_int,       # Inicio Alumno (INT)
                            's_end_int': s_end_int,         # Fin Alumno (INT)
                            's_date': s_date_str,           # Fecha Alumno (STR)
                            's_weekday': s_weekday,         # Día Alumno (STR)
                            
                            's_time_str': s_time_str,       # Visual
                            's_day_diff': day_diff,
                            'is_preferred': is_preferred
                        })
                        
                    except Exception as ex:
                        logger.error(f"Timezone calc error: {ex}")

            except Exception as e:
                logger.error(f"Error getting slots: {e}")
            finally:
                session.close()
            return slots_data

        # === 2. INTERFAZ GRÁFICA (UI) ===
        
        with ui.dialog() as d, ui.card().classes('w-full max-w-[900px] h-[85vh] p-0 rounded-2xl flex flex-col overflow-hidden shadow-2xl'):
            
            # Header
            with ui.row().classes('w-full bg-slate-800 text-white p-6 justify-between items-center shrink-0'):
                with ui.column().classes('gap-1'):
                    ui.label('Reagendar Clase').classes('text-xl font-bold tracking-wide')
                    ui.label(f'Clase actual: {c.date} a las {c.start_time}').classes('text-xs text-slate-400')
                ui.button(icon='close', on_click=d.close).props('flat round dense color=white')

            # Contenido Scrollable
            with ui.column().classes('w-full flex-1 p-6 gap-6 overflow-hidden bg-slate-50'):
                
                # Selector de Fecha
                with ui.row().classes('w-full items-end gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm'):
                    # Usamos date_prof si existe (fecha maestra), si no date
                    default_date = c.date_prof if c.date_prof else c.date
                    
                    date_input = ui.input('Selecciona Fecha (Base Profesora)', value=default_date).props('outlined dense mask="####-##-##"').classes('flex-1')
                    with ui.menu().props('no-parent-event') as menu:
                            ui.date().bind_value(date_input).props('mask="YYYY-MM-DD"')
                    with date_input.add_slot('append'):
                        ui.icon('event').classes('cursor-pointer text-indigo-500').on('click', menu.open)
                    
                    search_btn = ui.button('Buscar Disponibilidad', icon='search') \
                        .props('unelevated color=indigo-600') \
                        .classes('h-[40px] px-6 font-bold')
                
                # Área de Resultados
                results_container = ui.column().classes('w-full flex-1 overflow-y-auto pr-2 gap-4')
                spinner = ui.spinner('dots', size='3em', color='indigo').classes('self-center hidden')

                async def show_slots():
                    results_container.clear()
                    spinner.classes(remove='hidden')
                    
                    date_val = date_input.value
                    # Ejecutar en hilo aparte
                    slots = await asyncio.to_thread(get_slots_data, date_val)
                    
                    spinner.classes(add='hidden')
                    
                    if not slots:
                        with results_container:
                            with ui.column().classes('w-full items-center justify-center py-10 opacity-50'):
                                ui.icon('event_busy', size='4xl', color='slate')
                                ui.label('No hay horarios disponibles esta fecha.').classes('text-lg')
                        return

                    with results_container:
                        ui.label(f'Opciones para {date_val}:').classes('text-xs font-bold text-slate-500 uppercase tracking-widest mb-2')
                        
                        with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4'):
                            for slot in slots:
                                # Estilos condicionales
                                card_bg = 'bg-emerald-50 border-emerald-200' if slot['is_preferred'] else 'bg-white border-slate-200'
                                
                                with ui.card().classes(f'p-4 border rounded-xl gap-2 {card_bg} hover:shadow-lg hover:border-indigo-500 cursor-pointer transition-all group') \
                                        .on('click', lambda s=slot: confirm_reschedule(s)):
                                    
                                    # Badge Preferencia
                                    if slot['is_preferred']:
                                        with ui.row().classes('w-full justify-end absolute top-2 right-2'):
                                            ui.icon('thumb_up', color='emerald').classes('text-xs opacity-50')

                                    # Horas
                                    with ui.row().classes('w-full justify-between items-center mt-2'):
                                        # Lado Izquierdo (Mundo Profe - Oculto/Discreto)
                                        # Lo mostramos sutilmente para depuración mental si quieres, o solo mostramos TU hora
                                        pass 

                                        # Lado Central/Principal (TU HORA)
                                        with ui.column().classes('w-full items-center gap-0'):
                                            ui.label('TU HORA').classes('text-[10px] font-bold text-slate-400 tracking-wider')
                                            ui.label(slot['s_time_str']).classes('text-2xl font-black text-slate-700 group-hover:text-indigo-600')
                                            if slot['s_day_diff']:
                                                ui.label(f"{slot['s_date']} {slot['s_day_diff']}").classes('text-xs text-orange-500 font-bold')
                                            else:
                                                ui.label("Mismo día").classes('text-xs text-slate-300')

                # === 3. LÓGICA DE CONFIRMACIÓN Y GUARDADO ===
                def confirm_reschedule(slot_data):
                    with ui.dialog() as confirm_d, ui.card().classes('w-96 p-6 rounded-xl'):
                        ui.label('Confirmar cambio').classes('text-xl font-bold text-slate-800')
                        
                        with ui.column().classes('my-4 gap-1'):
                            ui.label('Nueva hora para ti:').classes('text-sm text-slate-500')
                            ui.label(f"{slot_data['s_date']} a las {slot_data['s_time_str']}").classes('text-lg font-bold text-indigo-600')
                        
                        with ui.row().classes('w-full justify-end gap-2'):
                            ui.button('Cancelar', on_click=confirm_d.close).props('flat color=slate')
                            
                            async def execute_save():
                                session = PostgresSession()
                                try:
                                    # 1. Obtener la clase de la BD
                                    class_db = session.query(AsignedClasses).filter(AsignedClasses.id == c.id).first()
                                    if not class_db:
                                        ui.notify("Error: Clase no encontrada", type='negative')
                                        return

                                    # 2. Actualizar datos del ESTUDIANTE
                                    class_db.date = slot_data['s_date']
                                    class_db.days = slot_data['s_weekday']
                                    class_db.start_time = slot_data['s_time_int']
                                    class_db.end_time = slot_data['s_end_int']
                                    
                                    # 3. Actualizar datos de la PROFESORA
                                    class_db.date_prof = slot_data['t_date']
                                    class_db.start_prof_time = slot_data['t_time_int']
                                    class_db.end_prof_time = slot_data['t_end_int']
                                    
                                    # 4. Resetear status 
                                    
                                    class_db.status = 'Pendiente'

                                    session.commit()
                                    ui.notify(f"¡Clase movida exitosamente!", type='positive')
                                    
                                    # Cerrar todo
                                    confirm_d.close()
                                    d.close()


                                    ui.navigate.to('/myclasses') # Forzar recarga si es necesario
                                    
                                except Exception as e:
                                    session.rollback()
                                    ui.notify(f"Error guardando: {e}", type='negative')
                                    logger.error(f"Save error: {e}")
                                finally:
                                    session.close()
                                    
                            ui.button('Confirmar Cambio', on_click=execute_save).props('unelevated color=indigo')
                    confirm_d.open()

                # Listeners
                search_btn.on('click', show_slots)
                # Auto-carga inicial
                if default_date:
                    ui.timer(0.1, show_slots, once=True)

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
                    if not c.status == ('Cancelada', 'No Asistió', 'Completada'):
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