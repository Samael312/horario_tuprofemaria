from nicegui import ui
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import os

# 1. CARGAR ENTORNO
load_dotenv()

# 2. CONFIGURACIÓN DE RUTAS (ROBUSTA)
# Obtenemos la ruta absoluta de la carpeta donde está este archivo (chatbot.py)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Construimos la ruta absoluta a la carpeta prompts
PROMPTS_DIR = os.path.join(BASE_DIR, 'prompts')

# 3. CLIENTE OPENAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- LÓGICA DEL BOT (BACKEND) ---

def read_prompt(filename):
    """Lee archivos de la carpeta prompts usando rutas absolutas"""
    try:
        # Usamos PROMPTS_DIR que definimos arriba
        path = os.path.join(PROMPTS_DIR, filename)
        
        # Debug: Imprimir ruta si falla algo (opcional, ayuda a verificar)
        # print(f"Leyendo prompt desde: {path}") 
        
        if not os.path.exists(path): 
            print(f"⚠️ Alerta: No se encontró el archivo {filename} en {path}")
            return ""
            
        with open(path, 'r', encoding='utf-8') as f: 
            return f.read()
    except Exception as e:
        print(f"Error leyendo prompt {filename}: {e}")
        return ""

async def get_bot_response(message):
    """Cerebro del Bot (Solo Español)"""
    
    # 1. Cargar contexto base
    base_prompt = read_prompt('context.txt')
    
    # 2. Router Simple: ¿Preguntan por precios?
    msg_lower = message.lower()
    keywords_planes = ['precio', 'costo', 'plan', 'dólar', 'cuanto', 'valor', 'pago', 'money', 'vale', 'ofreces']
    
    extra_content = ""
    if any(k in msg_lower for k in keywords_planes):
        extra_content = read_prompt('info_planes.txt')
        # print("DEBUG: Inyectando info_planes.txt") # Descomentar para debug
    
    # 3. Inyectar información
    # Asegúrate que en context.txt esté escrito literalmente {info_planes}
    final_system_prompt = base_prompt.replace('{info_planes}', extra_content)

    try:
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=250, # Reducido a 250 para controlar costos, 1000 es mucho para chat simple
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error OpenAI: {e}")
        return "Lo siento, mi conexión falló un momento. 🔌"

# --- INTERFAZ VISUAL (FRONTEND) ---

