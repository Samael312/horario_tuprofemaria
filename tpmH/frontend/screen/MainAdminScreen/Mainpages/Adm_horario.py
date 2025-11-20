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
    user = app.storage.user.get("username", "Usuario")
    create_admin_screen()

    # Verificar sesión
    username_sess = app.storage.user.get("username")
    if not username_sess:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    with ui.row().classes('w-full items-center justify-center'):
        ui.label('Horario de Disponibilidad').classes('text-h4 mt-4 text-center')
    
    with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):

        with ui.card().classes('w-full max-w-3xl p-4') as assigned_card:
            ui.label('¿Que modalidad quieres agregar?').classes('text-lg font-bold')
            ui.separator()
            has_classes = ui.radio(['General', 'Especifica'], value='Especifica')

        dynamic_container = ui.column().classes('w-full')

        def show_class_logic(e=None):
            dynamic_container.clear()
            if has_classes.value == 'Especifica':
                show_especifica(dynamic_container)
            else:
                show_general(dynamic_container)

        has_classes.on('update:modelValue', show_class_logic)
        show_class_logic()

def show_general(container):
    user = app.storage.user.get("username", "Usuario")

    with container:
        # ===================================================================
        # ========================  GENERALES  ===============================
        # ===================================================================
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
            ui.label('Generales').classes('text-h4 mt-1')

            # Selector de días
            with ui.card().classes('w-full p-4'):
                ui.label('Selecciona los días').classes('text-lg font-bold')
                ui.separator()
                day_selector_g = ui.select(
                    days_of_week,
                    label='Días',
                    multiple=True,
                    value=[]
                ).classes('w-auto min-w-[150px]')

            # Selector de disponibilidad y horas
            with ui.card().classes('w-full p-4'):
                ui.label('Disponibilidad y horas').classes('text-lg font-bold')
                ui.separator()

                with ui.row().classes('gap-4 mt-2'):

                    avai_selector_g = ui.select(
                        availability_options,
                        label='Disponibilidad'
                    ).classes('w-48')

                    # Hora inicio
                    with ui.input('Hora inicio') as start_time_g:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(start_time_g):
                                ui.button('Close', on_click=menuD.close).props('flat')
                        with start_time_g.add_slot('append'):
                            ui.icon('access_time').on('click', menuD.open)

                    # Hora fin
                    with ui.input('Hora fin') as end_time_g:
                        with ui.menu().props('no-parent-event') as menuD2:
                            with ui.time().bind_value(end_time_g):
                                ui.button('Close', on_click=menuD2.close).props('flat')
                        with end_time_g.add_slot('append'):
                            ui.icon('access_time').on('click', menuD2.open)

                add_hour_btn_g = ui.button('Agregar hora', color='primary')

            # TABLA GENERAL
            table5_card = ui.card().classes('w-full max-w-6xl p-4')
            with table5_card:
                ui.label("Tabla de Clases").classes('text-lg font-bold')
                ui.separator()

                table5 = ui.table(
                    columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora'}] +
                            [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                    rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                    row_key='hora',
                    selection='multiple'
                ).classes('w-full').props('dense bordered flat')

                with ui.row().classes('gap-4 mt-2'):
                    ui.button('Limpiar Tabla', on_click=lambda: clear_table(table5, group_data5), color='yellow')
                    ui.button('Eliminar filas seleccionadas',
                            color='negative',
                            on_click=lambda: delete_selected_rows_v2(table5, selection_state_g, id_column="hora"))

            selection_handler_g, selection_state_g = make_selection_handler(table5, logger=logger)
            table5.on('selection', selection_handler_g)
    
            with ui.row().classes('w-full items-center justify-center'):
                    save_button = ui.button('Guardar Información', color='positive')

# Función agregar horarios generales
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
            notify_success="Hora agregada",
            notify_missing_time="Selecciona hora de inicio",
            notify_missing_end_time="Selecciona hora de fin",
            notify_missing_avai="Selecciona disponibilidad",
            notify_invalid_hour="Hora no válida",
            notify_bad_format="Formato incorrecto HH:MM",
            notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
        )
    
    # Guardar
        create_save_schedule_admin_button(
            button= save_button,
            table= table5,
            days_of_week=days_of_week,
            availability=avai_selector_g
        )

