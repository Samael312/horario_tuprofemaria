from fastapi.responses import RedirectResponse
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256
import zoneinfo
from prompts.chatbot import render_floating_chatbot

# --- NUEVOS IMPORTS PARA LA NUEVA LÓGICA ---
from db.models import User
from db.postgres_db import PostgresSession  # Para consultar si ya existe en la nube
from db.services import create_user_service # Para guardar (Nube + Backup)
from components.share_data import PACKAGE_LIMITS, goals_list # IMPORTANTE: Para obtener los límites
# -------------------------------------------

# =====================================================
# CONFIGURACIÓN
# =====================================================
unrestricted_page_routes = {'/signup', '/login', '/resetpass', '/MainPage', '/method'}
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
        
        # --- LÓGICA DE REGISTRO ACTUALIZADA ---
        def try_signup():
            # Obtener valores limpios
            data = {
                'u': username.value.strip(),
                'p': password.value.strip(),
                'e': email.value.strip(),
                'm': goal_selector.value.strip(),
                'n': name.value.strip(),
                's': surname.value.strip(),
                't': time_zone.value,
                'pkg': package_select.value # Nuevo campo
            }

            # Validación básica de campos vacíos
            if not all(data.values()):
                ui.notify('Por favor, completa todos los campos obligatorios (incluyendo el Plan).', type='warning', icon='warning')
                return

            # 1. VALIDACIÓN EN LA NUBE (Postgres es la fuente de la verdad)
            session_check = PostgresSession()
            try:
                if session_check.query(User).filter_by(username=data['u']).first():
                    ui.notify("El nombre de usuario ya está en uso.", type='negative', icon='error')
                    username.props('error error-message="Usuario no disponible"') 
                    return
                
                if session_check.query(User).filter_by(email=data['e']).first():
                    ui.notify("Este correo ya está registrado.", type='negative', icon='mail_lock')
                    email.props('error error-message="Email registrado"')
                    return
            except Exception as e:
                ui.notify("Error de conexión con el servidor. Intenta más tarde.", type='negative')
                print(f"Error check user: {e}")
                return
            finally:
                session_check.close()

            # 2. CREACIÓN DEL USUARIO CON JSON DE PAGOS AUTOMÁTICO
            try:
                # A. Calcular el límite según el paquete seleccionado
                limit = PACKAGE_LIMITS.get(data['pkg'], 0)

                # B. Generar el JSON automático
                selected_methods = app.storage.user.get('temp_payment_methods', [])

                payment_json = {
                    "Clases_paquete": f"0/{limit}", # Formato: Pagadas/Límite
                    "Clases_totales": 0,             # Inicializado en 0
                    "preferred_methods": selected_methods
                }

                # C. Preparar diccionario
                password_hash = pbkdf2_sha256.hash(data['p'])
                
                user_dict = {
                    'username': data['u'],
                    'name': data['n'],
                    'surname': data['s'],
                    'email': data['e'],
                    'goal': data['m'],
                    'role': "client",
                    'time_zone': data['t'],
                    'password_hash': password_hash,
                    'status': "Active",
                    'package': data['pkg'],        # Guardamos el plan elegido
                    'payment_info': payment_json   # Guardamos el JSON generado
                }

                # LLAMADA AL SERVICIO (Guarda en Neon -> Respalda en SQLite)
                create_user_service(user_dict)
                
                # Éxito
                ui.notify("¡Cuenta creada con éxito! Redirigiendo...", type='positive', icon='check_circle')
                ui.timer(1.5, lambda: ui.navigate.to('/login'))

            except Exception as e:
                ui.notify(f"No se pudo crear el usuario: {str(e)}", type='negative')

        # --- DISEÑO DEL FORMULARIO COMPACTO ---
        # CAMBIO 1: Reducimos max-w-2xl a max-w-xl y p-8 a p-6 (menos ancho y menos relleno)
        with ui.card().classes('w-full max-w-xl p-6 shadow-xl rounded-2xl bg-white border border-gray-100'):
            
            # CAMBIO 2: Reducimos mb-6 a mb-4 y gap-y-1 a gap-0
            with ui.column().classes('w-full items-center mb-4 text-center gap-0'):
                
                # Icono más pequeño (p-2 en vez de p-3)
                with ui.element('div').classes('bg-pink-50 p-2 rounded-full mb-2'):
                    ui.icon('person_add', size='sm', color='pink-600') # size='sm'
                
                ui.label('Crear Cuenta Nueva').classes('text-xl font-bold text-gray-800') # text-xl
                ui.label('Únete para gestionar tus horarios').classes('text-xs text-gray-500')
                
                with ui.row().classes('items-center justify-center mt-1 gap-1'):
                    ui.label('Si no sabes tu zona horaria, pregúntale a Chipi AI').classes('text-xs text-gray-500')
                    with ui.element('div').classes('w-8 h-8 rounded-full border-3 border-white shadow-2xl overflow-hidden relative ring-1 ring-rose-300 bg-white'):
                        icon_img = '/static/icon/logo.png' 
                        ui.image(icon_img).classes('w-full h-full object-cover')

                    ui.element('div').classes('absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/30 to-transparent pointer-events-none')


            ui.separator().classes('mb-4') # mb-6 a mb-4

            # CAMBIO 3: Grid gap-5 a gap-3 (inputs más juntos)
            with ui.grid(columns=2).classes('w-full gap-3'):
                
                name = ui.input('Nombre').classes('w-full').props('outlined dense')
                name.add_slot('prepend', '<q-icon name="badge" />')
                
                surname = ui.input('Apellido').classes('w-full').props('outlined dense')
                surname.add_slot('prepend', '<q-icon name="badge" />')

                username = ui.input('Usuario').classes('w-full').props('outlined dense')
                username.add_slot('prepend', '<q-icon name="account_circle" />')

                email = ui.input('Email').classes('w-full').props('outlined dense type="email"')
                email.add_slot('prepend', '<q-icon name="email" />')

                password = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined dense')
                password.add_slot('prepend', '<q-icon name="key" />')

                time_zone = ui.select(
                    options=all_timezones, 
                    label='Zona Horaria',
                    value='UTC',
                ).classes('w-full').props('outlined dense use-input input-debounce="0" behavior="menu"')
                time_zone.add_slot('prepend', '<q-icon name="schedule" />')

                # Aquí aplicamos el fix del tooltip que vimos antes
                with time_zone:
                    ui.tooltip('Si no sabes tu zona horaria, pregúntale a Chipi AI').classes('bg-pink-600 text-white text-xs')

                # Selectores de ancho completo
                # Usamos dense options también si es posible
                preselected_plan = app.storage.user.get('selected_plan')
                package_options = list(PACKAGE_LIMITS.keys())
                default_value = preselected_plan if preselected_plan in package_options else (package_options[0] if package_options else None)
                
                package_select = ui.select(
                    options=package_options,
                    label='Elige tu Plan',
                    value=default_value
                ).classes('w-full col-span-2').props('outlined dense options-dense') 
                package_select.add_slot('prepend', '<q-icon name="inventory_2" />')

                goal_options = goals_list
                goal_selector = ui.select(
                    options=goal_options,
                    label='¿Por qué quieres clases?',
                    value=goal_options[0] if goal_options else None
                ).classes('w-full col-span-2').props('outlined dense options-dense')
                goal_selector.add_slot('prepend', '<q-icon name="assignment" />')

            # CAMBIO 4: Footer mt-8 a mt-5
            with ui.column().classes('w-full mt-5 gap-2'):
                ui.button('Registrarse', on_click=try_signup) \
                    .props('unelevated color=pink-600') \
                    .classes('w-full font-bold shadow-md rounded-lg') # Quitamos size=lg para que sea estándar
                
                with ui.row().classes('w-full justify-center gap-1 text-xs'): # text-xs
                    ui.label('¿Ya tienes cuenta?')
                    ui.link('Inicia sesión aquí', target='/login').classes('text-pink-600 font-bold hover:underline')

            # Atajos
            for input_elem in [name, surname, username, email, password]:
                input_elem.on('keydown.enter', try_signup)
    # Renderizar UI
    create_ui(render_signup_content)
    render_floating_chatbot('signup') 