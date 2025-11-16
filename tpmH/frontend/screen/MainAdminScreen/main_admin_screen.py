from nicegui import ui, app
from components.headerAdmin import create_admin_screen

@ui.page('/admin')
def main_admin_screen():
    create_admin_screen()
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    if app.storage.user.get('role') != "admin":
        ui.notify("Access denied", color="negative")
        ui.navigate.to('/mainscreen')
        return

    with ui.column().classes('items-center p-8'):
        ui.label("Admin Dashboard").classes('text-3xl font-bold')

        ui.label("Bienvenido administrador").classes('text-lg')
        
        # Aquí puedes agregar más herramientas de admin
        ui.button("Ver usuarios", on_click=lambda: ui.notify("Función pendiente"))
