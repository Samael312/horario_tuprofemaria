from nicegui import ui, app
import pandas as pd
from db.sqlite_db import SQLiteSession
from db.models import User
from components.headerAdmin import create_admin_screen

@ui.page('/Students')
def students():
    # 1. Header y Autenticación
    create_admin_screen()
    
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    username = app.storage.user.get("username")
    if not username:
        ui.label("Sesión inválida").classes('text-negative p-4')
        return

    session = SQLiteSession()
    try:
        # Obtenemos lista de usuarios 
        # Traemos todos para poder mostrar métricas
        all_users = session.query(User).all()
        
        # Filtramos la lista principal para la tabla 
        # O mostramos todos. En este caso mostramos todos menos el admin actual para evitar auto-edición
        lista_estudiantes = [u for u in all_users if u.username != username] 

        # --- CONTENEDOR PRINCIPAL ---
        with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
            
            # 2. Título y Métricas (Dashboard)
            with ui.row().classes('w-full items-center justify-between mb-2'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('group', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Gestión de Usuarios').classes('text-3xl font-bold text-gray-800')
                        ui.label('Administra estudiantes y permisos').classes('text-sm text-gray-500')

            # Tarjetas de Resumen (Métricas)
            with ui.grid(columns=3).classes('w-full gap-4 mb-4'):
                def stat_card(label, value, icon, color):
                    with ui.card().classes(f'border-l-4 border-{color}-500 items-center p-4 shadow-sm'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('gap-0'):
                                ui.label(label).classes('text-gray-500 text-xs font-bold uppercase')
                                ui.label(str(value)).classes('text-2xl font-black text-gray-800')
                            ui.icon(icon, size='md', color=f'{color}-500').classes('opacity-50')

                total_users = len(all_users)
                total_admins = sum(1 for u in all_users if u.role == 'admin')
                total_clients = sum(1 for u in all_users if u.role == 'client')

                stat_card('Total Usuarios', total_users, 'people', 'blue')
                stat_card('Estudiantes', total_clients, 'school', 'pink')
                stat_card('Administradores', total_admins, 'security', 'gray')

            # 3. Tarjeta de Tabla con Buscador
            with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
                
                # Barra de herramientas de la tabla
                with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center justify-between wrap gap-4'):
                    ui.label('Directorio').classes('text-lg font-bold text-gray-700')
                    
                    # Buscador
                    search = ui.input(placeholder='Buscar por nombre o usuario...') \
                        .props('outlined dense rounded debounce="300"') \
                        .classes('w-full md:w-64 bg-white')
                    search.add_slot('prepend', '<q-icon name="search" />')
                    search.add_slot('append', '<q-icon name="close" @click="text = \'\'" class="cursor-pointer" />')

                # Preparar Datos
                if not lista_estudiantes:
                    with ui.column().classes('w-full p-8 items-center justify-center'):
                        ui.icon('person_off', size='xl', color='gray-400')
                        ui.label("No se encontraron estudiantes registrados.").classes('text-gray-500 mt-2')
                else:
                    rows_data = [{
                        'Usuario': s.username,  
                        'Nombre': f"{s.name} {s.surname}", # Combinamos nombre y apellido
                        'Email': getattr(s, 'email', 'N/A') or 'N/A', # Manejo seguro de None
                        'Role': s.role.upper() if s.role else 'CLIENT',
                        'Zona': getattr(s, 'time_zone', '-') or '-',
                        'Package': getattr(s, 'package', 'Standard'), 
                        'Status': 'ACTIVO' 
                    } for s in lista_estudiantes]

                    # Definir Columnas Estilizadas
                    cols = [
                        {'name': 'Usuario', 'label': 'USUARIO', 'field': 'Usuario', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-pink-50 text-pink-900 font-bold'},
                        {'name': 'Nombre', 'label': 'NOMBRE COMPLETO', 'field': 'Nombre', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                        {'name': 'Email', 'label': 'CORREO', 'field': 'Email', 'align': 'left', 'headerClasses': 'bg-gray-100 font-bold'},
                        {'name': 'Zona', 'label': 'ZONA H.', 'field': 'Zona', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                        {'name': 'Role', 'label': 'ROL', 'field': 'Role', 'align': 'center', 'sortable': True, 'headerClasses': 'bg-gray-100 font-bold'},
                    ]

                    # Renderizar Tabla
                    table = ui.table(
                        columns=cols,
                        rows=rows_data,
                        pagination={'rowsPerPage': 10},
                        selection='none'
                    ).classes('w-full').props('flat bordered separator=cell')

                    # Lógica de búsqueda
                    def filter_table(e):
                        val = e.value.lower()
                        if not val:
                            table.rows = rows_data
                        else:
                            table.rows = [
                                row for row in rows_data 
                                if val in str(row.values()).lower()
                            ]
                    
                    search.on('update:modelValue', filter_table)

    finally:
        session.close()

    # 4. Botón Flotante (FAB) Estilizado
    # Usamos position fixed para asegurarnos que flote sobre todo
    with ui.page_sticky(position='bottom-left', x_offset=20, y_offset=20):
        with ui.fab(icon='settings', color='pink-600').props('glossy'):
            ui.fab_action(
                icon='edit', 
                label='Editar Masivo', 
                color='pink-200',
                on_click=lambda: ui.navigate.to('/students_edit')
            )