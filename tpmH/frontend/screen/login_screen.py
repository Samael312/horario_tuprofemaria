from typing import Optional, Dict
from fastapi.responses import RedirectResponse
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256
from db.postgres_db import PostgresSession
from db.models import User

# =====================================================
# DICCIONARIO DE TRADUCCIONES
# =====================================================
LOGIN_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        'welcome': 'Bienvenido',
        'subtitle': 'Ingresa a tu cuenta para continuar',
        'username': 'Usuario',
        'password': 'Contraseña',
        'placeholder_user': 'Tu usuario',
        'placeholder_pass': '••••••',
        'login_btn': 'Iniciar Sesión',
        'separator': 'o',
        'signup_btn': 'Crear cuenta nueva',
        'forgot_pass': '¿Olvidaste tu contraseña?',
        'notify_complete': 'Por favor, completa todos los campos.',
        'notify_inactive': 'Esta cuenta ha sido desactivada.',
        'notify_welcome': 'Bienvenido de nuevo, {name}!',
        'notify_error': 'Usuario o contraseña incorrectos',
        'notify_conn_error': 'Error de conexión con el servidor: {error}',
        'tooltip_logout': 'Cerrar Sesión',
        'btn_back': 'Volver',
        'btn_lang_es': 'Español',
        'btn_lang_en': 'English'
    },
    'en': {
        'welcome': 'Welcome',
        'subtitle': 'Log in to your account to continue',
        'username': 'Username',
        'password': 'Password',
        'placeholder_user': 'Your username',
        'placeholder_pass': '••••••',
        'login_btn': 'Log In',
        'separator': 'or',
        'signup_btn': 'Create new account',
        'forgot_pass': 'Forgot your password?',
        'notify_complete': 'Please complete all fields.',
        'notify_inactive': 'This account has been deactivated.',
        'notify_welcome': 'Welcome back, {name}!',
        'notify_error': 'Incorrect username or password',
        'notify_conn_error': 'Connection error with the server: {error}',
        'tooltip_logout': 'Log Out',
        'btn_back': 'Back',
        'btn_lang_es': 'Spanish',
        'btn_lang_en': 'English'
    }
}

# =====================================================
# VARIABLES PARA REFERENCIA (Inputs)
# =====================================================
# Las definimos aquí para que el 'try_login' pueda acceder a ellas
# aunque se regeneren al refrescar el componente.
username_input: Optional[ui.input] = None
password_input: Optional[ui.input] = None

# =====================================================
# LÓGICA DE NEGOCIO (LOGIN Y IDIOMA)
# =====================================================

def change_language_global(new_lang: str):
    """
    1. Actualiza la variable GLOBAL de sesión del usuario.
    2. Refresca los componentes visuales de la pantalla actual.
    """
    # ESTO ES LO IMPORTANTE: Guardamos en la "memoria" global del usuario
    app.storage.user['lang'] = new_lang
    
    # Refrescamos la UI actual para reflejar el cambio inmediatamente
    render_login_header.refresh()
    render_login_form.refresh()

def try_login_action():
    """Intenta loguear usando el idioma actual para las notificaciones."""
    global username_input, password_input
    
    # Leemos el idioma GLOBAL actual para saber en qué idioma dar los errores
    lang = app.storage.user.get('lang', 'es')
    t = LOGIN_TRANSLATIONS[lang]

    if not username_input or not password_input:
        return

    u_val = username_input.value.strip()
    p_val = password_input.value.strip()

    if not u_val or not p_val:
        ui.notify(t["notify_complete"], type='warning')
        return

    session = PostgresSession()
    try:
        user = session.query(User).filter_by(username=u_val).first()
        
        if user and pbkdf2_sha256.verify(p_val, user.password_hash):
            if getattr(user, 'status', 'Active') != 'Active':
                 ui.notify(t["notify_inactive"], type='negative', icon='block')
                 return

            # ACTUALIZAMOS LA SESIÓN GLOBAL
            app.storage.user.update({
                'username': u_val,
                'authenticated': True,
                'role': user.role,
                'name': user.name,
                'surname': user.surname,
                'email': getattr(user, 'email', ''),
                # El 'lang' NO lo tocamos aquí, se mantiene el que el usuario eligió
            })

            ui.notify(t['notify_welcome'].format(name=user.name), type='positive')

            # Redirección
            target = '/admin' if user.role == "admin" else '/mainscreen'
            ui.navigate.to(target)
        else:
            ui.notify(t['notify_error'], type='negative', icon='error')
            
    except Exception as e:
        ui.notify(t['notify_conn_error'].format(error=str(e)), type='negative')
    finally:
        session.close()

