from nicegui import ui, app
from datetime import datetime
import logging
from components.header import create_main_screen
from components.share_data import *
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

# =========================
# OLD STUDENT PAGE
# =========================
@ui.page('/oldStudent')
def OldStudent():
    # Verificar sesión (opcional, buena práctica)
    if not app.storage.user.get("username"):
        ui.navigate.to('/login')
        return

    create_main_screen()

    # Contenedor Principal
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        
        # Encabezado de Página
        with ui.row().classes('items-center gap-4 mb-2'):
            ui.icon('history_edu', size='lg', color='pink-600')
            with ui.column().classes('gap-0'):
                ui.label('Portal de Estudiante').classes('text-3xl font-bold text-gray-800')
                ui.label('Gestionar recuperación de clases o nuevos horarios').classes('text-gray-500 text-sm')

        # --- TARJETA DE DECISIÓN ---
        with ui.card().classes('w-full bg-white shadow-md rounded-xl p-6 border-l-4 border-pink-500'):
            ui.label('Estado Actual').classes('text-xs font-bold text-gray-400 uppercase tracking-wider')
            with ui.row().classes('w-full items-center justify-between wrap gap-4'):
                ui.label('¿Tienes clases pendientes por asignar?').classes('text-xl font-bold text-gray-800')
                
                # Toggle estilizado en lugar de radio simple
                has_classes = ui.toggle(['Si', 'No'], value='Si').props('no-caps push color=pink-600 toggle-color=pink-100 text-color=grey-8')

        # Contenedor Dinámico
        dynamic_container = ui.column().classes('w-full transition-all duration-300')

        def show_class_logic(e=None):
            dynamic_container.clear()
            if has_classes.value == 'Si':
                show_existing_classes(dynamic_container)
            else:
                show_new_student_like(dynamic_container)

        has_classes.on('update:modelValue', show_class_logic)
        show_class_logic() # Carga inicial


