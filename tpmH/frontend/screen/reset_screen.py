from nicegui import ui, app
from passlib.hash import pbkdf2_sha256
from typing import Dict

# --- TUS IMPORTS ---
from db.models import User
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
# -------------------

# =====================================================
# 1. DICCIONARIO DE TRADUCCIONES
# =====================================================
RESET_TRANSLATIONS: Dict[str, Dict[str, str]] = {
    'es': {
        'title': 'Cambiar Contraseña',
        'subtitle': 'Ingresa tus credenciales actuales',
        'label_user': 'Usuario',
        'label_old_pass': 'Contraseña Actual',
        'label_new_pass': 'Nueva Contraseña',
        'btn_update': 'Actualizar Contraseña',
        'link_back': 'Volver al inicio',
        'btn_cancel': 'Cancelar',
        'notify_fill': 'Por favor, completa todos los campos.',
        'notify_user_not_found': 'El usuario no existe.',
        'notify_wrong_pass': 'La contraseña actual es incorrecta.',
        'notify_success': '¡Contraseña actualizada correctamente!',
        'notify_conn_error': 'Error de conexión con el servidor: {error}',
        'btn_lang_es': 'Español',
        'btn_lang_en': 'English'
    },
    'en': {
        'title': 'Reset Password',
        'subtitle': 'Enter your current credentials',
        'label_user': 'Username',
        'label_old_pass': 'Current Password',
        'label_new_pass': 'New Password',
        'btn_update': 'Update Password',
        'link_back': 'Back to login',
        'btn_cancel': 'Cancel',
        'notify_fill': 'Please complete all fields.',
        'notify_user_not_found': 'User does not exist.',
        'notify_wrong_pass': 'Current password is incorrect.',
        'notify_success': 'Password updated successfully!',
        'notify_conn_error': 'Connection error with server: {error}',
        'btn_lang_es': 'Spanish',
        'btn_lang_en': 'English'
    }
}

# =====================================================
# 2. COMPONENTES VISUALES
# =====================================================

