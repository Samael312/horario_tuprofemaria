from nicegui import ui, app
from datetime import datetime

# =========================
# HEADER COMÚN
# =========================
def create_main_screen():
    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    with ui.header().classes('p-2 items-center justify-between'):
        ui.label('Tuprofemaria').classes('text-white text-xl font-bold')
        with ui.row().classes('gap-4'):
            ui.button('Menu Creator', on_click=lambda: ui.navigate.to('/mainscreen')).props('flat color=white')
            ui.button('My Classes', on_click=lambda: ui.navigate.to('/myclasses')).props('flat color=white')
            ui.button('Profile', on_click=lambda: ui.navigate.to('/profile')).props('flat color=white')
            ui.button('Log out', on_click=logout).props('flat color=black')


# =========================
# PÁGINAS
# =========================
@ui.page('/mainscreen')
def mainscreen():
    create_main_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label(f'Bienvenido, {app.storage.user.get("username", "Usuario")}!').classes('text-2xl')
        with ui.row().classes('gap-2'):
            ui.button('Old Student', on_click=lambda: ui.navigate.to('/oldStudent')).props('flat color=primary')
            ui.button('New Student', on_click=lambda: ui.navigate.to('/newStudent')).props('flat color=primary')


# =========================
# Lógica de paquetes y clases (global)
# =========================
days_of_week = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
duration_options = ['30 minutos', '1 hora']
pack_of_classes = ["Plan1", "Plan2", "Plan3"]

max_days_per_plan = {"Plan1": 1, "Plan2": 2, "Plan3": 3}
max_classes_per_plan = {"Plan1": 1, "Plan2": 1, "Plan3": 3}

hours_of_day = [f'{h:02d}:{m:02d}' 
                for h in range(24) 
                for m in (0, 30)]

group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data1 = {h: {d: '' for d in days_of_week} for h in hours_of_day}
group_data2 = {}


# ===============================
# FUNCIONES DE TABLAS (UNIVERSALES)
# ===============================


