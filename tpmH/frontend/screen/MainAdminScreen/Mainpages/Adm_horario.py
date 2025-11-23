from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from components.share_data import *
from components.clear_table import clear_table
from components.botones.button_avai_dur import make_add_hour_avai_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save.save_admin_esp import create_save_asgn_classes_admin
from components.save.save_admin_rgo import create_save_schedule_admin_button
from components.botones.button_avai_esp_dur import make_add_hours_by_date_button

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

@ui.page('/Admhorario')
def adm_horario():
    # 1. Header y Auth
    create_admin_screen()

    username_sess = app.storage.user.get("username")
    if not username_sess:
        ui.navigate.to('/login')
        return

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        
        # 2. Encabezado de Página
        with ui.row().classes('w-full items-center gap-4 mb-2'):
            ui.icon('calendar_month', size='lg', color='pink-600')
            with ui.column().classes('gap-0'):
                ui.label('Gestión de Disponibilidad').classes('text-3xl font-bold text-gray-800')
                ui.label('Configura tus horarios generales o fechas específicas').classes('text-sm text-gray-500')

        # 3. Contenedor de Pestañas (Reemplaza al Radio Button)
        with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
            
            with ui.tabs().classes('w-full text-gray-600 bg-gray-50 border-b border-gray-200') \
                .props('active-color="pink-600" indicator-color="pink-600" align="justify" narrow-indicator') as tabs:
                t_general = ui.tab('General', icon='update').classes('h-14')
                t_specific = ui.tab('Específico', icon='event').classes('h-14')

            with ui.tab_panels(tabs, value=t_general).classes('w-full p-6'):
                
                #Panel General
                with ui.tab_panel(t_general):
                    show_general_content(username_sess)
                
                # Panel Específico
                with ui.tab_panel(t_specific):
                    show_specific_content(username_sess)


