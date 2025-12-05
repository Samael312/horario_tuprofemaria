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

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# --- 1. TRADUCCIONES ---
TRANSLATIONS = {
    'es': {
        'no_session': 'No hay usuario en sesión',
        'user_not_found': 'Usuario no encontrado en la Nube',
        'page_title': 'Editar Perfil',
        'page_subtitle': 'Actualiza tus datos y disponibilidad',
        'card_personal_title': 'Información Personal',
        'label_name': 'Nombre',
        'label_surname': 'Apellido',
        'label_email': 'Correo',
        'label_timezone': 'Zona Horaria',
        'card_schedule_title': 'Configuración de Clases y Horarios',
        'label_package': 'Paquete de Clases Activo',
        'alert_package': 'Debes terminar el paquete actual antes de cambiarlo o renovarlo.',
        'section_add_availability': 'Añadir Disponibilidad',
        'step_1': '1. DÍAS',
        'select_days_label': 'Seleccionar días',
        'step_2': '2. DURACIÓN',
        'label_minutes': 'Minutos',
        'step_3': '3. HORARIO',
        'label_start': 'Inicio',
        'label_end': 'Fin',
        'tooltip_add': 'Agregar al horario',
        'col_hour': 'HORA',
        'btn_clear_table': 'Limpiar Tabla',
        'btn_delete_selected': 'Borrar Seleccionados',
        'btn_back': 'Volver al Perfil',
        'btn_save': 'Guardar Cambios',
        'notify_saving': 'Guardando cambios...',
        'notify_success': 'Perfil actualizado correctamente',
        'notify_error': 'Error al guardar: {}',
        'add_btn_success': 'Intervalo agregado',
        'add_btn_missing_day': 'Selecciona un día',
        'add_btn_missing_dur': 'Selecciona duración',
        'add_btn_missing_time': 'Falta hora inicio',
        'add_btn_missing_end': 'Falta hora fin',
        'add_btn_invalid_hour': 'Hora inválida',
        'add_btn_bad_fmt': 'Formato HH:MM requerido',
        'add_btn_invalid_int': 'Intervalo inválido',
        'log_neon_ok': '✅ Cambios guardados en NEON',
        'log_sqlite_ok': '💾 Respaldo actualizado en SQLITE',
        'log_local_err': '⚠️ Error backup local: {}'
    },
    'en': {
        'no_session': 'No user in session',
        'user_not_found': 'User not found in Cloud',
        'page_title': 'Edit Profile',
        'page_subtitle': 'Update your data and availability',
        'card_personal_title': 'Personal Information',
        'label_name': 'Name',
        'label_surname': 'Surname',
        'label_email': 'Email',
        'label_timezone': 'Time Zone',
        'card_schedule_title': 'Class & Schedule Settings',
        'label_package': 'Active Class Package',
        'alert_package': 'You must finish the current package before changing or renewing it.',
        'section_add_availability': 'Add Availability',
        'step_1': '1. DAYS',
        'select_days_label': 'Select days',
        'step_2': '2. DURATION',
        'label_minutes': 'Minutes',
        'step_3': '3. SCHEDULE',
        'label_start': 'Start',
        'label_end': 'End',
        'tooltip_add': 'Add to schedule',
        'col_hour': 'HOUR',
        'btn_clear_table': 'Clear Table',
        'btn_delete_selected': 'Delete Selected',
        'btn_back': 'Back to Profile',
        'btn_save': 'Save Changes',
        'notify_saving': 'Saving changes...',
        'notify_success': 'Profile updated successfully',
        'notify_error': 'Error saving: {}',
        'add_btn_success': 'Interval added',
        'add_btn_missing_day': 'Select a day',
        'add_btn_missing_dur': 'Select duration',
        'add_btn_missing_time': 'Missing start time',
        'add_btn_missing_end': 'Missing end time',
        'add_btn_invalid_hour': 'Invalid hour',
        'add_btn_bad_fmt': 'HH:MM format required',
        'add_btn_invalid_int': 'Invalid interval',
        'log_neon_ok': '✅ Changes saved to NEON',
        'log_sqlite_ok': '💾 SQLITE backup updated',
        'log_local_err': '⚠️ Local backup error: {}'
    }
}