# CORRECCIÓN: Quitamos ui.header() de aquí. Esto solo renderiza lo de ADENTRO del header.
@ui.refreshable
def render_header_content(on_lang_change):
    """Solo el contenido interno del Header (Logo, Botones, Idioma)."""
    lang = app.storage.user.get('lang', 'es')
    t = RESET_TRANSLATIONS[lang]

    # Helper para cambiar idioma
    def change_lang(new_lang):
        app.storage.user['lang'] = new_lang
        render_header_content.refresh() # Refresca el contenido del header
        on_lang_change() # Refresca el formulario principal

    # Logo (Izquierda)
    with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/login')):
        ui.icon('school', color='pink-600', size='md')
        ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

    # Controles (Derecha)
    with ui.row().classes('items-center gap-3'):
        # Selector de idioma
        current_flag = '/static/icon/espana.png' if lang == 'es' else '/static/icon/usa.png'
        
        with ui.button(icon='expand_more').props('flat round dense color=white text-color=slate-700 shadow-sm border border-gray-200'):
            ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
            with ui.menu().classes('bg-white shadow-lg rounded-xl'):
                with ui.menu_item(on_click=lambda: change_lang('es')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/espana.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_es']).classes('text-slate-700')
                with ui.menu_item(on_click=lambda: change_lang('en')).classes('gap-2 hover:bg-slate-50'):
                    ui.image('/static/icon/usa.png').classes('w-6 h-6')
                    ui.label(t['btn_lang_en']).classes('text-slate-700')

        # Separador
        ui.element('div').classes('h-6 w-[1px] bg-gray-300')

        # Botón Cancelar
        ui.button(t['btn_cancel'], on_click=lambda: ui.navigate.to('/login')) \
            .props('flat color=grey-8 icon=close')


@ui.refreshable
def render_reset_form(form_state: dict):
    """Formulario vinculado al estado local."""
    lang = app.storage.user.get('lang', 'es')
    t = RESET_TRANSLATIONS[lang]

    # Referencias locales a inputs para gestión de errores visuales
    username_input = None
    old_password_input = None

    def try_reset_action():
        # Usamos nonlocal para acceder a los inputs definidos abajo si necesitamos marcar error
        nonlocal username_input, old_password_input

        u = form_state['u'].strip()
        old_p = form_state['old'].strip()
        new_p = form_state['new'].strip()

        if not (u and old_p and new_p):
            ui.notify(t['notify_fill'], type='warning', icon='warning')
            return

        session_pg = PostgresSession()
        success = False
        
        try:
            user_pg = session_pg.query(User).filter_by(username=u).first()
            
            if not user_pg:
                ui.notify(t['notify_user_not_found'], type='negative', icon='person_off')
                if username_input: username_input.props('error')
                return

            if not pbkdf2_sha256.verify(old_p, user_pg.password_hash):
                ui.notify(t['notify_wrong_pass'], type='negative', icon='gpp_bad')
                if old_password_input: old_password_input.props('error') 
                return

            new_hash = pbkdf2_sha256.hash(new_p)
            user_pg.password_hash = new_hash
            session_pg.commit()
            success = True
            ui.notify(t['notify_success'], type='positive', icon='check_circle')
            ui.timer(1.5, lambda: ui.navigate.to('/login'))

        except Exception as e:
            session_pg.rollback()
            ui.notify(t['notify_conn_error'].format(error=str(e)), type='negative')
            return
        finally:
            session_pg.close()

        if success:
            try:
                session_sqlite = BackupSession()
                user_sqlite = session_sqlite.query(User).filter_by(username=u).first()
                if user_sqlite:
                    user_sqlite.password_hash = new_hash
                    session_sqlite.commit()
            except Exception as e:
                print(f"Backup error: {e}")
            finally:
                session_sqlite.close()

    # --- UI DEL CARD ---
    with ui.card().classes('w-full max-w-sm p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
        with ui.column().classes('w-full items-center mb-6 text-center'):
            with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                ui.icon('lock_reset', size='md', color='pink-600')
            ui.label(t['title']).classes('text-2xl font-bold text-gray-800')
            ui.label(t['subtitle']).classes('text-sm text-gray-500')

        with ui.column().classes('w-full gap-4'):
            username_input = ui.input(t['label_user']).bind_value(form_state, 'u') \
                .props('outlined dense').classes('w-full')
            username_input.add_slot('prepend', '<q-icon name="account_circle" />')

            old_password_input = ui.input(t['label_old_pass'], password=True, password_toggle_button=True).bind_value(form_state, 'old') \
                .props('outlined dense').classes('w-full')
            old_password_input.add_slot('prepend', '<q-icon name="vpn_key" />')

            new_pass_input = ui.input(t['label_new_pass'], password=True, password_toggle_button=True).bind_value(form_state, 'new') \
                .props('outlined dense').classes('w-full')
            new_pass_input.add_slot('prepend', '<q-icon name="lock" />')

            ui.button(t['btn_update'], on_click=try_reset_action) \
                .props('unelevated color=pink-600') \
                .classes('w-full mt-2 font-bold shadow-md hover:shadow-lg transition-shadow rounded-lg py-2')

        with ui.row().classes('w-full justify-center mt-6'):
            ui.link(t['link_back'], target='/login') \
                .classes('text-sm text-gray-500 hover:text-pink-600 transition-colors decoration-none')
        
        # Enter shortcut
        new_pass_input.on('keydown.enter', try_reset_action)

# =====================================================
# 3. PÁGINA PRINCIPAL
# =====================================================
@ui.page('/reset')
def reset_password_screen():
    
    ui.add_head_html("""<style>body { background-color: #f8fafc; margin: 0; }</style>""")

    # 1. Estado Local
    form_state = {'u': '', 'old': '', 'new': ''}

    # 2. DEFINIR ESTRUCTURA FIJA (Aquí va el ui.header)
    # El header es fijo, pero su CONTENIDO es dinámico (refreshable)
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm sticky top-0 z-50'):
        # Llamamos al CONTENIDO refrescable, no al header entero
        render_header_content(on_lang_change=lambda: render_reset_form.refresh())

    # 3. Cuerpo
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        render_reset_form(form_state)