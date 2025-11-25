from fastapi.responses import RedirectResponse
from nicegui import app, ui
from db.sqlite_db import SQLiteSession
from db.models import User
from auth.sync import sync_sqlite_to_postgres
from passlib.hash import pbkdf2_sha256
import zoneinfo

# =====================================================
# CONFIGURACIÓN
# =====================================================
unrestricted_page_routes = {'/signup', '/login'}
all_timezones = sorted(zoneinfo.available_timezones())

# =====================================================
# UI PRINCIPAL (HEADER + LAYOUT GENERAL)
# =====================================================
def create_ui(content_function=None):
    """Crea la interfaz base consistente con el login."""
    ui.dark_mode().set_value(False)

    ui.add_head_html("""
    <style>
    body { background-color: #f8fafc; }
    </style>
    """)

    # HEADER (Estilo consistente)
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/login')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

        # Botón volver al login (Sutil)
        ui.button('Iniciar Sesión', on_click=lambda: ui.navigate.to('/login')) \
            .props('flat color=grey-8 icon=login')

    # CONTENEDOR CENTRAL
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        if content_function:
            content_function()

# =====================================================
# PÁGINA DE SIGNUP
# =====================================================
@ui.page('/signup')
def create_signup_screen():
    """Pantalla de registro."""

    # Redirigir si ya está logueado
    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')

    def render_signup_content():
        
        # --- LÓGICA DE REGISTRO ---
        def try_signup():
            # Obtener valores limpios
            data = {
                'u': username.value.strip(),
                'p': password.value.strip(),
                'e': email.value.strip(),
                'n': name.value.strip(),
                's': surname.value.strip(),
                't': time_zone.value
            }

            # Validación básica
            if not all(data.values()):
                ui.notify('Por favor, completa todos los campos obligatorios.', type='warning', icon='warning')
                return

            session = SQLiteSession()
            try:
                # Validaciones de unicidad
                if session.query(User).filter_by(username=data['u']).first():
                    ui.notify("El nombre de usuario ya está en uso.", type='negative', icon='error')
                    username.props('error error-message="Usuario no disponible"') # Feedback visual en el input
                    return
                
                if session.query(User).filter_by(email=data['e']).first():
                    ui.notify("Este correo ya está registrado.", type='negative', icon='mail_lock')
                    email.props('error error-message="Email registrado"')
                    return

                # Crear usuario
                password_hash = pbkdf2_sha256.hash(data['p'])
                new_user = User(
                    username=data['u'],
                    name=data['n'], 
                    surname=data['s'],
                    email=data['e'], 
                    role="client",
                    time_zone=data['t'],
                    password_hash=password_hash
                )
                session.add(new_user)
                session.commit()
                
                ui.notify("¡Cuenta creada con éxito! Redirigiendo...", type='positive', icon='check_circle')
                
                # Sincronización (Manejo de errores silencioso para no bloquear al usuario)
                try:
                    sync_sqlite_to_postgres()
                except Exception as e:
                    print(f"Error sync: {e}")

                # Redirigir tras breve pausa
                ui.timer(1.5, lambda: ui.navigate.to('/login'))

            except Exception as e:
                ui.notify(f"Error del servidor: {str(e)}", type='negative')
            finally:
                session.close()

        # --- DISEÑO DEL FORMULARIO ---
        with ui.card().classes('w-full max-w-2xl p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
            
            # Encabezado Tarjeta
            with ui.column().classes('w-full items-center mb-6 text-center'):
                with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                    ui.icon('person_add', size='md', color='pink-600')
                ui.label('Crear Cuenta Nueva').classes('text-2xl font-bold text-gray-800')
                ui.label('Únete para gestionar tus horarios fácilmente').classes('text-sm text-gray-500')

            ui.separator().classes('mb-6')

            # Grid de Inputs (2 Columnas)
            with ui.grid(columns=2).classes('w-full gap-5'):
                
                # Datos Personales
                name = ui.input('Nombre').classes('w-full').props('outlined dense')
                name.add_slot('prepend', '<q-icon name="badge" />')
                
                surname = ui.input('Apellido').classes('w-full').props('outlined dense')
                surname.add_slot('prepend', '<q-icon name="badge" />')

                # Datos de Cuenta
                username = ui.input('Usuario').classes('w-full').props('outlined dense')
                username.add_slot('prepend', '<q-icon name="account_circle" />')

                email = ui.input('Email').classes('w-full').props('outlined dense type="email"')
                email.add_slot('prepend', '<q-icon name="email" />')

                # Configuración
                password = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined dense')
                password.add_slot('prepend', '<q-icon name="key" />')

                time_zone = ui.select(
                    options=all_timezones, 
                    label='Zona Horaria',
                    value='UTC' 
                ).classes('w-full').props('outlined dense use-input input-debounce="0" behavior="menu"')
                time_zone.add_slot('prepend', '<q-icon name="schedule" />')

            # Footer con Botón
            with ui.column().classes('w-full mt-8 gap-3'):
                ui.button('Registrarse', on_click=try_signup) \
                    .props('unelevated color=pink-600 size=lg') \
                    .classes('w-full font-bold shadow-md hover:shadow-lg transition-all rounded-lg')
                
                with ui.row().classes('w-full justify-center gap-1 text-sm'):
                    ui.label('¿Ya tienes cuenta?')
                    ui.link('Inicia sesión aquí', target='/login').classes('text-pink-600 font-bold hover:underline')

            # Atajos de teclado (Enter para enviar)
            for input_elem in [name, surname, username, email, password]:
                input_elem.on('keydown.enter', try_signup)

    # Renderizar UI
    create_ui(render_signup_content)