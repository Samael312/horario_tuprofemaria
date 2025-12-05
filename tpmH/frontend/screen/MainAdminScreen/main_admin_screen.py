from nicegui import ui, app
from components.headerAdmin import (
    create_admin_screen,
    headerAdmin_language_selector,
    refreshable_admin_header_content
)

TRANSLATIONS = {
    'es': {
        'admin_welcome': 'Bienvenido',
        'admin_panel': 'Panel de Administración',
        'admin_students_title': 'Gestión de Estudiantes',
        'admin_students_desc': 'Ver y administrar la lista de estudiantes registrados.',
        'admin_students_btn': 'Ver Estudiantes',
        'admin_classes_title': 'Mis Clases',
        'admin_classes_desc': 'Ver y administrar las clases asignadas a los estudiantes.',
        'admin_classes_btn': 'Ver Mis Clases',
        'admin_footer': '© 2024 TuProfeMaria - Panel de Administración',
        'access_denied': 'Acceso denegado'
    },
    'en': {
        'admin_welcome': 'Welcome',
        'admin_panel': 'Admin Panel',
        'admin_students_title': 'Student Management',
        'admin_students_desc': 'View and manage the list of registered students.',
        'admin_students_btn': 'View Students',
        'admin_classes_title': 'My Classes',
        'admin_classes_desc': 'View and manage classes assigned to students.',
        'admin_classes_btn': 'View My Classes',
        'admin_footer': '© 2024 TuProfeMaria - Admin Panel',
        'access_denied': 'Access denied'
    }
}


# --- 1. FOOTER REFRESHABLE ---
@ui.refreshable
def footer_content():
    lang = app.storage.user.get('lang', 'es')
    t = TRANSLATIONS[lang]
    ui.label(t['admin_footer']).classes('text-sm text-gray-500')


# --- 2. MANEJO DEL CAMBIO DE IDIOMA ---
def trigger_lang_change(new_lang):
    app.storage.user['lang'] = new_lang

    # Refrescar navegación, contenido y footer
    refreshable_admin_header_content.refresh()
    main_admin_content.refresh()
    footer_content.refresh()


# --- 3. CONTENIDO CENTRAL REFRESHABLE ---
@ui.refreshable
def main_admin_content():
    lang = app.storage.user.get('lang', 'es')
    t = TRANSLATIONS[lang]
    username = app.storage.user.get('username', t['admin_welcome'])

    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):

        # Bienvenida
        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(f"{t['admin_welcome']}, {username}") \
                .classes('text-4xl md:text-5xl font-black text-gray-800 tracking-tight')
            ui.label(t['admin_panel']).classes('text-lg text-gray-500 mt-2 font-medium')

        # Tarjetas
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            # Tarjeta Estudiantes
            with ui.card().classes(
                'w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl '
                'transition-all duration-300 border-t-4 border-green-500 rounded-xl cursor-pointer'
            ).on('click', lambda: ui.navigate.to('/Students')):
                with ui.element('div').classes('bg-green-50 p-4 rounded-full mb-4'):
                    ui.icon('group', size='xl', color='green-600')

                ui.label(t['admin_students_title']).classes('text-xl font-bold text-gray-800 mb-2')
                ui.label(t['admin_students_desc']).classes('text-sm text-gray-500 mb-6 leading-relaxed')

                ui.button(t['admin_students_btn'], icon='arrow_forward',
                          on_click=lambda: ui.navigate.to('/Students')) \
                    .props('rounded outline color=green').classes('w-full hover:bg-green-50')

            # Tarjeta Clases
            with ui.card().classes(
                'w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl '
                'transition-all duration-300 border-t-4 border-purple-500 rounded-xl cursor-pointer'
            ).on('click', lambda: ui.navigate.to('/myclassesAdmin')):
                with ui.element('div').classes('bg-purple-50 p-4 rounded-full mb-4'):
                    ui.icon('class', size='xl', color='purple-600')

                ui.label(t['admin_classes_title']).classes('text-xl font-bold text-gray-800 mb-2')
                ui.label(t['admin_classes_desc']).classes('text-sm text-gray-500 mb-6 leading-relaxed')

                ui.button(t['admin_classes_btn'], icon='arrow_forward',
                          on_click=lambda: ui.navigate.to('/myclassesAdmin')) \
                    .props('rounded outline color=purple').classes('w-full hover:bg-purple-50')


# --- 4. PÁGINA PRINCIPAL DE ADMIN ---
@ui.page('/admin')
def main_admin_screen():
    lang = app.storage.user.get('lang', 'es')
    t = TRANSLATIONS[lang]

    # 1. Seguridad
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    if app.storage.user.get('role') != "admin":
        ui.notify(t['access_denied'], color="negative")
        ui.navigate.to('/mainscreen')
        return

    # 2. HEADER ADMIN (usa su propio refresh y selector)
    create_admin_screen(page_refresh_callback=main_admin_content.refresh)

    # 3. Contenido dinámico
    main_admin_content()

    # 4. Footer dinámico
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        footer_content()
