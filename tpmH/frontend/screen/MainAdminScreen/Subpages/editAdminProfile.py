from nicegui import ui, app
import logging
from components.headerAdmin import create_admin_screen
from db.sqlite_db import SQLiteSession
from db.models import User, ScheduleProf, ScheduleProfEsp
from auth.sync_edit import sync_sqlite_to_postgres_edit
from zoneinfo import available_timezones
from components.h_selection import make_selection_handler
from components.clear_table import clear_table
from components.delete_rows import delete_selected_rows_v2
from components.botones.button_avai_dur_edit import make_add_hour_avai_button
from components.botones.button_avai_esp_dur_edit import make_add_hours_by_date_button
from components.share_data import *

logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

@ui.page('/profileA_edit')
def profileA_edit():
    create_admin_screen()
    
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    session = SQLiteSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label("Usuario no encontrado").classes('text-negative p-4')
            return

        # --- INICIALIZACIÓN DE DATOS ---
        
        # 1. Horario General
        # Estructura visual: "08:00-09:00 (Virtual)"
        local_group_general = {h: {d: "" for d in days_of_week} for h in hours_of_day}
        
        sched_db = session.query(ScheduleProf).filter(ScheduleProf.username == username).all()
        for s in sched_db:
            h_ini = f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}"
            h_fin = f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
            # Cargamos con el formato (Disponibilidad) para que sea consistente al editar
            val = f"{h_ini}-{h_fin} ({s.availability})"
            
            if h_ini in local_group_general: local_group_general[h_ini][s.days] = val
            if h_fin in local_group_general: local_group_general[h_fin][s.days] = val

        # 2. Fechas Específicas
        rows_specific = []
        sched_esp_db = session.query(ScheduleProfEsp).filter(ScheduleProfEsp.username == username).all()
        for e in sched_esp_db:
            h_ini = f"{str(e.start_time).zfill(4)[:2]}:{str(e.start_time).zfill(4)[2:]}"
            h_fin = f"{str(e.end_time).zfill(4)[:2]}:{str(e.end_time).zfill(4)[2:]}"
            rows_specific.append({
                'id': e.id,
                'fecha': e.date,
                'dia': e.days,
                'hora': f"{h_ini}-{h_fin}",
                'disponibilidad': e.avai 
            })

        # --- UI LAYOUT ---
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
            
            # Encabezado
            with ui.row().classes('w-full items-center gap-4 mb-2'):
                ui.icon('manage_accounts', size='lg', color='pink-600')
                with ui.column().classes('gap-0'):
                    ui.label('Editar Perfil Admin').classes('text-3xl font-bold text-gray-800')
                    ui.label('Actualiza tu información y disponibilidad').classes('text-sm text-gray-500')

            # --- PESTAÑAS (TABS) ---
            with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
                
                with ui.tabs().classes('w-full text-gray-600 bg-gray-50 border-b border-gray-200') \
                    .props('active-color="pink-600" indicator-color="pink-600" align="justify" narrow-indicator') as tabs:
                    t_info = ui.tab('Datos Personales', icon='person')
                    t_general = ui.tab('Horario General', icon='update')
                    t_specific = ui.tab('Fechas Específicas', icon='event')

                with ui.tab_panels(tabs, value=t_info).classes('w-full p-6'):

                    # ==========================
                    # TAB 1: DATOS PERSONALES
                    # ==========================
                    with ui.tab_panel(t_info):
                        with ui.grid(columns=2).classes('w-full gap-6'):
                            personal_inputs = {}
                            def make_input(key, label, val, icon):
                                inp = ui.input(label, value=val).props('outlined dense').classes('w-full')
                                inp.add_slot('prepend', f'<q-icon name="{icon}" />')
                                personal_inputs[key] = inp
                            
                            make_input('name', 'Nombre', user_obj.name, 'badge')
                            make_input('surname', 'Apellido', user_obj.surname, 'badge')
                            make_input('email', 'Correo', getattr(user_obj, 'email', ''), 'email')
                            personal_inputs['time_zone'] = ui.select(sorted(available_timezones()), value=getattr(user_obj, 'time_zone', ''), label='Zona Horaria').props('outlined dense behavior="menu"').classes('w-full')

                    # ==========================
                    # TAB 2: HORARIO GENERAL
                    # ==========================
                    with ui.tab_panel(t_general):
                        with ui.column().classes('w-full gap-4'):
                            
                            # Toolbar General
                            with ui.row().classes('w-full bg-pink-50 p-4 rounded-lg border border-pink-100 items-center justify-between wrap gap-4'):
                                day_selector = ui.select(days_of_week, label='Días', multiple=True, value=[])\
                                    .props('outlined dense bg-white use-chips multiple').classes('w-full md:w-64')
                                
                                avai_selector = ui.select(availability_options, label='Disponibilidad')\
                                    .props('outlined dense bg-white').classes('w-40')

                                with ui.row().classes('items-center gap-2'):
                                    start_time = ui.input('Inicio').props('outlined dense bg-white mask="time"').classes('w-28')
                                    with start_time.add_slot('append'):
                                        ui.icon('access_time').classes('cursor-pointer').on('click', lambda: start_time_menu.open())
                                    start_time_menu = ui.menu().props('no-parent-event')
                                    with start_time_menu: ui.time().bind_value(start_time)

                                    ui.label('-')

                                    end_time = ui.input('Fin').props('outlined dense bg-white mask="time"').classes('w-28')
                                    with end_time.add_slot('append'):
                                        ui.icon('access_time').classes('cursor-pointer').on('click', lambda: end_time_menu.open())
                                    end_time_menu = ui.menu().props('no-parent-event')
                                    with end_time_menu: ui.time().bind_value(end_time)

                                add_btn_gen = ui.button('Añadir', icon='add', color='pink-600').props('push')

                            # Tabla General
                            filtered_rows_gen = [{'hora': h, **vals} for h, vals in local_group_general.items() if any(vals.values())]
                            cols_gen = [{'name': 'hora', 'label': 'HORA', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'}] + \
                                       [{'name': d, 'label': d[:3].upper(), 'field': d, 'align': 'center', 'headerClasses': 'bg-pink-50 text-pink-900 font-bold'} for d in days_of_week]
                            table_gen = ui.table(columns=cols_gen, rows=filtered_rows_gen, row_key='hora', selection='multiple')\
                                .classes('w-full border border-gray-200 rounded-lg').props('flat bordered separator=cell density=compact')
                            
                            with ui.row().classes('gap-2'):
                                ui.button('Limpiar', on_click=lambda: clear_table(table_gen, local_group_general), color='warning', icon='cleaning_services').props('flat dense')
                                ui.button('Borrar Selección', color='negative', icon='delete', on_click=lambda: delete_selected_rows_v2(table_gen, selection_state_gen, id_column="hora")).props('flat dense')
                            sel_hand_gen, selection_state_gen = make_selection_handler(table_gen, logger=logger)
                            table_gen.on('selection', sel_hand_gen)

                    # ==========================
                    # TAB 3: FECHAS ESPECÍFICAS
                    # ==========================
                    with ui.tab_panel(t_specific):
                        with ui.column().classes('w-full gap-4'):
                            
                            # Toolbar Specific (Inputs de hora corregidos con ui.time)
                            with ui.row().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-100 items-center justify-between wrap gap-4'):
                                avai_selector_e = ui.select(availability_options, label='Disponibilidad')\
                                    .props('outlined dense bg-white').classes('w-40')
                                
                                date_input_e = ui.input('Fecha').props('outlined dense bg-white').classes('w-40')
                                with date_input_e.add_slot('append'):
                                    ui.icon('event').classes('cursor-pointer').on('click', lambda: date_menu.open())
                                date_menu = ui.menu().props('no-parent-event')
                                with date_menu: ui.date().bind_value(date_input_e)

                                with ui.row().classes('items-center gap-2'):
                                    # HORA INICIO CON SLOT DE RELOJ
                                    start_time_e = ui.input('Inicio').props('outlined dense bg-white mask="time"').classes('w-28')
                                    with start_time_e.add_slot('append'):
                                        ui.icon('access_time').classes('cursor-pointer').on('click', lambda: st_menu_e.open())
                                    st_menu_e = ui.menu().props('no-parent-event')
                                    with st_menu_e: ui.time().bind_value(start_time_e)

                                    ui.label('-')

                                    # HORA FIN CON SLOT DE RELOJ
                                    end_time_e = ui.input('Fin').props('outlined dense bg-white mask="time"').classes('w-28')
                                    with end_time_e.add_slot('append'):
                                        ui.icon('access_time').classes('cursor-pointer').on('click', lambda: et_menu_e.open())
                                    et_menu_e = ui.menu().props('no-parent-event')
                                    with et_menu_e: ui.time().bind_value(end_time_e)

                                add_btn_esp = ui.button('Añadir', icon='add', color='blue-600').props('push')

                            cols_esp = [
                                {'name': 'fecha', 'label': 'FECHA', 'field': 'fecha', 'align': 'left', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'dia', 'label': 'DÍA', 'field': 'dia', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'hora', 'label': 'HORARIO', 'field': 'hora', 'align': 'center', 'headerClasses': 'bg-blue-50 text-blue-900 font-bold'},
                                {'name': 'disponibilidad', 'label': 'TIPO', 'field': 'disponibilidad', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                            ]
                            table_esp = ui.table(columns=cols_esp, rows=rows_specific, row_key='hora', selection='multiple')\
                                .classes('w-full border border-gray-200 rounded-lg').props('flat bordered separator=cell density=compact')
                            
                            def clear_esp():
                                table_esp.rows = []
                                table_esp.update()
                            with ui.row().classes('gap-2'):
                                ui.button('Limpiar', on_click=clear_esp, color='warning', icon='cleaning_services').props('flat dense')
                                ui.button('Borrar Selección', color='negative', icon='delete', on_click=lambda: delete_selected_rows_v2(table_esp, selection_state_esp, id_column="hora")).props('flat dense')
                            sel_hand_esp, selection_state_esp = make_selection_handler(table_esp, logger=logger)
                            table_esp.on('selection', sel_hand_esp)

            # ==========================
            # LÓGICA DE GUARDADO
            # ==========================
            def save_all_changes():
                session2 = SQLiteSession()
                try:
                    ui.notify("Guardando...", type='ongoing', timeout=1000)
                    u = session2.query(User).filter(User.username == username).first()
                    if u:
                        u.name = personal_inputs['name'].value
                        u.surname = personal_inputs['surname'].value
                        u.time_zone = personal_inputs['time_zone'].value
                        u.email = personal_inputs['email'].value
                    
                    # 1. Guardar General
                    session2.query(ScheduleProf).filter(ScheduleProf.username == username).delete()
                    seen_gen = set()
                    for row in table_gen.rows:
                        for d in days_of_week:
                            cell = row.get(d)
                            # Se espera formato: "08:00-09:00 (Virtual)"
                            if cell and "-" in str(cell):
                                try:
                                    # Parser robusto
                                    parts = cell.split('(')
                                    time_part = parts[0].strip()
                                    # Extraer disponibilidad
                                    avai_part = parts[1].replace(')', '').strip() if len(parts) > 1 else "General"
                                    
                                    s_str, e_str = time_part.split('-')
                                    s_int = int(s_str.replace(':', ''))
                                    e_int = int(e_str.replace(':', ''))
                                    
                                    key = (d, s_int, e_int)
                                    if key not in seen_gen:
                                        session2.add(ScheduleProf(
                                            username=username, name=u.name, surname=u.surname, 
                                            days=d, start_time=s_int, end_time=e_int, availability=avai_part
                                        ))
                                        seen_gen.add(key)
                                except: pass

                    # 2. Guardar Específico
                    session2.query(ScheduleProfEsp).filter(ScheduleProfEsp.username == username).delete()
                    for row in table_esp.rows:
                        if "-" in row['hora']:
                            try:
                                s_str, e_str = row['hora'].split('-')
                                # Buscamos la clave 'disponibilidad' (que viene del botón corregido)
                                avai_val = row.get('disponibilidad') or row.get('availability') or "General"
                                
                                session2.add(ScheduleProfEsp(
                                    username=username, date=row['fecha'], days=row['dia'],
                                    start_time=int(s_str.replace(':', '')), end_time=int(e_str.replace(':', '')),
                                    avai=avai_val 
                                ))
                            except: pass

                    session2.commit()
                    sync_sqlite_to_postgres_edit()
                    ui.notify("Perfil actualizado exitosamente", type='positive', icon='check_circle')
                    ui.timer(1.0, lambda: ui.navigate.to('/adminProfile'))
                except Exception as e:
                    session2.rollback()
                    ui.notify(f"Error: {e}", type='negative')
                finally:
                    session2.close()

            with ui.row().classes('w-full justify-center pt-4 pb-8'):
                ui.button("Guardar Todos los Cambios", on_click=save_all_changes, icon='save').props('push color=positive size=lg').classes('px-8')

    finally:
        session.close()

    # Conexión de Botones Lógicos
    make_add_hour_avai_button(
        add_btn_gen, day_selector, avai_selector, f"btn_gen_{username}",
        start_time, end_time, hours_of_day, local_group_general, days_of_week, table_gen,
        notify_success="Bloque añadido"
    )
    
    # Dummy dict necesario por la firma de la función, aunque no se use para grid
    local_dummy = {}
    make_add_hours_by_date_button(
        add_btn_esp, start_time_e, end_time_e, avai_selector_e, date_input_e,
        local_dummy, table_esp, None, notify_success="Fecha añadida"
    )