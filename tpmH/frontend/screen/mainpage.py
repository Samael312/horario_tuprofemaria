import os
from pathlib import Path
from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256

# =====================================================
# CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS
# =====================================================
current_dir = Path(__file__).parent.resolve()
project_root = current_dir.parent.parent
static_dir = project_root / 'components'

if static_dir.exists():
    app.add_static_files('/static', str(static_dir))
else:
    print(f"⚠️ ERROR: No se encuentra la carpeta {static_dir}")

unrestricted_page_routes = {'/login', '/signup', '/reset', '/MainPage'}

# =====================================================
# MIDDLEWARE DE AUTENTICACIÓN
# =====================================================
class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path == '/':
                return RedirectResponse('/MainPage')
            # Permitimos /static explícitamente para que carguen las imágenes
            if (not request.url.path.startswith('/_nicegui') 
                and not request.url.path.startswith('/static') 
                and not request.url.path.startswith('/uploads')
                and request.url.path not in unrestricted_page_routes):
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        return await call_next(request)

# =====================================================
# DICCIONARIO DE TRADUCCIONES
# =====================================================
TRANSLATIONS = {
    'es': {
        'nav_about': 'Sobre mí', 'nav_video': 'Video', 'nav_plans': 'Planes', 'nav_contact': 'Contacto',
        'btn_login': 'Iniciar Sesión', 'btn_signup': 'Registrarse',
        'badge': '✨ Bilingüe Español • Inglés',
        'hero_title': 'Desbloquea tu Potencial con Nuevos Idiomas',
        'hero_subtitle': 'Únete a mí en un viaje de exploración cultural y dominio lingüístico. Planes personalizados para cada nivel.',
        'btn_start': 'Empieza Ahora', 'btn_view_plans': 'Ver Planes',
        'video_tag': 'Mi Método de Enseñanza', 'video_title': 'Conóceme', 'video_desc': 'Una pequeña introducción a mi dinámica y herramientas.',
        'about_tag': 'Sobre Mí', 'about_title': '¡Hola! Soy María.',
        'about_desc': 'Una entusiasta del inglés y **profesora apasionada** de Venezuela. Además de ser bilingüe en **Inglés**, tengo una base sólida en **Francés** e **Italiano**.\n\nAmo aprender idiomas, leer y explorar nuevas culturas. **Enseñar es mi vocación**.',
        'stat_lang': 'Idiomas', 'stat_passion': 'Pasión', 'stat_online': 'Clases Online',
        'card_certified': 'Profesora Certificada', 'card_multi': 'Múltiples Idiomas',
        'plans_tag': 'Planes y Precios', 'plans_title': 'Invierte en tu Futuro', 'plans_subtitle': 'Elige el plan que se adapte a tu ritmo de aprendizaje.',
        'btn_choose': 'Elegir Plan', 'most_popular': 'MÁS POPULAR',
        'footer_open': 'Ver Enlaces y Contacto', 'footer_rights': 'Todos los derechos reservados.',
        'footer_desc': 'Empoderando estudiantes alrededor del mundo a través del aprendizaje de idiomas.',
        'footer_nav': 'Navegación', 'footer_lang': 'Idioma', 'footer_contact': 'Contacto', 'footer_home': 'Inicio'
    },
    'en': {
        'nav_about': 'About me', 'nav_video': 'Video', 'nav_plans': 'Plans', 'nav_contact': 'Contact',
        'btn_login': 'Log In', 'btn_signup': 'Sign Up',
        'badge': '✨ Bilingual Spanish • English',
        'hero_title': 'Unlock Your Potential with New Languages',
        'hero_subtitle': 'Join me in a journey of cultural exploration and linguistic mastery. Customized plans for every level.',
        'btn_start': 'Start Learning Now', 'btn_view_plans': 'View Plans',
        'video_tag': 'My Teaching Method', 'video_title': 'Getting to know me', 'video_desc': 'A brief introduction to my dynamics and tools.',
        'about_tag': 'About Me', 'about_title': 'Hello! I\'m María.',
        'about_desc': 'An English enthusiast and **passionate teacher** from Venezuela. Besides being bilingual in **English**, I also have a solid foundation in **French** and **Italian**.\n\nI love learning languages, reading, and exploring new cultures. **Teaching is my calling**.',
        'stat_lang': 'Languages', 'stat_passion': 'Passion', 'stat_online': 'Classes',
        'card_certified': 'Certified Teacher', 'card_multi': 'Multiple Languages',
        'plans_tag': 'Plans & Pricing', 'plans_title': 'Invest in Your Future', 'plans_subtitle': 'Choose the plan that fits your learning pace.',
        'btn_choose': 'Choose Plan', 'most_popular': 'MOST POPULAR',
        'footer_open': 'View Links & Contact', 'footer_rights': 'All rights reserved.',
        'footer_desc': 'Empowering students worldwide through language learning.',
        'footer_nav': 'Navigation', 'footer_lang': 'Language', 'footer_contact': 'Contact', 'footer_home': 'Home'
    }
}