# --- 2. LÓGICA DE WORKER (PERSISTENCIA) ---
def _persist_data_sync(username, user_update, schedules_list, lang='es'):
    """
    Función worker que corre en otro hilo.
    Acepta 'lang' para devolver logs traducidos si fuera necesario,
    aunque los logs suelen ser técnicos.
    """
    t = TRANSLATIONS.get(lang, TRANSLATIONS['es'])
    log_msgs = []
    
    # FASE 1: NEON
    pg_session = PostgresSession()
    try:
        # User
        u_pg = pg_session.query(User).filter(User.username == username).first()
        if u_pg:
            u_pg.name = user_update['name']
            u_pg.surname = user_update['surname']
            u_pg.time_zone = user_update['time_zone']
            u_pg.email = user_update['email']
        
        # Schedules
        pg_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
        for item in schedules_list:
            pg_session.add(SchedulePref(**item))
        
        pg_session.commit()
        log_msgs.append(t['log_neon_ok'])
    except Exception as e:
        pg_session.rollback()
        raise e
    finally:
        pg_session.close()

    # FASE 2: SQLITE
    try:
        sqlite_session = BackupSession()
        u_sq = sqlite_session.query(User).filter(User.username == username).first()
        if u_sq:
            u_sq.name = user_update['name']
            u_sq.surname = user_update['surname']
            u_sq.time_zone = user_update['time_zone']
            u_sq.email = user_update['email']
        
        sqlite_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
        for item in schedules_list:
            sqlite_session.add(SchedulePref(**item))
        
        sqlite_session.commit()
        log_msgs.append(t['log_sqlite_ok'])
    except Exception as e:
        log_msgs.append(t['log_local_err'].format(e))
    finally:
        sqlite_session.close()
    
    return log_msgs


