from nicegui import ui, app
from datetime import datetime
import logging

# --- IMPORTS DE COMPONENTES ---
from components.header import create_main_screen
# Importamos t_val para traducir valores de BD/Listas
from components.share_data import (
    pack_of_classes, 
    duration_options, 
    days_of_week, 
    hours_of_day, 
    t_val
)
from components.clear_table import clear_table
from components.botones.button_dur import make_add_hour_button
from components.botones.button_fecha import make_add_hours_by_date_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save.save_rgo import create_save_schedule_button
from components.save.save_asg import create_save_asgn_classes

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =====================================================
# 1. TRADUCCIONES DE LA PANTALLA
# =====================================================
OS_TRANSLATIONS = {
    'es': {
        'page_title': 'Portal de Estudiante',
        'page_subtitle': 'Gestionar recuperación de clases o nuevos horarios',
        'status_label': 'Estado Actual',
        'question_classes': '¿Tienes clases pendientes por asignar?',
        'yes': 'Si',
        'no': 'No',
        # Sección Clases Pendientes
        'title_pending': 'Agendar Clases Pendientes',
        'label_package': 'Paquete Activo',
        'label_config_ind': 'Configurar Clase Individual',
        'label_date': 'Fecha',
        'label_duration': 'Duración',
        'label_start_time': 'Hora Inicio',
        'btn_add': 'Agregar',
        'table_title_scheduled': 'Clases Agendadas',
        'col_date': 'FECHA',
        'col_day': 'DÍA',
        'col_time': 'HORA',
        'btn_clear': 'Limpiar',
        'btn_delete_sel': 'Borrar Seleccionados',
        'btn_confirm': 'Confirmar Clases',
        # Sección Preferencias
        'title_preferences': 'Definir Preferencia de Horario Semanal',
        'label_package_pref': 'Paquete',
        'label_duration_typ': 'Duración Típica',
        'label_days_enabled': 'Días Habilitados',
        'label_add_block': 'Añadir Bloque de Disponibilidad',
        'label_from': 'Desde',
        'label_to': 'Hasta',
        'btn_add_range': 'Añadir Rango',
        'table_title_proposed': 'Horario Propuesto',
        'btn_save_pref': 'Guardar Preferencias',
        # Notificaciones
        'notify_added': 'Clase agregada a la lista',
        'notify_range_added': 'Rango horario añadido',
        'notify_miss_day': 'Selecciona al menos un día arriba',
        'notify_miss_dur': 'Falta duración',
        'notify_miss_start': 'Falta inicio',
        'notify_miss_end': 'Falta fin',
        'notify_inv_hour': 'Hora inválida',
        'notify_bad_fmt': 'Formato HH:MM',
        'notify_inv_int': 'Intervalo inválido'
    },
    'en': {
        'page_title': 'Student Portal',
        'page_subtitle': 'Manage class recovery or new schedules',
        'status_label': 'Current Status',
        'question_classes': 'Do you have classes pending assignment?',
        'yes': 'Yes',
        'no': 'No',
        # Pending Classes Section
        'title_pending': 'Schedule Pending Classes',
        'label_package': 'Active Package',
        'label_config_ind': 'Configure Individual Class',
        'label_date': 'Date',
        'label_duration': 'Duration',
        'label_start_time': 'Start Time',
        'btn_add': 'Add',
        'table_title_scheduled': 'Scheduled Classes',
        'col_date': 'DATE',
        'col_day': 'DAY',
        'col_time': 'TIME',
        'btn_clear': 'Clear',
        'btn_delete_sel': 'Delete Selected',
        'btn_confirm': 'Confirm Classes',
        # Preferences Section
        'title_preferences': 'Define Weekly Schedule Preference',
        'label_package_pref': 'Package',
        'label_duration_typ': 'Typical Duration',
        'label_days_enabled': 'Enabled Days',
        'label_add_block': 'Add Availability Block',
        'label_from': 'From',
        'label_to': 'To',
        'btn_add_range': 'Add Range',
        'table_title_proposed': 'Proposed Schedule',
        'btn_save_pref': 'Save Preferences',
        # Notifications
        'notify_added': 'Class added to list',
        'notify_range_added': 'Time range added',
        'notify_miss_day': 'Select at least one day above',
        'notify_miss_dur': 'Duration missing',
        'notify_miss_start': 'Start time missing',
        'notify_miss_end': 'End time missing',
        'notify_inv_hour': 'Invalid hour',
        'notify_bad_fmt': 'Format HH:MM',
        'notify_inv_int': 'Invalid interval'
    }
}

