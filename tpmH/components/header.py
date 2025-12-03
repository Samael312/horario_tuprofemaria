from nicegui import ui, app

def create_main_screen():
    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    # Header con degradado y sombra suave
    with ui.header().classes('px-6 py-3 items-center justify-between bg-gradient-to-r from-pink-600 to-pink-500 shadow-md'):
        
        # 1. Logo y Título
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/mainscreen')):
            ui.icon('school', size='md', color='white')
            ui.label('TuProfeMaria').classes('text-white text-xl font-bold tracking-wide')

        # 2. Menú de Navegación
        with ui.row().classes('gap-1 items-center'):
            
            # Helper para crear botones de navegación uniformes
            def nav_btn(label, route, icon):
                ui.button(label, icon=icon, on_click=lambda: ui.navigate.to(route)) \
                    .props('flat round color=white') \
                    .classes('text-white font-medium hover:bg-white/20 transition-all duration-300 rounded-lg px-3')

            nav_btn('Inicio', '/mainscreen', 'home')
            nav_btn('Horario', '/ScheduleMaker', 'edit_calendar')
            nav_btn('Mis Clases', '/myclasses', 'school')
            nav_btn('Profesora', '/teacher', 'people')
            
            # Separador vertical pequeño
            ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')

            # Perfil y Logout destacados
            nav_btn('Perfil', '/profile', 'person')
            
            # Botón Logout con diseño diferente (outline)
            ui.button(on_click=logout, icon='logout') \
                .props('outline color=white') \
                .tooltip('Cerrar Sesión') \
                .classes('ml-2 hover:bg-red-500 hover:border-red-500 transition-colors')