def get_plans(lang):
    """Devuelve la lista de planes traducida según el idioma seleccionado."""
    is_es = lang == 'es'
    return [
        {
            'name': 'Básico' if is_es else 'Basic', 'price': '$45', 'period': '/mes' if is_es else '/mo',
            'features': ['4 Clases al mes' if is_es else '4 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode', 'Material incluido' if is_es else 'Material included', 'Clases Conversacionales' if is_es else 'Conversational Classes','Ideal para practicar sin presión' if is_es else 'Ideal for low-pressure practice'],
            'color': 'slate', 'recommended': False
        },
        {
            'name': 'Personalizado' if is_es else 'Customized', 'price': '$80', 'period': '/mes' if is_es else '/mo',
            'features': ['8 Clases al mes' if is_es else '8 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode','Clases Conversacionales' if is_es else 'Conversational Classes' ,'Clases 100% Personalizadas' if is_es else '100% Personalized Classes', 'Equilibrio progreso/flexibilidad' if is_es else 'Balance progress/flexibility'],
            'color': 'rose', 'recommended': True
        },
        {
            'name': 'Intensivo' if is_es else 'Intensive', 'price': '$115', 'period': '/mes' if is_es else '/mo',
            'features': ['12 Clases al mes' if is_es else '12 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode','Clases Conversacionales' if is_es else 'Conversational Classes' ,'Preparación exámenes/viajes' if is_es else 'Exam/Travel preparation', 'Avance rápido' if is_es else 'Fast progress'],
            'color': 'purple', 'recommended': False
        },
        {
            'name': 'Flexible' if is_es else 'Flexible', 'price': '$10', 'period': '/clase' if is_es else '/class',
            'features': ['Paga por clase individual' if is_es else 'Pay per individual class', 'Modalidad Online' if is_es else 'Online Mode', 'Clases Conversacionales' if is_es else 'Conversational Classes','Horario flexible' if is_es else 'Flexible schedule', 'Sin compromisos mensuales' if is_es else 'No monthly commitment'],
            'color': 'blue', 'recommended': False
        }
    ]