def clear_table(table, group_dict):
    """Limpia toda la tabla y el diccionario asociado."""
    for h in group_dict:
        for d in group_dict[h]:
            group_dict[h][d] = ''

    table.rows = []
    table.update()

    ui.notify("Tabla limpiada", color="positive")
    
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


                    add_hour_btn2 = ui.button('Agregar horas', color='primary')

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

            # Función para agregar horas seleccionadas en la tabla usando group_data
            #add_hour_btn1
            def add_hours_to_table_pref():
                # Validaciones
                if not package_selector.value:
                    ui.notify('Selecciona un paquete primero', color='warning')
                    return

                if not startD_time.value or not endDe_time.value:
                    ui.notify('Selecciona hora de inicio y fin', color='warning')
                    return

                if not date_input.value:
                    ui.notify('Selecciona una fecha', color='warning')
                    return

                # Convertir horas a enteros
                try:
                    h_start, m_start = map(int, startD_time.value.split(':'))
                    h_end, m_end = map(int, endDe_time.value.split(':'))
                except:
                    ui.notify('Formato de hora incorrecto HH:MM', color='warning')
                    return

                # Crear intervalos EXACTOS según el usuario
                intervalos = []

                # Agregar inicio exactamente como lo ingresó
                intervalos.append(f"{h_start:02d}:{m_start:02d}")

                # Si la hora fin es diferente, agregarla también
                if not (h_start == h_end and m_start == m_end):
                    intervalos.append(f"{h_end:02d}:{m_end:02d}")

                # Obtener fecha y día
                fecha = date_input.value  # YYYY-MM-DD
                fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
                dia_str = fecha_dt.strftime('%A')  # Monday, Tuesday...
                
                # Si lo quieres en español:
                dias_es = {
                    "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                    "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
                }
                dia = dias_es[dia_str]

                 # Crear si no existe esa fecha
                if fecha not in group_data2:
                    group_data2[fecha] = {}

                   # Guardar intervalos igual que en group_data
                for h_lbl in intervalos:
                    group_data2[fecha][h_lbl] = {
                        'fecha': fecha,
                        'dia': dia,
                        'hora': h_lbl
                    }

                # Reconstruir tabla1
                new_rows = []
                for fecha_key, horas in group_data2.items():
                    for h_lbl, data in horas.items():
                        new_rows.append(data)

                # Ordenar la tabla por fecha y hora
                new_rows.sort(key=lambda x: (x['fecha'], x['hora']))

                table1.rows = new_rows
                table1.update()

                ui.notify('Horas agregadas', type='positive')


            add_hour_btn1.on('click', add_hours_to_table_pref)
    
    # Función para agregar horas seleccionadas en la tabla usando group_data
    #add_hour_btn2
            def add_hours_to_table():
                selected_package = package_selector.value
                duration = duration_selector.value
                hora_inicio = start_time.value

                if not selected_package:
                    ui.notify('Selecciona un paquete primero', color='warning')
                    return
                if not duration:
                    ui.notify('Selecciona duración', color='warning')
                    return  
                if not start_time.value :
                    ui.notify('Selecciona hora de inicio', color='warning')
                    return
                if not day_selector.value:
                    ui.notify('Selecciona al menos un día', color='warning')
                    return

                try:
                    h, m = map(int, hora_inicio.split(':'))
                    hora_label = f'{h:02d}:00'
                    if hora_label not in hours_of_day:
                        ui.notify('Hora no válida', color='warning')
                        return
                except:
                    ui.notify('Formato incorrecto HH:MM', color='warning')
                    return

                #Intervalos segun duracion
                intervalos = [f'{h:02d}:{m:02d}']
                if duration == '30 minutos':
                    m2 = m + 30
                    h2 = h + (m2 // 60)       # suma 1 hora si pasa de 60 min
                    m2 = m2 % 60              # minutos finales corregidos
                    if h2 < 24:
                        intervalos.append(f'{h2:02d}:{m2:02d}')
                elif duration == '1 hora':
                    h2 = h + 1
                    if h2 < 24:
                        intervalos.append(f'{h2:02d}:00')

                # Actualizar group_data
                for h_lbl in intervalos:
                    if h_lbl not in group_data:
                        ui.notify(f'Hora {h_lbl} es invalida, solo intervalos de 1h o 30minutos')
                        continue  # evita el KeyError y pasa al siguiente intervalo
                    for d in days_of_week:
                        group_data[h_lbl][d] = 'Elegida' if d in day_selector.value else ''

                # Reconstruir tabla
                new_rows = [{
                    'hora': h_lbl, **group_data[h_lbl]} for h_lbl in hours_of_day 
                    if any(group_data[h_lbl][d] for d in days_of_week)]
                table2.rows = new_rows
                table2.update()
                ui.notify('Horas agregadas', type='positive')

            add_hour_btn2.on('click', add_hours_to_table)

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
                        add_hour_btn3 = ui.button('Agregar hora', color='primary')

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
        def add_hour_action():
            selected_days = day_selector.value
            duration = duration_selector.value
            hora_inicio = time_input.value

            if not selected_days:
                ui.notify('Selecciona al menos un día', color='warning')
                return
            if not duration:
                ui.notify('Selecciona duración', color='warning')
                return
            if not hora_inicio:
                ui.notify('Selecciona hora de inicio', color='warning')
                return

            try:
                h, m = map(int, hora_inicio.split(':'))
                hora_label = f'{h:02d}:00'
                if hora_label not in hours_of_day:
                    ui.notify('Hora no válida', color='warning')
                    return
            except:
                ui.notify('Formato incorrecto HH:MM', color='warning')
                return

            # Calcular intervalos
            intervalos = [hora_label]
            if duration == '30 minutos':
                m2 = m + 30
                h2 = h + (m2 // 60)
                m2 = m2 % 60
                if h2 < 24:
                    intervalos.append(f'{h2:02d}:{m2:02d}')

            elif duration == '1 hora':
                h2 = h + 1
                if h2 < 24:
                    intervalos.append(f'{h2:02d}:00')

            # Actualizar group_data1
            for h_lbl in intervalos:
                if h_lbl not in group_data1:
                    ui.notify(f'Hora {h_lbl} es invalida, solo intervalos de 1h o 30minutos', color='warning')
                    continue
                for d in days_of_week:
                    group_data1[h_lbl][d] = 'Elegida' if d in selected_days else ''

            # ---- ESTA PARTE DEBE IR FUERA DEL BUCLE ----
            # Reconstruir filas de tabla
            new_rows = [
                {'hora': h_lbl, **group_data1[h_lbl]}
                for h_lbl in hours_of_day
                if any(group_data1[h_lbl][d] for d in days_of_week)
            ]

            table4.rows = new_rows
            table4.update()

            ui.notify('Hora agregada', type='positive')
            time_input.value = ''

        add_hour_btn3.on('click', add_hour_action)

                

    

# =========================
# NEW STUDENT
# =========================
@ui.page('/newStudent')
def new_student():
    create_main_screen()

    # Variables globales
    days_of_week = ['Lunes','Martes','Miércoles','Jueves','Viernes','Sábado','Domingo']
    duration_options = ['30 minutos', '1 hora']
    hours_of_day = [f'{h:02d}:{m:02d}' 
                for h in range(24) 
                for m in (0, 30)]
    group_data = {h: {d: '' for d in days_of_week} for h in hours_of_day}

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
                with ui.input('Hora de inicio') as time_input:
                    with ui.menu().props('no-parent-event') as menu:
                        with ui.time().bind_value(time_input):
                            with ui.row().classes('justify-end'):
                                ui.button('Close', on_click=menu.close).props('flat')
                    with time_input.add_slot('append'):
                        ui.icon('access_time').on('click', menu.open).classes('cursor-pointer')
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
            ).classes('w-full').props('dense bordered flat')
            #Limpiar tabla
            ui.button('Limpiar Tabla', on_click=lambda: clear_table(table3, group_data), color='negative').classes('mt-2')
        
        # Botón de guardado
        save_button = ui.button('Guardar Información', on_click=None, color='positive').classes

        # Función para agregar hora
        def add_hour_action():
            selected_days = day_selector.value
            duration = duration_selector.value
            hora_inicio = time_input.value

            if not selected_days:
                ui.notify('Selecciona al menos un día', color='warning')
                return
            if not duration:
                ui.notify('Selecciona duración', color='warning')
                return
            if not hora_inicio:
                ui.notify('Selecciona hora de inicio', color='warning')
                return

            try:
                h, m = map(int, hora_inicio.split(':'))
                hora_label = f'{h:02d}:00'
                if hora_label not in hours_of_day:
                    ui.notify('Hora no válida', color='warning')
                    return
            except:
                ui.notify('Formato incorrecto HH:MM', color='warning')
                return

            # Calcular intervalos según duración
            intervalos = [hora_label]
            if duration == '30 minutos':
               if duration == '30 minutos':
                    m2 = m + 30
                    h2 = h + (m2 // 60)       # suma 1 hora si pasa de 60 min
                    m2 = m2 % 60              # minutos finales corregidos
                    if h2 < 24:
                        intervalos.append(f'{h2:02d}:{m2:02d}')
            elif duration == '1 hora':
                h2 = h + 1
                if h2 < 24:
                    intervalos.append(f'{h2:02d}:00')

            for h_lbl in intervalos:
                if h_lbl not in group_data:
                    ui.notify(f'Hora {h_lbl} es invalida, solo intervalos de 1h o 30minutos', color='warning')
                    continue  # evita el KeyError y pasa al siguiente intervalo
                for d in days_of_week:
                    group_data[h_lbl][d] = 'Elegida' if d in day_selector.value else ''

            # Reconstruir filas de tabla
            new_rows = [{'hora': h_lbl, **group_data[h_lbl]} for h_lbl in hours_of_day if any(group_data[h_lbl][d] for d in days_of_week)]
            table3.rows = new_rows
            table3.update()
            ui.notify('Hora agregada', type='positive')
            time_input.value = ''

        add_hour_btn.on('click', add_hour_action)



@ui.page('/myclasses')
def my_classes():
    create_main_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label('Aquí se muestran tus clases.')


@ui.page('/profile')
def profile():
    create_main_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label('Página de perfil del usuario.')