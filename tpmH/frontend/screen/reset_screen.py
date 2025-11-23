from nicegui import ui, app
from db.sqlite_db import SQLiteSession
from db.models import User
from passlib.hash import pbkdf2_sha256
from auth.sync import sync_sqlite_to_postgres

# =====================================================
# CONFIGURACIÓN
# =====================================================
unrestricted_page_routes = {'/reset', '/login'}

# =====================================================
# UI PRINCIPAL (HEADER + LAYOUT GENERAL)
# =====================================================
def create_ui(content_function=None):
    """Crea la interfaz base consistente con el resto de la app."""
    ui.dark_mode().set_value(False)

    ui.add_head_html("""
    <style>
    body { background-color: #f8fafc; }
    </style>
    """)

    # HEADER
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/login')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

        # Botón volver al login
        ui.button('Cancelar', on_click=lambda: ui.navigate.to('/login')) \
            .props('flat color=grey-8 icon=close')

    # CONTENEDOR CENTRAL
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        if content_function:
            content_function()

# =====================================================
# PÁGINA DE RESET PASSWORD
# =====================================================
@ui.page('/reset')
def reset_password_screen():
    """Pantalla para cambiar contraseña."""

    def render_reset_content():
        
        # --- LÓGICA ---
        def try_reset():
            u = username_input.value.strip()
            old_p = old_password_input.value.strip()
            new_p = new_password_input.value.strip()

            if not (u and old_p and new_p):
                ui.notify('Por favor, completa todos los campos.', type='warning', icon='warning')
                return

            session = SQLiteSession()
            try:
                user = session.query(User).filter_by(username=u).first()
                
                # 1. Verificar Usuario
                if not user:
                    ui.notify('El usuario no existe.', type='negative', icon='person_off')
                    username_input.props('error error-message="Usuario no encontrado"')
                    return

                # 2. Verificar Contraseña Antigua
                if not pbkdf2_sha256.verify(old_p, user.password_hash):
                    ui.notify('La contraseña actual es incorrecta.', type='negative', icon='gpp_bad')
                    old_password_input.props('error') # Marca el input en rojo
                    return

                # 3. Actualizar
                user.password_hash = pbkdf2_sha256.hash(new_p)
                session.commit()
                
                ui.notify('¡Contraseña actualizada correctamente!', type='positive', icon='check_circle')
                
                # 4. Sincronizar
                try:
                    sync_sqlite_to_postgres()
                except Exception as e:
                    print(f"Error sync: {e}")

                # Redirigir
                ui.timer(1.5, lambda: ui.navigate.to('/login'))

            except Exception as e:
                ui.notify(f"Error del sistema: {str(e)}", type='negative')
            finally:
                session.close()

        # --- DISEÑO ---
        with ui.card().classes('w-full max-w-sm p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
            
            # Encabezado Tarjeta
            with ui.column().classes('w-full items-center mb-6 text-center'):
                with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                    ui.icon('lock_reset', size='md', color='pink-600')
                ui.label('Cambiar Contraseña').classes('text-2xl font-bold text-gray-800')
                ui.label('Ingresa tus credenciales actuales').classes('text-sm text-gray-500')

            # Inputs
            with ui.column().classes('w-full gap-4'):
                username_input = ui.input('Usuario') \
                    .props('outlined dense') \
                    .classes('w-full')
                username_input.add_slot('prepend', '<q-icon name="account_circle" />')

                old_password_input = ui.input('Contraseña Actual', password=True, password_toggle_button=True) \
                    .props('outlined dense') \
                    .classes('w-full')
                old_password_input.add_slot('prepend', '<q-icon name="vpn_key" />')

                new_password_input = ui.input('Nueva Contraseña', password=True, password_toggle_button=True) \
                    .props('outlined dense') \
                    .classes('w-full')
                new_password_input.add_slot('prepend', '<q-icon name="lock" />')

                # Botón Acción
                ui.button('Actualizar Contraseña', on_click=try_reset) \
                    .props('unelevated color=pink-600') \
                    .classes('w-full mt-2 font-bold shadow-md hover:shadow-lg transition-shadow rounded-lg py-2')

            # Enlaces footer
            with ui.row().classes('w-full justify-center mt-6'):
                ui.link('Volver al inicio', target='/login') \
                    .classes('text-sm text-gray-500 hover:text-pink-600 transition-colors decoration-none')

            # Atajos de teclado
            for field in (username_input, old_password_input, new_password_input):
                field.on('keydown.enter', try_reset)

    # Renderizar UI
    create_ui(render_reset_content)