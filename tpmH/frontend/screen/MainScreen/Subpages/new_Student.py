from nicegui import ui, app
import logging
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from components.button_dur import make_add_hour_button
from components.h_selection import make_selection_handler
from components.delete_rows import delete_selected_rows_v2
from components.save_rgo import create_save_schedule_button

logging.basicConfig(
    level=logging.DEBUG,
    format="%(levelname)s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


# =========================
# NEW STUDENT
# =========================
@ui.page('/newStudent')
def new_student():
    user = app.storage.user.get("username", "Usuario")
    create_main_screen()


    with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):

        # 1. Selector de paquete
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Selecciona tu paquete de clases').classes('text-lg font-bold')
            ui.separator()
            package_selector = ui.select(pack_of_classes, label='Paquetes').classes('w-auto min-w-[150px]')

        # 2. Selector de días
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Selecciona los días').classes('text-lg font-bold')
            ui.separator()
            day_selector = ui.select(days_of_week, label='Días', multiple=True, value=[]).classes('w-auto min-w-[150px]')

            # Limitar días según paquete
            def limit_days(e):
                selected_package = package_selector.value
                max_days = max_days_per_plan.get(selected_package, 3)
                if len(day_selector.value) > max_days:
                    ui.notify(f'Solo puedes seleccionar {max_days} días para {selected_package}', color='warning')
                    day_selector.value = day_selector.value[:max_days]

            day_selector.on('update:modelValue', limit_days)

        # 3. Selector de duración
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Duración de la clase').classes('text-lg font-bold')
            ui.separator()
            duration_selector = ui.select(duration_options, label='Duración').classes('w-48')

        # 4. Selector de hora
        with ui.card().classes('w-full max-w-3xl p-4'):
            ui.label('Selecciona la hora').classes('text-lg font-bold')
            ui.separator()

            with ui.row().classes('gap-4 mt-2'):
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
        table3_card = ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4')
        with table3_card:
            ui.label("Tabla de Clases").classes('text-lg font-bold')
            ui.separator()
            table3 = ui.table(
                columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True}] +
                        [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                row_key='hora',
                selection='multiple'
            ).classes('w-full').props('dense bordered flat')
            with ui.row().classes('gap-4 mt-2'):
                #Limpiar tabla
                ui.button('Limpiar Tabla', on_click=lambda: clear_table(table3, group_data), color='yellow').classes('mt-2')
                ui.button('Eliminar filas seleccionadas',color='negative',on_click=lambda: delete_selected_rows_v2(table3, selection_state)).classes('mt-2')
        selection_handler, selection_state = make_selection_handler(table3, logger=logger)

        table3.on('selection', selection_handler)
        ids = selection_state["selected_rows"]

        # Botón de guardado
        save_button = ui.button('Guardar Información',color='positive')
    
        # -----------------------------
        # Reemplazo del botón "Agregar hora"
        # -----------------------------
        make_add_hour_button(
            add_hour_btn,
            day_selector=day_selector,
            duration_selector=duration_selector,
            button_id=f"rango_horario_de_{user}",
            time_input=start_time,
            end_time_input=end_time,
            valid_hours=hours_of_day,
            group_data=group_data,
            days_of_week=days_of_week,
            table=table3,
            notify_success="Hora agregada",
            notify_missing_day="Selecciona al menos un día",
            notify_missing_duration="Selecciona duración",
            notify_missing_time="Selecciona hora de inicio",
            notify_missing_end_time="Selecciona hora de fin",
            notify_invalid_hour="Hora no válida",
            notify_bad_format="Formato incorrecto HH:MM",
            notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
        )

        create_save_schedule_button(
            button= save_button,
            table=table3,
            days_of_week=days_of_week,
            duration_selector=duration_selector,
            package_selector=package_selector
        )
  