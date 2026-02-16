from nicegui import ui, app
from fastapi.responses import RedirectResponse
# Asegúrate de que estos imports existan en tu proyecto, si no, coméntalos para probar
from db.postgres_db import PostgresSession
from db.models import User
from prompts.chatbot import render_floating_chatbot

TRANSLATIONS = {
    'es': {
        'plans_tag': 'Planes y Precios', 'plans_title': 'Invierte en tu Futuro', 'plans_subtitle': 'Elige el plan que se adapte a tu ritmo de aprendizaje.',
        'btn_choose': 'Elegir Plan', 'most_popular': 'MÁS POPULAR',
    },
    'en': {
        'plans_tag': 'Plans & Pricing', 'plans_title': 'Invest in Your Future', 'plans_subtitle': 'Choose the plan that fits your learning pace.',
        'btn_choose': 'Choose Plan', 'most_popular': 'MOST POPULAR',
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

def select_plan(plan_id):
        # 1. Guardar en memoria
        app.storage.user['selected_plan'] = plan_id
        # 2. Notificar sutilmente
        ui.notify(f'Plan seleccionado. Continuemos...', type='positive', position='top')
        # 3. Redirigir al selector de método de pago (paso intermedio antes del signup)
        ui.navigate.to('/method')




def create_ui(content_function=None):
    """Crea la interfaz base consistente con el login."""
    ui.dark_mode().set_value(False)

    # HEADER COMPACTO
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

def plan_screen():

    @ui.page('/planScreen')
    def create_plan_screen():
        
        # Renderizamos el marco base
        create_ui()

        def render_plan_screen():
            lang = app.storage.user.get('lang', 'es')
            t = TRANSLATIONS[lang]
            current_plans = get_plans(lang)

            with ui.element('section').classes('w-full py-32 bg-slate-50 relative') as plans_sec:
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
            
        render_plan_screen()
        render_floating_chatbot('planes')

# EJECUCIÓN
if __name__ in {"__main__", "__mp_main__"}:
    plan_screen()
    ui.run(storage_secret='clave_secreta_temporal')