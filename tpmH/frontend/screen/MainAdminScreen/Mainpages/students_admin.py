from nicegui import ui, app
import pandas as pd
from db.sqlite_db import SQLiteSession
from db.models import User, SchedulePref, AsignedClasses
from components.headerAdmin import create_admin_screen



@ui.page('/Students')
def students():
    create_admin_screen()
    # 1. Verificar autenticación
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    # create_admin_screen() # Descomentar en tu código
    
    # Título y FAB
    with ui.row().classes('w-full items-center justify-between mt-4 relative'):
        ui.label('Tus Estudiantes').classes('text-h4 absolute left-1/2 transform -translate-x-1/2')
        with ui.fab(icon='menu', label='Opciones'):
            ui.fab_action(icon='edit', label='Editar', on_click=lambda: ui.navigate.to('/students_edit'), color='positive')
            
    username = app.storage.user.get("username")
    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative')
        return

    session = SQLiteSession()
    try:
        # Obtenemos lista de estudiantes
        lista_estudiantes = session.query(User).filter(User.role != 'admin').all() # Filtra superuser en vez de admin para ver admins y clientes

        if not lista_estudiantes:
            with ui.column().classes('w-full max-w-5xl mx-auto p-4'):
                ui.label("No se encontraron estudiantes registrados.")
        else:
            with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
                ui.label("Lista de Estudiantes").classes('text-h5 mt-6')

                # 2. Crear DataFrame con TODAS las columnas necesarias
                # Usamos getattr para evitar errores si el campo es None en DB
                df_user = pd.DataFrame([{
                    'Usuario': s.username,  
                    'Name': s.name,
                    'Surname': s.surname,
                    'Email': s.email,
                    'Role': getattr(s, 'role', 'client'),
                    'Package': getattr(s, 'package', 'None'),
                    'Status': getattr(s, 'status', 'Active') # Valor default si no existe en DB
                } for s in lista_estudiantes])

                # 3. Definir columnas explícitamente para mapear los Slots
                # 'name' debe coincidir con la parte final de 'body-cell-NAME'
                cols = [
                    {'name': 'Usuario', 'label': 'Usuario', 'field': 'Usuario', 'align': 'left', 'sortable': True},
                    {'name': 'Name', 'label': 'Nombre', 'field': 'Name', 'align': 'left', 'sortable': True},
                    {'name': 'Surname', 'label': 'Apellido', 'field': 'Surname', 'align': 'left', 'sortable': True},
                    # Columnas Editables:
                    {'name': 'Role', 'label': 'Role', 'field': 'Role', 'align': 'left'},
                    {'name': 'Package', 'label': 'Package', 'field': 'Package', 'align': 'left'},
                    {'name': 'Status', 'label': 'Status', 'field': 'Status', 'align': 'left'},
                ]

                # 4. Renderizar la tabla
                table = ui.table(
                    columns=cols,
                    rows=df_user.to_dict(orient='records'),
                    pagination=10
                ).classes('w-full')

                

    finally:
        session.close()