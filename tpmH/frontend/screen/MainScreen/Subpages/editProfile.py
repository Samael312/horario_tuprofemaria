from nicegui import ui, app, run
import logging
from components.header import create_main_screen
# --- IMPORTS ACTUALIZADOS ---
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
from db.models import User, SchedulePref
# ----------------------------
from zoneinfo import available_timezones
from components.h_selection import make_selection_handler
from components.clear_table import clear_table
from components.delete_rows import delete_selected_rows_v2
from components.botones.button_dur import make_add_hour_button
from components.share_data import *
from collections import Counter
from prompts.chatbot import render_floating_chatbot

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/profile_edit')
def profile_edit():
    # Verificar sesión de NiceGUI
    ui.add_head_html('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined" />')
    username = app.storage.user.get("username")
    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4 text-xl font-bold p-4')
        return

    create_main_screen()

    # --- USAR POSTGRES PARA CARGAR DATOS (Fuente Real) ---
    session = PostgresSession() 
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label("Usuario no encontrado en la Nube").classes('text-negative mt-4 p-4')
            return
        
        # Inicializar estructura de datos para la tabla
        local_group_data = {h: {d: "" for d in days_of_week} for h in hours_of_day}

        # --- CONTENEDOR PRINCIPAL ---
        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-8'):
            
            # Encabezado de página
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.icon('manage_accounts', size='lg', color='gray-700')
                with ui.column().classes('gap-0'):
                    ui.label('Editar Perfil').classes('text-3xl font-bold text-gray-800')
                    ui.label('Actualiza tus datos y disponibilidad').classes('text-gray-500 text-sm')

            # =================================================
            # TARJETA 1: DATOS PERSONALES
            # =================================================
            with ui.card().classes('w-full p-0 shadow-lg rounded-xl border border-gray-200 overflow-hidden'):
                # Header Tarjeta
                with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center gap-2'):
                    ui.icon('person', color='primary')
                    ui.label("Información Personal").classes('text-lg font-bold text-gray-700')

                # Cuerpo Tarjeta
                with ui.grid(columns=2).classes('w-full p-6 gap-6'):
                    personal_inputs = {}
                    

                    # Configuración de campos (CORREGIDA)
                    # Usamos getattr(obj, attr, default) directamente sobre user_obj
                    fields_config = [
                        ('name', 'Nombre', getattr(user_obj, 'name', ''), 'badge'),
                        ('surname', 'Apellido', getattr(user_obj, 'surname', ''), 'badge'),
                        ('email', 'Correo', getattr(user_obj, 'email', ''), 'email'), # Corrección aquí
                        ('time_zone', 'Zona Horaria', getattr(user_obj, 'time_zone', 'UTC'), 'public'), # Corrección aquí
                    ]

                    for field_key, label, value, icon in fields_config:
                        with ui.column().classes('w-full gap-1'):
                            ui.label(label).classes('text-sm font-semibold text-gray-600 ml-1')
                            
                            if field_key == 'time_zone':
                                # 1. Creamos el select
                                sel = ui.select(
                                    options=sorted(available_timezones()),
                                    value=value
                                ).props('outlined dense options-dense use-input input-debounce="0" behavior="menu"').classes('w-full')
                                
                                # 2. AÑADIMOS EL ICONO (Esta era la parte que faltaba)
                                sel.add_slot('prepend', f'<q-icon name="{icon}" />')
                                
                                personal_inputs[field_key] = sel
                            else:
                                inp = ui.input(value=value).props('outlined dense').classes('w-full')
                                inp.add_slot('prepend', f'<q-icon name="{icon}" />')
                                personal_inputs[field_key] = inp
                    
                    # Selector de Objetivo (Goal)
                    # Recuperar valor actual y validarlo
                    raw_goal = getattr(user_obj, 'goal', None)
                    goal_value = raw_goal if raw_goal in goals_list else None

                    payment_info = getattr(user_obj, 'payment_info', {}) or {}
                    methods = payment_info.get('preferred_methods', [])

                    # 5. Selector de Objetivo (Se colocará en la Columna 1 de la siguiente fila disponible)
                    with ui.column().classes('w-full gap-1'):
                        ui.label('Objetivo de Aprendizaje').classes('text-sm font-semibold text-gray-600 ml-1')
                        goal_selector = ui.select(
                            options=sorted(goals_list),
                            value=goal_value
                        ).props('outlined dense').classes('w-full')
                        
                        goal_selector.add_slot('prepend', '<q-icon name="assignment" />')
                        personal_inputs['goal'] = goal_selector

                    # 6. Selector de Métodos de Pago (Se colocará en la Columna 2, al lado del Objetivo)
                    with ui.column().classes('w-full gap-1'):
                        ui.label('Métodos de pago').classes('text-sm font-semibold text-gray-600 ml-1')
                        
                        method_selector = ui.select(
                            options=sorted(method_list),
                            multiple=True,
                            value=methods,
                        ).props('outlined dense use-chips').classes('w-full') # Agregué 'use-chips' para que se vea mejor múltiple

                        method_selector.add_slot('prepend', '<q-icon name="credit_card" />')
                        personal_inputs['payment_methods'] = method_selector

            # =================================================
            # TARJETA 2: GESTIÓN DE HORARIOS Y PAQUETE
            # =================================================
            # Consultamos los horarios actuales desde POSTGRES
            rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
            
            # Validamos el paquete para evitar errores
            raw_package = getattr(rgh_obj, 'package', None) if rgh_obj else None
            package_value = raw_package if raw_package in pack_of_classes else None

            with ui.card().classes('w-full p-0 shadow-lg rounded-xl border border-gray-200 overflow-hidden'):
                # Header Tarjeta
                with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-2'):
                    ui.icon('calendar_month', color='pink-500')
                    ui.label("Configuración de Clases y Horarios").classes('text-lg font-bold text-gray-800')

                with ui.column().classes('w-full p-6 gap-6'):
                    
                    # --- SECCIÓN PAQUETE (MODIFICADA: NO EDITABLE) ---
                    rgh_inputs = {}
                    with ui.row().classes('w-full items-end gap-4'):
                        with ui.column().classes('flex-grow gap-1'):
                            ui.label("Paquete de Clases Activo").classes('text-sm font-bold text-gray-600')
                            
                            # Función para mostrar la alerta
                            def show_package_alert():
                                ui.notify('Debes terminar el paquete actual antes de cambiarlo o renovarlo.', 
                                          type='warning', 
                                          icon='lock_clock',
                                          position='center')

                            # Envolvemos el select en un div que captura el click
                            with ui.element('div').classes('w-full md:w-1/2 cursor-not-allowed').on('click', show_package_alert):
                                pkg_select = ui.select(
                                    options=sorted(pack_of_classes),
                                    value=package_value
                                ).props('outlined dense disable').classes('w-full pointer-events-none') 
                                
                                pkg_select.add_slot('prepend', '<q-icon name="inventory_2" />')
                                rgh_inputs['package'] = pkg_select

                    ui.separator().classes('my-2')

                    # --- SECCIÓN CONTROL DE HORARIO ---
                    ui.label("Añadir Disponibilidad").classes('text-md font-bold text-gray-700 mb-2')
                    
                    with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center gap-4 justify-between wrap'):
                        
                        # 1. Días
                        with ui.column().classes('gap-1'):
                            ui.label('1. Días').classes('text-xs font-bold text-gray-500 uppercase')
                            day_selector = ui.select(
                                days_of_week, 
                                multiple=True, 
                                value=[],
                                label='Seleccionar días'
                            ).props('outlined dense bg-white').classes('min-w-[200px]')

                        # 2. Duración
                        durations_user = [s.duration for s in session.query(SchedulePref).filter(SchedulePref.username == username).all()]
                        default_duration = Counter(durations_user).most_common(1)[0][0] if durations_user else None
                        
                        with ui.column().classes('gap-1'):
                            ui.label('2. Duración').classes('text-xs font-bold text-gray-500 uppercase')
                            duration_selector = ui.select(
                                duration_options, 
                                value=default_duration,
                                label='Minutos'
                            ).props('outlined dense bg-white').classes('w-32')

                        # 3. Horas
                        with ui.column().classes('gap-1'):
                            ui.label('3. Horario').classes('text-xs font-bold text-gray-500 uppercase')
                            with ui.row().classes('gap-2 items-center'):
                                with ui.input('Inicio').props('outlined dense bg-white placeholder="00:00" mask="time"').classes('w-28') as start_time:
                                    with ui.menu().props('no-parent-event') as menuD:
                                        with ui.time().bind_value(start_time):
                                            with ui.row().classes('justify-end'):
                                                ui.button('OK', on_click=menuD.close).props('flat dense')
                                        with start_time.add_slot('append'):
                                            ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-500')

                                ui.label("-").classes('text-gray-400')

                                with ui.input('Fin').props('outlined dense bg-white placeholder="00:00" mask="time"').classes('w-28') as end_time:
                                    with ui.menu().props('no-parent-event') as menuD2:
                                        with ui.time().bind_value(end_time):
                                            with ui.row().classes('justify-end'):
                                                ui.button('OK', on_click=menuD2.close).props('flat dense')
                                        with end_time.add_slot('append'):
                                            ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-500')

                        # 4. Botón Agregar
                        add_hour_btn = ui.button(icon='add', color='primary').props('round shadow-lg').tooltip('Agregar al horario')

                    # --- TABLA DE HORARIOS ---
                    schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
                    if schedule_data:
                        for s in schedule_data:
                            # Aseguramos formato correcto HH:MM incluso si viene como entero
                            start_str = str(s.start_time).zfill(4)
                            end_str = str(s.end_time).zfill(4)
                            h_ini = f"{start_str[:2]}:{start_str[2:]}"
                            h_fin = f"{end_str[:2]}:{end_str[2:]}"
                            
                            texto_intervalo = f"{h_ini}-{h_fin}"
                            
                            if h_ini in local_group_data: local_group_data[h_ini][s.days] = texto_intervalo
                            if h_fin in local_group_data: local_group_data[h_fin][s.days] = texto_intervalo

                    filtered_rows = []
                    for hora, vals in local_group_data.items():
                        if any(v != "" for v in vals.values()):
                            filtered_rows.append({'hora': hora, **vals})

                    table_cols = [
                        {'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-gray-100 text-gray-800 font-bold'},
                    ] + [
                        {'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold'} 
                        for d in days_of_week
                    ]

                    table = ui.table(
                        columns=table_cols,
                        rows=filtered_rows,
                        row_key='hora',
                        selection='multiple'
                    ).classes('w-full mt-4 border border-gray-200 rounded-lg overflow-hidden shadow-sm').props('flat bordered separator=cell density=compact')

                    selection_handler, selection_state = make_selection_handler(table, logger=logger)
                    table.on('selection', selection_handler)

                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                            ui.button('Limpiar Tabla', 
                                on_click=lambda: clear_table(table, local_group_data),
                                icon='cleaning_services', color='warning').props('flat dense')
                        
                            ui.button('Borrar Seleccionados',
                                color='negative',
                                icon='delete',
                                on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="hora")
                                ).props('flat dense')
            
            # Renderizar el chatbot flotante
            render_floating_chatbot('edit_profile')

            # =================================================
            # LÓGICA DE GUARDADO (NEON -> SQLITE)
            # =================================================
            
            # 1. Función Worker (Bloqueante, corre en otro hilo)
            def _persist_data_sync(username, user_update, schedules_list):
                log_msgs = []
                
                # FASE 1: NEON
                pg_session = PostgresSession()
                try:
                    # User update
                    u_pg = pg_session.query(User).filter(User.username == username).first()
                    if u_pg:
                        u_pg.name = user_update['name']
                        u_pg.surname = user_update['surname']
                        u_pg.time_zone = user_update['time_zone']
                        u_pg.email = user_update['email']
                        u_pg.goal = user_update['goal'] # IMPORTANTE: Ahora guardamos el goal
                        u_pg.payment_info = user_update['payment_info']   # <----- NUEVO
                    
                    # Schedules update (Replace strategy)
                    pg_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
                    for item in schedules_list:
                        pg_session.add(SchedulePref(**item))
                    
                    pg_session.commit()
                    log_msgs.append("✅ Cambios guardados en NEON")
                except Exception as e:
                    pg_session.rollback()
                    raise e
                finally:
                    pg_session.close()

                # FASE 2: SQLITE (Respaldo)
                try:
                    sqlite_session = BackupSession()
                    u_sq = sqlite_session.query(User).filter(User.username == username).first()
                    if u_sq:
                        u_sq.name = user_update['name']
                        u_sq.surname = user_update['surname']
                        u_sq.time_zone = user_update['time_zone']
                        u_sq.email = user_update['email']
                        u_sq.goal = user_update['goal'] # También en el respaldo
                        u_sq.payment_info = user_update['payment_info']   # <----- NUEVO
                    
                    sqlite_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
                    for item in schedules_list:
                        sqlite_session.add(SchedulePref(**item))
                    
                    sqlite_session.commit()
                    log_msgs.append("💾 Respaldo actualizado en SQLITE")
                except Exception as e:
                    log_msgs.append(f"⚠️ Error backup local: {e}")
                finally:
                    sqlite_session.close()
                
                return log_msgs

            # 2. Función UI (Asíncrona)
            async def save_changes():
                # --- Recolectar Datos ---
                user_data_update = {
                    'name': personal_inputs['name'].value,
                    'surname': personal_inputs['surname'].value,
                    'time_zone': personal_inputs['time_zone'].value,
                    'email': personal_inputs['email'].value,
                    'goal': personal_inputs['goal'].value,
                    'payment_info': {
                        'preferred_methods': personal_inputs['payment_methods'].value
                    }
                }
                
                pkg_val = rgh_inputs['package'].value
                dur_val = duration_selector.value
                new_schedules = []
                seen_intervals = set()

                for row in table.rows:
                    for day in days_of_week:
                        cell_val = row.get(day)
                        if cell_val and "-" in str(cell_val):
                            parts = cell_val.split('-')
                            if len(parts) == 2:
                                try:
                                    s_int = int(parts[0].strip().replace(':', ''))
                                    e_int = int(parts[1].strip().replace(':', ''))
                                    
                                    unique_key = (day, s_int, e_int)
                                    if unique_key not in seen_intervals:
                                        new_schedules.append({
                                            'username': username,
                                            'name': user_data_update['name'],
                                            'surname': user_data_update['surname'],
                                            'duration': dur_val,
                                            'package': pkg_val,
                                            'days': day,
                                            'start_time': s_int,
                                            'end_time': e_int
                                        })
                                        seen_intervals.add(unique_key)
                                except ValueError: pass

                notification = None  
                # --- Ejecutar Worker ---
                try:
                    notification = ui.notify("Guardando cambios...", type='ongoing', timeout=5000, icon='cloud_upload')
                    msgs = await run.io_bound(_persist_data_sync, username, user_data_update, new_schedules)
                    
                    for m in msgs: logger.info(m)
                    
                    ui.notify("Perfil actualizado correctamente", type='positive', icon='check_circle')
                    
                    
                except Exception as e:
                    logger.error(f"Error fatal: {e}")
                    ui.notify(f"Error al guardar: {e}", type='negative', close_button=True)
                finally:
                    if 'notification' in locals():
                        if notification:
                            notification.dismiss()

            # --- BOTONES DE ACCIÓN ---
            with ui.row().classes('w-full justify-center gap-6 pt-6 pb-12'):
                
                # Botón Volver
                ui.button("Volver al Perfil", on_click=lambda: ui.navigate.to('/profile'), icon='arrow_back')\
                    .props('outline color=grey-8').classes('px-6')

                # Botón Guardar
                ui.button("Guardar Cambios", on_click=save_changes, icon='save')\
                    .props('push color=positive size=lg').classes('px-8')
    
        

    finally:
        # CERRAR LA SESIÓN DE CARGA INICIAL
        session.close()

    

    # Lógica del botón agregar hora (vinculación final)
    make_add_hour_button(
        add_hour_btn,
        day_selector=day_selector,
        duration_selector=duration_selector,
        button_id=f"btn_add_{username}",
        time_input=start_time,
        end_time_input=end_time,
        valid_hours=hours_of_day,
        group_data=local_group_data,
        days_of_week=days_of_week,
        table=table,
        notify_success="Intervalo agregado",
        notify_missing_day="Selecciona un día",
        notify_missing_duration="Selecciona duración",
        notify_missing_time="Falta hora inicio",
        notify_missing_end_time="Falta hora fin",
        notify_invalid_hour="Hora inválida",
        notify_bad_format="Formato HH:MM requerido",
        notify_interval_invalid="Intervalo inválido"
    )