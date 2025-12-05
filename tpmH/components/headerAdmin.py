from nicegui import ui, app
from typing import Callable, Optional

# ==============================================================================
# DATOS DE TRADUCCIÓN
# ==============================================================================
HEADER_TRANSLATIONS = {
    'es': {
        'nav_home': 'Inicio', 'nav_schedule': 'Horario', 'nav_classes': 'Mis Clases',
        'nav_students': 'Estudiantes', 'nav_public_profile': 'Perfil Público',
        'nav_profile': 'Perfil', 'tooltip_logout': 'Cerrar Sesión'
    },
    'en': {
        'nav_home': 'Home', 'nav_schedule': 'Schedule', 'nav_classes': 'My Classes',
        'nav_students': 'Students', 'nav_public_profile': 'Public Profile',
        'nav_profile': 'Profile', 'tooltip_logout': 'Log Out'
    }
}

# ==============================================================================
# 1. Selector de Idioma (Refrescable)
# ==============================================================================
@ui.refreshable
def headerAdmin_language_selector(on_lang_change: Callable):
    """
    Renderiza el botón de idioma.
    """
    current_lang = app.storage.user.get('lang', 'es')
    current_flag = '/static/icon/espana.png' if current_lang == 'es' else '/static/icon/usa.png'
    
    # Botón blanco circular con sombra
    with ui.button(icon='expand_more').props('flat round dense color=white text-color=slate-700 shadow-sm').classes('bg-white'):
        # Bandera centrada
        ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
        
        with ui.menu().classes('bg-white shadow-lg rounded-xl'):
            # Opción Español
            with ui.menu_item(on_click=lambda: on_lang_change('es')).classes('gap-2 hover:bg-slate-50'):
                ui.image('/static/icon/espana.png').classes('w-6 h-6')
                ui.label('Español').classes('text-slate-700')
            
            # Opción Inglés
            with ui.menu_item(on_click=lambda: on_lang_change('en')).classes('gap-2 hover:bg-slate-50'):
                ui.image('/static/icon/usa.png').classes('w-6 h-6')
                ui.label('English').classes('text-slate-700')

# ==============================================================================
# 2. Contenido Header (Refrescable)
# ==============================================================================
@ui.refreshable
def refreshable_admin_header_content(internal_on_change: Callable):
    """Contiene toda la navegación y el selector."""
    lang = app.storage.user.get('lang', 'es')
    t = HEADER_TRANSLATIONS[lang]

    def logout():
        app.storage.user.clear()
        ui.navigate.to('/login')

    # --- LOGO ---
    with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/admin')):
        ui.icon('school', size='md', color='white')
        ui.label('TuProfeMaria').classes('text-white text-xl font-bold tracking-wide')

    # --- NAVEGACIÓN Y ACCIONES ---
    with ui.row().classes('items-center gap-3'):
        
        # Links de Navegación
       with ui.row().classes('gap-1 items-center flex'):
        def nav_btn(label, route):
            ui.button(label, on_click=lambda: ui.navigate.to(route))\
                .props('flat')\
                .classes('text-white font-medium hover:bg-white/20 transition-all duration-300 rounded-lg px-3')

        nav_btn(t['nav_home'], '/admin')
        nav_btn(t['nav_schedule'], '/Admhorario')
        nav_btn(t['nav_classes'], '/myclassesAdmin')
        nav_btn(t['nav_students'], '/Students')

        ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2')

        nav_btn(t['nav_public_profile'], '/teacher')
        nav_btn(t['nav_profile'], '/adminProfile')
        
        # Separador
        ui.element('div').classes('w-[1px] h-6 bg-pink-300 mx-2 hidden md:block')
        
        # Selector de Idioma
        # Pasamos la función interna que gestiona el cambio
        headerAdmin_language_selector(internal_on_change) 
        
        # Logout
        ui.button(on_click=logout, icon='logout')\
            .props('outline color=white').tooltip(t['tooltip_logout'])\
            .classes('ml-2 hover:bg-red-500 hover:border-red-500 hover:text-white transition-colors')

# ==============================================================================
# 3. Función Principal (Entry Point)
# ==============================================================================
def create_admin_screen(page_refresh_callback: Optional[Callable] = None):
    """
    Crea el Header de Admin.
    
    Args:
        page_refresh_callback: Función que refresca el CONTENIDO de la página padre.
                               (El header se refresca a sí mismo automáticamente).
    """
    
    # Función interna que maneja la lógica:
    # 1. Actualiza Storage Global
    # 2. Refresca el Header (Menús)
    # 3. Llama al callback de la página (Cuerpo)
    def handle_language_change(new_lang):
        app.storage.user['lang'] = new_lang
        refreshable_admin_header_content.refresh() # Se refresca a sí mismo
        if page_refresh_callback:
            page_refresh_callback() # Refresca el resto de la página

    with ui.header().classes('px-6 py-3 items-center justify-between bg-gradient-to-r from-pink-600 to-pink-500 shadow-md'):
        refreshable_admin_header_content(handle_language_change)