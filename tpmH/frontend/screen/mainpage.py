from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui
from passlib.hash import pbkdf2_sha256

unrestricted_page_routes = {'/login', '/signup', '/reset', '/MainPage'}

# =====================================================
# MIDDLEWARE DE AUTENTICACIÓN
# =====================================================
class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware para proteger páginas que requieren autenticación."""
    async def dispatch(self, request: Request, call_next):
        if not app.storage.user.get('authenticated', False):
            if request.url.path == '/':
                return RedirectResponse('/MainPage')
            
            if not request.url.path.startswith('/_nicegui') and request.url.path not in unrestricted_page_routes:
                return RedirectResponse(f'/login?redirect_to={request.url.path}')
        
        return await call_next(request)

# --- DATOS DE LA LANDING PAGE ---
PLANS = [
    {
        'name': 'Básico',
        'price': '$50',
        'period': '/mes',
        'features': ['4 Clases al mes', 'Material incluido', 'Acceso a comunidad', 'Feedback semanal'],
        'color': 'slate',
        'recommended': False
    },
    {
        'name': 'Intensivo',
        'price': '$120',
        'period': '/mes',
        'features': ['12 Clases al mes', 'Clases 1 a 1', 'Soporte WhatsApp', 'Preparación exámenes', 'Club de conversación'],
        'color': 'rose',
        'recommended': True
    },
    {
        'name': 'Flexible',
        'price': '$20',
        'period': '/hora',
        'features': ['Paga por clase', 'Horario flexible', 'Sin compromisos', 'Enfoque específico'],
        'color': 'blue',
        'recommended': False
    }
]

@ui.page('/MainPage')
def render_landing_page():
    """Renderiza la página inicial moderna para usuarios no autenticados."""
    
    # --- ESTILOS CSS (CORREGIDO PARA BORDES BLANCOS) ---
    ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            
            /* Reset básico */
            body { 
                font-family: 'Inter', sans-serif; 
                background-color: #F8FAFC; 
                margin: 0 !important; 
                padding: 0 !important;
                overflow-x: hidden; /* Evita scroll horizontal accidental */
            }

            /* --- SOLUCIÓN BORDES BLANCOS --- */
            /* NiceGUI pone padding por defecto en .nicegui-content. Lo quitamos aquí: */
            .nicegui-content {
                padding: 0 !important;
                margin: 0 !important;
                max-width: 100% !important;
                width: 100% !important;
            }

            /* Animaciones */
            @keyframes fadeInUp {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .animate-enter {
                animation: fadeInUp 0.8s ease-out forwards;
                opacity: 0;
            }
            .delay-100 { animation-delay: 0.1s; }
            .delay-200 { animation-delay: 0.2s; }
            .delay-300 { animation-delay: 0.3s; }

            /* Glassmorphism Header */
            .glass {
                background: rgba(255, 255, 255, 0.9);
                backdrop-filter: blur(10px);
                border-bottom: 1px solid rgba(200, 200, 200, 0.2);
            }
            
            /* Fix para el acordeón del footer */
            .remove-default-expansion-style .q-expansion-item__container {
                border: none !important;
            }
        </style>
    ''')

    # --- HEADER / NAVBAR ---
    with ui.header().classes('glass text-slate-800 p-4 sticky top-0 z-50 transition-all'):
        with ui.row().classes('w-full max-w-7xl mx-auto justify-between items-center'):
            # Logo
            with ui.row().classes('items-center gap-2'):
                ui.icon('school', size='md', color='rose-600')
                ui.label('Tu Profe María').classes('text-xl font-bold tracking-tight text-slate-800')
            
            # Nav Desktop
            with ui.row().classes('hidden md:flex items-center gap-6'):
                ui.link('Sobre mí', '#about').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
                ui.link('Video', '#video').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
                ui.link('Planes', '#plans').classes('text-sm font-medium text-slate-600 hover:text-rose-600 no-underline')
            
            # Auth Buttons
            with ui.row().classes('items-center gap-3'):
                ui.button('Log In', on_click=lambda: ui.navigate.to('/login')) \
                    .props('flat text-color=slate-700').classes('font-bold text-sm')
                ui.button('Sign Up', on_click=lambda: ui.navigate.to('/signup')) \
                    .props('unelevated color=rose-600 text-color=white') \
                    .classes('rounded-full px-6 font-bold shadow-md hover:bg-rose-700 text-sm')

    # --- HERO SECTION ---
    with ui.element('section').classes('w-full min-h-[85vh] flex items-center justify-center bg-gradient-to-br from-slate-50 via-rose-50 to-white relative overflow-hidden'):
        ui.element('div').classes('absolute top-20 left-10 w-64 h-64 bg-rose-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse')
        ui.element('div').classes('absolute bottom-10 right-10 w-72 h-72 bg-blue-200 rounded-full mix-blend-multiply filter blur-3xl opacity-30 animate-pulse delay-100')

        with ui.column().classes('max-w-4xl mx-auto text-center px-4 z-10 gap-6'):
            with ui.row().classes('mx-auto bg-white border border-rose-100 rounded-full px-4 py-1 shadow-sm animate-enter'):
                ui.label('✨ Bilingual English • French • Italian').classes('text-xs font-bold text-rose-600 uppercase tracking-widest')
            
            ui.label('Unlock Your Potential with New Languages').classes('text-5xl md:text-7xl font-extrabold text-slate-900 leading-tight animate-enter delay-100')
            ui.label('Join me in a journey of cultural exploration and linguistic mastery. Customized plans for every level.') \
                .classes('text-lg md:text-xl text-slate-500 max-w-2xl mx-auto animate-enter delay-200')
            
            with ui.row().classes('mx-auto gap-4 mt-4 animate-enter delay-300'):
                ui.button('Start Learning Now', icon='rocket_launch') \
                    .props('unelevated color=slate-900 text-color=white size=lg') \
                    .classes('rounded-xl shadow-xl hover:scale-105 transition-transform font-bold px-8')
                ui.button('Watch Video', icon='play_circle', on_click=lambda: ui.run_javascript("document.getElementById('video').scrollIntoView({behavior: 'smooth'})")) \
                    .props('outline color=slate-900 size=lg') \
                    .classes('rounded-xl hover:bg-slate-50 transition-colors font-bold px-8')

    # --- VIDEO SECTION (NUEVA) ---
    with ui.element('section').classes('w-full py-24 bg-slate-900 text-white relative overflow-hidden') as video_sec:
        video_sec.props('id=video')
        
        # Fondo decorativo sutil
        ui.element('div').classes('absolute top-0 left-0 w-full h-full bg-[url("https://www.transparenttextures.com/patterns/cubes.png")] opacity-10')

        with ui.column().classes('max-w-5xl mx-auto px-6 w-full items-center gap-12 z-10'):
            # Textos Video
            with ui.column().classes('text-center gap-4'):
                ui.label('Mi Método de Enseñanza').classes('text-rose-400 font-bold tracking-widest uppercase text-sm')
                ui.label('Mira cómo son las clases').classes('text-4xl md:text-5xl font-bold')
                ui.label('Una pequeña introducción a mi dinámica y herramientas.').classes('text-slate-400 text-lg')

            # Contenedor del Video (Estilo Cine)
            with ui.element('div').classes('w-full aspect-video bg-black rounded-2xl shadow-2xl border border-slate-700 overflow-hidden relative group'):
                
                # OPCIÓN 1: Video local o URL directa (MP4)
                # Reemplaza la URL con tu propio video
                ui.video('https://test-videos.co.uk/vids/bigbuckbunny/mp4/h264/360/Big_Buck_Bunny_360_10s_1MB.mp4') \
                    .classes('w-full h-full object-cover')
                
                # OPCIÓN 2: Si usas YouTube, comenta la línea de arriba y descomenta esta:
                # ui.html('<iframe width="100%" height="100%" src="https://www.youtube.com/embed/TU_VIDEO_ID" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>') \
                #    .classes('w-full h-full')

    # --- ABOUT SECTION ---
    with ui.element('section').classes('w-full py-24 bg-white') as about_sec:
        about_sec.props('id=about')
        with ui.row().classes('max-w-6xl mx-auto px-6 gap-12 items-center'):
            with ui.column().classes('w-full md:w-1/2 relative'):
                with ui.card().classes('w-full aspect-[4/5] bg-slate-200 rounded-2xl shadow-2xl rotate-3 border-4 border-white relative overflow-hidden'):
                      with ui.column().classes('w-full h-full items-center justify-center bg-slate-100'):
                          ui.icon('face_3', size='6xl', color='slate-300')
                          ui.label('María Photo').classes('text-slate-400 font-bold')
                
                with ui.card().classes('absolute -bottom-6 -right-6 bg-white p-4 rounded-xl shadow-xl border border-slate-50 animate-bounce duration-[3000ms]'):
                    with ui.row().classes('items-center gap-3'):
                        with ui.element('div').classes('p-3 bg-green-100 rounded-full'):
                            ui.icon('verified', color='green-600')
                        with ui.column().classes('gap-0'):
                            ui.label('Certified Teacher').classes('text-sm font-bold text-slate-800')
                            ui.label('Multiple Languages').classes('text-xs text-slate-500')

            with ui.column().classes('w-full md:w-1/2 gap-6'):
                ui.label('About Me').classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                ui.label('Hello! I\'m María.').classes('text-4xl font-bold text-slate-900')
                ui.markdown('''
                An English enthusiast and **passionate teacher** from Venezuela. 
                Besides being bilingual in **English**, I also have a solid foundation in **French** and **Italian**, which I'm currently perfecting.
                ''').classes('text-lg text-slate-600 leading-relaxed space-y-4')

    # --- PLANS SECTION ---
    with ui.element('section').classes('w-full py-24 bg-slate-50') as plans_sec:
        plans_sec.props('id=plans')
        with ui.column().classes('max-w-7xl mx-auto px-6 w-full'):
            with ui.column().classes('w-full text-center mb-16 gap-4'):
                ui.label('Planes & Precios').classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                ui.label('Invest in Your Future').classes('text-4xl font-bold text-slate-900')

            with ui.grid().classes('grid-cols-1 md:grid-cols-3 gap-8 w-full'):
                for plan in PLANS:
                    is_rec = plan['recommended']
                    scale_class = 'scale-105 shadow-2xl border-rose-200 ring-2 ring-rose-500 ring-offset-2' if is_rec else 'hover:scale-105 shadow-lg border-slate-100 hover:shadow-xl'
                    bg_class = 'bg-white'
                    
                    with ui.card().classes(f'w-full p-8 rounded-2xl border transition-all duration-300 flex flex-col gap-6 {scale_class} {bg_class}'):
                        with ui.column().classes('gap-2'):
                            if is_rec:
                                ui.label('MOST POPULAR').classes('self-start bg-rose-100 text-rose-700 text-[10px] font-bold px-2 py-1 rounded-full mb-2')
                            ui.label(plan['name']).classes(f'text-xl font-bold text-{plan["color"]}-600')
                            with ui.row().classes('items-baseline'):
                                ui.label(plan['price']).classes('text-4xl font-extrabold text-slate-900')
                                ui.label(plan['period']).classes('text-slate-500 font-medium')
                        
                        ui.separator().classes('bg-slate-100')
                        with ui.column().classes('gap-3 flex-grow'):
                            for feature in plan['features']:
                                with ui.row().classes('items-center gap-3'):
                                    ui.icon('check_circle', color=f'{plan["color"]}-500', size='xs')
                                    ui.label(feature).classes('text-slate-600 text-sm')

                        btn_style = f'bg-{plan["color"]}-600 text-white hover:bg-{plan["color"]}-700' if is_rec else 'bg-slate-100 text-slate-800 hover:bg-slate-200'
                        ui.button('Choose Plan').props('unelevated').classes(f'w-full rounded-xl font-bold py-3 transition-colors {btn_style}')

    # --- FOOTER DESPLEGABLE (CORREGIDO Y SIN BORDES) ---
    with ui.element('footer').classes('w-full bg-slate-900 text-white mt-auto transition-all duration-300'):
        with ui.expansion(text='').classes('w-full text-white bg-slate-900 remove-default-expansion-style group') as footer_expansion:
            with footer_expansion.add_slot('header'):
                with ui.row().classes('w-full justify-between items-center py-2 px-4'):
                    with ui.row().classes('items-center gap-2'):
                         ui.icon('school', color='rose-400')
                         ui.label('© 2024 Tu Profe María').classes('text-sm text-slate-400')
                    with ui.row().classes('items-center gap-2 opacity-70 group-hover:opacity-100 transition-opacity'):
                        ui.label('Ver Enlaces y Contacto').classes('text-xs font-bold uppercase tracking-wider')
            
            ui.separator().classes('bg-slate-800 mb-6')
            with ui.column().classes('max-w-6xl mx-auto w-full px-6 pb-12'):
                with ui.row().classes('w-full justify-between items-start flex-wrap gap-8'):
                    with ui.column().classes('max-w-xs gap-4'):
                        ui.label('Tu Profe María').classes('text-2xl font-bold text-white')
                        ui.label('Empowering students worldwide through language learning.').classes('text-slate-400 text-sm')
                    with ui.column().classes('gap-2'):
                        ui.label('Navegación').classes('font-bold text-slate-200 mb-2')
                        ui.link('Home', '#').classes('text-slate-400 hover:text-white no-underline text-sm')
                        ui.link('Planes', '#plans').classes('text-slate-400 hover:text-white no-underline text-sm')
                    with ui.column().classes('gap-2'):
                        ui.label('Contacto').classes('font-bold text-slate-200 mb-2')
                        ui.label('maria@example.com').classes('text-slate-400 text-sm')