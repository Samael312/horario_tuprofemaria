from fastapi.responses import RedirectResponse
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256
import zoneinfo
from typing import Optional, Dict

# --- NUEVOS IMPORTS PARA LA LÓGICA DE NEGOCIO ---
from db.models import User
from db.postgres_db import PostgresSession
from db.services import create_user_service
from components.share_data import PACKAGE_LIMITS
# -------------------------------------------

# =====================================================
# 1. TRADUCCIONES
# =====================================================
SIGNUP_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        'title': 'Crear Cuenta Nueva',
        'subtitle': 'Únete para gestionar tus horarios fácilmente',
        'label_name': 'Nombre',
        'label_surname': 'Apellido',
        'label_user': 'Usuario',
        'label_email': 'Email',
        'label_pass': 'Contraseña',
        'label_zone': 'Zona Horaria',
        'label_plan': 'Elige tu Plan',
        'btn_signup': 'Registrarse',
        'text_already': '¿Ya tienes cuenta?',
        'link_login': 'Inicia sesión aquí',
        'btn_login_header': 'Iniciar Sesión',
        'notify_fill': 'Por favor, completa todos los campos obligatorios.',
        'notify_user_taken': 'El nombre de usuario ya está en uso.',
        'notify_email_taken': 'Este correo ya está registrado.',
        'notify_error_conn': 'Error de conexión con el servidor. Intenta más tarde.',
        'notify_success': '¡Cuenta creada con éxito! Redirigiendo...',
        'notify_fail': 'No se pudo crear el usuario: {error}',
        'btn_lang_es': 'Español',
        'btn_lang_en': 'English'
    },
    'en': {
        'title': 'Create New Account',
        'subtitle': 'Join to manage your schedules easily',
        'label_name': 'Name',
        'label_surname': 'Surname',
        'label_user': 'Username',
        'label_email': 'Email',
        'label_pass': 'Password',
        'label_zone': 'Time Zone',
        'label_plan': 'Choose your Plan',
        'btn_signup': 'Sign Up',
        'text_already': 'Already have an account?',
        'link_login': 'Log in here',
        'btn_login_header': 'Log In',
        'notify_fill': 'Please complete all required fields.',
        'notify_user_taken': 'Username is already taken.',
        'notify_email_taken': 'This email is already registered.',
        'notify_error_conn': 'Connection error with server. Try again later.',
        'notify_success': 'Account created successfully! Redirecting...',
        'notify_fail': 'Could not create user: {error}',
        'btn_lang_es': 'Spanish',
        'btn_lang_en': 'English'
    }
}

# =====================================================
# 2. CONFIGURACIÓN Y ESTADO GLOBAL
# =====================================================
all_timezones = sorted(zoneinfo.available_timezones())

# Variables globales para los inputs (necesarias para @ui.refreshable)
name_input: Optional[ui.input] = None
surname_input: Optional[ui.input] = None
username_input: Optional[ui.input] = None
email_input: Optional[ui.input] = None
password_input: Optional[ui.input] = None
timezone_input: Optional[ui.select] = None
package_input: Optional[ui.select] = None

# =====================================================
# 3. LÓGICA DE NEGOCIO (CAMBIO DE IDIOMA Y REGISTRO)
# =====================================================

def change_signup_language(new_lang: str):
    """Actualiza el idioma global y refresca la pantalla de signup."""
    app.storage.user['lang'] = new_lang
    render_signup_header.refresh()
    render_signup_form.refresh()

def try_signup_action():
    """Lógica de registro utilizando las variables globales y traducciones."""
    global name_input, surname_input, username_input, email_input, password_input, timezone_input, package_input
    
    # Obtener idioma actual para notificaciones
    lang = app.storage.user.get('lang', 'es')
    t = SIGNUP_TRANSLATIONS[lang]

    # Validar que los inputs existen (seguridad)
    if not all([name_input, surname_input, username_input, email_input, password_input, timezone_input, package_input]):
        return

    # Obtener valores limpios
    data = {
        'u': username_input.value.strip(),
        'p': password_input.value.strip(),
        'e': email_input.value.strip(),
        'n': name_input.value.strip(),
        's': surname_input.value.strip(),
        't': timezone_input.value,
        'pkg': package_input.value
    }

    # Validación básica de campos vacíos
    if not all(data.values()):
        ui.notify(t['notify_fill'], type='warning', icon='warning')
        return

    # 1. VALIDACIÓN EN LA NUBE (Postgres)
    session_check = PostgresSession()
    try:
        if session_check.query(User).filter_by(username=data['u']).first():
            ui.notify(t['notify_user_taken'], type='negative', icon='error')
            username_input.props('error') 
            return
        
        if session_check.query(User).filter_by(email=data['e']).first():
            ui.notify(t['notify_email_taken'], type='negative', icon='mail_lock')
            email_input.props('error')
            return
    except Exception as e:
        ui.notify(t['notify_error_conn'], type='negative')
        print(f"Error check user: {e}")
        return
    finally:
        session_check.close()

    # 2. CREACIÓN DEL USUARIO
    try:
        # A. Calcular límite según paquete
        limit = PACKAGE_LIMITS.get(data['pkg'], 0)

        # B. Generar JSON automático
        payment_json = {
            "Clases_paquete": f"0/{limit}",
            "Clases_totales": 0
        }

        # C. Preparar diccionario
        password_hash = pbkdf2_sha256.hash(data['p'])
        
        user_dict = {
            'username': data['u'],
            'name': data['n'],
            'surname': data['s'],
            'email': data['e'],
            'role': "client",
            'time_zone': data['t'],
            'password_hash': password_hash,
            'status': "Active",
            'package': data['pkg'],
            'payment_info': payment_json
        }

        # LLAMADA AL SERVICIO
        create_user_service(user_dict)
        
        # Éxito
        ui.notify(t['notify_success'], type='positive', icon='check_circle')
        ui.timer(1.5, lambda: ui.navigate.to('/login'))

    except Exception as e:
        ui.notify(t['notify_fail'].format(error=str(e)), type='negative')

