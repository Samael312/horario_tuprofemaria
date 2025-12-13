from nicegui import ui, app
from components.header import create_main_screen
# Imports de Base de Datos
from db.postgres_db import PostgresSession
import logging
# AÑADIDO: TeacherProfile para sacar el número
from db.models import AsignedClasses, SchedulePref, TeacherProfile 

# Imports de Subpáginas
from frontend.screen.MainScreen.Subpages import old_Student, new_Student 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@ui.page('/mainscreen')
def mainscreen():
    # 1. Verificar sesión
    username = app.storage.user.get("username", "Estudiante")
    
    # Variables para almacenar el teléfono dinámico
    teacher_phone = ""
    
    # 2. LÓGICA DE BASE DE DATOS (Redirección + Obtención de datos del profesor)
    session = PostgresSession()
    try:
        # A. Verificación de Estudiante (Redirección)
        has_pref = session.query(SchedulePref).filter(SchedulePref.username == username).first()
        has_classes = session.query(AsignedClasses).filter(AsignedClasses.username == username).first()
        
        if has_pref or has_classes:
            ui.navigate.to('/myclasses')
            return 
        
        # B. Obtención de datos de contacto del Profesor (Igual que en teacher_profile_view)
        # Esto se ejecuta solo si el usuario es NUEVO (no fue redirigido)
        db_profile = session.query(TeacherProfile).first()
        if db_profile and db_profile.social_links:
            # Extraemos el teléfono del JSON, con un fallback vacío
            teacher_phone = db_profile.social_links.get('phone', '')

    except Exception as e:
        logger.error(f"Error en mainscreen DB logic: {e}")
    finally:
        session.close()

    # --- HELPER: REDES SOCIALES (Copiado de teacher_profile_view) ---
    def open_social_link(url):
        if not url: return
        final_url = str(url).strip()
        if not final_url.startswith('http://') and not final_url.startswith('https://'):
            final_url = 'https://' + final_url
        
        logger.info(f"Abriendo link: {final_url}")
        ui.navigate.to(final_url, new_tab=True)

    # ==============================================================================
    # SI LLEGA AQUÍ: Es un usuario NUEVO
    # ==============================================================================
    
    # Header global
    create_main_screen()

    # --- DIÁLOGO DE RECORDATORIO DE PAGO ---
    # Se define aquí y se abrirá automáticamente con un timer al final
    with ui.dialog() as payment_dialog, ui.card().classes('w-full max-w-sm p-0 rounded-2xl overflow-hidden shadow-2xl'):
        
        # Cabecera del diálogo
        with ui.column().classes('w-full bg-rose-500 p-6 items-center'):
            ui.icon('payments', size='3em', color='white')
            ui.label('Paso Importante').classes('text-white text-xl font-bold mt-2')

        # Cuerpo del mensaje
        with ui.column().classes('p-6 items-center text-center gap-4'):
            ui.label('Antes de terminar de configurar tu perfil, ponte en contacto con tu profesora para concretar el pago de tus clases.').classes('text-gray-600 leading-relaxed')
            
            ui.separator()
            
            ui.label('Haz click aquí para contactar:').classes('text-xs font-bold text-gray-400 uppercase tracking-wider')

            # --- LÓGICA DEL BOTÓN ---
            # 1. Limpiamos el numero extraido de la DB (quitamos espacios, guiones, etc)
            clean_phone = ''.join(filter(str.isdigit, teacher_phone))
            
            # 2. Si hay numero, armamos la URL de WhatsApp, sino un fallback
            if clean_phone:
                wa_url = f"https://wa.me/{clean_phone}"
            else:
                # Fallback por si la DB está vacía o hay error
                wa_url = "https://wa.me/" 

            # 3. Botón usando el helper open_social_link
            ui.button('Contactar Profesora', icon='chat', on_click=lambda: open_social_link(wa_url)) \
                .props('rounded unelevated icon-right=open_in_new') \
                .classes('bg-rose-500 text-white w-full py-2 shadow-lg hover:bg-rose-600 transition-colors')

            # Botón para cerrar
            ui.button('Entendido, continuar', on_click=payment_dialog.close) \
                .props('flat text-color=grey') \
                .classes('text-sm')

    # --- CONTENEDOR PRINCIPAL ---
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] bg-gray-50 items-center justify-center p-4'):
        
        # 1. Sección de Bienvenida
        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(f'¡Hola {username}!').classes('text-4xl md:text-5xl font-black text-gray-800 tracking-tight')
            ui.label('Bienvenido a tu plataforma de aprendizaje.').classes('text-lg text-rose-500 font-bold mb-1')
            ui.label('¿Cómo deseas comenzar?').classes('text-lg text-gray-500 font-medium')

        # 2. Contenedor de Tarjetas 
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            # TARJETA 1: YA SOY ESTUDIANTE
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-blue-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/oldStudent')): 
                
                with ui.element('div').classes('bg-blue-50 p-4 rounded-full mb-4'):
                    ui.icon('history_edu', size='xl', color='blue-600')
                
                ui.label('Ya soy Estudiante').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Agendar clases anteriores y configurar horario preferencial.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                ui.button('CONFIGURAR PERFIL', icon='arrow_forward', on_click=lambda: ui.navigate.to('/myclasses')) \
                    .props('rounded outline color=blue').classes('w-full hover:bg-blue-50')

            # TARJETA 2: NUEVO ESTUDIANTE
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-pink-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/newStudent')):
                
                with ui.element('div').classes('bg-pink-50 p-4 rounded-full mb-4'):
                    ui.icon('school', size='xl', color='pink-600')
                
                ui.label('Nuevo Estudiante').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Configurar mi primer horario, definir preferencias y comenzar.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                ui.button('Configurar Horario', icon='add', on_click=lambda: ui.navigate.to('/newStudent')) \
                    .props('rounded unelevated color=pink').classes('w-full hover:bg-pink-700')

    # Footer
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        ui.label('TuProfeMaria App v1.0')

    # --- TRIGGER DEL POPUP ---
    ui.timer(0.5, payment_dialog.open, once=True)