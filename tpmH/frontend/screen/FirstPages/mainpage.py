import os
from pathlib import Path
from typing import Optional
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from nicegui import app, ui
from db.models import TeacherProfile
from db.postgres_db import PostgresSession
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import html
import datetime
from prompts.chatbot import render_floating_chatbot

def log_debug(msg):
    """Ayuda visual para ver los logs claramente en la consola"""
    timestamp = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"🔍 [{timestamp}] DEBUG: {msg}")

client = AsyncOpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

load_dotenv()
# =====================================================
# TRADUCCIONES
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
        'footer_nav': 'Navegación', 'footer_lang': 'Idioma', 'footer_contact': 'Contacto', 'footer_home': 'Inicio',
        'reviews_tag': 'Lo que dicen mis alumnos',
        'reviews_title': 'Historias de Éxito',
        'reviews_subtitle': 'Personas reales, resultados reales.',
        'chipi_tag': 'Asistente IA 24/7',
        'chipi_title': 'Conoce a Chipi',
        'chipi_subtitle': 'Tu compañero de aprendizaje inteligente.',
        'chipi_desc': '¿Tienes dudas sobre los precios? ¿No sabes qué plan elegir? ¿No sabes cómo agendar tus clases? Chipi está entrenado para guiarte, responder preguntas y ayudarte en toda tu travesía. ¡Siempre disponible, sin esperas!',
        'chipi_btn': 'Hablar con Chipi',
        'chipi_demo_1': 'Hola, necesito tu ayuda.',
        'chipi_demo_2': '¡Claro! 🤖 Estoy aquí para ayudarte a encontrar tu plan ideal.',
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
        'footer_nav': 'Navigation', 'footer_lang': 'Language', 'footer_contact': 'Contact', 'footer_home': 'Home',
        'reviews_tag': 'What my students say',
        'reviews_title': 'Success Stories',
        'reviews_subtitle': 'Real people, real results.',
        'chipi_tag': 'AI Assistant 24/7',
        'chipi_title': 'Meet Chipi',
        'chipi_subtitle': 'Your smart learning companion.',
        'chipi_desc': 'Doubts about pricing? Unsure which plan to pick? Chipi is trained to guide you, answer questions, and help you take the first step. Always available, no waiting!',
        'chipi_btn': 'Chat with Chipi',
        'chipi_demo_1': 'Hi, I need help with English.',
        'chipi_demo_2': 'Sure! 🤖 I\'m here to help you find your perfect plan.',
    }
}

def get_plans(lang):
    is_es = lang == 'es'
    # NOTA: Agregamos 'id' para identificar el plan internamente sin importar el idioma
    return [
        {
            'id': 'Básico', 
            'name': 'Básico' if is_es else 'Basic', 'price': '$57', 'period': '/mes' if is_es else '/mo',
            'features': ['4 Clases al mes' if is_es else '4 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode', 'Material incluido' if is_es else 'Material included', 'Conversacionales' if is_es else 'Conversational','Sin presión' if is_es else 'Low-pressure'],
            'color': 'slate', 'recommended': False
        },
        {
            'id': 'Personalizado',
            'name': 'Personalizado' if is_es else 'Customized', 'price': '$96', 'period': '/mes' if is_es else '/mo',
            'features': ['8 Clases al mes' if is_es else '8 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode','Conversacionales' if is_es else 'Conversational' ,'100% Personalizadas' if is_es else '100% Personalized', 'Progreso/flexibilidad' if is_es else 'Progress/flexibility'],
            'color': 'rose', 'recommended': True
        },
        {
            'id': 'Intensivo',
            'name': 'Intensivo' if is_es else 'Intensive', 'price': '$138', 'period': '/mes' if is_es else '/mo',
            'features': ['12 Clases al mes' if is_es else '12 Classes/mo', 'Modalidad Online' if is_es else 'Online Mode','Conversacionales' if is_es else 'Conversational' ,'Prep.Exámenes' if is_es else 'Exam preparation', 'Avance rápido' if is_es else 'Fast progress'],
            'color': 'purple', 'recommended': False
        },
        {
            'id': 'Flexible',
            'name': 'Flexible' if is_es else 'Flexible', 'price': '$12', 'period': '/clase' if is_es else '/class',
            'features': ['Paga individual' if is_es else 'Pay individualy', 'Modalidad Online' if is_es else 'Online Mode', 'Conversacionales' if is_es else 'Conversational','Horario flexible' if is_es else 'Flexible schedule', 'Sin pagos mensuales' if is_es else 'No monthly pay'],
            'color': 'blue', 'recommended': False
        }
    ]