# ===================================================================
# LÓGICA VISUAL: HORARIO GENERAL
# ===================================================================
def show_general_content(user):
    
    with ui.column().classes('w-full gap-6'):
        
        # 1. Configuración de Días
        ui.label('Paso 1: Selecciona los días de la semana').classes('text-sm font-bold text-gray-500 uppercase')
        day_selector_g = ui.select(
            days_of_week,
            label='Días Activos',
            multiple=True,
            value=[]
        ).props('outlined dense use-chips multiple').classes('w-full')
        day_selector_g.add_slot('prepend', '<q-icon name="date_range" />')

        ui.separator()

        # 2. Barra de Herramientas (Disponibilidad y Horas)
        ui.label('Paso 2: Define bloques de hora y tipo').classes('text-sm font-bold text-gray-500 uppercase')
        
        with ui.row().classes('w-full bg-pink-50 p-4 rounded-lg border border-pink-100 items-center justify-between wrap gap-4'):
            
            # Selector Disponibilidad
            avai_selector_g = ui.select(
                availability_options,
                label='Tipo Disponibilidad'
            ).props('outlined dense bg-white').classes('w-full md:w-64')
            avai_selector_g.add_slot('prepend', '<q-icon name="category" />')

            with ui.row().classes('items-center gap-2'):
                # Hora Inicio
                with ui.input('Desde').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as start_time_g:
                    with ui.menu().props('no-parent-event') as menuD:
                        with ui.time().bind_value(start_time_g):
                            with ui.row().classes('justify-end'):
                                ui.button('OK', on_click=menuD.close).props('flat dense')
                    with start_time_g.add_slot('append'):
                        ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer text-gray-600')

                ui.label("-").classes('font-bold text-gray-400')

                # Hora Fin
                with ui.input('Hasta').props('outlined dense bg-white mask="time" placeholder="00:00"').classes('w-32') as end_time_g:
                    with ui.menu().props('no-parent-event') as menuD2:
                        with ui.time().bind_value(end_time_g):
                            with ui.row().classes('justify-end'):
                                ui.button('OK', on_click=menuD2.close).props('flat dense')
                    with end_time_g.add_slot('append'):
                        ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer text-gray-600')

            # Botón Agregar
            add_hour_btn_g = ui.button('Añadir Bloque', icon='add_circle', color='pink-600').props('push')

        # 3. Tabla General
        ui.label("Vista Previa del Horario Semanal").classes('text-lg font-bold text-gray-800 mt-2')
        
        # Definir columnas bonitas
        cols_g = [{'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'}] + \
                 [{'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-900 font-bold'} for d in days_of_week]

        table5 = ui.table(
            columns=cols_g,
            rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
            row_key='hora',
            selection='multiple'
        ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

        # Controles Tabla
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('gap-2'):
                ui.button('Limpiar', on_click=lambda: clear_table(table5, group_data5), icon='cleaning_services', color='warning').props('flat dense')
                ui.button('Borrar Selección', color='negative', icon='delete', on_click=lambda: delete_selected_rows_v2(table5, selection_state_g, id_column="hora")).props('flat dense')
            
            # Botón Guardar
            save_button = ui.button('Guardar Cambios Generales', icon='save', color='positive').props('push')

        # --- Handlers y Lógica ---
        selection_handler_g, selection_state_g = make_selection_handler(table5, logger=logger)
        table5.on('selection', selection_handler_g)

        make_add_hour_avai_button(
            add_hour_btn_g,
            day_selector=day_selector_g,
            availability=avai_selector_g,
            button_id=f"rango_horario_de_{user}",
            time_input=start_time_g,
            end_time_input=end_time_g,
            valid_hours=hours_of_day,
            group_data=group_data5,
            days_of_week=days_of_week,
            table=table5,
            notify_success="Bloque añadido",
            notify_missing_time="Falta hora inicio",
            notify_missing_end_time="Falta hora fin",
            notify_missing_avai="Selecciona disponibilidad",
            notify_invalid_hour="Hora inválida",
            notify_bad_format="Formato HH:MM requerido",
            notify_interval_invalid="Intervalo inválido"
        )
        
        create_save_schedule_admin_button(
            button=save_button,
            table=table5,
            days_of_week=days_of_week,
            availability=avai_selector_g
        )


# ===================================================================
# LÓGICA VISUAL: HORARIO ESPECÍFICO
# ===================================================================
def show_specific_content(user):
    
    with ui.column().classes('w-full gap-6'):
        
        ui.label('Configuración de Fechas Puntuales').classes('text-sm font-bold text-gray-500 uppercase')

        # Barra de Herramientas Unificada
        with ui.row().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-100 items-end justify-between wrap gap-4'):
            
            # Disponibilidad
            avai_selector_e = ui.select(
                availability_options,
                label='Disponibilidad'
            ).props('outlined dense bg-white').classes('w-full md:w-48')
            
            # Fecha
            with ui.input("Fecha").props('outlined dense bg-white').classes('w-40') as date_input_e:
                with ui.menu().props('no-parent-event') as menu:
                    with ui.date().bind_value(date_input_e):
                        with ui.row().classes('justify-end'):
                            ui.button('OK', on_click=menu.close).props('flat dense')
                with date_input_e.add_slot('append'):
                    ui.icon('event').on('click', menu.open).classes('cursor-pointer text-blue-600')

            # Horas
            with ui.row().classes('items-center gap-2'):
                with ui.input('Inicio').props('outlined dense bg-white mask="time"').classes('w-28') as start_time_e:
                    with ui.menu().props('no-parent-event') as menuD:
                        with ui.time().bind_value(start_time_e):
                            with ui.row().classes('justify-end'):
                                ui.button('OK', on_click=menuD.close).props('flat dense')
                    with start_time_e.add_slot('append'):
                        ui.icon('schedule').on('click', menuD.open).classes('cursor-pointer text-blue-600')

                with ui.input('Fin').props('outlined dense bg-white mask="time"').classes('w-28') as end_time_e:
                    with ui.menu().props('no-parent-event') as menuD2:
                        with ui.time().bind_value(end_time_e):
                            with ui.row().classes('justify-end'):
                                ui.button('OK', on_click=menuD2.close).props('flat dense')
                    with end_time_e.add_slot('append'):
                        ui.icon('schedule').on('click', menuD2.open).classes('cursor-pointer text-blue-600')

            # Botón Agregar
            add_hour_btn_e = ui.button('Añadir', icon='add', color='primary').props('push')

        # Tabla Específica
        ui.label("Lista de Excepciones / Fechas Puntuales").classes('text-lg font-bold text-gray-800 mt-2')
        
        cols_e = [
            {'name': 'fecha', 'label': 'FECHA', 'field': 'fecha', 'align': 'left', 'headerClasses': 'bg-gray-100 font-bold'},
            {'name': 'dia', 'label': 'DÍA', 'field': 'dia', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
            {'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-blue-100 text-blue-900 font-bold'},
        ]

        table6 = ui.table(
            columns=cols_e,
            rows=[{'fecha': '', 'dia': '', 'hora': h} for h in hours_of_day],
            row_key='hora',
            selection='multiple'
        ).classes('w-full border border-gray-200 rounded-lg overflow-hidden').props('flat bordered separator=cell density=compact')

        # Controles Tabla
        with ui.row().classes('w-full justify-between items-center'):
            with ui.row().classes('gap-2'):
                ui.button('Limpiar', on_click=lambda: clear_table(table6, group_data6), icon='cleaning_services', color='warning').props('flat dense')
                ui.button('Borrar Selección', color='negative', icon='delete', on_click=lambda: delete_selected_rows_v2(table6, selection_state_e, id_column="hora")).props('flat dense')
            
            # Botón Guardar
            save_button = ui.button('Confirmar Fechas', icon='save', color='positive').props('push')

        # --- Handlers y Lógica ---
        selection_handler_e, selection_state_e = make_selection_handler(table6, logger=logger)
        table6.on('selection', selection_handler_e)

        make_add_hours_by_date_button(
            add_hour_btn_e,
            start_time_input=start_time_e,
            end_time_input=end_time_e,
            availability=avai_selector_e,
            date_input=date_input_e,
            group_data=group_data6,
            table=table6,
            button_id=None,
            notify_no_package="Falta disponibilidad",
            notify_no_start="Falta hora inicio",
            notify_no_end="Falta hora fin",
            notify_no_date="Falta fecha",
            notify_bad_format="Formato HH:MM incorrecto",
            notify_success="Fecha añadida"
        )

        create_save_asgn_classes_admin(
            button=save_button,
            user=user,
            table=table6,
            avai=avai_selector_e,
            days_of_week=days_of_week,
        )