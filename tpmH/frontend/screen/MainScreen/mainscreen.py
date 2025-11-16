from nicegui import ui, app
from components.header import create_main_screen
from frontend.screen.MainScreen.Subpages import old_Student
from frontend.screen.MainScreen.Subpages import new_Student    

@ui.page('/mainscreen')
def mainscreen():
    create_main_screen()
    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label(f'Bienvenido, {app.storage.user.get("username", "Usuario")}!').classes('text-2xl')
        with ui.row().classes('gap-2'):
            ui.button('Old Student', on_click=lambda: ui.navigate.to('/oldStudent'))
            ui.button('New Student', on_click=lambda: ui.navigate.to('/newStudent'))

