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

    with ui.column().classes('w-full p-4 md:p-8 absolute-center items-center gap-8'):
        ui.label(f'Bienvenido, {app.storage.user.get("name", "Usuario")}!').classes('text-3xl font-bold')

        ui.label("Bienvenido administrador").classes('text-3x1')
        
        with ui.row().classes('gap-6'):
            # Aquí puedes agregar más herramientas de admin
            ui.button("Ver estudiantes", on_click= lambda: ui.navigate.to('/Students'))
            ui.button("Ver Mis Clases", on_click=lambda:ui.navigate.to('/myclassesAdmin'))
            
