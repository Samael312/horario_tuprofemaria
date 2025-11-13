from nicegui import ui, app

@ui.page('/mainscreen')

def create_main_screen():
    """Pantalla principal mostrada tras hacer login."""

    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    with ui.column().classes('absolute-center items-center'):
        ui.label(f'Bienvenido, {app.storage.user["username"]}!').classes('text-2xl mb-4')
        ui.button('Cerrar sesión', on_click=logout, color='negative').props('outline round')
        ui.button('Ir a Subpágina', on_click=lambda: ui.navigate.to('/subpage')).props('flat color=primary')

@ui.page('/subpage')
def sub_page():
    with ui.column().classes('absolute-center items-center'):
        ui.label('Esta es una subpágina protegida.')
        ui.button('Volver', on_click=lambda: ui.navigate.to('/mainscreen'))
