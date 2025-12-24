from nicegui import ui, app
from openai import AsyncOpenAI
from dotenv import load_dotenv
import asyncio
import os

# 1. CARGA DE ENTORNO
load_dotenv()

# 2. CONFIGURACIÓN DE RUTAS (CORREGIDO)
# Obtenemos la ruta donde está ESTE archivo (chatbot.py)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Lógica inteligente: Si chatbot.py está en la raíz, busca 'prompts'.
# Si por error chatbot.py estuviera dentro de 'prompts', usa el directorio actual.
if os.path.basename(CURRENT_DIR) == 'prompts':
    PROMPTS_DIR = CURRENT_DIR
else:
    PROMPTS_DIR = os.path.join(CURRENT_DIR, 'prompts')

# Cliente OpenAI
client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ==============================================================================
# LÓGICA DEL BACKEND
# ==============================================================================

def read_prompt(filename):
    """Lee el archivo .txt localmente (ESTO ES GRATIS, NO GASTA TOKENS)"""
    try:
        path = os.path.join(PROMPTS_DIR, filename)
        if not os.path.exists(path):
            # Debug silencioso en consola para no molestar al usuario final
            print(f"⚠️ Archivo faltante: {path}") 
            return ""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error leyendo {filename}: {e}")
        return ""

async def get_bot_response(message, screen_name):
    """
    Cerebro con Logs detallados en terminal.
    """
    
    # LOG INICIAL: NUEVA PETICIÓN
    print(f"\n{'='*60}")
    print(f"🤖 [BOT] Nueva Petición Recibida")
    print(f"👤 Mensaje Usuario: '{message}'")
    print(f"📍 Pantalla Detectada: '{screen_name}'")

    # A. Auth
    is_authenticated = app.storage.user.get('authenticated', False)
    
    # B. MAPA DE PANTALLAS
    screen_map = {
        # --- PÚBLICAS ---
        'main': 'screen_main.txt',
        'login': 'screen_login.txt',
        'signup': 'screen_signup.txt',
        'planes': 'screen_planes.txt',
        'methods': 'screen_adv_methods.txt',
        'reset_pass': 'screen_reset_pass.txt',
        
        # --- ESTUDIANTE ---
        'student_home': 'screen_student_home.txt',
        'profile': 'screen_student_profile.txt',
        'my_classes': 'screen_my_classes.txt',
        'schedule': 'screen_schedule.txt',
        'teacher_view': 'screen_teacher_view.txt',
        'materials': 'screen_materials.txt',
        'homework': 'screen_homework.txt',
        'onboarding': 'screen_onboarding.txt',
        'edit_profile': 'screen_edit_profile.txt',
        'change_password': 'screen_change_password.txt',

        # --- ADMIN ---
        'admin_home': 'screen_admin_home.txt',
        'admin_students': 'screen_admin_students.txt',
        'admin_schedule': 'screen_admin_schedule.txt',
        'admin_content': 'screen_admin_content.txt'
    }

    # C. SELECCIÓN DE CONTENIDO
    dynamic_content = ""
    loaded_file = "Ninguno (Default)" # Para el log
    
    if screen_name in screen_map:
        filename = screen_map[screen_name]
        
        # Filtro de Seguridad
        public_list = ['main', 'login', 'signup', 'planes', 'methods', 'reset_pass']
        
        if not is_authenticated and screen_name not in public_list:
            dynamic_content = "El usuario no está logueado y trata de ver ayuda privada."
            print(f"🚫 [SEGURIDAD] Acceso denegado a prompt privado: {filename}")
        else:
            dynamic_content = read_prompt(filename)
            loaded_file = filename
            print(f"📂 [CARGA] Prompt de Pantalla cargado: {filename}")
    else:
        dynamic_content = "El usuario está navegando por la plataforma."
        print(f"⚠️ [ALERTA] ID de pantalla '{screen_name}' no encontrado en el mapa.")

    # --- REGLA DE ORO: PRECIOS ---
    msg_lower = message.lower()
    keywords_planes = ['precio', 'costo', 'plan', 'valor', 'cuanto', 'pago', 'dolar', 'usd']
    
    if any(k in msg_lower for k in keywords_planes):
        print(f"💰 [OVERRIDE] Tema de dinero detectado. Cambiando contexto a 'screen_planes.txt'")
        dynamic_content = read_prompt('screen_planes.txt')
        loaded_file = "screen_planes.txt (Forzado por Keyword)"

    # D. INYECCIÓN
    print(f"🧠 [CARGA] Leyendo contexto base: context.txt")
    base_prompt = read_prompt('context.txt') 
    
    if not base_prompt:
        base_prompt = "Eres un asistente útil. INFORMACIÓN ACTUAL: {dynamic_info}"

    final_system_prompt = base_prompt.replace('{dynamic_info}', dynamic_content)

    # E. LLAMADA A OPENAI
    try:
        print(f"🚀 [API] Enviando solicitud a OpenAI... (Archivo final: {loaded_file})")
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_system_prompt},
                {"role": "user", "content": message}
            ],
            temperature=0.7,
            max_tokens=300, 
        )
        print(f"✅ [EXITO] Respuesta recibida ({len(response.choices[0].message.content)} caracteres)")
        print(f"{'='*60}\n")
        return response.choices[0].message.content
    except Exception as e:
        print(f"❌ [ERROR] Fallo en OpenAI: {e}")
        return "Lo siento, tuve un problema de conexión. 🔌"

# ==============================================================================
# UI (FRONTEND)
# ==============================================================================