# =====================================================
# 4. COMPONENTES VISUALES (UI REFRESCHABLE)
# =====================================================

@ui.refreshable
def render_signup_header():
    """Header con selector de idioma y botón de login."""
    lang = app.storage.user.get('lang', 'es')
    t = SIGNUP_TRANSLATIONS[lang]

    # Logo
    with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/login')):
        ui.icon('school', color='pink-600', size='md')
        ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

    # Controles Derecha
    with ui.row().classes('items-center gap-3'):
        
        # --- SELECTOR DE IDIOMA ---
        current_flag = '/static/icon/espana.png' if lang == 'es' else '/static/icon/usa.png'
        with ui.button(icon='expand_more').props('flat round dense color=white text-color=slate-700 shadow-sm border border-gray-200'):
            ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
            with ui.menu().classes('bg-white shadow-lg rounded-xl'):
                with ui.menu_item(on_click=lambda: change_signup_language('es')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/espana.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_es']).classes('text-slate-700')
                with ui.menu_item(on_click=lambda: change_signup_language('en')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/usa.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_en']).classes('text-slate-700')

        # Separador
        ui.element('div').classes('h-6 w-[1px] bg-gray-300')

        # Botón Login
        ui.button(t['btn_login_header'], on_click=lambda: ui.navigate.to('/login')) \
            .props('flat color=grey-8 icon=login')

@ui.refreshable
def render_signup_form():
    """Formulario de registro traducible."""
    global name_input, surname_input, username_input, email_input, password_input, timezone_input, package_input
    
    lang = app.storage.user.get('lang', 'es')
    t = SIGNUP_TRANSLATIONS[lang]
    #tp = SHARED_TRANSLATION[lang]

    with ui.card().classes('w-full max-w-2xl p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
        
        # Encabezado Tarjeta
        with ui.column().classes('w-full items-center mb-6 text-center'):
            with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                ui.icon('person_add', size='md', color='pink-600')
            ui.label(t['title']).classes('text-2xl font-bold text-gray-800')
            ui.label(t['subtitle']).classes('text-sm text-gray-500')

        ui.separator().classes('mb-6')

        # Grid de Inputs
        with ui.grid(columns=2).classes('w-full gap-5'):
            
            # Datos Personales
            name_input = ui.input(t['label_name']).classes('w-full').props('outlined dense')
            name_input.add_slot('prepend', '<q-icon name="badge" />')
            
            surname_input = ui.input(t['label_surname']).classes('w-full').props('outlined dense')
            surname_input.add_slot('prepend', '<q-icon name="badge" />')

            # Datos de Cuenta
            username_input = ui.input(t['label_user']).classes('w-full').props('outlined dense')
            username_input.add_slot('prepend', '<q-icon name="account_circle" />')

            email_input = ui.input(t['label_email']).classes('w-full').props('outlined dense type="email"')
            email_input.add_slot('prepend', '<q-icon name="email" />')

            # Configuración
            password_input = ui.input(t['label_pass'], password=True, password_toggle_button=True).classes('w-full').props('outlined dense')
            password_input.add_slot('prepend', '<q-icon name="key" />')

            timezone_input = ui.select(
                options=all_timezones, 
                label=t['label_zone'],
                value='UTC' 
            ).classes('w-full').props('outlined dense use-input input-debounce="0" behavior="menu"')
            timezone_input.add_slot('prepend', '<q-icon name="schedule" />')

            # PAQUETES
            package_options = list(PACKAGE_LIMITS.keys())
            #package_options = [tp[k] for k in package_keys]
            package_input = ui.select(
                options=package_options,
                label=t['label_plan'],
                value=package_options[0] if package_options else None
            ).classes('w-full col-span-2').props('outlined dense')
            package_input.add_slot('prepend', '<q-icon name="inventory_2" />')

        # Footer
        with ui.column().classes('w-full mt-8 gap-3'):
            ui.button(t['btn_signup'], on_click=try_signup_action) \
                .props('unelevated color=pink-600 size=lg') \
                .classes('w-full font-bold shadow-md hover:shadow-lg transition-all rounded-lg')
            
            with ui.row().classes('w-full justify-center gap-1 text-sm'):
                ui.label(t['text_already'])
                ui.link(t['link_login'], target='/login').classes('text-pink-600 font-bold hover:underline')

        # Atajos de teclado
        for input_elem in [name_input, surname_input, username_input, email_input, password_input]:
            input_elem.on('keydown.enter', try_signup_action)

# =====================================================
# 5. SETUP DE LA PÁGINA
# =====================================================

@ui.page('/signup')
def create_signup_screen():
    """Página principal de registro."""
    
    # Redirigir si ya está logueado
    if app.storage.user.get('authenticated', False):
        return RedirectResponse('/')

    # CSS Base
    ui.add_head_html("""
    <style>
        body { background-color: #f8fafc; margin: 0; }
    </style>
    """)

    # 1. RENDERIZAR HEADER (Sticky)
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm sticky top-0 z-50'):
        render_signup_header()

    # 2. RENDERIZAR CUERPO
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        render_signup_form()