# --- 3. PÁGINA PRINCIPAL ---
@ui.page('/profile_edit')
def profile_edit():
    # Verificar sesión
    username = app.storage.user.get("username")
    # Obtener idioma inicial para errores tempranos
    current_lang = app.storage.user.get('lang', 'es') 
    t_init = TRANSLATIONS[current_lang]

    if not username:
        ui.label(t_init['no_session']).classes('text-negative mt-4')
        return

    # --- CARGAR DATOS (Fuente Real) UNA SOLA VEZ ---
    # Esto se hace fuera del refreshable para no re-consultar la DB al cambiar idioma.
    session = PostgresSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label(t_init['user_not_found']).classes('text-negative mt-4')
            return
        
        # Datos para inputs iniciales
        initial_user_data = {
            'name': user_obj.name,
            'surname': user_obj.surname,
            'email': getattr(user_obj, 'email', ''),
            'time_zone': getattr(user_obj, 'time_zone', '')
        }

        # Datos para inputs de horario
        rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
        raw_package = getattr(rgh_obj, 'package', None) if rgh_obj else None
        package_value = raw_package if raw_package in pack_of_classes else None
        
        durations_user = [s.duration for s in session.query(SchedulePref).filter(SchedulePref.username == username).all()]
        default_duration = Counter(durations_user).most_common(1)[0][0] if durations_user else None

        # Inicializar estructura de datos para la tabla (Estado Local)
        local_group_data = {h: {d: "" for d in days_of_week} for h in hours_of_day}

        # Poblar local_group_data con datos de DB
        schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
        if schedule_data:
            for s in schedule_data:
                h_ini = f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}"
                h_fin = f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                texto_intervalo = f"{h_ini}-{h_fin}"
                
                if h_ini in local_group_data: local_group_data[h_ini][s.days] = texto_intervalo
                if h_fin in local_group_data: local_group_data[h_fin][s.days] = texto_intervalo

    except Exception as e:
        ui.label(f"Error loading data: {e}").classes('text-negative')
        session.close()
        return
    finally:
        session.close()

    # --- CONTENIDO REFRESHABLE (INTERNACIONALIZADO) ---
    @ui.refreshable
    def profile_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]

        # --- CONTENEDOR PRINCIPAL ---
        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-8'):
            
            # Encabezado de página
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.icon('manage_accounts', size='lg', color='gray-700')
                with ui.column().classes('gap-0'):
                    ui.label(t['page_title']).classes('text-3xl font-bold text-gray-800')
                    ui.label(t['page_subtitle']).classes('text-gray-500 text-sm')

            # =================================================
            # TARJETA 1: DATOS PERSONALES
            # =================================================
            personal_inputs = {}
            
            with ui.card().classes('w-full p-0 shadow-lg rounded-xl border border-gray-200 overflow-hidden'):
                # Header Tarjeta
                with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center gap-2'):
                    ui.icon('person', color='primary')
                    ui.label(t['card_personal_title']).classes('text-lg font-bold text-gray-700')

                # Cuerpo Tarjeta
                with ui.grid(columns=2).classes('w-full p-6 gap-6'):
                    fields_config = [
                        ('name', t['label_name'], initial_user_data['name'], 'badge'),
                        ('surname', t['label_surname'], initial_user_data['surname'], 'badge'),
                        ('email', t['label_email'], initial_user_data['email'], 'email'),
                        ('time_zone', t['label_timezone'], initial_user_data['time_zone'], 'schedule')
                    ]

                    for field_key, label, value, icon in fields_config:
                        with ui.column().classes('w-full gap-1'):
                            ui.label(label).classes('text-sm font-semibold text-gray-600 ml-1')
                            
                            if field_key == 'time_zone':
                                personal_inputs[field_key] = ui.select(
                                    options=sorted(available_timezones()),
                                    value=value
                                ).props('outlined dense options-dense use-input input-debounce="0" behavior="menu"').classes('w-full')
                            else:
                                inp = ui.input(value=value).props('outlined dense').classes('w-full')
                                inp.add_slot('prepend', f'<q-icon name="{icon}" />')
                                personal_inputs[field_key] = inp

            # =================================================
            # TARJETA 2: GESTIÓN DE HORARIOS Y PAQUETE
            # =================================================
            with ui.card().classes('w-full p-0 shadow-lg rounded-xl border border-gray-200 overflow-hidden'):
                # Header Tarjeta
                with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-2'):
                    ui.icon('calendar_month', color='pink-500')
                    ui.label(t['card_schedule_title']).classes('text-lg font-bold text-gray-800')

                with ui.column().classes('w-full p-6 gap-6'):
                    
                    # --- SECCIÓN PAQUETE ---
                    rgh_inputs = {}
                    with ui.row().classes('w-full items-end gap-4'):
                        with ui.column().classes('flex-grow gap-1'):
                            ui.label(t['label_package']).classes('text-sm font-bold text-gray-600')
                            
                            def show_package_alert():
                                ui.notify(t['alert_package'], 
                                          type='warning', 
                                          icon='lock_clock',
                                          position='center')

                            with ui.element('div').classes('w-full md:w-1/2 cursor-not-allowed').on('click', show_package_alert):
                                pkg_select = ui.select(
                                    options=sorted(pack_of_classes),
                                    value=package_value
                                ).props('outlined dense disable').classes('w-full pointer-events-none') 
                                
                                pkg_select.add_slot('prepend', '<q-icon name="inventory_2" />')
                                rgh_inputs['package'] = pkg_select

                    ui.separator().classes('my-2')

                    # --- SECCIÓN CONTROL DE HORARIO ---
                    ui.label(t['section_add_availability']).classes('text-md font-bold text-gray-700 mb-2')
                    
                    with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center gap-4 justify-between wrap'):
                        
                        # 1. Días
                        with ui.column().classes('gap-1'):
                            ui.label(t['step_1']).classes('text-xs font-bold text-gray-500 uppercase')
                            day_selector = ui.select(
                                days_of_week, 
                                multiple=True, 
                                value=[],
                                label=t['select_days_label']
                            ).props('outlined dense bg-white').classes('min-w-[200px]')

                        # 2. Duración
                        with ui.column().classes('gap-1'):
                            ui.label(t['step_2']).classes('text-xs font-bold text-gray-500 uppercase')
                            duration_selector = ui.select(
                                duration_options, 
                                value=default_duration,
                                label=t['label_minutes']
                            ).props('outlined dense bg-white').classes('w-32')

                        # 3. Horas
                        with ui.column().classes('gap-1'):
                            ui.label(t['step_3']).classes('text-xs font-bold text-gray-500 uppercase')
                            with ui.row().classes('gap-2 items-center'):
                                with ui.input(t['label_start']).props('outlined dense bg-white placeholder="00:00" mask="time"').classes('w-28') as start_time:
                                    with ui.menu().props('no-parent-event') as menuD:
                                        with ui.time().bind_value(start_time):
                                            with ui.row().classes('justify-end'):
                                                ui.button('OK', on_click=menuD.close).props('flat dense')
                                        with start_time.add_slot('append'):
                                            ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-500')

                                ui.label("-").classes('text-gray-400')

                                with ui.input(t['label_end']).props('outlined dense bg-white placeholder="00:00" mask="time"').classes('w-28') as end_time:
                                    with ui.menu().props('no-parent-event') as menuD2:
                                        with ui.time().bind_value(end_time):
                                            with ui.row().classes('justify-end'):
                                                ui.button('OK', on_click=menuD2.close).props('flat dense')
                                        with end_time.add_slot('append'):
                                            ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-500')

                        # 4. Botón Agregar
                        add_hour_btn = ui.button(icon='add', color='primary').props('round shadow-lg').tooltip(t['tooltip_add'])

                    # --- TABLA DE HORARIOS ---
                    # Reconstruimos filtered_rows cada vez que se refresca el UI para reflejar local_group_data
                    filtered_rows = []
                    for hora, vals in local_group_data.items():
                        if any(v != "" for v in vals.values()):
                            filtered_rows.append({'hora': hora, **vals})

                    table_cols = [
                        {'name': 'hora', 'label': t['col_hour'], 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-gray-100 text-gray-800 font-bold'},
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
                            ui.button(t['btn_clear_table'], 
                                on_click=lambda: clear_table(table, local_group_data),
                                icon='cleaning_services', color='warning').props('flat dense')
                        
                            ui.button(t['btn_delete_selected'],
                                color='negative',
                                icon='delete',
                                on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="hora")
                                ).props('flat dense')

            # =================================================
            # BOTONES GUARDAR / VOLVER
            # =================================================
            async def save_changes():
                # --- Recolectar Datos de los Inputs de este render ---
                # Importante: se leen de las variables locales del refreshable
                user_data_update = {
                    'name': personal_inputs['name'].value,
                    'surname': personal_inputs['surname'].value,
                    'time_zone': personal_inputs['time_zone'].value,
                    'email': personal_inputs['email'].value
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

                # --- Ejecutar Worker ---
                try:
                    notification = ui.notify(t['notify_saving'], type='ongoing', timeout=5000, icon='cloud_upload')
                    # Pasamos el idioma al worker por si quiere devolver strings traducidos
                    msgs = await run.io_bound(_persist_data_sync, username, user_data_update, new_schedules, lang)
                    
                    for m in msgs: logger.info(m)
                    
                    ui.notify(t['notify_success'], type='positive', icon='check_circle')
                    
                except Exception as e:
                    logger.error(f"Error fatal: {e}")
                    ui.notify(t['notify_error'].format(e), type='negative', close_button=True)
                finally:
                    notification.dismiss()

            with ui.row().classes('w-full justify-center gap-6 pt-6 pb-12'):
                ui.button(t['btn_back'], on_click=lambda: ui.navigate.to('/profile'), icon='arrow_back')\
                    .props('outline color=grey-8').classes('px-6')

                ui.button(t['btn_save'], on_click=save_changes, icon='save')\
                    .props('push color=positive size=lg').classes('px-8')

            # Inicializar lógica del botón (debe estar dentro del refreshable porque depende de los inputs creados aquí)
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
                # Pasar traducciones al componente
                notify_success=t['add_btn_success'],
                notify_missing_day=t['add_btn_missing_day'],
                notify_missing_duration=t['add_btn_missing_dur'],
                notify_missing_time=t['add_btn_missing_time'],
                notify_missing_end_time=t['add_btn_missing_end'],
                notify_invalid_hour=t['add_btn_invalid_hour'],
                notify_bad_format=t['add_btn_bad_fmt'],
                notify_interval_invalid=t['add_btn_invalid_int']
            )

    # --- INICIALIZACIÓN ---
    # 1. Crear Header y pasarle la función de refresco del contenido
    create_main_screen(page_refresh_callback=profile_content.refresh)

    # 2. Renderizar contenido inicial
    profile_content()