# =====================================================
# 2. PÁGINA PRINCIPAL
# =====================================================
@ui.page('/oldStudent')
def OldStudent():
    # Verificar sesión
    if not app.storage.user.get("username"):
        ui.navigate.to('/login')
        return

    # Renderizar Header (pasamos el callback de refresco)
    create_main_screen(page_refresh_callback=lambda: render_page_content.refresh())

    # Renderizar contenido refrescable
    render_page_content()

@ui.refreshable
def render_page_content():
    # 1. Obtener idioma y diccionario
    lang = app.storage.user.get('lang', 'es')
    t = OS_TRANSLATIONS[lang]

    # Contenedor Principal
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        
        # Encabezado de Página
        with ui.row().classes('items-center gap-4 mb-2'):
            ui.icon('history_edu', size='lg', color='pink-600')
            with ui.column().classes('gap-0'):
                ui.label(t['page_title']).classes('text-3xl font-bold text-gray-800')
                ui.label(t['page_subtitle']).classes('text-gray-500 text-sm')

        # --- TARJETA DE DECISIÓN ---
        with ui.card().classes('w-full bg-white shadow-md rounded-xl p-6 border-l-4 border-pink-500'):
            ui.label(t['status_label']).classes('text-xs font-bold text-gray-400 uppercase tracking-wider')
            with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                ui.label(t['question_classes']).classes('text-xl font-bold text-gray-800')
                
                # Toggle Traducido: Mapea 'Si' -> 'Yes', pero guarda 'Si' internamente
                toggle_options = {'Si': t['yes'], 'No': t['no']}
                
                has_classes = ui.toggle(toggle_options, value='Si')\
                    .props('no-caps push color=pink-600 toggle-color=pink-100 text-color=grey-8')

        # Contenedor Dinámico
        dynamic_container = ui.column().classes('w-full transition-all duration-300')

        def show_class_logic(e=None):
            dynamic_container.clear()
            # Usamos el valor interno 'Si' (no traducido)
            if has_classes.value == 'Si':
                show_existing_classes(dynamic_container, t, lang)
            else:
                show_new_student_like(dynamic_container, t, lang)

        has_classes.on('update:modelValue', show_class_logic)
        show_class_logic() # Carga inicial

