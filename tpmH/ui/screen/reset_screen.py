# ui/reset_screen.py
from nicegui import ui, app

# Base de datos de ejemplo (mismo diccionario que signup)
users_db = {}  # {username: {'email': ..., 'name': ..., 'surname': ..., 'password': ...}}

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
                username_input = ui.input('User')
                old_password_input = ui.input('Old Password', password=True, password_toggle_button=True)
                new_password_input = ui.input('New Password', password=True, password_toggle_button=True)

                # Función para cambiar contraseña
                def try_reset():
                    u = username_input.value.strip()
                    old_p = old_password_input.value.strip()
                    new_p = new_password_input.value.strip()

                    if not (u and old_p and new_p):
                        ui.notify('Completa todos los campos', color='warning')
                        return

                    if u not in users_db:
                        ui.notify('El usuario no existe', color='negative')
                        return

                    if users_db[u]['password'] != old_p:
                        ui.notify('Contraseña antigua incorrecta', color='negative')
                        return

                    # Reemplaza la contraseña por la nueva
                    users_db[u]['password'] = new_p
                    ui.notify('Contraseña actualizada correctamente', color='positive')
                    ui.navigate.to('/login')

                # Botón de reset
                ui.button('Change Password', on_click=try_reset, color='primary').classes('mt-2 w-full')

                # Enter dispara la función
                for field in (username_input, old_password_input, new_password_input):
                    field.on('keydown.enter', try_reset)

    # Usar layout general
    create_ui(render_reset_content)