def render_floating_chatbot(screen_name):
    """
    Dibuja el chat. ESTA FUNCIÓN NO GASTA TOKENS.
    Solo prepara la interfaz visual.
    """
    
    logo_img = '/static/icon/logo.png' 
    
    # 1. CONTENEDOR
    with ui.element('div').classes('fixed bottom-24 right-6 w-[340px] h-[500px] bg-white rounded-2xl shadow-2xl flex flex-col overflow-hidden z-50 border border-slate-200 font-sans') as chat_window:
        chat_window.style('display: none; opacity: 0; transition: all 0.3s ease-in-out; transform: translateY(20px);')

        # 2. HEADER
        with ui.row().classes('w-full bg-rose-600 p-4 justify-between items-center shrink-0 shadow-md'):
            with ui.row().classes('items-center gap-3'):
                with ui.element('div').classes('w-10 h-10 bg-white rounded-full flex items-center justify-center overflow-hidden shadow-sm border-2 border-rose-400'):
                    ui.image(logo_img).classes('w-full h-full object-cover')
                with ui.column().classes('gap-0 leading-tight'):
                    ui.label('Chipi AI').classes('text-white font-bold text-base tracking-wide')
                    with ui.row().classes('items-center gap-1'):
                        ui.element('div').classes('w-2 h-2 bg-green-400 rounded-full animate-pulse')
                        ui.label('En línea').classes('text-rose-100 text-xs font-medium')
            
            ui.button(icon='close', on_click=lambda: toggle_chat()).props('flat round dense text-color=white size=sm').classes('hover:bg-rose-700 rounded-full transition-colors')

        # 3. AREA DE CHAT
        scroll_area = ui.element('div').classes('w-full flex-1 overflow-y-auto p-4 bg-slate-100 block space-y-4')
        
        def add_msg(text, is_user):
            with scroll_area:
                row_align = 'justify-end' if is_user else 'justify-start'
                with ui.element('div').classes(f'flex w-full {row_align} items-end gap-2 animate-fade-in'):
                    if not is_user:
                        with ui.element('div').classes('w-8 h-8 min-w-[32px] rounded-full overflow-hidden bg-white shadow-sm'):
                            ui.image(logo_img).classes('w-full h-full object-cover')
                    
                    bubble_bg = 'bg-rose-600 text-white' if is_user else 'bg-white text-slate-700'
                    bubble_shape = 'rounded-tr-none' if is_user else 'rounded-tl-none'
                    
                    with ui.element('div').classes(f'px-4 py-2.5 {bubble_bg} rounded-2xl {bubble_shape} shadow-sm max-w-[85%]'):
                        ui.label(text).classes('text-sm leading-relaxed break-words').style('white-space: pre-wrap;')

        add_msg('¡Hola! 👋 ¿En qué te ayudo?', False)

        # 4. INPUT (AQUÍ ES DONDE SE CONTROLA EL GASTO)
        with ui.row().classes('w-full p-3 bg-white border-t border-slate-200 items-center gap-2 shrink-0'):
            input_text = ui.input(placeholder='Escribe aquí...').props('outlined dense borderless').classes('flex-grow bg-slate-50 rounded-full px-4 text-sm')
            
            async def send():
                msg = input_text.value
                if not msg: return
                
                input_text.value = ''
                input_text.disable()
                
                add_msg(msg, True) # Muestra mensaje usuario
                
                # Loading...
                with scroll_area:
                    with ui.element('div').classes('flex w-full justify-start items-end gap-2 mb-2') as loading_div:
                         with ui.element('div').classes('w-8 h-8 min-w-[32px] rounded-full overflow-hidden bg-white shadow-sm'):
                            ui.image(logo_img).classes('w-full h-full object-cover')
                         with ui.element('div').classes('bg-white text-rose-500 rounded-2xl rounded-tl-none px-4 py-2 shadow-sm'):
                             ui.spinner('dots', size='sm', color='rose-500')
                
                # --- PUNTO CRÍTICO ---
                # Recién AQUÍ llamamos a la API. 
                # Cargar la página NO ejecuta esto. Solo dar click a enviar.
                response = await get_bot_response(msg, screen_name)
                # ---------------------

                loading_div.delete()
                add_msg(response, False)
                input_text.enable()

            input_text.on('keydown.enter', send)
            ui.button(icon='send', on_click=send).props('flat round dense text-color=rose-600')

    # 5. BOTÓN FLOTANTE
    def toggle_chat():
        if chat_window.style.get('display') == 'none':
            chat_window.style('display: flex; opacity: 1; transform: translateY(0px);')
        else:
            chat_window.style('display: none; opacity: 0; transform: translateY(20px);')

    logo_img = '/static/icon/logo.png' 
    with ui.button(on_click=toggle_chat) \
            .props('round unelevated') \
            .classes('fixed bottom-6 right-6 z-50 p-0 transition-transform duration-300 hover:scale-110 active:scale-90'):
        
        with ui.element('div').classes('w-16 h-16 rounded-full border-4 border-white shadow-2xl overflow-hidden relative ring-1 ring-rose-300 bg-white'):
            
            # La Imagen
            ui.image(logo_img).classes('w-full h-full object-cover')

            ui.element('div').classes('absolute top-0 left-0 w-full h-1/2 bg-gradient-to-b from-white/30 to-transparent pointer-events-none')

        # Tooltip
        ui.tooltip('Chipi Asistente').classes('bg-gray-900 text-white text-xs font-bold py-1 px-2 rounded')