# ==========================================
# LÓGICA 1: CLASES EXISTENTES (PENDIENTES)
# ==========================================
def show_existing_classes(container, t, lang):
    user = app.storage.user.get("username", "Usuario")

    with container:
        # Tarjeta Principal Estilo Dashboard
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header de la Tarjeta
            with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center gap-3'):
                ui.icon('edit_calendar', color='primary', size='sm')
                ui.label(t['title_pending']).classes('text-lg font-bold text-gray-800')

            with ui.column().classes('p-6 w-full gap-6'):
                
                # 1. Selección de Paquete (TRADUCIDO)
                pack_options_dict = {k: t_val(k, lang) for k in pack_of_classes}
                
                with ui.row().classes('w-full items-center'):
                    package_selector = ui.select(pack_options_dict, label=t['label_package'])\
                        .props('outlined dense options-dense behavior="menu"').classes('w-full md:w-1/3')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')

                ui.separator()

                # 2. Barra de Herramientas
                ui.label(t['label_config_ind']).classes('text-sm font-bold text-gray-500 uppercase')
                
                with ui.row().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-100 items-end gap-4 wrap'):
                    
                    # Fecha
                    with ui.input(t['label_date']).props('outlined dense bg-white').classes('w-40') as date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date().bind_value(date_input):
                                with ui.row().classes('justify-end'):
                                    ui.button('OK', on_click=menu.close).props('flat dense')
                        with date_input.add_slot('append'):
                            ui.icon('event').on('click', menu.open).classes('cursor-pointer text-blue-600')

                    # Duración (TRADUCIDO)
                    dur_options_dict = {k: t_val(k, lang) for k in duration_options}
                    duration_selector1 = ui.select(dur_options_dict, label=t['label_duration'])\
                        .props('outlined dense bg-white').classes('w-32')

                    # Hora Inicio
                    with ui.input(t['label_start_time']).props('outlined dense bg-white mask="time"').classes('w-32') as startD_time:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(startD_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('OK', on_click=menuD.close).props('flat dense')
                        with startD_time.add_slot('append'):
                            ui.icon('schedule').on('click', menuD.open).classes('cursor-pointer text-blue-600')

                    # Botón Agregar
                    add_hour_btn1 = ui.button(t['btn_add'], icon='add', color='primary').props('push')

                # 3. Tabla de Resultados
                ui.label(t['table_title_scheduled']).classes('text-lg font-bold mt-4')
                
                table_cols = [
                    {'name': 'fecha', 'label': t['col_date'], 'field': 'fecha', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'dia', 'label': t['col_day'], 'field': 'dia', 'align': 'center', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'hora', 'label': t['col_time'], 'field': 'hora', 'align': 'center', 'sortable': True, 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
                ]

                local_group_data = {} 

                table1 = ui.table(
                    columns=table_cols,
                    rows=[{'fecha': '', 'dia': '', 'hora': h} for h in hours_of_day],
                    selection='multiple',
                    row_key='hora'
                ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

                # --- MAGIA AQUÍ: SLOT TRADUCTOR ---
                # 1. Creamos un diccionario Python con las traducciones actuales: {'Lunes': 'Monday', 'Martes': 'Tuesday'...}
                # 2. Lo convertimos a string para inyectarlo en el Javascript del navegador.
                day_map_js = str({d: t_val(d, lang) for d in days_of_week})
                
                # 3. Definimos el slot 'body-cell-dia' (nombre de la columna 'dia')
                # Cuando la tabla va a pintar la celda, usa este mapa para traducir el valor al vuelo.
                table1.add_slot('body-cell-dia', f'''
                    <q-td :props="props">
                        {{{{ {day_map_js}[props.value] || props.value }}}}
                    </q-td>
                ''')
                # -----------------------------------

                # Controles de Tabla
                with ui.row().classes('w-full justify-between items-center mt-2'):
                    with ui.row().classes('gap-2'):
                        ui.button(t['btn_clear'], on_click=lambda: clear_table(table1, local_group_data), icon='cleaning_services', color='warning').props('flat dense')
                        btn_del = ui.button(t['btn_delete_sel'], icon='delete', color='negative').props('flat dense')
                    
                    save_button = ui.button(t['btn_confirm'], icon='save', color='positive').props('push')

                # Handlers
                selection_handler, selection_state = make_selection_handler(table1, logger=logger)
                table1.on('selection', selection_handler)
                btn_del.on('click', lambda: delete_selected_rows_v2(table1, selection_state, id_column="hora"))

                make_add_hours_by_date_button(
                    add_hour_btn1,
                    button_id=f"asignadas_de_{user}",
                    package_selector=package_selector,
                    start_time_input=startD_time,
                    duration_selector=duration_selector1,
                    date_input=date_input,
                    group_data=local_group_data,
                    table=table1,
                    notify_success=t['notify_added']
                )

                create_save_asgn_classes(  
                    button=save_button,
                    user=app.storage.user.get("username"),
                    table_clases=table1,
                    table_rangos=None, 
                    duration_selector=duration_selector1,
                    days_of_week=days_of_week, 
                    package_selector=package_selector
                )
# ==========================================
# LÓGICA 2: NUEVO HORARIO (PREFERENCIA)
# ==========================================
def show_new_student_like(container, t, lang):
    user = app.storage.user.get("username", "Usuario")
    
    with container:
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header
            with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-3'):
                ui.icon('settings_suggest', color='pink-600', size='sm')
                ui.label(t['title_preferences']).classes('text-lg font-bold text-gray-800')

            with ui.column().classes('p-6 w-full gap-6'):

                # 1. Configuración General
                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Paquete (TRADUCIDO)
                    pack_options_dict = {k: t_val(k, lang) for k in pack_of_classes}
                    package_selector = ui.select(pack_options_dict, label=t['label_package_pref'])\
                        .props('outlined dense options-dense').classes('w-full')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')

                    # Duración (TRADUCIDO)
                    dur_options_dict = {k: t_val(k, lang) for k in duration_options}
                    duration_selector3 = ui.select(dur_options_dict, label=t['label_duration_typ'])\
                        .props('outlined dense').classes('w-full')
                    duration_selector3.add_slot('prepend', '<q-icon name="timer" />')

                # Días Disponibles (TRADUCIDO)
                # Select múltiple: {'Lunes': 'Monday', ...}
                days_options_dict = {d: t_val(d, lang) for d in days_of_week}
                day_selector = ui.select(days_options_dict, label=t['label_days_enabled'], multiple=True, value=[])\
                    .props('outlined dense use-chips').classes('w-full')
                
                ui.separator()

                # 2. Barra de Herramientas
                ui.label(t['label_add_block']).classes('text-sm font-bold text-gray-500 uppercase')
                
                with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center gap-4 wrap'):
                    
                    with ui.row().classes('items-center gap-2'):
                        # Hora Inicio
                        with ui.input(t['label_from']).props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-28') as start_time:
                            with ui.menu().props('no-parent-event') as menu1:
                                with ui.time().bind_value(start_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menu1.close).props('flat dense')
                            with start_time.add_slot('append'):
                                ui.icon('access_time').on('click', menu1.open).classes('cursor-pointer text-gray-600')

                        ui.label('-').classes('text-gray-400 font-bold')

                        # Hora Fin
                        with ui.input(t['label_to']).props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-28') as end_time:
                            with ui.menu().props('no-parent-event') as menuD2:
                                with ui.time().bind_value(end_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD2.close).props('flat dense')
                            with end_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-600')

                    add_hour_btn2 = ui.button(t['btn_add_range'], icon='playlist_add', color='pink-600').props('push')

                # 3. Tabla de Resultados
                ui.label(t['table_title_proposed']).classes('text-lg font-bold mt-4')

                # Columnas dinámicas traducidas
                # t_val(d, lang)[:3] toma las primeras 3 letras del día traducido (ej: MON, TUE)
                cols = [{'name': 'hora', 'label': t['col_time'], 'field': 'hora', 'sortable': True, 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'}] + \
                       [{'name': d, 'label': t_val(d, lang)[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold'} for d in days_of_week]

                # Datos iniciales (vacíos)
                rows_data = [{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day]
                local_group_data_2 = {h: {d: '' for d in days_of_week} for h in hours_of_day}

                table4 = ui.table(
                    columns=cols,
                    rows=rows_data,
                    selection='multiple',
                    row_key='hora'
                ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

                # Footer Tabla
                with ui.row().classes('w-full justify-between items-center mt-2'):
                    with ui.row().classes('gap-2'):
                        ui.button(t['btn_clear'], on_click=lambda: clear_table(table4, local_group_data_2), icon='cleaning_services', color='warning').props('flat dense')
                        btn_del_2 = ui.button(t['btn_delete_sel'], icon='delete', color='negative').props('flat dense')

                    save_button = ui.button(t['btn_save_pref'], icon='save', color='positive').props('push')

                # Handlers
                selection_handler3, selection_state3 = make_selection_handler(table4, logger=logger)
                table4.on('selection', selection_handler3)
                btn_del_2.on('click', lambda: delete_selected_rows_v2(table4, selection_state3, id_column="hora"))

                # Botones lógicos
                make_add_hour_button(
                    add_hour_btn2,
                    button_id=f"rangos_horario_de_{user}",
                    day_selector=day_selector,
                    duration_selector=duration_selector3,
                    time_input=start_time,
                    end_time_input=end_time,
                    valid_hours=hours_of_day,
                    group_data=local_group_data_2,
                    days_of_week=days_of_week, # Interno (español) para mapear columnas de datos
                    table=table4,
                    # Notificaciones traducidas
                    notify_success=t['notify_range_added'],
                    notify_missing_day=t['notify_miss_day'],
                    notify_missing_duration=t['notify_miss_dur'],
                    notify_missing_time=t['notify_miss_start'],
                    notify_missing_end_time=t['notify_miss_end'],
                    notify_invalid_hour=t['notify_inv_hour'],
                    notify_bad_format=t['notify_bad_fmt'],
                    notify_interval_invalid=t['notify_inv_int']
                )
                
                create_save_schedule_button(
                    button=save_button,
                    table=table4,
                    days_of_week=days_of_week, # Interno
                    duration_selector=duration_selector3,
                    package_selector=package_selector
                )