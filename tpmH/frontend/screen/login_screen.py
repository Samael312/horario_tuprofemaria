from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256

# --- CAMBIO IMPORTANTE: Usamos Postgres para validar credenciales ---
from db.postgres_db import PostgresSession
from db.models import User
# ------------------------------------------------------------------

# =====================================================
# CONFIGURACIÓN
# =====================================================
unrestricted_page_routes = {'/login', '/signup', '/reset', '/MainPage', '/method','/planScreen'}

# =====================================================
# MIDDLEWARE DE AUTENTICACIÓN
# =====================================================
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            # 1. Redirección de raíz
            if request.url.path == '/':
                return RedirectResponse('/MainPage')
            
            # 2. Excepciones de seguridad (AQUÍ ESTABA EL PROBLEMA)
            # Permitimos:
            # - /_nicegui (archivos internos)
            # - /static (tus imágenes y videos) <--- NUEVO
            # - Rutas públicas (login, signup, etc)
            if (not request.url.path.startswith('/_nicegui') 
                and not request.url.path.startswith('/static') 
                and not request.url.path.startswith('/uploads')
                and request.url.path not in unrestricted_page_routes):
                
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        
        return await call_next(request)
# =====================================================
# UI PRINCIPAL (HEADER + LAYOUT GENERAL)
# =====================================================
def create_ui(content_function=None):
    """Crea la interfaz base. Si es login, centra el contenido verticalmente."""
    ui.dark_mode().set_value(False)

    # Estilos globales para tablas y scroll
    ui.add_head_html("""
    <style>
    body { background-color: #f8fafc; }
    .q-table td, .q-table th {
        white-space: normal !important;
        word-wrap: break-word !important;
        line-height: 1.3em;
        vertical-align: top;
    }
    </style>
    """)

    # HEADER (Simple y limpio)
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

        # Botón de salir (Solo si está autenticado)
        if app.storage.user.get('authenticated', False):
            def logout():
                app.storage.user.clear()
                ui.navigate.to('/login')
            
            ui.button(icon='logout', on_click=logout).props('flat round color=grey-7').tooltip('Cerrar Sesión')

    # CONTENEDOR CENTRAL
    # Usamos min-h-screen para centrar verticalmente si es necesario (útil para login)
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        if content_function:
            content_function()

# =====================================================
# SISTEMA DE AUTENTICACIÓN Y LOGIN
# =====================================================
def setup_auth_system():
    app.add_middleware(AuthMiddleware)

    @ui.page('/login')
    def login(redirect_to: str = '/') -> Optional[RedirectResponse]:
        
        # 1. Si ya está autenticado, redirigir
        if app.storage.user.get('authenticated', False):
            return RedirectResponse('/')

        # 2. Contenido del Login
        def render_login_content():
            
            # Lógica de Login
            def try_login():
                u_val = username.value.strip()
                p_val = password.value.strip()

                if not u_val or not p_val:
                    ui.notify("Por favor, completa todos los campos.", type='warning')
                    return

                # --- CONEXIÓN A NEON (POSTGRES) ---
                session = PostgresSession()
                try:
                    # Buscamos al usuario en la Nube
                    user = session.query(User).filter_by(username=u_val).first()
                    
                    if user and pbkdf2_sha256.verify(p_val, user.password_hash):
                        
                        # Verificar si la cuenta está activa (Opcional, pero recomendado)
                        if getattr(user, 'status', 'Active') != 'Active':
                             ui.notify("Esta cuenta ha sido desactivada.", type='negative', icon='block')
                             return

                        # Guardar sesión en el navegador
                        app.storage.user.update({
                            'username': u_val,
                            'authenticated': True,
                            'role': user.role,
                            'name': user.name,
                            'surname': user.surname,
                            'email': getattr(user, 'email', ''),
                            'time_zone': getattr(user, 'time_zone', '')
                        })

                        ui.notify(f"Bienvenido de nuevo, {user.name}!", type='positive')

                        # Redirección según rol
                        target = '/admin' if user.role == "admin" else '/mainscreen'
                        ui.navigate.to(target)
                    else:
                        ui.notify("Usuario o contraseña incorrectos", type='negative', icon='error')
                        
                except Exception as e:
                    # Error de conexión a Neon
                    ui.notify(f"Error de conexión con el servidor: {str(e)}", type='negative')
                finally:
                    session.close()

            # --- DISEÑO DE LA TARJETA DE LOGIN ---
            with ui.card().classes('w-full max-w-sm p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
                
                # Encabezado de la tarjeta
                with ui.column().classes('w-full items-center mb-6 gap-1'):
                    with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                        ui.icon('lock', size='md', color='pink-600')
                    ui.label('Bienvenido').classes('text-2xl font-bold text-gray-800')
                    ui.label('Ingresa a tu cuenta para continuar').classes('text-sm text-gray-500')

                # Formulario
                with ui.column().classes('w-full gap-4'):
                    username = ui.input('Usuario') \
                        .props('outlined dense placeholder="Tu usuario"') \
                        .classes('w-full') \
                        .on('keydown.enter', try_login)
                    username.add_slot('prepend', '<q-icon name="person" />')

                    password = ui.input('Contraseña', password=True, password_toggle_button=True) \
                        .props('outlined dense placeholder="••••••"') \
                        .classes('w-full') \
                        .on('keydown.enter', try_login)
                    password.add_slot('prepend', '<q-icon name="key" />')

                    # Botón Principal
                    ui.button('Iniciar Sesión', on_click=try_login) \
                        .props('unelevated color=pink-600 text-color=white') \
                        .classes('w-full py-2 text-md font-bold shadow-md hover:shadow-lg transition-shadow rounded-lg')

                # Separador
                with ui.row().classes('w-full items-center justify-center my-4 gap-2'):
                    ui.separator().classes('flex-grow')
                    ui.label('o').classes('text-xs text-gray-400 uppercase')
                    ui.separator().classes('flex-grow')

                # Botones Secundarios (Registro y Reset)
                with ui.column().classes('w-full items-center gap-2'):
                    # Crear cuenta (Botón secundario destacado)
                    ui.button('Crear cuenta nueva', on_click=lambda: ui.navigate.to('/method')) \
                        .props('outline color=primary') \
                        .classes('w-full rounded-lg')
                    
                    # Recuperar contraseña (Link sutil)
                    ui.link('¿Olvidaste tu contraseña?', target='/reset') \
                        .classes('text-sm text-gray-500 hover:text-pink-600 transition-colors mt-2 decoration-none')

        # 3. Renderizar Layout
        create_ui(render_login_content)
        return None