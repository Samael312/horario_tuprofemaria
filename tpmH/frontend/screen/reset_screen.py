# ui/reset_screen.py
from nicegui import ui, app
from db.sqlite_db import SQLiteSession
from db.models import User
from passlib.hash import pbkdf2_sha256
from auth.sync import sync_sqlite_to_postgres  # <-- importamos la sincronización

unrestricted_page_routes = {'/reset', '/login'}

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
# Página de reset password
# =====================================================
@ui.page('/reset')
def reset_password_screen():
    """Pantalla para cambiar contraseña."""

    def render_reset_content():
        with ui.column().classes('items-center justify-center'):
            ui.label('Reset your password').classes('text-3xl font-bold mb-4')
            with ui.card().classes('w-80 p-4'):
                ui.label('Ingresa tus datos').classes('text-xl font-bold mb-2')

                # Inputs
                username_input = ui.input('User').classes('w-full')
                old_password_input = ui.input('Old Password', password=True, password_toggle_button=True).classes('w-full')
                new_password_input = ui.input('New Password', password=True, password_toggle_button=True).classes('w-full')

                # Función para cambiar contraseña
                def try_reset():
                    u = username_input.value.strip()
                    old_p = old_password_input.value.strip()
                    new_p = new_password_input.value.strip()

                    if not (u and old_p and new_p):
                        ui.notify('Completa todos los campos', color='warning')
                        return

                    session = SQLiteSession()
                    user = session.query(User).filter_by(username=u).first()
                    if not user:
                        ui.notify('El usuario no existe', color='negative')
                        session.close()
                        return

                    if not pbkdf2_sha256.verify(old_p, user.password_hash):
                        ui.notify('Contraseña antigua incorrecta', color='negative')
                        session.close()
                        return

                    # Reemplaza la contraseña por la nueva (hash)
                    user.password_hash = pbkdf2_sha256.hash(new_p)
                    session.commit()
                    session.close()

                    # ====== SINCRONIZAR AUTOMÁTICAMENTE CON POSTGRES ======
                    sync_sqlite_to_postgres()

                    ui.notify('Contraseña actualizada correctamente', color='positive')
                    ui.navigate.to('/login')

                # Botón de reset
                ui.button('Change Password', on_click=try_reset, color='primary').classes('mt-2 w-full')

                # Enter dispara la función
                for field in (username_input, old_password_input, new_password_input):
                    field.on('keydown.enter', try_reset)

    # Usar layout general
    create_ui(render_reset_content)
