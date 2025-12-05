from nicegui import ui, app
from components.header import create_main_screen, refreshable_header_content
from frontend.screen.MainScreen.Subpages import old_Student, new_Student 
from typing import Callable


# --- 1. TRADUCCIONES ---
TRANSLATIONS = {
    'es': {
        'welcome': '¡Hola {username}!',
        'prompt': '¿Qué te gustaría hacer hoy?',
        'card1_title': 'Ya soy Estudiante',
        'card1_desc': 'Gestionar clases asignadas, ver historial o renovar paquetes.',
        'card1_btn': 'Ver mis Clases',
        'card2_title': 'Nuevo Estudiante',
        'card2_desc': 'Configurar mi primer horario, definir preferencias y comenzar.',
        'card2_btn': 'Configurar Horario',
        'footer': 'TuProfeMaria App v1.0',
        'access_denied': 'Acceso denegado'
    },
    'en': {
        'welcome': 'Hello {username}!',
        'prompt': 'What would you like to do today?',
        'card1_title': 'Existing Student',
        'card1_desc': 'Manage assigned classes, view history, or renew packages.',
        'card1_btn': 'View My Classes',
        'card2_title': 'New Student',
        'card2_desc': 'Set up my first schedule, define preferences, and get started.',
        'card2_btn': 'Set Up Schedule',
        'footer': 'TuProfeMaria App v1.0',
        'access_denied': 'Access denied'
    }
}


# --- 2. FOOTER REFRESHABLE ---
@ui.refreshable
def footer_content():
    lang = app.storage.user.get('lang', 'es')
    t = TRANSLATIONS[lang]
    ui.label(t['footer']).classes('text-sm text-gray-500')


# --- 3. TRIGGER PARA CAMBIO DE IDIOMA ---
def trigger_lang_change(new_lang: str):
    app.storage.user['lang'] = new_lang

    # Refrescar secciones dinámicas
    refreshable_header_content.refresh()
    main_content.refresh()
    footer_content.refresh()


# --- 4. CONTENIDO CENTRAL REFRESHABLE ---
@ui.refreshable
def main_content():
    lang = app.storage.user.get('lang', 'es')
    t = TRANSLATIONS[lang]
    username = app.storage.user.get('username', 'Estudiante')

    with ui.column().classes('w-full min-h-[calc(100vh-64px)] bg-gray-50 items-center justify-center p-4'):

        # Bienvenida
        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(t['welcome'].format(username=username)).classes(
                'text-4xl md:text-5xl font-black text-gray-800 tracking-tight'
            )
            ui.label(t['prompt']).classes('text-lg text-gray-500 mt-2 font-medium')

        # Tarjetas
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            # Tarjeta 1
            with ui.card().classes(
                'w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl '
                'transition-all duration-300 border-t-4 border-blue-500 rounded-xl cursor-pointer'
            ).on('click', lambda: ui.navigate.to('/oldStudent')):

                with ui.element('div').classes('bg-blue-50 p-4 rounded-full mb-4'):
                    ui.icon('history_edu', size='xl', color='blue-600')

                ui.label(t['card1_title']).classes('text-xl font-bold text-gray-800 mb-2')
                ui.label(t['card1_desc']).classes('text-sm text-gray-500 mb-6 leading-relaxed')

                ui.button(
                    t['card1_btn'], icon='arrow_forward',
                    on_click=lambda: ui.navigate.to('/oldStudent')
                ).props('rounded outline color=blue').classes('w-full hover:bg-blue-50')

            # Tarjeta 2
            with ui.card().classes(
                'w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl '
                'transition-all duration-300 border-t-4 border-pink-500 rounded-xl cursor-pointer'
            ).on('click', lambda: ui.navigate.to('/newStudent')):

                with ui.element('div').classes('bg-pink-50 p-4 rounded-full mb-4'):
                    ui.icon('school', size='xl', color='pink-600')

                ui.label(t['card2_title']).classes('text-xl font-bold text-gray-800 mb-2')
                ui.label(t['card2_desc']).classes('text-sm text-gray-500 mb-6 leading-relaxed')

                ui.button(
                    t['card2_btn'], icon='add',
                    on_click=lambda: ui.navigate.to('/newStudent')
                ).props('rounded unelevated color=pink').classes('w-full hover:bg-pink-700')


# --- 5. PÁGINA PRINCIPAL ---
@ui.page('/mainscreen')
def mainscreen():
    lang = app.storage.user.get('lang', 'es')

    # Seguridad
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    # HEADER CORRECTO
    create_main_screen(page_refresh_callback=main_content.refresh)

    # Contenido dinámico
    main_content()

    # Footer
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        footer_content()
