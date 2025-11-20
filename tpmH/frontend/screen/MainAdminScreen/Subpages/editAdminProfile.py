from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from db.sqlite_db import SQLiteSession
from db.models import User, ScheduleProf
from auth.sync_edit import sync_sqlite_to_postgres_edit
from zoneinfo import available_timezones
from components.h_selection import make_selection_handler
from components.clear_table import clear_table
from components.delete_rows import delete_selected_rows_v2
from components.botones.button_avai_dur import  make_add_hour_avai_button
from components.share_data import *
from collections import Counter

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/profileA_edit')
def profileA_edit():
    user = app.storage.user.get("username", "Usuario")
    create_admin_screen()
    with ui.column().classes('w-full h-full p-4 md:p-8 gap-6 flex items-center justify-center'):
        ui.label('Editar Perfil').classes('text-h4 mt-4 text-center')

        username = app.storage.user.get("username")

    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    session = SQLiteSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label("Usuario no encontrado en DB").classes('text-negative mt-4')
            return

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):

            # -----------------------------------
            # Campos personales
            # -----------------------------------
            personal_inputs = {}
            for field, value in [
                ('name', user_obj.name),
                ('surname', user_obj.surname),
                ('time_zone', getattr(user_obj, 'time_zone', '')),
                ('email', getattr(user_obj, 'email', ''))
            ]:
                with ui.row().classes('w-full gap-2'):
                    ui.label(f"{field.capitalize()}:").classes('w-1/4')
                    if field == 'time_zone':
                        personal_inputs[field] = ui.select(
                            options=sorted(available_timezones()),
                            value=value
                        ).classes('w-3/4')
                    else:
                        personal_inputs[field] = ui.input(value=value).classes('w-3/4')

        rgh_obj = session.query(ScheduleProf).filter(ScheduleProf.username == username).first()
        if not rgh_obj:
            ui.label("No se encontraron datos de rango de horarios").classes('text-negative mt-4')
            return

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):


            # 2. Selector de días
            with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4 mx-auto'):
                ui.label('Selecciona los días').classes('text-lg font-bold')
                ui.separator()
                day_selector = ui.select(days_of_week, label='Días', multiple=True, value=[]).classes('w-auto min-w-[150px]')

            # Selector de disponibilidad y horas
            with ui.card().classes('w-full p-4'):
                ui.label('Disponibilidad y horas').classes('text-lg font-bold')
                ui.separator()

                with ui.row().classes('gap-4 mt-2'):

                    avai_selector = ui.select(
                        availability_options,
                        label='Disponibilidad'
                    ).classes('w-48')

            # 4. Selector de hora
            with ui.card().classes('w-full max-w-6xl flex-1 overflow-auto p-4 mx-auto'):
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
                # -----------------------
                # Tabla de horarios
                # -----------------------
                schedule_data = session.query(ScheduleProf).filter(ScheduleProf.username == username).all()

                if schedule_data:
                    ui.label("Rangos horarios:").classes('text-h5 mt-6')

                    # === 2. Insertar datos desde DB en el group_data4 ===
                    for s in schedule_data:
                        h_ini = f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}"
                        h_fin = f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                        
                        texto_intervalo = f"{h_ini}-{h_fin}"

                        # Asignar a la hora de INICIO
                        if h_ini in group_data4:
                            group_data4[h_ini][s.days] = texto_intervalo
                        
                        # <--- MODIFICACIÓN AQUÍ: Asignar TAMBIÉN a la hora de FIN
                        if h_fin in group_data4:
                             group_data4[h_fin][s.days] = texto_intervalo


                    # Filtrar solo las horas que tienen algún dato en los días
                    filtered_rows = []
                    for hora, vals in group_data4.items():
                        # ¿Al menos un día tiene un valor distinto de ""?
                        if any(v != "" for v in vals.values()):
                            filtered_rows.append({'hora': hora, **vals})

                    # === 3. Crear tabla IGUAL que en /newStudent ===
                    table = ui.table(
                        columns=[{'name': 'hora', 'label': 'Hora', 'field': 'hora'}] +
                                [{'name': d, 'label': d, 'field': d} for d in days_of_week],
                        rows=filtered_rows,
                        row_key='hora',
                        selection='multiple'
                    ).classes('w-full').props('dense bordered flat')

                    # === 4. Manejo de selección igual que /newStudent ===
                    selection_handler, selection_state = make_selection_handler(table, logger=logger)
                    table.on('selection', selection_handler)

                    # === 5. Botones ===
                    with ui.row().classes('gap-4 mt-2'):
                        ui.button('Limpiar Tabla', 
                                on_click=lambda: clear_table(table, group_data4),
                                color='yellow').classes('mt-2')

                        ui.button('Eliminar filas seleccionadas',
                                color='negative',
                                on_click=lambda: delete_selected_rows_v2(table, selection_state, id_column="hora")
                                ).classes('mt-2')
                
                # -----------------------------------
                # Guardar cambios
                # -----------------------------------
                def save_changes():
                    session2 = SQLiteSession()
                    try:
                        # Guardar datos personales
                        user_obj2 = session2.query(User).filter(User.username == username).first()
                        if user_obj2:
                            user_obj2.name = personal_inputs['name'].value
                            user_obj2.surname = personal_inputs['surname'].value
                            user_obj2.time_zone = personal_inputs['time_zone'].value
                            user_obj2.email = personal_inputs['email'].value
                        
                        # --- LÓGICA DE HORARIOS ---
                        
                        # 1. Borrar horarios anteriores para este usuario
                        # Esta estrategia evita conflictos de IDs y maneja limpiamente las eliminaciones hechas en la UI
                        session2.query(ScheduleProf).filter(ScheduleProf.username == username).delete()
                        
                        
                        name_val = user_obj.name if user_obj else user
                        surname_val = user_obj.surname if user_obj else ""
                       
                        # 2. Set para evitar duplicados 
                        # (Como mostramos el intervalo en Inicio Y Fin en la tabla, aparecerá dos veces al iterar rows)
                        seen_intervals = set()

                        # 3. Recrear horarios desde la tabla visual
                        for row in table.rows:
                            for day in days_of_week:
                                # El valor de la celda es algo como "09:00-10:00" o vacío
                                cell_value = row.get(day)
                                
                                if cell_value and "-" in str(cell_value):
                                    parts = cell_value.split('-')
                                    if len(parts) == 2:
                                        s_str, e_str = parts[0].strip(), parts[1].strip()
                                        
                                        # Convertir a entero HHMM (formato de DB)
                                        try:
                                            s_int = int(s_str.replace(':', ''))
                                            e_int = int(e_str.replace(':', ''))
                                            
                                            # Clave única para detectar duplicados visuales: (dia, inicio, fin)
                                            unique_key = (day, s_int, e_int)
                                            
                                            if unique_key not in seen_intervals:
                                                new_pref = ScheduleProf(
                                                    username=username,
                                                    name= name_val,
                                                    surname= surname_val,
                                                    days=day,
                                                    start_time=s_int,
                                                    end_time=e_int
                                                )
                                                session2.add(new_pref)
                                                seen_intervals.add(unique_key)
                                        except ValueError:
                                            pass # Ignorar celdas con formato invalido

                        session2.commit()
                        sync_sqlite_to_postgres_edit()
                        ui.notify("Datos actualizados correctamente", color='positive')
                        ui.timer(1.0, lambda: ui.navigate.to(('/profile')))
                    except Exception as e:
                        session2.rollback()
                        logger.error(f"Error al guardar cambios: {e}")
                        ui.notify(f"Error al guardar: {str(e)}", color='negative')
                    finally:
                        session2.close()

        with ui.column().classes('w-full h-full p-4 md:p-8 items-center gap-6'):
            ui.button("Guardar Cambios", on_click=save_changes, color='positive')

    finally:
            session.close()
            

    make_add_hour_avai_button(
                    add_hour_btn,
                    day_selector=day_selector,
                    availability=avai_selector,
                    button_id=f"rango_horario_de_{user}",
                    time_input=start_time,
                    end_time_input=end_time,
                    valid_hours=hours_of_day,
                    group_data=group_data4,
                    days_of_week=days_of_week,
                    table=table,
                    notify_success="Hora agregada",
                    
                    
                    notify_missing_time="Selecciona hora de inicio",
                    notify_missing_end_time="Selecciona hora de fin",
                    notify_invalid_hour="Hora no válida",
                    notify_bad_format="Formato incorrecto HH:MM",
                    notify_interval_invalid="Hora {h_lbl} es invalida, solo intervalos válidos"
                )