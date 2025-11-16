# ui/ui.py
from nicegui import ui, app
from frontend.screen.login_screen import setup_auth_system
from frontend.screen.MainScreen.mainscreen import create_main_screen
from frontend.screen.signup_screen import create_signup_screen
from frontend.screen.reset_screen import reset_password_screen



def init_ui():
    """Puente entre las pantallas de la app."""
    setup_auth_system()  # agrega login + middleware

    # Página principal (solo accesible si el usuario está autenticado)
    @ui.page('/')
    def main_page():
        if not app.storage.user.get('authenticated', False):
            ui.navigate.to('/login')
            return

        create_main_screen()  # delega la UI real a mainscreen.py
        create_signup_screen()  # delega la UI real a signup_screen.py
        reset_password_screen()  # delega la UI real a reset_screen.py
