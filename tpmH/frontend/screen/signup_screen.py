# ui/signup_screen.py
from fastapi.responses import RedirectResponse
from nicegui import app, ui
from db.sqlite_db import SQLiteSession
from db.models import User
from auth.sync import sync_sqlite_to_postgres
from passlib.hash import pbkdf2_sha256
import zoneinfo


unrestricted_page_routes = {'/signup', '/login'}
# Obtener todas las zonas horarias ordenadas alfabéticamente
all_timezones = sorted(zoneinfo.available_timezones())
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

        # Botón de cerrar sesión solo si el usuario está autenticado
        if app.storage.user.get('authenticated', False):
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')

            ui.button(
                'Cerrar sesión',
                on_click=logout,
                icon='logout',
                color='negative'
            ).props('outline round')
        
        ui.button("Back to Log in", on_click=lambda: ui.navigate.to('/login')).props('flat color=white')

    # CONTENIDO CENTRAL
    with ui.column().classes('w-full p-4 md:p-8 items-center gap-8'):
        if content_function:
            content_function()


# =====================================================
# Página de signup
# =====================================================
@ui.page('/signup')
def create_signup_screen():
    """Pantalla de registro."""

    def render_signup_content():
        """Renderiza el formulario dentro del layout."""
        with ui.column().classes('items-center justify-center'):
            ui.label('Sign up to Tuprofemaria').classes('text-3xl font-bold mb-4')
            with ui.card().classes('w-80 p-4'):
                ui.label('Crea tu cuenta').classes('text-xl font-bold mb-2')

                # Inputs
                email = ui.input('Email').classes('w-full')
                name = ui.input('Name').classes('w-full')
                surname = ui.input('Surname').classes('w-full')
                username = ui.input('User').classes('w-full')
                password = ui.input('Password', password=True, password_toggle_button=True).classes('w-full')
                time_zone = ui.select(
                    options=all_timezones,
                    label='Time Zone'
                    
                ).classes('w-full').props('use-input input-debounce="0"').classes('w-full')

                # Función de registro
                def try_signup():
                    u = username.value.strip()
                    p = password.value.strip()
                    e = email.value.strip()
                    n = name.value.strip()
                    s = surname.value.strip()
                    t = time_zone.value.strip()
                    
                    if not (u and p and e and n and s and t):
                        ui.notify('Completa todos los campos obligatorios', color='warning')
                        return

                    session = SQLiteSession()
                    try:
                        if session.query(User).filter_by(username=u).first():
                            ui.notify("Usuario ya existe", color="warning")
                            return
                        if session.query(User).filter_by(email=e).first():
                            ui.notify("Email ya registrado", color="warning")
                            return

                        password_hash = pbkdf2_sha256.hash(p)
                        user = User(
                            username=u,
                            name= n, 
                            surname= s,
                            email=e, 
                            time_zone=t,
                            password_hash=password_hash
                            
                            )
                        session.add(user)
                        session.commit()
                        ui.notify("Usuario registrado correctamente", color="positive")

                        # ====== SINCRONIZAR AUTOMÁTICAMENTE ======
                        sync_sqlite_to_postgres()

                        ui.navigate.to('/login')
                    finally:
                        session.close()

                # Botón de signup
                ui.button('Sign up', on_click=try_signup, color='primary').classes('mt-2 w-full')

                # Asignar la tecla Enter a la función de registro
                for field in (email, name, surname, username, password):
                    field.on('keydown.enter', try_signup)

    # Usar layout general
    create_ui(render_signup_content)
