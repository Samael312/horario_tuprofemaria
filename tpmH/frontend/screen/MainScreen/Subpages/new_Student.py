from nicegui import ui, app
import logging

# --- IMPORTS DE COMPONENTES ---
from components.header import create_main_screen
# Importamos valores compartidos y el helper de traducción
from components.share_data import (
    pack_of_classes, 
    duration_options, 
    days_of_week, 
    hours_of_day, 
    t_val
)
from components.clear_table import clear_table
from components.botones.button_dur import make_add_hour_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save.save_rgo import create_save_schedule_button

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =====================================================
# 1. TRADUCCIONES DE LA PANTALLA (NEW STUDENT)
# =====================================================
NS_TRANSLATIONS = {
    'es': {
        'page_title': 'Bienvenido/a a TuProfeMaria',
        'page_subtitle': 'Configuremos tu plan de estudios y disponibilidad ideal',
        'step1_title': 'Paso 1: Configuración del Plan',
        'label_package': 'Paquete Seleccionado',
        'label_duration': 'Duración de Clase',
        'label_days': 'Días Disponibles',
        'step2_title': 'Paso 2: Definir Rangos Horarios',
        'label_avail': 'Disponibilidad:',
        'label_from': 'Desde',
        'label_to': 'Hasta',
        'btn_add_range': 'Añadir Rango',
        'table_title': 'Vista Previa de Disponibilidad',
        'col_time': 'HORA',
        'btn_clear': 'Limpiar',
        'btn_delete_sel': 'Borrar Selección',
        'btn_save': 'Guardar Preferencias',
        # Notificaciones
        'notify_success': 'Rango añadido correctamente',
        'notify_miss_day': 'Selecciona al menos un día arriba',
        'notify_miss_dur': 'Falta seleccionar la duración',
        'notify_miss_start': 'Falta hora inicio',
        'notify_miss_end': 'Falta hora fin',
        'notify_inv_hour': 'Hora no válida',
        'notify_bad_fmt': 'Formato HH:MM requerido',
        'notify_inv_int': 'Intervalo inválido'
    },
    'en': {
        'page_title': 'Welcome to TuProfeMaria',
        'page_subtitle': 'Let\'s configure your study plan and ideal availability',
        'step1_title': 'Step 1: Plan Configuration',
        'label_package': 'Selected Package',
        'label_duration': 'Class Duration',
        'label_days': 'Available Days',
        'step2_title': 'Step 2: Define Time Ranges',
        'label_avail': 'Availability:',
        'label_from': 'From',
        'label_to': 'To',
        'btn_add_range': 'Add Range',
        'table_title': 'Availability Preview',
        'col_time': 'TIME',
        'btn_clear': 'Clear',
        'btn_delete_sel': 'Delete Selection',
        'btn_save': 'Save Preferences',
        # Notificaciones
        'notify_success': 'Range added successfully',
        'notify_miss_day': 'Select at least one day above',
        'notify_miss_dur': 'Duration missing',
        'notify_miss_start': 'Start time missing',
        'notify_miss_end': 'End time missing',
        'notify_inv_hour': 'Invalid hour',
        'notify_bad_fmt': 'Format HH:MM required',
        'notify_inv_int': 'Invalid interval'
    }
}

# =========================
# NEW STUDENT PAGE
# =========================
@ui.page('/newStudent')
def new_student():
    # Verificar sesión
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # Header con Callback de Refresco
    create_main_screen(page_refresh_callback=lambda: render_new_student_content.refresh())

    # Renderizar contenido refrescable
    render_new_student_content()