# ==========================================
# LÓGICA 1: CLASES EXISTENTES (PENDIENTES)
# ==========================================
def show_existing_classes(container):
    user = app.storage.user.get("username", "Usuario")

    with container:
        # Tarjeta Principal Estilo Dashboard
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header de la Tarjeta
            with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center gap-3'):
                ui.icon('edit_calendar', color='primary', size='sm')
                ui.label('Agendar Clases Pendientes').classes('text-lg font-bold text-gray-800')

            with ui.column().classes('p-6 w-full gap-6'):
                
                # 1. Selección de Paquete
                with ui.row().classes('w-full items-center'):
                    package_selector = ui.select(pack_of_classes, label='Paquete Activo')\
                        .props('outlined dense options-dense behavior="menu"').classes('w-full md:w-1/3')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')

                ui.separator()

                # 2. Barra de Herramientas (Toolbox) para agregar
                ui.label('Configurar Clase Individual').classes('text-sm font-bold text-gray-500 uppercase')
                
                with ui.row().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-100 items-end gap-4 wrap'):
                    
                    # Fecha
                    with ui.input("Fecha").props('outlined dense bg-white').classes('w-40') as date_input:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date().bind_value(date_input):
                                with ui.row().classes('justify-end'):
                                    ui.button('OK', on_click=menu.close).props('flat dense')
                        with date_input.add_slot('append'):
                            ui.icon('event').on('click', menu.open).classes('cursor-pointer text-blue-600')

                    # Duración
                    duration_selector1 = ui.select(duration_options, label='Duración')\
                        .props('outlined dense bg-white').classes('w-32')

                    # Hora Inicio
                    with ui.input('Hora Inicio').props('outlined dense bg-white mask="time"').classes('w-32') as startD_time:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(startD_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('OK', on_click=menuD.close).props('flat dense')
                        with startD_time.add_slot('append'):
                            ui.icon('schedule').on('click', menuD.open).classes('cursor-pointer text-blue-600')

                    # Botón Agregar
                    add_hour_btn1 = ui.button('Agregar', icon='add', color='primary').props('push')

                # 3. Tabla de Resultados
                ui.label("Clases Agendadas").classes('text-lg font-bold mt-4')
                
                table_cols = [
                    {'name': 'fecha', 'label': 'FECHA', 'field': 'fecha', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'dia', 'label': 'DÍA', 'field': 'dia', 'align': 'center', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    {'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'sortable': True, 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
                ]

                table1 = ui.table(
                    columns=table_cols,
                    rows=[{'fecha': '', 'dia': '', 'hora': h} for h in hours_of_day], # Inicialización original
                    selection='multiple',
                    row_key='hora'
                ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

                # Controles de Tabla
                with ui.row().classes('w-full justify-between items-center mt-2'):
                    with ui.row().classes('gap-2'):
                        ui.button('Limpiar', on_click=lambda: clear_table(table1, group_data3), icon='cleaning_services', color='warning').props('flat dense')
                        ui.button('Borrar Seleccionados', icon='delete', color='negative', on_click=lambda: delete_selected_rows_v2(table1, selection_state, id_column="hora")).props('flat dense')
                    
                    # Botón Guardar Principal
                    save_button = ui.button('Confirmar Clases', icon='save', color='positive').props('push')

                # Handlers (Lógica interna)
                selection_handler, selection_state = make_selection_handler(table1, logger=logger)
                table1.on('selection', selection_handler)

                # Vinculación lógica botón agregar
                make_add_hours_by_date_button(
                    add_hour_btn1,
                    button_id=f"asignadas_de_{user}",
                    package_selector=package_selector,
                    start_time_input=startD_time,
                    duration_selector=duration_selector1,
                    date_input=date_input,
                    group_data=group_data3,
                    table=table1,
                    notify_success="Clase agregada a la lista"
                )

                # Vinculación lógica guardar
                create_save_asgn_classes(  
                    button=save_button,
                    user=app.storage.user.get("username"),
                    table_clases=table1,
                    table_rangos=None, # No aplica aquí
                    duration_selector=duration_selector1,
                    days_of_week=days_of_week,
                    package_selector=package_selector
                )

# ==========================================
# LÓGICA 2: NUEVO HORARIO (PREFERENCIA)
# ==========================================
def show_new_student_like(container):
    user = app.storage.user.get("username", "Usuario")
    
    with container:
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header
            with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-3'):
                ui.icon('settings_suggest', color='pink-600', size='sm')
                ui.label('Definir Preferencia de Horario Semanal').classes('text-lg font-bold text-gray-800')

            with ui.column().classes('p-6 w-full gap-6'):

                # 1. Configuración General
                with ui.grid(columns=2).classes('w-full gap-4'):
                    # Paquete
                    package_selector = ui.select(pack_of_classes, label='Paquete')\
                        .props('outlined dense options-dense').classes('w-full')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')

                    # Duración
                    duration_selector3 = ui.select(duration_options, label='Duración Típica')\
                        .props('outlined dense').classes('w-full')
                    duration_selector3.add_slot('prepend', '<q-icon name="timer" />')

                # Días Disponibles
                day_selector = ui.select(days_of_week, label='Días Habilitados', multiple=True, value=[])\
                    .props('outlined dense use-chips').classes('w-full')
                
                ui.separator()

                # 2. Barra de Herramientas (Rango de horas)
                ui.label('Añadir Bloque de Disponibilidad').classes('text-sm font-bold text-gray-500 uppercase')
                
                with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center gap-4 wrap'):
                    
                    with ui.row().classes('items-center gap-2'):
                        # Hora Inicio
                        with ui.input('Desde').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-28') as start_time:
                            with ui.menu().props('no-parent-event') as menu1:
                                with ui.time().bind_value(start_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menu1.close).props('flat dense')
                            with start_time.add_slot('append'):
                                ui.icon('access_time').on('click', menu1.open).classes('cursor-pointer text-gray-600')

                        ui.label('-').classes('text-gray-400 font-bold')

                        # Hora Fin
                        with ui.input('Hasta').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-28') as end_time:
                            with ui.menu().props('no-parent-event') as menuD2:
                                with ui.time().bind_value(end_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD2.close).props('flat dense')
                            with end_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-600')

                    add_hour_btn2 = ui.button('Añadir Rango', icon='playlist_add', color='pink-600').props('push')

                # 3. Tabla de Resultados (Style)
                ui.label("Horario Propuesto").classes('text-lg font-bold mt-4')

                # Columnas dinámicas bonitas
                cols = [{'name': 'hora', 'label': 'HORA', 'field': 'hora', 'sortable': True, 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'}] + \
                       [{'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold'} for d in days_of_week]

                table4 = ui.table(
                    columns=cols,
                    rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                    selection='multiple',
                    row_key='hora'
                ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

                # Footer Tabla
                with ui.row().classes('w-full justify-between items-center mt-2'):
                    with ui.row().classes('gap-2'):
                        ui.button('Limpiar', on_click=lambda: clear_table(table4, group_data2), icon='cleaning_services', color='warning').props('flat dense')
                        ui.button('Borrar Seleccionados', icon='delete', color='negative', on_click=lambda: delete_selected_rows_v2(table4, selection_state3, id_column="hora")).props('flat dense')

                    save_button = ui.button('Guardar Preferencias', icon='save', color='positive').props('push')

                # Handlers
                selection_handler3, selection_state3 = make_selection_handler(table4, logger=logger)
                table4.on('selection', selection_handler3)

                # Botones lógicos
                make_add_hour_button(
                    add_hour_btn2,
                    button_id=f"rangos_horario_de_{user}",
                    day_selector=day_selector,
                    duration_selector=duration_selector3,
                    time_input=start_time,
                    end_time_input=end_time,
                    valid_hours=hours_of_day,
                    group_data=group_data2,
                    days_of_week=days_of_week,
                    table=table4,
                    notify_success="Rango horario añadido",
                    notify_missing_day="Selecciona al menos un día arriba",
                    notify_missing_duration="Falta duración",
                    notify_missing_time="Falta inicio",
                    notify_missing_end_time="Falta fin",
                    notify_invalid_hour="Hora inválida",
                    notify_bad_format="Formato HH:MM",
                    notify_interval_invalid="Intervalo inválido"
                )
                
                create_save_schedule_button(
                    button=save_button,
                    table=table4,
                    days_of_week=days_of_week,
                    duration_selector=duration_selector3,
                    package_selector=package_selector
                )