@ui.page('/MainPage')
def render_landing_page():
    
    # --- CSS & JS AVANZADO ---
    ui.add_head_html('''
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
            
            html, body {
                font-family: 'Inter', sans-serif;
                background-color: #FFFFFF;
                margin: 0;
                padding: 0;
                width: 100%;
                overflow-x: hidden !important; 
                scroll-behavior: smooth;
            }
            
            .nicegui-content { 
                padding: 0 !important; 
                margin: 0 !important; 
                max-width: 100% !important; 
                width: 100% !important; 
            }
            
            @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
            .animate-enter { animation: fadeInUp 0.8s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; }
            
            @keyframes float { 
                0% { transform: translateY(0px); } 
                50% { transform: translateY(-10px); } 
                100% { transform: translateY(0px); } 
            }
            .animate-float { animation: float 5s ease-in-out infinite; }

            @keyframes blob {
                0% { transform: translate(0px, 0px) scale(1); }
                33% { transform: translate(30px, -50px) scale(1.1); }
                66% { transform: translate(-20px, 20px) scale(0.9); }
                100% { transform: translate(0px, 0px) scale(1); }
            }
            .blob-motion { animation: blob 10s infinite; }
            
            .scroll-hidden { opacity: 0; transform: translateY(40px); transition: all 1s cubic-bezier(0.16, 1, 0.3, 1); }
            .scroll-visible { opacity: 1; transform: translateY(0); }
            
            .delay-100 { animation-delay: 0.1s; transition-delay: 0.1s; } 
            .delay-200 { animation-delay: 0.2s; transition-delay: 0.2s; } 
            .delay-300 { animation-delay: 0.3s; transition-delay: 0.3s; }
            .delay-500 { animation-delay: 0.5s; transition-delay: 0.5s; }
            
            .glass { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(12px); border-bottom: 1px solid rgba(255, 255, 255, 0.3); }
            .remove-default-expansion-style .q-expansion-item__container { border: none !important; }
                     
            @keyframes scroll {
                0% { transform: translateX(0); }
                100% { transform: translateX(-50%); }
            }
            
            .animate-scroll {
                animation: scroll 40s linear infinite;
            }
            
            /* Pausar animación al pasar el mouse para leer tranquilo */
            .animate-scroll:hover {
                animation-play-state: paused;
            }
            /* Máscara para desvanecer los bordes */
            .mask-fade {
                mask-image: linear-gradient(to right, transparent 0, black 128px, black calc(100% - 128px), transparent 100%);
                -webkit-mask-image: linear-gradient(to right, transparent 0, black 128px, black calc(100% - 128px), transparent 100%);
            
            /* Ocultar barra de scroll pero permitir funcionalidad */
            .hide-scrollbar::-webkit-scrollbar {
                display: none;
            }
            .hide-scrollbar {
                -ms-overflow-style: none;
                scrollbar-width: none;
                cursor: grab; /* Cursor de mano abierta por defecto */
            }
            
            /* Clase que se activa vía JS al hacer click */
            .hide-scrollbar.active {
                cursor: grabbing; /* Cursor de mano cerrada agarrando */
                cursor: -webkit-grabbing;
            }

            /* Evitar selección de texto al arrastrar */
            .no-select {
                user-select: none;
                -webkit-user-select: none;
            }
                     
            /* --- ESTILOS ZONA VIDEO --- */
            
            /* Fondo de rejilla muy sutil sobre el azul */
            .bg-grid-slate {
                background-size: 40px 40px;
                background-image: linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
                                  linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
                mask-image: linear-gradient(to bottom, black 40%, transparent 100%);
            }

            /* Panel de Cristal Oscuro (Dark Glassmorphism) */
            .glass-panel-dark {
                background: rgba(15, 23, 42, 0.6); /* Azul muy oscuro semitransparente */
                backdrop-filter: blur(12px);
                -webkit-backdrop-filter: blur(12px);
                border: 1px solid rgba(255, 255, 255, 0.08); /* Borde muy fino */
                box-shadow: 0 20px 50px -12px rgba(0, 0, 0, 0.7);
            }

            /* Animación suave de brillo (Breathing effect) */
            .animate-glow {
                animation: soft-pulse 4s infinite ease-in-out;
            }
            @keyframes soft-pulse {
                0% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); border-color: rgba(255,255,255,0.1); }
                50% { box-shadow: 0 0 30px -5px rgba(244, 63, 94, 0.15); border-color: rgba(244, 63, 94, 0.3); }
                100% { box-shadow: 0 0 0 0 rgba(244, 63, 94, 0); border-color: rgba(255,255,255,0.1); }
            }

            /* Luces de fondo flotantes */
            .ambient-blob {
                filter: blur(90px);
                opacity: 0.5;
                animation: float-blob 10s infinite alternate cubic-bezier(0.45, 0.05, 0.55, 0.95);
            }
            @keyframes float-blob {
                0% { transform: translate(0, 0) scale(1); }
                100% { transform: translate(30px, -30px) scale(1.1); }
            }
        </style>
        
        <script>
            document.addEventListener('DOMContentLoaded', () => {
                const observerOptions = { threshold: 0.1, rootMargin: "0px 0px -50px 0px" };
                const observer = new IntersectionObserver((entries) => {
                    entries.forEach(entry => {
                        if (entry.isIntersecting) {
                            entry.target.classList.add('scroll-visible');
                            observer.unobserve(entry.target); 
                        }
                    });
                }, observerOptions);
                setTimeout(() => {
                    document.querySelectorAll('.scroll-hidden').forEach(el => observer.observe(el));
                }, 100);
            });
            
        </script>
    ''')

    # FONDO GLOBAL (Solo Gradiente Suave)
    with ui.element('div').classes('fixed inset-0 w-screen h-screen -z-20 overflow-hidden pointer-events-none'):
        ui.element('div').classes('absolute inset-0 bg-gradient-to-br from-slate-50 via-rose-50/30 to-white')

    header_shell = ui.header(elevated=False).classes('glass text-slate-800 p-4 transition-all shadow-sm')

    def trigger_lang_change(new_lang):
        app.storage.user['lang'] = new_lang
        render_header_content.refresh()
        render_body_content.refresh()
        ui.run_javascript("setTimeout(() => { document.querySelectorAll('.scroll-hidden').forEach(el => { el.classList.remove('scroll-visible'); }); }, 50);")

    # --- LÓGICA DE SELECCIÓN DE PLAN ---
    def select_plan(plan_id):
        # 1. Guardar en memoria
        app.storage.user['selected_plan'] = plan_id
        # 2. Notificar sutilmente
        ui.notify(f'Plan seleccionado. Continuemos...', type='positive', position='top')
        # 3. Redirigir al selector de método de pago (paso intermedio antes del signup)
        ui.navigate.to('/method')

    # 2. HEADER CONTENT
    @ui.refreshable
    def render_header_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]

        with ui.row().classes('w-full max-w-7xl mx-auto justify-between items-center'):
            with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/MainPage')):
                ui.icon('school', size='md', color='rose-600')
                ui.label('Tu Profe María').classes('text-xl font-bold tracking-tight text-slate-800')
            
            with ui.row().classes('hidden md:flex items-center gap-8'):
                for key, anchor in [('nav_about', '#about'), ('nav_video', '#video'), ('nav_plans', '#plans')]:
                    ui.link(t[key], anchor).classes('text-sm font-semibold text-slate-600 hover:text-rose-600 transition-colors duration-300 no-underline')
            
            with ui.row().classes('items-center gap-3'):
                logo_img = '/static/icon/logo.png'
                ui.button(t['btn_login'], on_click=lambda: ui.navigate.to('/login')) \
                    .props('flat text-color=slate-700')\
                    .classes('rounded-full px-6 font-bold shadow-lg shadow-gray-200 hover:shadow-gray-300 hover:bg-white-700 hover:-translate-y-0.5 transition-all text-sm')
                ui.button(t['btn_signup'], on_click=lambda: ui.navigate.to('/method')) \
                    .props('unelevated color=rose-600 text-color=white') \
                    .classes('rounded-full px-6 font-bold shadow-lg shadow-rose-200 hover:shadow-rose-300 hover:bg-rose-700 hover:-translate-y-0.5 transition-all text-sm')
                ui.image(logo_img).classes('w-10 h-10 rounded-full border-2 border-rose-600 shadow-md').classes('rounded-full border-4 border-white shadow-2xl overflow-hidden relative ring-1 ring-rose-300 bg-white')

    # 3. BODY CONTENT
    @ui.refreshable
    def render_body_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]
        current_plans = get_plans(lang)

        # --- HERO ---
        with ui.element('section').classes('w-full min-h-[90vh] flex items-center justify-center relative overflow-hidden'):
            
            # BLOBS HERO
            with ui.element('div').classes('absolute inset-0 pointer-events-none'):
                 ui.element('div').classes('absolute top-0 -left-10 w-96 h-96 bg-purple-200/60 rounded-full mix-blend-multiply filter blur-3xl opacity-50 blob-motion')
                 ui.element('div').classes('absolute top-1/4 -right-20 w-[30rem] h-[30rem] bg-yellow-200/60 rounded-full mix-blend-multiply filter blur-3xl opacity-50 blob-motion').style('animation-delay: 2s')
                 ui.element('div').classes('absolute -bottom-32 left-20 w-[35rem] h-[35rem] bg-rose-300/50 rounded-full mix-blend-multiply filter blur-3xl opacity-50 blob-motion').style('animation-delay: 4s')

            # Contenido Hero
            with ui.column().classes('max-w-4xl mx-auto text-center px-4 z-10 gap-8 relative'):
                with ui.row().classes('mx-auto bg-white/80 backdrop-blur-sm border border-rose-100 rounded-full px-4 py-1.5 shadow-sm animate-enter hover:shadow-md transition-shadow cursor-default'):
                    ui.label(t['badge']).classes('text-xs font-bold text-rose-600 uppercase tracking-widest')
                
                ui.label(t['hero_title']).classes('text-5xl md:text-7xl font-extrabold text-slate-900 leading-tight animate-enter delay-100 drop-shadow-sm')
                ui.label(t['hero_subtitle']).classes('text-lg md:text-xl text-slate-500 max-w-2xl mx-auto animate-enter delay-200 leading-relaxed')
                
                with ui.row().classes('mx-auto gap-4 mt-4 animate-enter delay-300'):
                    ui.button(t['btn_start'], icon='rocket_launch', on_click=lambda: ui.navigate.to('/planScreen')).props('unelevated color=slate-900 text-color=white size=lg').classes('rounded-xl shadow-xl hover:shadow-2xl hover:-translate-y-1 transition-all duration-300 font-bold px-8 py-3')
                    ui.button(t['btn_view_plans'], icon='visibility', on_click=lambda: ui.run_javascript("document.getElementById('plans').scrollIntoView({behavior: 'smooth'})")).props('outline color=slate-900 size=lg').classes('rounded-xl border-2 hover:bg-white/50 transition-colors font-bold px-8 py-3')

        # --- VIDEO SECTION (Estilo Dark Moderno) ---
        with ui.element('section').classes('w-full py-32 relative overflow-hidden flex items-center justify-center bg-slate-900') as video_sec:
            video_sec.props('id=video')

            # 1. FONDO AMBIENTAL (Capas estáticas y animadas)
            with ui.element('div').classes('absolute inset-0 pointer-events-none'):
                # Gradiente base azul oscuro
                ui.element('div').classes('absolute inset-0 bg-gradient-to-b from-slate-900 via-slate-900 to-[#0B1120]')
                # Rejilla sutil
                ui.element('div').classes('absolute inset-0 bg-grid-slate')
                
                # Orbes de luz (Cyan y Rosa) - Dan el toque "Tech"
                ui.element('div').classes('absolute top-0 right-0 w-[500px] h-[500px] bg-rose-900/20 rounded-full ambient-blob').style('top: -10%; right: -10%;')
                ui.element('div').classes('absolute bottom-0 left-0 w-[500px] h-[500px] bg-cyan-900/20 rounded-full ambient-blob').style('bottom: -10%; left: -10%; animation-delay: -5s;')

            # 2. CONTENIDO (Centrado y Elegante)
            with ui.row().classes('max-w-7xl mx-auto px-6 w-full items-center justify-between gap-16 relative z-10'):
                
                # --- LADO IZQUIERDO: TEXTO ---
                with ui.column().classes('w-full lg:w-5/12 gap-8 scroll-hidden'):
                    with ui.column().classes('gap-2'):
                        # Etiqueta pequeña
                        ui.label(t['video_tag']).classes('text-rose-400 font-bold tracking-widest uppercase text-xs mb-2')
                        # Título
                        ui.label(t['video_title']).classes('text-4xl md:text-5xl font-bold text-white leading-tight')
                        # Línea decorativa
                        ui.element('div').classes('w-20 h-1 bg-gradient-to-r from-rose-500 to-transparent rounded-full my-2')
                        # Descripción
                        ui.label(t['video_desc']).classes('text-slate-400 text-lg leading-relaxed font-light')

                # --- LADO DERECHO: VIDEO CARD ---
                with ui.column().classes('w-full lg:w-6/12 scroll-hidden').style('transition-delay: 200ms'):
                    # Tarjeta contenedora con efecto Glass Dark y borde brillante suave (animate-glow)
                    with ui.card().classes('w-full glass-panel-dark rounded-2xl p-1.5 animate-glow'):
                        
                        # Barra superior estilo ventana (Mac Dark Mode)
                        with ui.row().classes('w-full px-4 py-3 items-center gap-2 border-b border-white/5 bg-white/5 rounded-t-xl'):
                            with ui.row().classes('gap-2'):
                                ui.element('div').classes('w-3 h-3 rounded-full bg-red-500/80')
                                ui.element('div').classes('w-3 h-3 rounded-full bg-yellow-500/80')
                                ui.element('div').classes('w-3 h-3 rounded-full bg-green-500/80')
                            ui.label('Conoce_a_TuprofeMaria.mp4').classes('ml-auto text-xs text-slate-500 font-mono tracking-wider')

                        # Video Container
                        with ui.element('div').classes('w-full aspect-video bg-black relative overflow-hidden rounded-b-xl'):
                             # El Video
                             ui.video('/static/resources/Presentacion%20preply%20chu.mp4').classes('w-full h-full object-cover')
        
        # --- ABOUT ME ---
        with ui.element('section').classes('w-full py-32 relative bg-white') as about_sec:
            about_sec.props('id=about')
            ui.element('div').classes('absolute right-0 bottom-0 w-1/3 h-full bg-slate-50/50 -skew-x-12 translate-x-20 z-0')

            with ui.row().classes('max-w-6xl mx-auto px-6 gap-y-16 md:gap-x-24 items-center relative z-10'):
                # FOTO
                with ui.column().classes('w-full md:w-1/3 relative group scroll-hidden'):
                    with ui.card().classes('w-full aspect-[4/5] bg-slate-200 rounded-3xl shadow-2xl rotate-3 group-hover:rotate-1 transition-transform duration-700 ease-out border-4 border-white relative overflow-hidden'):
                          ui.image('/static/resources/profile.jpg').classes('w-full h-full object-cover scale-100 group-hover:scale-110 transition-transform duration-700')
                    
                    with ui.card().classes('absolute -bottom-8 -right-8 bg-white/95 backdrop-blur-sm p-4 rounded-2xl shadow-xl border border-slate-100 animate-float'):
                        with ui.row().classes('items-center gap-4'):
                            with ui.element('div').classes('p-3 bg-green-100 rounded-full'): 
                                ui.icon('verified', color='green-600', size='sm')
                            with ui.column().classes('gap-0'): 
                                ui.label(t['card_certified']).classes('text-sm font-bold text-slate-800')
                                ui.label(t['card_multi']).classes('text-xs text-slate-500')
                
                # TEXTO
                with ui.column().classes('w-full md:w-1/2 gap-8 relative justify-center scroll-hidden delay-200'):
                    with ui.column().classes('gap-4'):
                        ui.label(t['about_tag']).classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                        ui.label(t['about_title']).classes('text-5xl font-bold text-slate-900 leading-tight')
                        ui.markdown(t['about_desc']).classes('text-lg text-slate-600 leading-relaxed space-y-4')
                    ui.separator().classes('bg-slate-100')
                    with ui.row().classes('gap-12 mt-2'):
                        with ui.column().classes('scroll-hidden delay-300'): 
                            ui.label('2+').classes('text-4xl font-extrabold text-slate-900')
                            ui.label(t['stat_lang']).classes('text-sm font-bold text-slate-400 uppercase tracking-wider')
                        with ui.column().classes('scroll-hidden delay-500'): 
                            ui.label('100%').classes('text-4xl font-extrabold text-slate-900')
                            ui.label(t['stat_passion']).classes('text-sm font-bold text-slate-400 uppercase tracking-wider')
                        with ui.column().classes('scroll-hidden delay-500'):
                            ui.label('Online').classes('text-4xl font-extrabold text-slate-900')
                            ui.label(t['stat_online']).classes('text-sm font-bold text-slate-400 uppercase tracking-wider')

        # --- SECCIÓN CHIPI AI (NUEVA) ---
        with ui.element('section').classes('w-full py-32 relative bg-white') as chipi_sec:
            # Fondo decorativo tecnológico sutil
            with ui.element('div').classes('absolute inset-0 pointer-events-none'):
                # Círculo gradiente animado
                ui.element('div').classes('absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[40rem] h-[40rem] bg-gradient-to-tr from-white-200/40 to-rose-200/40 rounded-full mix-blend-multiply filter blur-3xl opacity-60 blob-motion')
                # Grid pattern muy sutil
                ui.element('div').classes('absolute inset-0 bg-[url("https://www.transparenttextures.com/patterns/graphy.png")] opacity-[0.03]')

            with ui.row().classes('max-w-6xl mx-auto px-6 items-center gap-16 md:gap-24 relative z-10'):
                logo_img = '/static/icon/logo.png'
                # COLUMNA IZQUIERDA: VISUAL (El Robot y el Chat Demo)
                with ui.column().classes('w-full md:w-1/2 items-center justify-center relative'):
                    
                    # 1. El Aura/Contenedor del Robot
                    with ui.element('div').classes('relative w-64 h-64 md:w-80 md:h-80 flex items-center justify-center border-4 border-white ring-1 ring-rose-300 bg-white/50 rounded-full shadow-2xl shadow-rose-200/30 mx-auto'):
                        # Círculos concéntricos animados (Efecto Radar)
                        ui.element('div').classes('absolute inset-0 border border-rose-200 rounded-full animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite] opacity-80')
                        ui.element('div').classes('absolute inset-4 border border-rose-300 rounded-full animate-[ping_3s_cubic-bezier(0,0,0.2,1)_infinite] opacity-80 delay-300')
                        
                        # Avatar Central Flotando
                        with ui.element('div').classes('w-48 h-48 md:w-56 md:h-56 bg-white rounded-full border-4 border-rose-300 shadow-2xl shadow-rose-200/50 flex items-center justify-center z-10 animate-float glow-effect'):
                            ui.image(logo_img).classes('w-40 h-40 md:w-48 md:h-48 object-contain transform hover:scale-110 transition-transform duration-500 ')
                            
                        # Badge "Online"
                        with ui.element('div').classes('absolute bottom-6 right-6 bg-green-500 border-4 border-white w-6 h-6 rounded-full z-20 shadow-md animate-bounce'):
                            pass

                    # 2. Burbujas de Chat "Demo" Flotantes (Decorativas)
                    # Burbuja Usuario
                    with ui.element('div').classes('absolute -top-4 -right-4 md:right-0 bg-white p-3 rounded-2xl rounded-tr-none shadow-lg border border-slate-100 max-w-[180px] chat-entry') as b1:
                        b1.style('animation-delay: 1s')
                        ui.label(t['chipi_demo_1']).classes('text-xs text-slate-600 font-medium')
                    
                    # Burbuja Chipi
                    with ui.element('div').classes('absolute -bottom-8 -left-4 md:left-0 bg-slate-900 border-4 border-white p-4 rounded-2xl rounded-bl-none shadow-xl max-w-[220px] chat-entry flex gap-3 items-center') as b2:
                        b2.style('animation-delay: 1.0s')
                        with ui.avatar(color='white').props('size=sm'):
                            ui.image(logo_img).classes('object-contain p-0.5 rounded-full border-2 border-white shadow-2xl overflow-hidden relative ring-1 ring-rose-300 bg-white')
                        with ui.column().classes('gap-1'):
                            ui.label('Chipi AI').classes('text-[10px] text-rose-400 font-bold uppercase')
                            ui.label(t['chipi_demo_2']).classes('text-xs text-white leading-tight')

                # COLUMNA DERECHA: TEXTO Y CTA
                with ui.column().classes('w-full md:w-1/3 text-center md:text-left gap-6 scroll-hidden'):
                    ui.label(t['chipi_tag']).classes('text-rose-600 font-bold tracking-widest uppercase text-sm self-center md:self-start bg-rose-50 px-3 py-1 rounded-full')
                    
                    with ui.column().classes('gap-2'):
                        ui.label(t['chipi_title']).classes('text-4xl md:text-5xl font-extrabold text-slate-900')
                        ui.label(t['chipi_subtitle']).classes('text-xl text-rose-500 font-medium')
                    
                    ui.label(t['chipi_desc']).classes('text-slate-600 text-lg leading-relaxed')

                    # Botón Mágico que abre el chat existente
                    # NOTA: Usamos JS para hacer click en el botón flotante que ya tienes
                    # Asumimos que el botón flotante tiene la clase 'fixed' y 'bottom-6' como en tu código original.
                    ui.button(t['chipi_btn'], icon='chat_bubble', 
                            on_click=lambda: ui.run_javascript('''
                                const chatBtn = document.querySelector('.fixed.bottom-6.right-6'); 
                                if(chatBtn) {
                                    chatBtn.click();
                                    // Efecto de foco visual
                                    chatBtn.classList.add('ring-4', 'ring-rose-300');
                                    setTimeout(() => chatBtn.classList.remove('ring-4', 'ring-rose-300'), 1000);
                                }
                            ''')) \
                        .props('unelevated color=slate-900 text-color=white size=lg') \
                        .classes('rounded-full px-8 py-3 shadow-xl shadow-rose-900/10 hover:shadow-2xl hover:scale-105 transition-all duration-300 font-bold mt-4 self-center md:self-start')

       # --- REVIEWS / TESTIMONIOS (DESDE BD) ---
        with ui.element('section').classes('w-full py-32 relative bg-white') as reviews_sec:
            
            # 1. OBTENER DATOS DE LA BD
            reviews_list = []
            
            try:
                # Usamos el gestor de contexto de la sesión (ajusta SessionLocal a tu configuración)
                with PostgresSession()as session:
                    # OPCIÓN A: Si quieres las reviews de un profesor específico (Recomendado para Landing Page personal)
                    # teacher = session.query(TeacherProfile).filter(TeacherProfile.username == 'tu_usuario_maria').first()
                    # if teacher and teacher.reviews:
                    #     reviews_list = teacher.reviews

                    # OPCIÓN B: (La que pediste) Traer TODAS las reviews de TODOS los perfiles encontrados
                    profiles = session.query(TeacherProfile).all()
                    
                    for profile in profiles:
                        # Verificamos que el campo no sea None y sea una lista
                        if profile.reviews and isinstance(profile.reviews, list):
                            reviews_list.extend(profile.reviews)
                            
            except Exception as e:
                print(f"Error conectando a la BD o extrayendo reviews: {e}")
                # No hacemos nada más aquí, dejaremos que el bloque 'if not reviews_list' ponga los datos de ejemplo si falló

            # 2. LOGICA DE DESPLAZAMIENTO INFINITO
            # --- REVIEWS / TESTIMONIOS (CORREGIDO) ---
            with ui.element('section').classes('w-full py-20 bg-slate-50 overflow-hidden relative border-y border-slate-200'):
                
                # 1. OBTENER DATOS DE LA BD
                reviews_list = []
                try:
                    with PostgresSession() as session:
                        profiles = session.query(TeacherProfile).all()
                        for profile in profiles:
                            if profile.reviews and isinstance(profile.reviews, list):
                                reviews_list.extend(profile.reviews)
                except Exception as e:
                    print(f"Error conectando a la BD o extrayendo reviews: {e}")

                # 2. LOGICA DE DUPLICADO PARA SCROLL INFINITO
                # Duplicamos varias veces para asegurar que haya suficiente contenido para el scroll
                if not reviews_list:
                    reviews_list = [{'name': 'Maria', 'comment': 'Excellent teacher!', 'rating': 5}]
                
                # Multiplicamos por 20 para tener suficiente contenido para el buffer
                # Esto crea: [A, B, C, ... A, B, C ...] muchas veces.
                infinite_reviews = reviews_list * 20

                # 3. RENDERIZADO UI
                with ui.column().classes('max-w-7xl mx-auto px-6 mb-12 text-center z-10 relative'):
                    ui.label(t.get('reviews_tag', 'Reviews')).classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                    ui.label(t.get('reviews_title', 'Historias de Éxito')).classes('text-4xl font-bold text-slate-900')
                    ui.label(t.get('reviews_subtitle', 'Personas reales, resultados reales.')).classes('text-slate-500 text-lg')

                # Contenedor con máscara de desvanecimiento
                with ui.element('div').classes('w-full overflow-hidden mask-fade relative'):
                    
                    # CONTENEDOR DEL SLIDER (Con ID 'reviews-container' y clases corregidas)
                    with ui.row().classes('gap-6 py-4 flex-nowrap overflow-x-auto hide-scrollbar w-full items-stretch no-select') as scroll_container:
                        scroll_container.props('id=reviews-container')
                        
                        for review in infinite_reviews:
                            first_name = review.get('name', '')
                            last_name = review.get('surname', '')
                            full_name = f"{first_name} {last_name}".strip()
                            r_name = full_name if full_name else review.get('username', 'Estudiante')
                            r_text = review.get('comment', 'Sin comentarios.')
                            r_time = review.get('time_zone', '')
                            r_total = review.get('total_classes', "")
                            
                            try:
                                r_stars = int(review.get('rating', 5))
                            except:
                                r_stars = 5
                            r_date = review.get('date', '') 

                            # TARJETA
                            # Usamos pointer-events-none en los hijos para que no interfieran con el arrastre del padre
                            with ui.card().classes('w-[350px] shrink-0 p-6 rounded-2xl bg-white border border-slate-100 shadow-lg shadow-slate-200/50 flex flex-col gap-4 select-none'): 
                                with ui.row().classes('items-center gap-3 w-full'):
                                    initial = (r_name[:2].upper())
                                    with ui.element('div').classes('w-10 h-10 rounded-full bg-rose-50 flex items-center justify-center text-rose-600 font-bold text-sm shadow-sm'):
                                        ui.label(initial)
                                    
                                    with ui.column().classes('gap-0'):
                                        with ui.row().classes('gap-2 items-center'):
                                            ui.label(r_name).classes('font-bold text-slate-800 text-sm')
                                            if r_total:
                                                ui.label(f'{r_total} clases').classes('text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-bold')
                                        if r_date:
                                            ui.label(r_date).classes('text-xs text-slate-400')
                                    
                                    with ui.row().classes('ml-auto gap-0'):
                                        for _ in range(r_stars):
                                            ui.icon('star', color='amber-400', size='xs')

                                ui.icon('format_quote', color='rose-100', size='md').classes('mb-[-15px]')
                                ui.label(r_text).classes('text-slate-600 text-sm italic leading-relaxed line-clamp-4')

                # --- SCRIPT JAVASCRIPT CORREGIDO (SEAMLESS LOOP) ---
                ui.add_body_html('''
                <script>
                    document.addEventListener('DOMContentLoaded', () => {
                        function initReviewsSlider() {
                            const slider = document.getElementById('reviews-container');
                            
                            // Si NiceGUI aún no renderizó el elemento, reintentar.
                            if (!slider) {
                                setTimeout(initReviewsSlider, 50);
                                return;
                            }

                            let isDown = false;
                            let isHovered = false;
                            let startX;
                            let scrollLeft;
                            let animationId;
                            
                            // Velocidad del scroll (ajusta si lo quieres más rápido/lento)
                            const speed = 0.5; 

                            // 1. EVENTOS RATÓN (DRAG)
                            slider.addEventListener('mousedown', (e) => {
                                isDown = true;
                                slider.classList.add('active');
                                startX = e.pageX - slider.offsetLeft;
                                scrollLeft = slider.scrollLeft;
                                cancelAnimationFrame(animationId);
                            });

                            slider.addEventListener('mouseleave', () => {
                                isDown = false;
                                isHovered = false;
                                slider.classList.remove('active');
                                requestAnimationFrame(autoPlay);
                            });

                            slider.addEventListener('mouseup', () => {
                                isDown = false;
                                slider.classList.remove('active');
                            });

                            slider.addEventListener('mousemove', (e) => {
                                if (!isDown) return;
                                e.preventDefault();
                                const x = e.pageX - slider.offsetLeft;
                                const walk = (x - startX) * 2; 
                                slider.scrollLeft = scrollLeft - walk;
                            });

                            // 2. PAUSAR EN HOVER
                            slider.addEventListener('mouseenter', () => {
                                isHovered = true;
                            });

                            // 3. LÓGICA DE LOOP INFINITO PERFECTO
                            function autoPlay() {
                                if (!isDown && !isHovered) {
                                    slider.scrollLeft += speed;
                                }

                                // TRUCO MATEMÁTICO:
                                // Si hemos scrolleado más de la mitad del ancho total del contenido...
                                // Restamos exactamente la mitad.
                                // Al ser la lista un espejo (A+A), saltar de la mitad al inicio es invisible.
                                if (slider.scrollLeft >= (slider.scrollWidth / 2)) {
                                    slider.scrollLeft -= (slider.scrollWidth / 2);
                                } 
                                
                                // Protección para scroll hacia atrás (si el usuario arrastra a la izquierda)
                                if (slider.scrollLeft <= 0) {
                                    slider.scrollLeft += (slider.scrollWidth / 2);
                                }

                                animationId = requestAnimationFrame(autoPlay);
                            }

                            // Iniciar
                            animationId = requestAnimationFrame(autoPlay);
                        }

                        initReviewsSlider();
                    });
                </script>
                ''')
        # --- PLANS ---
        with ui.element('section').classes('w-full py-32 bg-white relative') as plans_sec:
            plans_sec.props('id=plans')
            with ui.column().classes('max-w-7xl mx-auto px-6 w-full relative z-10'):
                with ui.column().classes('w-full text-center mb-20 gap-4 scroll-hidden'):
                    ui.label(t['plans_tag']).classes('text-rose-600 font-bold tracking-widest uppercase text-sm')
                    ui.label(t['plans_title']).classes('text-4xl md:text-5xl font-bold text-slate-900')
                    ui.label(t['plans_subtitle']).classes('text-slate-500 text-lg max-w-2xl mx-auto')
                
                with ui.grid().classes('grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8 w-full'):
                    for i, plan in enumerate(current_plans):
                        is_rec = plan['recommended']
                        rec_classes = 'scale-105 shadow-2xl border-rose-200 ring-2 ring-rose-500 ring-offset-4 ring-offset-slate-50 z-10' if is_rec else 'hover:scale-105 shadow-lg hover:shadow-2xl border-transparent hover:border-slate-200 bg-white'
                        btn_style = f'bg-{plan["color"]}-600 text-white hover:bg-{plan["color"]}-700 shadow-lg shadow-{plan["color"]}-200' if is_rec else 'bg-slate-100 text-slate-800 hover:bg-slate-200'
                        delay_cls = f'transition-delay: {i * 150}ms'
                        
                        with ui.card().classes(f'w-full p-8 rounded-3xl border transition-all duration-500 flex flex-col gap-6 scroll-hidden {rec_classes}').style(delay_cls):
                            with ui.column().classes('gap-3'):
                                if is_rec: 
                                    ui.label(t['most_popular']).classes('self-start bg-rose-100 text-rose-700 text-[10px] font-bold px-3 py-1 rounded-full mb-1')
                                ui.label(plan['name']).classes(f'text-xl font-bold text-{plan["color"]}-600')
                                with ui.row().classes('items-baseline gap-1'): 
                                    ui.label(plan['price']).classes('text-4xl font-extrabold text-slate-900')
                                    ui.label(plan['period']).classes('text-slate-500 text-sm font-medium')
                            ui.separator().classes('bg-slate-100')
                            with ui.column().classes('gap-4 flex-grow'):
                                for feature in plan['features']:
                                    with ui.row().classes('items-start gap-3'): 
                                        ui.icon('check_circle', color=f'{plan["color"]}-500', size='xs').classes('mt-1 shrink-0')
                                        ui.label(feature).classes('text-slate-600 text-sm leading-snug')
                            
                            # === BOTÓN MODIFICADO PARA SELECCIONAR PLAN ===
                            # Usamos una función lambda para pasar el plan['id']
                            ui.button(t['btn_choose'], on_click=lambda p=plan['id']: select_plan(p)).props('unelevated').classes(f'w-full rounded-xl font-bold py-3 text-sm transition-transform active:scale-95 {btn_style}')

        # --- FOOTER ---
        with ui.element('footer').classes('w-full bg-slate-900 text-white mt-auto'):
            with ui.expansion(text='').classes('w-full text-white bg-slate-900 remove-default-expansion-style group') as footer_expansion:
                with footer_expansion.add_slot('header'):
                    with ui.row().classes('w-full justify-between items-center py-4 px-6 hover:bg-slate-800/50 transition-colors rounded-t-xl'):
                        with ui.row().classes('items-center gap-3'):
                             ui.icon('school', color='rose-500', size='sm')
                             ui.label(f'© 2025 Tu Profe María.').classes('text-sm text-slate-400')
                        with ui.row().classes('items-center gap-2 text-rose-400 group-hover:text-rose-300 transition-colors'):
                            ui.label(t['footer_open']).classes('text-xs font-bold uppercase tracking-wider')
                            ui.icon('keyboard_arrow_up').classes('transition-transform duration-300 group-expanded:rotate-180')
                ui.separator().classes('bg-slate-800 mb-8 mx-6 opacity-50')
                with ui.column().classes('max-w-6xl mx-auto w-full px-8 pb-16'):
                    with ui.row().classes('w-full justify-between items-start flex-wrap gap-12'):
                        with ui.column().classes('max-w-xs gap-6'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('school', size='md', color='rose-500')
                                ui.label('Tu Profe María').classes('text-2xl font-bold text-white')
                            ui.label(t['footer_desc']).classes('text-slate-400 text-sm leading-relaxed')
                        with ui.column().classes('gap-4'):
                            ui.label(t['footer_nav']).classes('font-bold text-white mb-2 tracking-wide text-sm uppercase')
                            for lbl, lnk in [(t['footer_home'], '#'), (t['nav_plans'], '#plans')]:
                                ui.link(lbl, lnk).classes('text-slate-400 hover:text-rose-400 transition-colors no-underline text-sm')
                            #ui.label(t['footer_lang']).classes('font-bold text-white text-sm uppercase mt-4 mb-2 tracking-wide')
                            #with ui.button(icon='language', color='slate-800').props('flat dense').classes('text-slate-400 hover:text-white'):
                            #    with ui.menu().classes('bg-slate-800 border border-slate-700'):
                            #        with ui.menu_item(on_click=lambda: trigger_lang_change('es')).classes('gap-3 hover:bg-slate-700'):
                            #            ui.image('/static/icon/espana.png').classes('w-5 h-5')
                            #            ui.label('Español').classes('text-slate-200')
                            #        with ui.menu_item(on_click=lambda: trigger_lang_change('en')).classes('gap-3 hover:bg-slate-700'):
                            #            ui.image('/static/icon/usa.png').classes('w-5 h-5')
                            #            ui.label('English').classes('text-slate-200')
                        with ui.column().classes('gap-4'):
                            ui.label(t['footer_contact']).classes('font-bold text-white mb-2 tracking-wide text-sm uppercase')
                            with ui.row().classes('items-center gap-2 text-slate-400'):
                                ui.icon('mail', size='xs')
                                ui.label('tuprofemariaa@gmail.com').classes('text-sm')
                            with ui.row().classes('gap-4 mt-4'):
                                icon_class = 'w-10 h-10 p-2 bg-slate-800 rounded-full hover:bg-rose-600 hover:scale-110 transition-all cursor-pointer'
                                with ui.link(target='https://www.linkedin.com/in/maria-farias-2aa87a312/', new_tab=True):
                                    ui.image('/static/icon/linkedin.png').classes(icon_class)
                                with ui.link(target='https://www.tiktok.com/@tuprofemaria', new_tab=True): 
                                    ui.image('/static/icon/tik-tok.png').classes(icon_class)

    with header_shell:
        render_header_content()
    
    render_body_content()
    
    # Renderizar el chatbot flotante
    render_floating_chatbot('main')

