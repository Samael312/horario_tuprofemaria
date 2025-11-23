from nicegui import ui, app


def create_admin_screen():
    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

     # Header con degradado y sombra suave
    with ui.header().classes('px-6 py-3 items-center justify-between bg-gradient-to-r from-pink-600 to-pink-500 shadow-md'):
        
        # 1. Logo y Título
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/admin')):
            ui.icon('school', size='md', color='white')
            ui.label('TuProfeMaria').classes('text-white text-xl font-bold tracking-wide')

        with ui.row().classes('gap-1 items-center'):

            def nav_btn(label, route):
                ui.button(label, on_click=lambda: ui.navigate.to(route))\
                    .props('flat color=white')\
                    .classes('text-white font-medium hover:bg-white/20 transition-all duration-300 rounded-lg px-3')

            nav_btn('Inicio', '/admin')
            nav_btn('Horario', '/Admhorario')
            nav_btn('Mis Clases', '/myclassesAdmin')
            nav_btn('Estudiantes', '/Students')
            

            ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')

            #perfil y Logout destacados
            nav_btn('Perfil', '/adminProfile')

            # Botón Logout con diseño diferente (outline)
            ui.button(on_click=logout, icon='logout')\
                            .props('outline color=white')\
                            .tooltip('Cerrar Sesión')\
                            .classes('ml-2 hover:bg-red-500 hover:border-red-500 transition-colors')

           