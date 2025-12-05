from nicegui import ui, app
from typing import Callable, Optional
from nicegui import ui, app


# ==============================================================================
# DATOS DE TRADUCCIÓN (Para que el componente sea autocontenido)
# ==============================================================================
HEADER_TRANSLATIONS = {
    'es': {
        'nav_home': 'Inicio', 
        'nav_schedule': 'Horario', 
        'nav_classes': 'Mis Clases',
        'nav_teacher': 'Profesora', 
        'nav_profile': 'Perfil', 
        'tooltip_logout': 'Cerrar Sesión'
    },
    'en': {
        'nav_home': 'Home', 
        'nav_schedule': 'Schedule', 
        'nav_classes': 'My Classes',
        'nav_teacher': 'Teacher', 
        'nav_profile': 'Profile', 
        'tooltip_logout': 'Log Out'
    }
}


@ui.refreshable
def header_language_selector(on_lang_change: Callable):
    current_lang = app.storage.user.get('lang','es')
    current_flag= '/static/icon/espana.png' if current_lang == 'es' else '/static/icon/usa.png'

    # Propiedades para que el botón sea un círculo blanco con sombra
    button_props = 'flat round dense color=white text-color=slate-700 shadow-md'

    with ui.button(icon='expand_more').props(button_props).classes('bg-white'):
        # Bandera actual
        ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
        
        with ui.menu().classes('bg-white shadow-lg rounded-xl'):
            # ES
            with ui.menu_item(on_click=lambda: on_lang_change('es')).classes('gap-2'):
                ui.image('/static/icon/espana.png').classes('w-6 h-6')
                ui.label('Español').classes('text-slate-700')
            
            # EN
            with ui.menu_item(on_click=lambda: on_lang_change('en')).classes('gap-2'):
                ui.image('/static/icon/usa.png').classes('w-6 h-6')
                ui.label('English').classes('text-slate-700')

@ui.refreshable
def refreshable_header_content(on_lang_change: Callable):
    lang = app.storage.user.get('lang', 'es')
    t = HEADER_TRANSLATIONS[lang]

    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

        
    # 1. Logo y Título
    with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/mainscreen')):
        ui.icon('school', size='md', color='white')
        ui.label('TuProfeMaria').classes('text-white text-xl font-bold tracking-wide')

    # Acciones + Selector
    with ui.row().classes('items-center gap-3'):
        
        # Navegación
        with ui.row().classes('gap-1 items-center'):
            def nav_btn(label, route):
                ui.button(label, on_click=lambda: ui.navigate.to(route))\
                    .props('flat color=white')\
                    .classes('text-white font-medium hover:bg-white/20 transition-all duration-300 rounded-lg px-3')

            nav_btn(t['nav_home'], '/mainscreen')
            nav_btn(t['nav_schedule'], '/ScheduleMaker')
            nav_btn(t['nav_classes'], '/myclasses')
            nav_btn(t['nav_teacher'], '/teacher')
            ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')
            nav_btn(t['nav_profile'], '/profile')
        
        # Separador y Logout
        ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')
        
        # Selector de Idioma (Botón con círculo blanco)
        header_language_selector(on_lang_change) 
        
        # Botón de Logout
        ui.button(on_click=logout, icon='logout')\
            .props('outline color=white').tooltip(t['tooltip_logout'])\
            .classes('ml-2 hover:bg-red-500 hover:border-red-500 transition-colors')




def create_main_screen(page_refresh_callback: Optional[Callable] = None):
    """Crea la estructura estática del Header e inserta el contenido dinámico."""

    # Callback para cambio de idioma
    def handle_language_change(new_lang):
        app.storage.user['lang'] = new_lang
        refreshable_header_content.refresh()  # Se refresca a sí mismo

        # Ahora NO es obligatorio
        if callable(page_refresh_callback):
            page_refresh_callback()

    # Header principal
    with ui.header().classes(
        'px-6 py-3 items-center justify-between bg-gradient-to-r '
        'from-pink-600 to-pink-500 shadow-md'
    ):
        refreshable_header_content(handle_language_change)