# ui/login_signup_ui.py
from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui
from passlib.hash import bcrypt
from db.sqlite_db import SQLiteSession
from db.models import User
from auth.sync import sync_sqlite_to_postgres
from passlib.hash import pbkdf2_sha256  # <--- importa esto

# =====================================================
# CONFIGURACIÓN SIMPLE DE USUARIOS
# =====================================================
#passwords = {'user1': 'pass1', 'user2': 'pass2'}
unrestricted_page_routes = {'/login', '/signup', '/reset'}


# =====================================================
# MIDDLEWARE DE AUTENTICACIÓN
# =====================================================
class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para proteger páginas que requieren autenticación."""
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if not request.url.path.startswith('/_nicegui') and request.url.path not in unrestricted_page_routes:
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        return await call_next(request)


# =====================================================
# UI PRINCIPAL (HEADER + LAYOUT)
# =====================================================
def create_ui(content_function=None):
    """Crea la interfaz general con header y un contenedor central."""
    ui.dark_mode().set_value(False)

    ui.add_head_html("""
    <style>
    .q-table td, .q-table th {
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.3em;
        vertical-align: top;
        padding: 6px 8px !important;
    }
    .q-table__container {
        max-height: 600px;
    }
    </style>
    """)

    # HEADER
    with ui.header().classes('items-center justify-between'):
        ui.label('Tuprofemaria: Creador de Horarios').classes('text-lg font-bold')

        # Solo mostrar el botón si el usuario está autenticado
        if app.storage.user.get('authenticated', False):
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')

    # CONTENIDO CENTRAL
    with ui.column().classes('w-full p-4 md:p-8 items-center gap-8'):
        if content_function:
            content_function()  # Renderiza el contenido dinámico (como el login o dashboard)


# =====================================================
# Sistema de autenticación y login
# =====================================================
def setup_auth_system():
    app.add_middleware(AuthMiddleware)

    @ui.page('/login')
    def login(redirect_to: str = '/') -> Optional[RedirectResponse]:
        """Pantalla de inicio de sesión"""

        def render_login_content():
            """Función que renderiza el formulario dentro del layout."""
            def try_login():
                u = username.value.strip()
                p = password.value.strip()

                session = SQLiteSession()
                try:
                    user = session.query(User).filter_by(username=u).first()
                    if not user:
                        ui.notify("Usuario o contraseña incorrectos", color="negative")
                        return

                    if pbkdf2_sha256.verify(p, user.password_hash):
                        app.storage.user.update({
                            'username': u,
                            'authenticated': True,
                            'role': user.role,
                            'name': user.name,
                            'surname': user.surname,
                            'email':user.email,
                            'time_zone':user.time_zone
                            

                        })

                        if user.role == "admin":
                            ui.navigate.to('/admin')
                        else:
                            ui.navigate.to('/mainscreen')
                    else:
                        ui.notify("Usuario o contraseña incorrectos", color="negative")
                finally:
                    session.close()
                    
            with ui.column().classes('items-center justify-center'):
                ui.label('Sign in to Tuprofemaria').classes('text-3xl font-bold mb-4')
                with ui.card().classes('w-80 p-4'):
                    ui.label('Log in').classes('text-xl font-bold mb-2')
                    username = ui.input('User').on('keydown.enter', try_login).classes('w-full')
                    password = ui.input(
                        'Password',
                        password=True,
                        password_toggle_button=True
                    ).on('keydown.enter', try_login).classes('w-full')
                    ui.button('Sign in', on_click=try_login, color='primary').classes('mt-2 w-full')
                with ui.row().classes('mt-2'):
                    ui.label("Don't have an account?")
                    ui.button('Sign up', on_click=lambda: ui.navigate.to('/signup'), color='primary').classes('mt-2 w-full')
                with ui.row().classes('mt-2'):
                    ui.label("Forgot your password?")
                    ui.button('Reset', on_click=lambda: ui.navigate.to('/reset'), color='primary').classes('mt-2 w-full') 

        # Si ya está autenticado → redirigir
        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')

        # Usar el layout general, insertando el contenido del login
        create_ui(render_login_content)
        return None
