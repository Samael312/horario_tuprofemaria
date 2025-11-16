from nicegui import ui
from datetime import datetime
from components.header import create_main_screen
from components.share_data import *
from components.clear_table import clear_table
from components.button_dur import make_add_hour_button
from components.button_fecha import make_add_hours_by_date_button


# =========================
# OLD STUDENT
# =========================
@ui.page('/oldStudent')
def OldStudent():
    create_main_screen()

    with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):

        with ui.card().classes('w-full max-w-3xl p-4') as assigned_card:
            ui.label('¿Tienes clases ya asignadas?').classes('text-lg font-bold')
            ui.separator()
            has_classes = ui.radio(['Si', 'No'], value='Si')

        dynamic_container = ui.column().classes('w-full')

        def show_class_logic(e=None):
            dynamic_container.clear()
            if has_classes.value == 'Si':
                show_existing_classes(dynamic_container)
            else:
                show_new_student_like(dynamic_container)

        has_classes.on('update:modelValue', show_class_logic)
        show_class_logic()


def show_existing_classes(container):
    with container:
        with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):
            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona tu paquete de clases').classes('text-lg font-bold')
                ui.separator()
                package_selector = ui.select(pack_of_classes, label='Paquetes').classes('w-auto min-w-[150px]')


            # Selector de hora inicio y hora fin
            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona hora de inicio y fin').classes('text-lg font-bold')
                ui.separator()

                with ui.input("Date") as date_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.date().bind_value(date_input):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with date_input.add_slot('append'):
                        ui.icon('event').on('click', menu.open).classes('cursor-pointer')

                with ui.row().classes('gap-4 mt-2'):
                    with ui.input('Hora inicio') as startD_time:
                        with ui.menu().props('no-parent-event') as menuD:
                            with ui.time().bind_value(startD_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menuD.close).props('flat')
                        with startD_time.add_slot('append'):
                            ui.icon('access_time').on('click', menuD.open).classes('cursor-pointer')

                    with ui.input('Hora fin') as endDe_time:
                        with ui.menu().props('no-parent-event') as menuD2:
                            with ui.time().bind_value(endDe_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menuD2.close).props('flat')
                        with endDe_time.add_slot('append'):
                            ui.icon('access_time').on('click', menuD2.open).classes('cursor-pointer')

                    add_hour_btn1 = ui.button('Agregar horas', color='primary')

            # Tabla
            with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4'):
                ui.label("Tabla de Clases Asiganadas").classes('text-lg font-bold')
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
                            'hora': h
                        }
                        for h in hours_of_day
                    ],
                    row_key='hora'
                ).classes('w-full').props('dense bordered flat')
                # Botón de limpiar tabla
                ui.button('Limpiar Tabla', on_click=lambda: clear_table(table1, group_data2), color='negative').classes('mt-2')

            # Selector de duración y días para nuevas horas
            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona duración').classes('text-lg font-bold')
                ui.separator()
                duration_selector = ui.select(duration_options, label='Duración').classes('w-48')

            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona los días').classes('text-lg font-bold')
                ui.separator()
                day_selector = ui.select(days_of_week, label='Días', multiple=True, value=[]).classes('w-auto min-w-[150px]')

                # Habilitar días al seleccionar paquete
                def enable_days(e):
                    if package_selector.value:
                        day_selector.props('disable=false')
                    else:
                        day_selector.props('disable=true')
                        day_selector.value = []

                package_selector.on('update:modelValue', enable_days)

                # Limitar días según paquete
                def limit_days(e):
                    selected_package = package_selector.value
                    if not selected_package:
                        return
                    max_days = max_days_per_plan.get(selected_package, 3)
                    if len(day_selector.value) > max_days:
                        ui.notify(f'Solo puedes seleccionar {max_days} días para {selected_package}', color='warning')
                        day_selector.value = day_selector.value[:max_days]

                day_selector.on('update:modelValue', limit_days)

                with ui.row().classes('gap-4 mt-2'):
                    with ui.input('Hora inicio') as start_time:
                        with ui.menu().props('no-parent-event') as menu1:
                            with ui.time().bind_value(start_time):
                                with ui.row().classes('justify-end'):
                                    ui.button('Close', on_click=menu1.close).props('flat')
                        with start_time.add_slot('append'):
                            ui.icon('access_time').on('click', menu1.open).classes('cursor-pointer')


                    add_hour_btn = ui.button('Agregar horas', color='primary')

            # Tabla
            with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4'):
                ui.label("Tabla de Clases").classes('text-lg font-bold')
                ui.separator()
                table2 = ui.table(
                    columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True}] +
                            [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                    rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                    row_key='hora'
                ).classes('w-full').props('dense bordered flat')
                # Botón de limpiar tabla
                ui.button('Limpiar Tabla', on_click=lambda: clear_table(table2, group_data), color='negative').classes('mt-2')
            
            #Boton de guardado
            save_button = ui.button('Guardar Información', on_click=None, color='positive').classes('mt-4')

            make_add_hours_by_date_button(
                add_hour_btn1,
                package_selector=package_selector,
                start_time_input=startD_time,
                end_time_input=endDe_time,
                date_input=date_input,
                group_data=group_data2,
                table=table1,
                notify_success="Horas agregadas correctamente"
            )


            make_add_hour_button(
                add_hour_btn,             # El botón que dispara la acción
                day_selector=day_selector,
                duration_selector=duration_selector,
                time_input=start_time,
                valid_hours=hours_of_day,  # Lista de horas válidas
                group_data=group_data,     # Dict donde se guardan los estados de las horas
                days_of_week=days_of_week, # Lista de días de la semana
                table=table2,              # Tabla a actualizar
                # Opcionales: personalizar mensajes
                notify_success="Hora agregada",
                notify_missing_day="Selecciona al menos un día",
                notify_missing_duration="Selecciona duración",
                notify_missing_time="Selecciona hora de inicio",
                notify_invalid_hour="Hora no válida",
                notify_bad_format="Formato incorrecto HH:MM",
                notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
)