# =====================================================
# COMPONENTES VISUALES (UI)
# =====================================================

@ui.refreshable
def render_login_header():
    """Header que cambia según app.storage.user['lang']"""
    # Leemos la variable global
    lang = app.storage.user.get('lang', 'es') 
    t = LOGIN_TRANSLATIONS[lang]
    
    # Logo
    with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
        ui.icon('school', color='pink-600', size='md')
        ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

    # Controles Derecha (Selector + Botón Volver)
    with ui.row().classes('items-center gap-3'):
        
        # --- SELECTOR DE IDIOMA EN EL HEADER ---
        current_flag = '/static/icon/espana.png' if lang == 'es' else '/static/icon/usa.png'
        
        # Botón circular blanco
        with ui.button(icon='expand_more').props('flat round dense color=white text-color=slate-700 shadow-sm border border-gray-200'):
            ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
            
            with ui.menu().classes('bg-white shadow-lg rounded-xl'):
                # Opción ES
                with ui.menu_item(on_click=lambda: change_language_global('es')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/espana.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_es']).classes('text-slate-700')
                
                # Opción EN
                with ui.menu_item(on_click=lambda: change_language_global('en')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/usa.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_en']).classes('text-slate-700')

        # Separador visual
        ui.element('div').classes('h-6 w-[1px] bg-gray-300')

        # Botón Volver / Logout
        if app.storage.user.get('authenticated', False):
             ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login')))\
                .props('flat round color=grey-7').tooltip(t['tooltip_logout'])
        else:
            ui.button(t['btn_back'], on_click=lambda: ui.navigate.to('/MainPage')) \
                .props('flat color=grey-8 icon=login')

@ui.refreshable
def render_login_form():
    """Formulario que cambia según app.storage.user['lang']"""
    global username_input, password_input
    
    # Leemos la variable global
    lang = app.storage.user.get('lang', 'es')
    t = LOGIN_TRANSLATIONS[lang]

    with ui.card().classes('w-full max-w-sm p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
        
        # Header del Formulario
        with ui.column().classes('w-full items-center mb-6 gap-1'):
            with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                ui.icon('lock', size='md', color='pink-600')
            ui.label(t['welcome']).classes('text-2xl font-bold text-gray-800')
            ui.label(t['subtitle']).classes('text-sm text-gray-500')

        # Campos
        with ui.column().classes('w-full gap-4'):
            username_input = ui.input(t['username']) \
                .props(f'outlined dense placeholder="{t["placeholder_user"]}"') \
                .classes('w-full') \
                .on('keydown.enter', try_login_action)
            username_input.add_slot('prepend', '<q-icon name="person" />')

            password_input = ui.input(t['password'], password=True, password_toggle_button=True) \
                .props(f'outlined dense placeholder="{t["placeholder_pass"]}"') \
                .classes('w-full') \
                .on('keydown.enter', try_login_action)
            password_input.add_slot('prepend', '<q-icon name="key" />')

            # Botón Login
            ui.button(t['login_btn'], on_click=try_login_action) \
                .props('unelevated color=pink-600 text-color=white') \
                .classes('w-full py-2 text-md font-bold shadow-md hover:shadow-lg transition-shadow rounded-lg')

        # Footer Links
        with ui.row().classes('w-full items-center justify-center my-4 gap-2'):
            ui.separator().classes('flex-grow')
            ui.label(t['separator']).classes('text-xs text-gray-400 uppercase')
            ui.separator().classes('flex-grow')

        with ui.column().classes('w-full items-center gap-2'):
            ui.button(t['signup_btn'], on_click=lambda: ui.navigate.to('/signup')) \
                .props('outline color=primary') \
                .classes('w-full rounded-lg')
            
            ui.link(t['forgot_pass'], target='/reset') \
                .classes('text-sm text-gray-500 hover:text-pink-600 transition-colors mt-2 decoration-none')

# =====================================================
# SETUP DE LA PÁGINA DE LOGIN
# =====================================================
def setup_auth_system():

    @ui.page('/login')
    def login_page():
        # Si ya está autenticado, fuera
        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')

        # CSS Base
        ui.add_head_html("""
        <style>
            body { background-color: #f8fafc; margin: 0; }
        </style>
        """)

        # 1. RENDERIZAR HEADER (Con selector de idioma)
        # Usamos sticky top-0 para que se quede fijo arriba
        with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm sticky top-0 z-50'):
            render_login_header()

        # 2. RENDERIZAR CUERPO (Formulario)
        with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
            render_login_form()