@ui.refreshable
def render_new_student_content():
    # 1. Obtener idioma actual y traducciones
    lang = app.storage.user.get('lang', 'es')
    t = NS_TRANSLATIONS[lang]
    
    # Recuperamos usuario para IDs únicos
    username = app.storage.user.get("username")

    # Contenedor Principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
        
        # 1. Encabezado de la página
        with ui.row().classes('items-center gap-4 mb-2'):
            ui.icon('school', size='lg', color='pink-600')
            with ui.column().classes('gap-0'):
                ui.label(t['page_title']).classes('text-3xl font-bold text-gray-800')
                ui.label(t['page_subtitle']).classes('text-gray-500 text-sm')

        # 2. Tarjeta Principal de Configuración
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header de Tarjeta
            with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-2'):
                ui.icon('tune', color='pink-600')
                ui.label(t['step1_title']).classes('text-lg font-bold text-gray-800')

            # Cuerpo de Tarjeta
            with ui.column().classes('p-6 w-full gap-6'):
                
                # --- Fila 1: Paquete y Duración (Grid) ---
                with ui.grid(columns=2).classes('w-full gap-6'):
                    
                    # Selector Paquete (Traducido)
                    pack_options_dict = {k: t_val(k, lang) for k in pack_of_classes}
                    package_selector = ui.select(pack_options_dict, label=t['label_package'])\
                        .props('outlined dense options-dense behavior="menu"').classes('w-full')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')

                    # Selector Duración (Traducido)
                    dur_options_dict = {k: t_val(k, lang) for k in duration_options}
                    duration_selector = ui.select(dur_options_dict, label=t['label_duration'])\
                        .props('outlined dense').classes('w-full')
                    duration_selector.add_slot('prepend', '<q-icon name="timer" />')

                # --- Fila 2: Días (Traducido) ---
                days_options_dict = {d: t_val(d, lang) for d in days_of_week}
                day_selector = ui.select(days_options_dict, label=t['label_days'], multiple=True, value=[])\
                    .props('outlined dense use-chips multiple').classes('w-full')
                day_selector.add_slot('prepend', '<q-icon name="calendar_month" />')

                ui.separator()

                # --- Fila 3: Barra de Herramientas para Horas ---
                ui.label(t['step2_title']).classes('text-sm font-bold text-gray-500 uppercase')
                
                # Contenedor gris para los controles de tiempo
                with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center justify-between wrap gap-4'):
                    
                    with ui.row().classes('items-center gap-3'):
                        ui.label(t['label_avail']).classes('font-bold text-gray-700')
                        
                        # Hora Inicio
                        with ui.input(t['label_from']).props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as start_time:
                            with ui.menu().props('no-parent-event') as menuD:
                                with ui.time().bind_value(start_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD.close).props('flat dense')
                            with start_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-600')

                        ui.label("-").classes('font-bold text-gray-400')

                        # Hora Fin
                        with ui.input(t['label_to']).props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as end_time:
                            with ui.menu().props('no-parent-event') as menuD2:
                                with ui.time().bind_value(end_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD2.close).props('flat dense')
                            with end_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-600')

                    # Botón Agregar
                    add_hour_btn = ui.button(t['btn_add_range'], icon='add_circle', color='pink-600').props('push')

        # 3. Tarjeta de Tabla (Resultados)
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
             # Header de Tabla
            with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('table_view', color='gray-600')
                    ui.label(t['table_title']).classes('text-lg font-bold text-gray-800')
                
                # Botones de acción rápida en el header de la tabla
                with ui.row().classes('gap-2'):
                    # Inicializamos group_data localmente para refresco seguro
                    local_group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
                    
                    ui.button(t['btn_clear'], on_click=lambda: clear_table(table3, local_group_data), icon='cleaning_services', color='warning').props('flat dense')
                    btn_del = ui.button(t['btn_delete_sel'], color='negative', icon='delete').props('flat dense')

            # Definición de columnas con estilos y traducción
            # t_val(d, lang)[:3] -> 'Lunes' -> 'Monday' -> 'MON'
            columns_style = [
                {'name': 'hora', 'label': t['col_time'], 'field': 'hora', 'sortable': True, 'align': 'center', 'headerClasses': 'bg-gray-100 text-gray-800 font-bold border-b'}
            ] + [
                {'name': d, 'label': t_val(d, lang)[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-50 text-pink-800 font-bold border-b'} 
                for d in days_of_week
            ]

            # Tabla
            table3 = ui.table(
                columns=columns_style,
                rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                row_key='hora',
                selection='multiple'
            ).classes('w-full').props('flat bordered separator=cell density=compact')

            # Footer de Tabla (Botón Guardar)
            with ui.row().classes('w-full p-4 bg-gray-50 border-t border-gray-200 justify-end'):
                 save_button = ui.button(t['btn_save'], icon='save', color='positive').props('push size=lg')

        # --- Lógica y Handlers ---
        selection_handler, selection_state = make_selection_handler(table3, logger=logger)
        table3.on('selection', selection_handler)
        btn_del.on('click', lambda: delete_selected_rows_v2(table3, selection_state, id_column="hora"))

        # Conectar lógica del botón agregar hora (Pasamos textos traducidos para notificaciones)
        make_add_hour_button(
            add_hour_btn,
            day_selector=day_selector,
            duration_selector=duration_selector,
            button_id=f"rango_horario_de_{username}",
            time_input=start_time,
            end_time_input=end_time,
            valid_hours=hours_of_day,
            group_data=local_group_data,
            days_of_week=days_of_week, # Clave interna (español) para mapear datos
            table=table3,
            notify_success=t['notify_success'],
            notify_missing_day=t['notify_miss_day'],
            notify_missing_duration=t['notify_miss_dur'],
            notify_missing_time=t['notify_miss_start'],
            notify_missing_end_time=t['notify_miss_end'],
            notify_invalid_hour=t['notify_inv_hour'],
            notify_bad_format=t['notify_bad_fmt'],
            notify_interval_invalid=t['notify_inv_int']
        )

        # Conectar lógica del botón guardar
        create_save_schedule_button(
            button=save_button,
            table=table3,
            days_of_week=days_of_week, # Clave interna
            duration_selector=duration_selector,
            package_selector=package_selector
        )