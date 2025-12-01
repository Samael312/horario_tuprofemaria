import pandas as pd
from nicegui import ui, app
from components.header import create_main_screen
from db.postgres_db import PostgresSession 
# --------------------------------------------------
from db.models import User, SchedulePref, AsignedClasses
from components.delete_all import confirm_delete

@ui.page('/profile')
def profile():
    create_main_screen()

    # --- Header y Título ---
    with ui.row().classes('w-full items-center justify-between mt-4 relative'):
        ui.label('PERFIL').classes('text-h4 absolute left-1/2 transform -translate-x-1/2 font-bold text-gray-800')
        with ui.fab(icon='menu', label='Opciones', color='pink'):
            ui.fab_action(icon='edit', label='Editar', on_click=lambda: ui.navigate.to('/profile_edit'), color='positive')
            # OJO: Asegúrate de actualizar también 'confirm_delete' para que borre de Neon
            ui.fab_action(icon='delete', label='Eliminar cuenta', on_click=confirm_delete, color='negative')

    # --- Verificación de Sesión ---
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # --- CAMBIO: USAR SESIÓN DE POSTGRES PARA LEER DATOS REALES ---
    session = PostgresSession()
    # -------------------------------------------------------------
    
    try:
        # Ahora esta consulta busca en la Nube (Neon)
        user_obj = session.query(User).filter(User.username == username).first()
        
        if not user_obj:
            ui.notify("Usuario no encontrado en la Base de Datos", type='negative')
            return

        # --- Contenedor Principal ---
        with ui.column().classes('w-full max-w-3xl mx-auto p-4 gap-6'):
            
            # 1. Tarjeta de Datos Personales
            with ui.card().classes('w-full p-0 shadow-lg rounded-xl overflow-hidden'):
                with ui.row().classes('w-full bg-gray-100 p-4 items-center gap-3 border-b border-gray-200'):
                    ui.icon('person', size='md', color='gray-700')
                    ui.label("Datos Personales").classes('text-xl font-bold text-gray-800')

                with ui.grid(columns=2).classes('w-full p-6 gap-y-4 items-center'):
                    datos_personales = [
                        ('Nombre', user_obj.name, 'badge'),
                        ('Apellido', user_obj.surname, 'badge'),
                        ('Usuario', user_obj.username, 'account_circle'),
                        ('Zona Horaria', getattr(user_obj, 'time_zone', 'N/A'), 'schedule'),
                        ('Correo', getattr(user_obj, 'email', 'N/A'), 'email')
                    ]
                    for label, value, icon_name in datos_personales:
                        with ui.row().classes('items-center gap-2 text-gray-500'):
                            ui.icon(icon_name, size='xs')
                            ui.label(label).classes('font-semibold text-sm uppercase tracking-wide')
                        ui.label(str(value)).classes('text-lg text-gray-800 font-medium')

            # 2. Tarjeta de Paquete
            rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
            if not rgh_obj:
                ui.label("⚠ No se encontraron datos de rango de horarios").classes('text-red-500 font-bold bg-red-50 p-4 rounded-lg w-full text-center')
            else:
                with ui.card().classes('w-full p-0 shadow-lg rounded-xl overflow-hidden border-t-4 border-pink-500'):
                    with ui.row().classes('w-full p-4 items-center justify-between'):
                        with ui.row().classes('items-center gap-3'):
                            ui.icon('inventory_2', size='md', color='pink-500')
                            ui.label("Paquete Activo").classes('text-xl font-bold text-gray-800')
                        ui.chip('ACTIVO', color='green').props('dense square icon=check')
                    ui.separator()
                    with ui.row().classes('w-full p-6 bg-pink-50'):
                        with ui.column():
                            ui.label('Plan Seleccionado').classes('text-sm text-pink-600 font-bold uppercase')
                            ui.label(rgh_obj.package).classes('text-3xl font-black text-gray-800')

            # 3. Tabs: Horarios y Clases
            with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
                
                # Definición de pestañas
                with ui.tabs().classes('w-full text-gray-600 bg-gray-50 border-b border-gray-200') \
                    .props('active-color="pink-600" indicator-color="pink-600" align="justify" narrow-indicator') as tabs:
                    t_schedule = ui.tab('Horario Disponibilidad', icon='calendar_month')
                    t_assigned = ui.tab('Tus Clases', icon='school')

                # Contenido de pestañas
                with ui.tab_panels(tabs, value=t_schedule).classes('w-full p-6'):
                    
                    # --- TAB 1: HORARIO DE DISPONIBILIDAD ---
                    with ui.tab_panel(t_schedule):
                        schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
                        
                        if not schedule_data:
                            with ui.column().classes('w-full items-center justify-center py-8 text-gray-400'):
                                ui.icon('event_busy', size='xl')
                                ui.label("No has configurado disponibilidad.").classes('text-sm italic')
                        else:
                            df_schedule = pd.DataFrame([{
                                'DÍA': s.days,
                                'HORA INICIO': f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}",
                                'HORA FIN': f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                            } for s in schedule_data])

                            cols_sched = [
                                {'name': 'dia', 'label': 'DÍA', 'field': 'DÍA', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-pink-200 text-pink-900 font-bold uppercase text-sm'},
                                {'name': 'inicio', 'label': 'HORA INICIO', 'field': 'HORA INICIO', 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold text-sm'},
                                {'name': 'fin', 'label': 'HORA FIN', 'field': 'HORA FIN', 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold text-sm'}
                            ]
                            
                            ui.table(columns=cols_sched, rows=df_schedule.to_dict(orient='records'), pagination={'rowsPerPage': 7})\
                                .classes('w-full bg-white rounded-xl shadow-sm overflow-hidden border border-pink-200')\
                                .props('flat bordered separator=cell')

                    # --- TAB 2: CLASES ASIGNADAS ---
                    with ui.tab_panel(t_assigned):
                        assigned_data = session.query(AsignedClasses).filter(AsignedClasses.username == username).all()
                        
                        if not assigned_data:
                            with ui.column().classes('w-full items-center justify-center py-8 text-gray-400'):
                                ui.icon('class', size='xl')
                                ui.label("No tienes clases asignadas aún.").classes('text-sm italic')
                        else:
                            df_assigned = pd.DataFrame([{
                                'Fecha': a.date,
                                'Día': a.days,
                                'Hora Inicio': f"{str(a.start_time).zfill(4)[:2]}:{str(a.start_time).zfill(4)[2:]}",
                                'Hora Fin': f"{str(a.end_time).zfill(4)[:2]}:{str(a.end_time).zfill(4)[2:]}"
                            } for a in assigned_data])

                            cols_assigned = [
                                {'name': 'fecha', 'label': 'FECHA', 'field': 'Fecha', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-pink-200 text-pink-900 font-bold'},
                                {'name': 'dia', 'label': 'DÍA', 'field': 'Día', 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold text-sm'},
                                {'name': 'inicio', 'label': 'INICIO', 'field': 'Hora Inicio', 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold text-sm'},
                                {'name': 'fin', 'label': 'FIN', 'field': 'Hora Fin', 'align': 'center', 'headerClasses': 'bg-pink-100 text-pink-800 font-bold text-sm'},
                            ]

                            ui.table(columns=cols_assigned, rows=df_assigned.to_dict(orient='records'), pagination={'rowsPerPage': 5})\
                                .classes('w-full bg-white rounded-xl shadow-sm overflow-hidden border border-pink-200')\
                                .props('flat bordered separator=cell')

    finally:
        session.close()