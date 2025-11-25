from nicegui import ui, app
from components.header import create_main_screen
from frontend.screen.MainScreen.Subpages import old_Student, new_Student 

@ui.page('/mainscreen')
def mainscreen():
    # Verificar sesión
    username = app.storage.user.get("username", "Estudiante")
    
    # Header global
    create_main_screen()

    # --- CONTENEDOR PRINCIPAL CON FONDO ---
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] bg-gray-50 items-center justify-center p-4'):
        
        # 1. Sección de Bienvenida
        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(f'¡Hola {username}!').classes('text-4xl md:text-5xl font-black text-gray-800 tracking-tight')
            ui.label('¿Qué te gustaría hacer hoy?').classes('text-lg text-gray-500 mt-2 font-medium')

        # 2. Contenedor de Tarjetas 
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            # ==========================================
            # TARJETA 1: ESTUDIANTE RECURRENTE (Old Student)
            # ==========================================
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-blue-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/oldStudent')):
                
                # Icono
                with ui.element('div').classes('bg-blue-50 p-4 rounded-full mb-4'):
                    ui.icon('history_edu', size='xl', color='blue-600')
                
                # Textos
                ui.label('Ya soy Estudiante').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Gestionar clases asignadas, ver historial o renovar paquetes.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                # Botón Simulado (para UX)
                ui.button('Ver mis Clases', icon='arrow_forward', on_click=lambda: ui.navigate.to('/oldStudent')) \
                    .props('rounded outline color=blue').classes('w-full hover:bg-blue-50')

            # ==========================================
            # TARJETA 2: NUEVO ESTUDIANTE (New Student)
            # ==========================================
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-pink-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/newStudent')):
                
                # Icono
                with ui.element('div').classes('bg-pink-50 p-4 rounded-full mb-4'):
                    ui.icon('school', size='xl', color='pink-600')
                
                # Textos
                ui.label('Nuevo Estudiante').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Configurar mi primer horario, definir preferencias y comenzar.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                # Botón Simulado
                ui.button('Configurar Horario', icon='add', on_click=lambda: ui.navigate.to('/newStudent')) \
                    .props('rounded unelevated color=pink').classes('w-full hover:bg-pink-700')

    # Footer decorativo opcional
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        ui.label('TuProfeMaria App v1.0')