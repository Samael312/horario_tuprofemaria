from nicegui import ui, app
import logging
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from components.botones.button_dur import make_add_hour_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save.save_rgo import create_save_schedule_button
from components.save.save_asg import create_save_asgn_classes
from db.postgres_db import PostgresSession
from db.models import User, SchedulePref, AsignedClasses

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
# =========================
# NEW STUDENT PAGE
# =========================
@ui.page('/newStudent')
def new_student():
    # Verificar sesión básico
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    create_main_screen()


    # --- Diálogo 1: Configuración de Horas ---
    with ui.dialog() as tuto_dialog_1, ui.card().classes('w-full max-w-sm p-0 rounded-2xl shadow-2xl border border-gray-100'):
    
        # Imagen/Gradiente decorativo superior
        with ui.column().classes('w-full bg-gradient-to-br from-rose-400 to-rose-600 p-8 items-center relative overflow-hidden'):
            # Decoración de fondo (círculos sutiles)
            ui.element('div').classes('absolute top-0 right-0 w-24 h-24 bg-white opacity-10 rounded-full -mr-10 -mt-10')
            ui.icon('menu_book', size='3.5em', color='white').classes('drop-shadow-md')
            ui.label('Guía Inicial').classes('text-white text-lg font-bold mt-3 tracking-wide')

        # Contenido
        with ui.column().classes('p-8 items-center text-center gap-4'):
            ui.label('En esta pantalla configurarás tus horas preferenciales, confirmarás tu paquete y definirás tu duración ideal.').classes('text-gray-600 leading-7 text-sm')
            
            ui.separator().classes('w-1/2 opacity-50')
            
            # Botón con estilo "Outline" moderno
            ui.button('Continuar', on_click=tuto_dialog_1.close) \
                .props('outline rounded') \
                .classes('text-rose-600 border-rose-200 hover:bg-rose-50 w-full font-semibold')
    
    ui.timer(0.5, tuto_dialog_1.open, once=True)

    # Contenedor Principal
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
        
        # 1. Encabezado de la página
        with ui.row().classes('items-center gap-4 mb-2'):
            ui.icon('school', size='lg', color='pink-600')
            with ui.column().classes('gap-0'):
                ui.label('Bienvenido/a a TuProfeMaria').classes('text-3xl font-bold text-gray-800')
                ui.label('Configuremos tu plan de estudios y disponibilidad ideal').classes('text-gray-500 text-sm')

        # 2. Tarjeta Principal de Configuración
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            # Header de Tarjeta
            with ui.row().classes('w-full bg-pink-50 p-4 border-b border-pink-100 items-center gap-2'):
                ui.icon('tune', color='pink-600')
                ui.label("Paso 1: Configuración del Plan").classes('text-lg font-bold text-gray-800')

            # Cuerpo de Tarjeta
            with ui.column().classes('p-6 w-full gap-6'):

                 # Verificar sesión
                username = app.storage.user.get("username")
                if not username:
                    ui.navigate.to('/login')
                    return
                            
                session = PostgresSession()
               
                user_obj = session.query(User).filter(User.username == username).first()
                    
                if not user_obj:
                        ui.notify("Usuario no encontrado", type='negative')
                
                package = user_obj.package

                # 1. Configuración General
                with ui.grid(columns=2).classes('w-full gap-4'):
                    app.storage.user.get('selected_plan')
                    
                    package_selector = ui.select(pack_of_classes, label='Paquete Activo', value=package)\
                        .props('outlined dense options-dense behavior="menu"').classes('w-full md:w-1/3')
                    package_selector.add_slot('prepend', '<q-icon name="inventory_2" />')
            

                    # Selector Duración
                    duration_selector = ui.select(duration_options, label='Duración de Clase')\
                        .props('outlined dense').classes('w-full')
                    duration_selector.add_slot('prepend', '<q-icon name="timer" />')

                # --- Fila 2: Días ---
                day_selector = ui.select(days_of_week, label='Días Disponibles', multiple=True, value=[])\
                    .props('outlined dense use-chips multiple').classes('w-full')
                day_selector.add_slot('prepend', '<q-icon name="calendar_month" />')

                ui.separator()

                # --- Fila 3: Barra de Herramientas para Horas ---
                ui.label("Paso 2: Definir Rangos Horarios").classes('text-sm font-bold text-gray-500 uppercase')
                
                # Contenedor gris para los controles de tiempo
                with ui.row().classes('w-full bg-gray-50 p-4 rounded-lg border border-gray-200 items-center justify-between wrap gap-4'):
                    
                    with ui.row().classes('items-center gap-3'):
                        ui.label("Disponibilidad:").classes('font-bold text-gray-700')
                        
                        # Hora Inicio
                        with ui.input('Desde').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as start_time:
                            with ui.menu().props('no-parent-event') as menuD:
                                with ui.time().bind_value(start_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD.close).props('flat dense')
                            with start_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-600')

                        ui.label("-").classes('font-bold text-gray-400')

                        # Hora Fin
                        with ui.input('Hasta').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as end_time:
                            with ui.menu().props('no-parent-event') as menuD2:
                                with ui.time().bind_value(end_time):
                                    with ui.row().classes('justify-end'):
                                        ui.button('OK', on_click=menuD2.close).props('flat dense')
                            with end_time.add_slot('append'):
                                ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-600')

                    # Botón Agregar
                    add_hour_btn = ui.button('Añadir Rango', icon='add_circle', color='pink-600').props('push')

        # 3. Tarjeta de Tabla (Resultados)
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
             # Header de Tabla
            with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('table_view', color='gray-600')
                    ui.label("Vista Previa de Disponibilidad").classes('text-lg font-bold text-gray-800')
                
                # Botones de acción rápida en el header de la tabla
                with ui.row().classes('gap-2'):
                    ui.button('Limpiar', on_click=lambda: clear_table(table3, group_data), icon='cleaning_services', color='warning').props('flat dense')
                    ui.button('Borrar Selección', color='negative', icon='delete', on_click=lambda: delete_selected_rows_v2(table3, selection_state, id_column="hora")).props('flat dense')

            # Definición de columnas con estilos
            columns_style = [
                {'name': 'hora', 'label': 'HORA', 'field': 'hora', 'sortable': True, 'align': 'center', 'headerClasses': 'bg-gray-100 text-gray-800 font-bold border-b'}
            ] + [
                {'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-50 text-pink-800 font-bold border-b'} 
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
                 save_button = ui.button('Guardar Preferencias', icon='save', color='positive').props('push size=lg')

        # --- Lógica y Handlers ---
        selection_handler, selection_state = make_selection_handler(table3, logger=logger)
        table3.on('selection', selection_handler)

        # Conectar lógica del botón agregar hora
        make_add_hour_button(
            add_hour_btn,
            day_selector=day_selector,
            duration_selector=duration_selector,
            button_id=f"rango_horario_de_{username}",
            time_input=start_time,
            end_time_input=end_time,
            valid_hours=hours_of_day,
            group_data=group_data,
            days_of_week=days_of_week,
            table=table3,
            notify_success="Rango añadido correctamente",
            notify_missing_day="Selecciona al menos un día arriba",
            notify_missing_duration="Falta seleccionar la duración",
            notify_missing_time="Falta hora inicio",
            notify_missing_end_time="Falta hora fin",
            notify_invalid_hour="Hora no válida",
            notify_bad_format="Formato HH:MM requerido",
            notify_interval_invalid="Intervalo inválido"
        )

        # Conectar lógica del botón guardar (IMPORTANTE: Esto ahora llama a la lógica de Neon)
        create_save_schedule_button(
            button=save_button,
            table=table3,
            days_of_week=days_of_week,
            duration_selector=duration_selector,
            package_selector=package_selector
        )