def show_especifica(container):
    user = app.storage.user.get("username", "Usuario")

    with container:
    # ===================================================================
    # =======================  ESPECIFICAS  ==============================
        # ===================================================================
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
            ui.label('Especificas').classes('text-h4 mt-1')

            with ui.card().classes('w-full p-4'):
                ui.label('Disponibilidad y Fecha').classes('text-lg font-bold')
                ui.separator()

                with ui.row().classes('gap-4 mt-2'):

                    avai_selector_e = ui.select(
                        availability_options,
                        label='Disponibilidad'
                    ).classes('w-48')

                    # Fecha
                    with ui.input("Fecha") as date_input_e:
                        with ui.menu().props('no-parent-event') as menu:
                            with ui.date().bind_value(date_input_e):
                                ui.button('Close', on_click=menu.close).props('flat')
                        with date_input_e.add_slot('append'):
                            ui.icon('event').on('click', menu.open)

                    # Hora inicio
                    with ui.input('Hora inicio') as start_time_e:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(start_time_e):
                                ui.button('Close', on_click=menuD.close).props('flat')
                        with start_time_e.add_slot('append'):
                            ui.icon('access_time').on('click', menuD.open)

                    # Hora fin
                    with ui.input('Hora fin') as end_time_e:
                        with ui.menu().props('no-parent-event') as menuD2:
                            with ui.time().bind_value(end_time_e):
                                ui.button('Close', on_click=menuD2.close).props('flat')
                        with end_time_e.add_slot('append'):
                            ui.icon('access_time').on('click', menuD2.open)

                    add_hour_btn_e = ui.button('Agregar horas', color='primary')

            # TABLA ESPECÍFICA
            with ui.card().classes('w-full max-w-6xl p-4'):
                ui.label("Tabla de Fechas").classes('text-lg font-bold')
                ui.separator()

                table6 = ui.table(
                    columns=[
                        {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha'},
                        {'name': 'dia', 'label': 'Día', 'field': 'dia'},
                        {'name': 'hora', 'label': 'Hora', 'field': 'hora'},
                    ],
                    rows=[
                        {'fecha': '', 'dia': '', 'hora': h}
                        for h in hours_of_day
                    ],
                    row_key='hora',
                    selection='multiple'
                ).classes('w-full').props('dense bordered flat')

                with ui.row().classes('gap-4 mt-2'):
                    ui.button('Limpiar Tabla', on_click=lambda: clear_table(table6, group_data6), color='yellow')
                    ui.button('Eliminar filas seleccionadas',
                            color='negative',
                            on_click=lambda: delete_selected_rows_v2(table6, selection_state_e, id_column="hora"))

            selection_handler_e, selection_state_e = make_selection_handler(table6, logger=logger)
            table6.on('selection', selection_handler_e)

        # ===================================================================
        # ========================== GUARDADO ================================
        # ===================================================================

        with ui.row().classes('w-full items-center justify-center'):
            save_button = ui.button('Guardar Información', color='positive')

        

        # Función agregar horarios específicos
        make_add_hours_by_date_button(
            add_hour_btn_e,
            start_time_input=start_time_e,
            end_time_input=end_time_e,
            availability=avai_selector_e,
            date_input=date_input_e,
            group_data=group_data6,
            table=table6,
            button_id=None,
            notify_no_package="Selecciona un paquete primero",
            notify_no_start="Selecciona la hora de inicio",
            notify_no_end="Selecciona la hora de fin",
            notify_no_date="Selecciona una fecha",
            notify_bad_format="Formato incorrecto HH:MM",
            notify_success="Horas agregadas"
        )

        # Guardar
        create_save_asgn_classes_admin(
            button=save_button,
            user=app.storage.user.get("username"),
            table=table6,
            avai=avai_selector_e,
            days_of_week=days_of_week,
        )