def show_new_student_like(container):
    with container:
        with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):
            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona tu paquete de clases').classes('text-lg font-bold')
                ui.separator()
                package_selector = ui.select(pack_of_classes, label='Paquetes').classes('w-auto min-w-[150px]')

            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona los días').classes('text-lg font-bold')
                ui.separator()
                day_selector = ui.select(days_of_week, label='Días', multiple=True, value=[]).classes('w-auto min-w-[150px]')

                def limit_days(e):
                    selected_package = package_selector.value
                    max_days = max_days_per_plan.get(selected_package, 3)
                    if len(day_selector.value) > max_days:
                        ui.notify(f'Solo puedes seleccionar {max_days} días para {selected_package}', color='warning')
                        day_selector.value = day_selector.value[:max_days]

                day_selector.on('update:modelValue', limit_days)

            with ui.card().classes('w-full max-w-3xl p-4'):
                ui.label('Selecciona duración').classes('text-lg font-bold')
                ui.separator()
                duration_selector = ui.select(duration_options, label='Duración').classes('w-48')

            with ui.card().classes('w-full max-w-3xl p-4'):
                    ui.label('Selecciona hora').classes('text-lg font-bold')
                    ui.separator()
                    with ui.row().classes('gap-4 mt-2'):
                        with ui.input('Hora de inicio') as time_input:
                            with ui.menu().props('no-parent-event') as menu:
                                with ui.time().bind_value(time_input):
                                    with ui.row().classes('justify-end'):
                                        ui.button('Close', on_click=menu.close).props('flat')
                            with time_input.add_slot('append'):
                                ui.icon('access_time').on('click', menu.open).classes('cursor-pointer')
                        add_hour_btn1 = ui.button('Agregar hora', color='primary')

            with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4'):
                ui.label("Tabla de Clases").classes('text-lg font-bold')
                ui.separator()
                table4 = ui.table(
                    columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora', 'sortable': True}] +
                            [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                    rows=[{'hora': h, **{d: '' for d in days_of_week}} for h in hours_of_day],
                    row_key='hora'
                ).classes('w-full').props('dense bordered flat')
                #Limpiar tabla
                ui.button('Limpiar Tabla', on_click=lambda: clear_table(table4, group_data1), color='negative').classes('mt-2') 
            
            # Botón de guardado
            save_button = ui.button('Guardar Información', on_click=None, color='positive').classes
            
             # Función para agregar hora
            make_add_hour_button(
                add_hour_btn1,             # El botón que dispara la acción
                day_selector=day_selector,
                duration_selector=duration_selector,
                time_input=time_input,
                valid_hours=hours_of_day,  # Lista de horas válidas
                group_data=group_data,     # Dict donde se guardan los estados de las horas
                days_of_week=days_of_week, # Lista de días de la semana
                table=table4,              # Tabla a actualizar
                # Opcionales: personalizar mensajes
                notify_success="Hora agregada",
                notify_missing_day="Selecciona al menos un día",
                notify_missing_duration="Selecciona duración",
                notify_missing_time="Selecciona hora de inicio",
                notify_invalid_hour="Hora no válida",
                notify_bad_format="Formato incorrecto HH:MM",
                notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
)