@ui.page('/MainPage')
def render_landing_page():
    
    # --- CSS ---
    ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            body { font-family: 'Inter', sans-serif; background-color: #F8FAFC; margin: 0; padding: 0; overflow-x: hidden; }
            .nicegui-content { padding: 0 !important; margin: 0 !important; max-width: 100% !important; width: 100% !important; }
            @keyframes fadeInUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
            .animate-enter { animation: fadeInUp 0.8s ease-out forwards; opacity: 0; }
            .delay-100 { animation-delay: 0.1s; } .delay-200 { animation-delay: 0.2s; } .delay-300 { animation-delay: 0.3s; }
            .glass { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border-bottom: 1px solid rgba(200, 200, 200, 0.2); }
            .remove-default-expansion-style .q-expansion-item__container { border: none !important; }
        </style>
    ''')

    # 1. Header Shell
    header_shell = ui.header().classes('glass text-slate-800 p-4 sticky top-0 z-50 transition-all')

    def trigger_lang_change(new_lang):
        app.storage.user['lang'] = new_lang
        render_header_content.refresh()
        render_body_content.refresh()

    # 2. HEADER CONTENT
    @ui.refreshable
    def render_header_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]

        with ui.row().classes('w-full max-w-7xl mx-auto justify-between items-center'):
            # Logo del Header
            with ui.row().classes('items-center gap-2'):
                ui.icon('school', size='md', color='rose-600')
                ui.label('Tu Profe María').classes('text-xl font-bold tracking-tight text-slate-800')
            
            # Nav Desktop
            with ui.row().classes('hidden md:flex items-center gap-6'):
                ui.link(t['nav_about'], '#about').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
                ui.link(t['nav_video'], '#video').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
                ui.link(t['nav_plans'], '#plans').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
            
            # Acciones + Selector
            with ui.row().classes('items-center gap-3'):
                current_flag = '/static/icon/espana.png' if lang == 'es' else '/static/icon/usa.png'
                logo_img = '/static/icon/logo.png'
                #with ui.button(icon='expand_more').props('flat round dense color=slate-700'):
                #    ui.image(current_flag).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
                #     with ui.menu().classes('bg-white shadow-lg rounded-xl'):
                #        with ui.menu_item(on_click=lambda: trigger_lang_change('es')).classes('gap-2'):
                #            ui.image('/static/icon/espana.png').classes('w-6 h-6')
                #            ui.label('Español').classes('text-slate-700')
                #        with ui.menu_item(on_click=lambda: trigger_lang_change('en')).classes('gap-2'):
                #            ui.image('/static/icon/usa.png').classes('w-6 h-6')
                #            ui.label('English').classes('text-slate-700')

                ui.button(t['btn_login'], on_click=lambda: ui.navigate.to('/login')) \
                    .props('flat text-color=slate-700').classes('font-bold text-sm')
                ui.button(t['btn_signup'], on_click=lambda: ui.navigate.to('/signup')) \
                    .props('unelevated color=rose-600 text-color=white') \
                    .classes('rounded-full px-6 font-bold shadow-md hover:bg-rose-700 text-sm')
                ui.image(logo_img).classes('w-10 h-10 rounded-full border-2 border-rose-600 shadow-md')

    # 3. BODY CONTENT
    @ui.refreshable
    def render_body_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]
        current_plans = get_plans(lang)

        # --- HERO ---
        with ui.element('section').classes('w-full min-h-[85vh] flex items-center justify-center bg-gradient-to-br from-slate-50 via-rose-50 to-white relative overflow-hidden'):
            ui.element('div').classes('absolute top-20 left-10 w-64 h-64 bg-rose-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse')
            ui.element('div').classes('absolute bottom-10 right-10 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse delay-100')
            with ui.column().classes('max-w-4xl mx-auto text-center px-4 z-10 gap-6'):
                with ui.row().classes('mx-auto bg-white border border-rose-100 rounded-full px-4 py-1 shadow-sm animate-enter'):
                    ui.label(t['badge']).classes('text-xs font-bold text-rose-600 uppercase tracking-widest')
                ui.label(t['hero_title']).classes('text-5xl md:text-7xl font-extrabold text-slate-900 leading-tight animate-enter delay-100')
                ui.label(t['hero_subtitle']).classes('text-lg md:text-xl text-slate-500 max-w-2xl mx-auto animate-enter delay-200')
                with ui.row().classes('mx-auto gap-4 mt-4 animate-enter delay-300'):
                    ui.button(t['btn_start'], icon='rocket_launch', on_click=lambda: ui.navigate.to('/signup')).props('unelevated color=slate-900 text-color=white size=lg').classes('rounded-xl shadow-xl hover:scale-105 transition-transform font-bold px-8')
                    ui.button(t['btn_view_plans'], icon='visibility', on_click=lambda: ui.run_javascript("document.getElementById('plans').scrollIntoView({behavior: 'smooth'})")).props('outline color=slate-900 size=lg').classes('rounded-xl hover:bg-slate-50 transition-colors font-bold px-8')

        # --- VIDEO ---
        with ui.element('section').classes('w-full py-24 bg-slate-900 text-white relative overflow-hidden') as video_sec:
            video_sec.props('id=video')
            ui.element('div').classes('absolute top-0 left-0 w-full h-full bg-[url("https://www.transparenttextures.com/patterns/cubes.png")] opacity-10')
            with ui.column().classes('max-w-5xl mx-auto px-6 w-full items-center gap-12 z-10'):
                with ui.column().classes('text-center gap-4'):
                    ui.label(t['video_tag']).classes('text-rose-400 font-bold tracking-widest uppercase text-sm')
                    ui.label(t['video_title']).classes('text-4xl md:text-5xl font-bold')
                    ui.label(t['video_desc']).classes('text-slate-400 text-lg')
                with ui.element('div').classes('w-full aspect-video bg-black rounded-2xl shadow-2xl border border-slate-700 overflow-hidden relative group'):
                    ui.video('/static/resources/Presentacion%20preply%20chu.mp4').classes('w-full h-full object-cover')

        # --- ABOUT (CON LOGO FLOTANTE CORREGIDO) ---
        with ui.element('section').classes('w-full py-24 bg-white') as about_sec:
            about_sec.props('id=about')
            with ui.row().classes('max-w-6xl mx-auto px-6 gap-12 items-center'):
                # FOTO (Izquierda)
                with ui.column().classes('w-full md:w-1/2 relative'):
                    with ui.card().classes('w-full aspect-[4/5] bg-slate-200 rounded-2xl shadow-2xl rotate-3 border-4 border-white relative overflow-hidden'):
                          ui.image('/static/resources/profile.jpg').classes('w-full h-full object-cover')
                    with ui.card().classes('absolute -bottom-6 -right-6 bg-white p-4 rounded-xl shadow-xl border border-slate-50 animate-bounce duration-[3000ms]'):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes('p-3 bg-green-100 rounded-full'): ui.icon('verified', color='green-600')
                            with ui.column().classes('gap-0'): ui.label(t['card_certified']).classes('text-sm font-bold text-slate-800'); ui.label(t['card_multi']).classes('text-xs text-slate-500')
                
                # TEXTO + LOGO (Derecha)
                # 'relative' es clave aquí para que el logo absoluto se posicione respecto a esta columna
                with ui.column().classes('w-full md:w-1/2 gap-6 relative min-h-[400px] justify-center'):
                    ui.label(t['about_tag']).classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                    ui.label(t['about_title']).classes('text-4xl font-bold text-slate-900')
                    ui.markdown(t['about_desc']).classes('text-lg text-slate-600 leading-relaxed space-y-4 z-10') # z-10 para que el texto esté sobre el logo si se solapan
                    
                    with ui.row().classes('gap-8 mt-4 z-10'):
                        with ui.column(): ui.label('2+').classes('text-3xl font-bold text-slate-900'); ui.label(t['stat_lang']).classes('text-sm text-slate-500 uppercase')
                        with ui.column(): ui.label('100%').classes('text-3xl font-bold text-slate-900'); ui.label(t['stat_passion']).classes('text-sm text-slate-500 uppercase')
                        with ui.column(): ui.label('Online').classes('text-3xl font-bold text-slate-900'); ui.label(t['stat_online']).classes('text-sm text-slate-500 uppercase')
    

        # --- PLANS ---
        with ui.element('section').classes('w-full py-24 bg-slate-50') as plans_sec:
            plans_sec.props('id=plans')
            with ui.column().classes('max-w-7xl mx-auto px-6 w-full'):
                with ui.column().classes('w-full text-center mb-16 gap-4'):
                    ui.label(t['plans_tag']).classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                    ui.label(t['plans_title']).classes('text-4xl font-bold text-slate-900')
                    ui.label(t['plans_subtitle']).classes('text-slate-500 text-lg')
                
                with ui.grid().classes('grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 w-full'):
                    for plan in current_plans:
                        is_rec = plan['recommended']
                        scale_class = 'scale-105 shadow-2xl border-rose-200 ring-2 ring-rose-500 ring-offset-2 z-10' if is_rec else 'hover:scale-105 shadow-lg border-slate-100 hover:shadow-xl'
                        btn_style = f'bg-{plan["color"]}-600 text-white hover:bg-{plan["color"]}-700' if is_rec else 'bg-slate-100 text-slate-800 hover:bg-slate-200'
                        with ui.card().classes(f'w-full p-6 rounded-2xl border transition-all duration-300 flex flex-col gap-4 bg-white {scale_class}'):
                            with ui.column().classes('gap-2'):
                                if is_rec: ui.label(t['most_popular']).classes('self-start bg-rose-100 text-rose-700 text-[10px] font-bold px-2 py-1 rounded-full mb-2')
                                ui.label(plan['name']).classes(f'text-lg font-bold text-{plan["color"]}-600')
                                with ui.row().classes('items-baseline'): 
                                    ui.label(plan['price']).classes('text-3xl font-extrabold text-slate-900')
                                    ui.label(plan['period']).classes('text-slate-500 text-sm font-medium')
                            ui.separator().classes('bg-slate-100')
                            with ui.column().classes('gap-2 flex-grow'):
                                for feature in plan['features']:
                                    with ui.row().classes('items-start gap-2'): 
                                        ui.icon('check_circle', color=f'{plan["color"]}-500', size='xs').classes('mt-1')
                                        ui.label(feature).classes('text-slate-600 text-xs leading-tight')
                            ui.button(t['btn_choose']).props('unelevated').classes(f'w-full rounded-xl font-bold py-2 text-sm transition-colors {btn_style}')

        # --- FOOTER ---
        with ui.element('footer').classes('w-full bg-slate-900 text-white mt-auto transition-all duration-300'):
            with ui.expansion(text='').classes('w-full text-white bg-slate-900 remove-default-expansion-style group') as footer_expansion:
                with footer_expansion.add_slot('header'):
                    with ui.row().classes('w-full justify-between items-center py-2 px-4'):
                        with ui.row().classes('items-center gap-2'):
                             ui.icon('school', color='rose-400')
                             ui.label(f'© 2025 Tu Profe María. {t["footer_rights"]}').classes('text-sm text-slate-400')
                        with ui.row().classes('items-center gap-2 opacity-70 group-hover:opacity-100 transition-opacity'):
                            ui.label(t['footer_open']).classes('text-xs font-bold uppercase tracking-wider')
                
                ui.separator().classes('bg-slate-800 mb-6')
                with ui.column().classes('max-w-6xl mx-auto w-full px-6 pb-12'):
                    with ui.row().classes('w-full justify-between items-start flex-wrap gap-8'):
                        with ui.column().classes('max-w-xs gap-4'):
                            ui.label('Tu Profe María').classes('text-2xl font-bold text-white'); ui.label(t['footer_desc']).classes('text-slate-400 text-sm')
                        with ui.column().classes('gap-2'):
                            ui.label(t['footer_nav']).classes('font-bold text-slate-200 mb-2')
                            ui.link(t['footer_home'], '#').classes('text-slate-400 hover:text-white no-underline text-sm')
                            ui.link(t['nav_plans'], '#plans').classes('text-slate-400 hover:text-white no-underline text-sm')
                            
                            ui.separator().classes('bg-slate-700 my-2 w-16')
                            ui.label(t['footer_lang']).classes('font-bold text-slate-200 text-xs mb-1')
                            
                            current_flag_footer = '/static/icon/espana.png' if lang == 'es' else '/static/icon/usa.png'
                            with ui.button(icon='expand_more').props('flat round dense color=slate-400'):
                                ui.image(current_flag_footer).classes('w-6 h-6 absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2')
                                with ui.menu().classes('bg-slate-800 border border-slate-700'):
                                    with ui.menu_item(on_click=lambda: trigger_lang_change('es')).classes('gap-2 hover:bg-slate-700'):
                                        ui.image('/static/icon/espana.png').classes('w-6 h-6')
                                        ui.label('Español').classes('text-white')
                                    with ui.menu_item(on_click=lambda: trigger_lang_change('en')).classes('gap-2 hover:bg-slate-700'):
                                        ui.image('/static/icon/usa.png').classes('w-6 h-6')
                                        ui.label('English').classes('text-white')

                        with ui.column().classes('gap-2'):
                            ui.label(t['footer_contact']).classes('font-bold text-slate-200 mb-2'); ui.label('tuprofemariaa@gmail.com').classes('text-slate-400 text-sm')
                            # REDES SOCIALES
                            with ui.row().classes('gap-4 mt-2'):
                                with ui.link(target='https://www.linkedin.com/in/maria-farias-2aa87a312/', new_tab=True):
                                    ui.image('/static/icon/linkedin.png').classes('w-8 h-8 cursor-pointer hover:scale-80 transition-transform')
                                with ui.link(target='https://www.tiktok.com/@tuprofemaria?is_from_webapp=1&sender_device=pc', new_tab=True): 
                                    ui.image('/static/icon/tik-tok.png').classes('w-8 h-8 cursor-pointer hover:scale-80 transition-transform')

    # 4. CONSTRUCCIÓN FINAL
    with header_shell:
        render_header_content()
    
    render_body_content()