from nicegui import ui, app
import logging
from components.header import create_main_screen
from db.sqlite_db import SQLiteSession
from db.models import User, SchedulePref
from auth.sync_edit import sync_sqlite_to_postgres_edit
from zoneinfo import available_timezones
from components.h_selection import make_selection_handler
from components.clear_table import clear_table
from components.delete_rows import delete_selected_rows_v2
from components.botones.button_dur import make_add_hour_button
from components.share_data import *
from collections import Counter

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/profile_edit')
def profile_edit():
    # Verificar sesión
    username = app.storage.user.get("username")
    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    create_main_screen()

    session = SQLiteSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label("Usuario no encontrado en DB").classes('text-negative mt-4')
            return
        
        # Inicializar estructura de datos para la tabla (Importante reiniciarla al cargar la página)
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
                    
                    # Definición de campos con iconos
                    fields_config = [
                        ('name', 'Nombre', user_obj.name, 'badge'),
                        ('surname', 'Apellido', user_obj.surname, 'badge'),
                        ('email', 'Correo', getattr(user_obj, 'email', ''), 'email'),
                        ('time_zone', 'Zona Horaria', getattr(user_obj, 'time_zone', ''), 'schedule')
                    ]

                    for field_key, label, value, icon in fields_config:
                        with ui.column().classes('w-full gap-1'):
                            ui.label(label).classes('text-sm font-semibold text-gray-600 ml-1')
                            
                            if field_key == 'time_zone':
                                personal_inputs[field_key] = ui.select(
                                    options=sorted(available_timezones()),
                                    value=value
                                ).props('outlined dense options-dense use-input input-debounce="0" behavior="menu"').classes('w-full')
                                # Nota: use-input permite filtrar si la lista es larga
                            else:
                                inp = ui.input(value=value).props('outlined dense').classes('w-full')
                                inp.add_slot('prepend', f'<q-icon name="{icon}" />')
                                personal_inputs[field_key] = inp

            # =================================================
            # TARJETA 2: GESTIÓN DE HORARIOS Y PAQUETE
            # =================================================
            rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
            if not rgh_obj:
                ui.label("No se encontraron datos de rango de horarios").classes('text-negative')
                return

            with ui.card().classes('w-full p-0 shadow-lg rounded-xl border border-gray-200 overflow-hidden'):
                # Header Tarjeta
                with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-2'):
                    ui.icon('calendar_month', color='pink-500')
                    ui.label("Configuración de Clases y Horarios").classes('text-lg font-bold text-gray-800')

                with ui.column().classes('w-full p-6 gap-6'):
                    
                    # --- SECCIÓN PAQUETE ---
                    rgh_inputs = {}
                    with ui.row().classes('w-full items-end gap-4'):
                        with ui.column().classes('flex-grow gap-1'):
                            ui.label("Paquete de Clases Activo").classes('text-sm font-bold text-gray-600')
                            pkg_select = ui.select(
                                options=sorted(pack_of_classes),
                                value=getattr(rgh_obj, 'package', '')
                            ).props('outlined dense').classes('w-full md:w-1/2')
                            pkg_select.add_slot('prepend', '<q-icon name="inventory_2" />')
                            rgh_inputs['package'] = pkg_select

                    ui.separator().classes('my-2')

                    # --- SECCIÓN CONTROL DE HORARIO (BARRA DE HERRAMIENTAS) ---
                    ui.label("Añadir Disponibilidad").classes('text-md font-bold text-gray-700 mb-2')
                    
                    # Contenedor gris para los controles
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

                        # 2. Duración (Cálculo del default)
                        durations_user = [s.duration for s in session.query(SchedulePref).filter(SchedulePref.username == username).all()]
                        default_duration = Counter(durations_user).most_common(1)[0][0] if durations_user else None
                        
                        with ui.column().classes('gap-1'):
                            ui.label('2. Duración').classes('text-xs font-bold text-gray-500 uppercase')
                            duration_selector = ui.select(
                                duration_options, 
                                value=default_duration,
                                label='Minutos'
                            ).props('outlined dense bg-white').classes('w-32')

                        # 3. Horas (Inicio y Fin)
                        with ui.column().classes('gap-1'):
                            ui.label('3. Horario').classes('text-xs font-bold text-gray-500 uppercase')
                            with ui.row().classes('gap-2 items-center'):
                                # Input Hora Inicio
                                with ui.input('Inicio').props('outlined dense bg-white placeholder="00:00" mask="time"').classes('w-28') as start_time:
                                    with ui.menu().props('no-parent-event') as menuD:
                                        with ui.time().bind_value(start_time):
                                            with ui.row().classes('justify-end'):
                                                ui.button('OK', on_click=menuD.close).props('flat dense')
                                    with start_time.add_slot('append'):
                                        ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-500')

                                ui.label("-").classes('text-gray-400')

                                # Input Hora Fin
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
                    
                    # Preparar datos existentes
                    schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
                    if schedule_data:
                        for s in schedule_data:
                            h_ini = f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}"
                            h_fin = f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                            texto_intervalo = f"{h_ini}-{h_fin}"
                            
                            if h_ini in local_group_data: local_group_data[h_ini][s.days] = texto_intervalo
                            if h_fin in local_group_data: local_group_data[h_fin][s.days] = texto_intervalo

                    # Filtrar filas vacías
                    filtered_rows = []
                    for hora, vals in local_group_data.items():
                        if any(v != "" for v in vals.values()):
                            filtered_rows.append({'hora': hora, **vals})

                    # Definir columnas con estilos personalizados
                    table_cols = [
                        {'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-gray-100 text-gray-800 font-bold'},
                    ] + [
                        {'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold'} 
                        for d in days_of_week
                    ]

                    # Renderizar Tabla
                    table = ui.table(
                        columns=table_cols,
                        rows=filtered_rows,
                        row_key='hora',
                        selection='multiple'
                    ).classes('w-full mt-4 border border-gray-200 rounded-lg overflow-hidden shadow-sm').props('flat bordered separator=cell density=compact')

                    # Handlers
                    selection_handler, selection_state = make_selection_handler(table, logger=logger)
                    table.on('selection', selection_handler)

                    # Botones de acción de tabla (Pie de tabla)
                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                         ui.button('Limpiar Tabla', 
                                on_click=lambda: clear_table(table, local_group_data),
                                icon='cleaning_services', color='warning').props('flat dense')
                         
                         ui.button('Borrar Seleccionados',
                                color='negative',
                                icon='delete',
                                on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="hora")
                                ).props('flat dense')

            # =================================================
            # BOTÓN GUARDAR (FOOTER FLOTANTE O FINAL)
            # =================================================
            def save_changes():
                session2 = SQLiteSession()
                try:
                    # 1. Guardar datos personales
                    u2 = session2.query(User).filter(User.username == username).first()
                    if u2:
                        u2.name = personal_inputs['name'].value
                        u2.surname = personal_inputs['surname'].value
                        u2.time_zone = personal_inputs['time_zone'].value
                        u2.email = personal_inputs['email'].value
                    
                    # 2. Guardar Horarios
                    session2.query(SchedulePref).filter(SchedulePref.username == username).delete()
                    
                    pkg_val = rgh_inputs['package'].value
                    # Nombre y apellido pueden venir del input actualizado o del objeto original
                    nm_val = personal_inputs['name'].value
                    sn_val = personal_inputs['surname'].value
                    dur_val = duration_selector.value
                    
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
                                            new_pref = SchedulePref(
                                                username=username, name=nm_val, surname=sn_val,
                                                duration=dur_val, package=pkg_val, days=day,
                                                start_time=s_int, end_time=e_int
                                            )
                                            session2.add(new_pref)
                                            seen_intervals.add(unique_key)
                                    except ValueError: pass
                    
                    session2.commit()
                    sync_sqlite_to_postgres_edit()
                    ui.notify("Perfil actualizado correctamente", type='positive', icon='check_circle')
                    ui.timer(1.0, lambda: ui.navigate.to('/profile'))
                
                except Exception as e:
                    session2.rollback()
                    logger.error(f"Error save: {e}")
                    ui.notify(f"Error: {e}", type='negative')
                finally:
                    session2.close()

            # Botón grande al final
            with ui.row().classes('w-full justify-center pt-4 pb-8'):
                ui.button("Guardar Todos los Cambios", on_click=save_changes, icon='save')\
                    .classes('w-full md:w-1/3 text-lg py-2')\
                    .props('color=positive push')

    finally:
        session.close()

    # Lógica del botón agregar hora (fuera del flujo visual, solo lógica)
    make_add_hour_button(
        add_hour_btn,
        day_selector=day_selector,
        duration_selector=duration_selector,
        button_id=f"btn_add_{username}",
        time_input=start_time,
        end_time_input=end_time,
        valid_hours=hours_of_day, # Asegúrate que esto existe en share_data
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