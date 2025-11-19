from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from components.share_data import *
from components.clear_table import clear_table
from components.button_avai_dur import make_add_hour_avai_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save_admin_rgo import create_save_schedule_admin_button

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

# =========================
# NEW STUDENT
# =========================
@ui.page('/Admhorario')
def adm_horario():
    user = app.storage.user.get("username", "Usuario")
    create_admin_screen()

    # Verificar sesión
    username_sess = app.storage.user.get("username")
    if not username_sess:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return
    
    with ui.row().classes('w-full items-center justify-center'):
        ui.label('Horario de Disponibilidad').classes('text-h4 mt-4 text-center')

    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
        with ui.row().classes('w-full mx-auto'):
                ui.label('Generales').classes('text-h4 max-auto mt-1 relative')
        # 1. Selector de días
        with ui.card().classes('w-full max-auto p-4'):
            ui.label('Selecciona los días').classes('text-lg font-bold')
            ui.separator()
            day_selector = ui.select(days_of_week, 
                                     label='Días', multiple=True, 
                                     value=[]).classes('w-auto min-w-[150px]')
        
        # 3. Selector de disponibilidad
        with ui.card().classes('w-full max-auto p-4'):
            ui.label('Disponibilidad y horas').classes('text-lg font-bold')
            ui.separator()
            with ui.row().classes('gap-4 mt-2'):
                avai_selector = ui.select(availability_options, label='Disponibilidad').classes('w-48')

        
                with ui.input('Hora inicio') as start_time:
                    with ui.menu().props('no-parent-event') as menuD:
                        with ui.time().bind_value(start_time):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menuD.close).props('flat')
                    with start_time.add_slot('append'):
                        ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer')

                with ui.input('Hora fin') as end_time:
                    with ui.menu().props('no-parent-event') as menuD2:
                        with ui.time().bind_value(end_time):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menuD2.close).props('flat')
                    with end_time.add_slot('append'):
                        ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer')

            add_hour_btn = ui.button('Agregar hora', color='primary')
        
        # 5. Tabla de clases
        table5_card = ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4')
        with table5_card:
            ui.label("Tabla de Clases").classes('text-lg font-bold')
            ui.separator()
            table5 = ui.table(
                columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True}] +
                        [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                row_key='hora',
                selection='multiple'
            ).classes('w-full').props('dense bordered flat')
            with ui.row().classes('gap-4 mt-2'):
                #Limpiar tabla
                ui.button('Limpiar Tabla', on_click=lambda: clear_table(table5, group_data5), color='yellow').classes('mt-2')
                ui.button('Eliminar filas seleccionadas',color='negative',on_click=lambda: delete_selected_rows_v2(table5, selection_state, id_column="hora")).classes('mt-2')
        selection_handler, selection_state = make_selection_handler(table5, logger=logger)

        table5.on('selection', selection_handler)
        ids = selection_state["selected_rows"]

#------------------------ESPECIFICOS----------------------------------------------------------
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
        with ui.row().classes('w-full mx-auto'):
                ui.label('Especificas').classes('text-h4 max-auto mt-1 relative')
        
            # 1. Selector de días
        with ui.card().classes('w-full max-auto p-4'):
            ui.label('Selecciona los días').classes('text-lg font-bold')
            ui.separator()
            day_selector = ui.select(days_of_week, 
                                    label='Días', multiple=True, 
                                    value=[]).classes('w-auto min-w-[150px]')
        
        # 3. Selector de disponibilidad
        with ui.card().classes('w-full max-auto p-4'):
            ui.label('Disponibilidad y Fecha').classes('text-lg font-bold')
            ui.separator()
            with ui.row().classes('gap-4 mt-2'):
                avai_selector = ui.select(availability_options, label='Disponibilidad').classes('w-48')

                with ui.input("Date") as date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date().bind_value(date_input):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with date_input.add_slot('append'):
                        ui.icon('event').on('click', menu.open).classes('cursor-pointer')
                    
                with ui.input('Hora inicio') as start_time:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(start_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menuD.close).props('flat')
                        with start_time.add_slot('append'):
                            ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer')

                with ui.input('Hora fin') as end_time:
                        with ui.menu().props('no-parent-event') as menuD2:
                            with ui.time().bind_value(end_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menuD2.close).props('flat')
                        with end_time.add_slot('append'):
                            ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer')

                add_hour_btn1 = ui.button('Agregar horas', color='primary')

        # Tabla
        with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4'):
                ui.label("Tabla de Fechas").classes('text-lg font-bold')
                ui.separator()

                table1 = ui.table(
                    columns=[
                        {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'sortable': True},
                        {'name': 'dia', 'label': 'Día', 'field': 'dia', 'sortable': True},
                        {'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True},
                        ],
                    rows=[
                        {
                            'fecha': '',
                            'dia': '',
                            'hora': h,
                        }
                        for h in hours_of_day
                    ],
                    selection='multiple',
                    row_key='hora'
                ).classes('w-full').props('dense bordered flat')
                with ui.row().classes('gap-4 mt-2'):
                    #Limpiar tabla
                    ui.button('Limpiar Tabla', on_click=lambda: clear_table(table1, group_data3), color='yellow').classes('mt-2')
                    ui.button('Eliminar filas seleccionadas',color='negative',on_click=lambda: delete_selected_rows_v2(table1, selection_state, id_column="hora")).classes('mt-2')
        selection_handler, selection_state = make_selection_handler(table1, logger=logger)
        table1.on('selection', selection_handler)
        ids = selection_state["selected_rows"]


#--------------------------------------SAVE-----------------------------------------------------------------
        with ui.row().classes('w-full items-center justify-center'):
        # Botón de guardado
            save_button = ui.button('Guardar Información',color='positive')
    
        # -----------------------------
        # Reemplazo del botón "Agregar hora"
        # -----------------------------
        make_add_hour_avai_button(
            add_hour_btn,
            day_selector=day_selector,
            availability=avai_selector,
            button_id=f"rango_horario_de_{user}",
            time_input=start_time,
            end_time_input=end_time,
            valid_hours=hours_of_day,
            group_data=group_data5,
            days_of_week=days_of_week,
            table=table5,
            notify_success="Hora agregada",
            notify_missing_day="Selecciona al menos un día",
            notify_missing_time="Selecciona hora de inicio",
            notify_missing_end_time="Selecciona hora de fin",
            notify_missing_avai="Selecciona disponibilidad",
            notify_invalid_hour="Hora no válida",
            notify_bad_format="Formato incorrecto HH:MM",
            notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
        )

        create_save_schedule_admin_button(
            button= save_button,
            table=table5,
            days_of_week=days_of_week,
            availability=avai_selector,
        )