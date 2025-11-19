from nicegui import ui, app


def create_admin_screen():
    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    with ui.header().classes('p-2 items-center justify-between'):
        ui.label('Tuprofemaria').classes('text-white text-xl font-bold')

        with ui.row().classes('gap-4'):
            ui.button('Primera In', on_click=lambda: ui.navigate.to('/admin')).props('flat color=white')
            ui.button('Tu Horario', on_click=lambda: ui.navigate.to('/Admhorario')).props('flat color=white')
            ui.button('Mis Clases', on_click=lambda: ui.navigate.to('/myclassesAdmin')).props('flat color=white')
            ui.button('Estudiantes', on_click=lambda: ui.navigate.to('/Students')).props('flat color=white')
            ui.button('Perfil', on_click=lambda: ui.navigate.to('/adminProfile')).props('flat color=white')
            ui.button('Log out', on_click=logout).props('flat color=black')
