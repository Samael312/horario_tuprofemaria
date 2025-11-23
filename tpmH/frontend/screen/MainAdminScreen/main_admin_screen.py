from nicegui import ui, app
from components.headerAdmin import create_admin_screen

@ui.page('/admin')
def main_admin_screen():
    create_admin_screen()
    username = app.storage.user.get("username", "Admin")
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    if app.storage.user.get('role') != "admin":
        ui.notify("Access denied", color="negative")
        ui.navigate.to('/mainscreen')
        return

     # --- CONTENEDOR PRINCIPAL CON FONDO ---
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):

        # 1. Sección de Bienvenida
        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(f'Bienvenido {username}!').classes('text-4xl md:text-5xl font-black text-gray-800 tracking-tight')
            ui.label('Panel de Administración').classes('text-lg text-gray-500 mt-2 font-medium')
        
       # 2. Contenedor de Tarjetas (Responsive: Columna en móvil, Fila en PC)
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-green-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/Students')):
                
                # Icono
                with ui.element('div').classes('bg-green-50 p-4 rounded-full mb-4'):
                    ui.icon('group', size='xl', color='green-600')
                
                # Textos
                ui.label('Gestión de Estudiantes').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Ver y administrar la lista de estudiantes registrados.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                # Botón Simulado (para UX)
                ui.button('Ver Estudiantes', icon='arrow_forward', on_click=lambda: ui.navigate.to('/Students')) \
                    .props('rounded outline color=green').classes('w-full hover:bg-green-50')

            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-purple-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/myclassesAdmin')):
                
                # Icono
                with ui.element('div').classes('bg-purple-50 p-4 rounded-full mb-4'):
                    ui.icon('class', size='xl', color='purple-600')
                
                # Textos
                ui.label('Mis Clases').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Ver y administrar las clases asignadas a los estudiantes.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                # Botón Simulado (para UX)
                ui.button('Ver Mis Clases', icon='arrow_forward', on_click=lambda: ui.navigate.to('/myclassesAdmin'))\
                    .props('rounded outline color=purple').classes('w-full hover:bg-purple-50')   
                
    # Footer decorativo opcional    
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        ui.label('© 2024 TuProfeMaria - Panel de Administración').classes('text-sm text-gray-500')  
            