def render_floating_chatbot():
    """Dibuja el chat flotante"""
    
    # Configuración Fija
    logo_img = '/static/icon/logo.png'
    t_header = 'Chipi'
    t_sub = 'Asistente IA'
    t_placeholder = 'Escribe tu duda...'

    # 1. VENTANA PRINCIPAL
    with ui.element('div').classes('fixed bottom-24 right-6 w-[340px] h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50 border border-slate-200 font-sans') as chat_window:
        chat_window.style('display: none; opacity: 0; transition: all 0.3s ease-in-out; transform: translateY(20px);')

        # 2. CABECERA
        with ui.row().classes('w-full bg-rose-600 p-4 justify-between items-center shrink-0 shadow-md'):
            with ui.row().classes('items-center gap-3'):
                # Avatar
                with ui.element('div').classes('w-10 h-10 bg-white rounded-full flex items-center justify-center overflow-hidden shadow-sm border-2 border-rose-400'):
                    ui.image(logo_img).classes('w-full h-full object-cover')
                
                # Textos
                with ui.column().classes('gap-0 leading-tight'):
                    ui.label(t_header).classes('text-white font-bold text-base tracking-wide')
                    with ui.row().classes('items-center gap-1'):
                        ui.element('div').classes('w-2 h-2 bg-green-400 rounded-full animate-pulse')
                        ui.label(t_sub).classes('text-rose-100 text-xs font-medium')
            
            # Botón Cerrar
            ui.button(icon='close', on_click=lambda: toggle_chat()).props('flat round dense text-color=white size=sm').classes('hover:bg-rose-700 rounded-full transition-colors')

        # 3. ÁREA DE MENSAJES (Block Layout - Anti Crash)
        scroll_area = ui.element('div').classes('w-full flex-1 overflow-y-auto p-4 bg-slate-100 block space-y-4')
        
        def add_msg(text, is_user):
            with scroll_area:
                row_align = 'justify-end' if is_user else 'justify-start'
                
                with ui.element('div').classes(f'flex w-full {row_align} items-end gap-2 animate-fade-in'):
                    # Avatar Bot
                    if not is_user:
                        with ui.element('div').classes('w-8 h-8 min-w-[32px] rounded-full overflow-hidden bg-white shadow-sm'):
                            ui.image(logo_img).classes('w-full h-full object-cover')

                    # Burbuja
                    if is_user:
                        bubble_style = 'bg-rose-600 text-white rounded-2xl rounded-tr-none shadow-md ml-12'
                    else:
                        bubble_style = 'bg-white text-slate-700 rounded-2xl rounded-tl-none shadow-sm mr-4'

                    with ui.element('div').classes(f'px-4 py-2.5 {bubble_style}'):
                        ui.label(text).classes('text-sm leading-relaxed break-words').style('white-space: pre-wrap;')

        # Bienvenida
        add_msg('¡Hola! 👋 Soy el asistente virtual. ¿En qué te ayudo hoy?', False)

        # 4. INPUT
        with ui.row().classes('w-full p-3 bg-white border-t border-slate-200 items-center gap-2 shrink-0'):
            input_text = ui.input(placeholder=t_placeholder).props('outlined dense borderless').classes('flex-grow bg-slate-50 rounded-full px-4 text-sm')
            input_text.props('input-class="px-1" no-error-icon hide-bottom-space')
            
            async def send():
                msg = input_text.value
                if not msg: return
                
                input_text.value = ''
                input_text.disable()
                
                # Usuario
                add_msg(msg, True)
                ui.run_javascript(f'var el = getElement({scroll_area.id}); el.scrollTop = el.scrollHeight;')
                
                # Animación Carga
                with scroll_area:
                    with ui.element('div').classes('flex w-full justify-start items-end gap-2 mb-2') as loading_div:
                         with ui.element('div').classes('w-8 h-8 min-w-[32px] rounded-full overflow-hidden bg-white shadow-sm'):
                            ui.image(logo_img).classes('w-full h-full object-cover')
                         with ui.element('div').classes('bg-white text-rose-500 rounded-2xl rounded-tl-none px-4 py-2 shadow-sm'):
                             ui.spinner('dots', size='sm', color='rose-500')
                ui.run_javascript(f'var el = getElement({scroll_area.id}); el.scrollTop = el.scrollHeight;')

                # Llamada API
                response = await get_bot_response(msg)

                loading_div.delete()
                add_msg(response, False)
                
                input_text.enable()
                await asyncio.sleep(0.1)
                ui.run_javascript(f'var el = getElement({scroll_area.id}); el.scrollTop = el.scrollHeight;')
                ui.run_javascript(f'getElement({input_text.id}).focus()')

            input_text.on('keydown.enter', send)
            ui.button(icon='send', on_click=send).props('flat round dense text-color=rose-600').classes('hover:bg-rose-50')

    # 5. TOGGLE Y BOTÓN FLOTANTE
    def toggle_chat():
        if chat_window.style.get('display') == 'none':
            chat_window.style('display: flex; opacity: 1; transform: translateY(0px);')
            ui.run_javascript(f'setTimeout(() => getElement({input_text.id}).focus(), 100);')
            ui.run_javascript(f'var el = getElement({scroll_area.id}); el.scrollTop = el.scrollHeight;')
        else:
            chat_window.style('display: none; opacity: 0; transform: translateY(20px);')

    with ui.button(icon='smart_toy', on_click=toggle_chat).classes('fixed bottom-6 right-6 w-14 h-14 rounded-full shadow-lg shadow-rose-300 z-50 bg-rose-600 hover:scale-110 transition-transform duration-300'):
        ui.tooltip('Asistente IA').classes('bg-gray-800 text-white')