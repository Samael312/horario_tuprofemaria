from nicegui import ui, app, Client  # <--- IMPORTANTE: Agrega Client aquí
import asyncio
import os
import time
from components.headerAdmin import create_admin_screen

# Importamos la lógica de sincronización
from auth.sync_cal import sync_google_calendar_logic


# --- VARIABLES GLOBALES DE CONTROL ---
IS_SYNCING = False
LAST_SYNC_TIME = 0  
SYNC_COOLDOWN = 3600 

# --- FUNCIÓN HELPER CORREGIDA ---
async def notify_all_admins(message, type='positive', spinner=False):
    """Envía notificaciones a todas las pestañas abiertas por administradores."""
    # CORRECCIÓN: Usamos Client.instances.values() en lugar de app.clients
    for client in Client.instances.values():
        try:
            # Entramos en el contexto del cliente para acceder a su sesión (storage)
            with client:
                # Verificamos si es un usuario autenticado y es admin
                if app.storage.user.get('authenticated') and app.storage.user.get('role') == 'admin':
                    ui.notify(message, type=type, close_button=True, position='bottom-right', spinner=spinner)
        except Exception:
            # Si el cliente está desconectado o hay error al acceder, ignoramos
            pass

@ui.page('/admin')
def main_admin_screen():
    create_admin_screen()
    
    # 1. Verificación de Seguridad
    username = app.storage.user.get("username", "Admin")
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    if app.storage.user.get('role') != "admin":
        ui.notify("Access denied", color="negative")
        ui.navigate.to('/mainscreen')
        return

    # =================================================================
    # 2. SINCRONIZACIÓN CONTROLADA (COOLDOWN + GLOBAL)
    # =================================================================
    async def run_auto_sync():
        global IS_SYNCING, LAST_SYNC_TIME
        
        # A. Si ya está corriendo, avisamos y salimos.
        if IS_SYNCING:
            ui.notify('⚠️ La sincronización ya está en curso en segundo plano.', type='warning', position='bottom-right')
            return

        # B. COOLDOWN: Si hace poco se sincronizó, no hacemos nada automáticamente.
        # Esto evita el reinicio al cambiar de pestaña.
        current_time = time.time()
        time_since_last = current_time - LAST_SYNC_TIME
        
        if time_since_last < SYNC_COOLDOWN:
            # Opcional: Imprimir en consola para depuración
            print(f"Sync omitido: Solo han pasado {int(time_since_last)} segs. Espera {SYNC_COOLDOWN}s.")
            return

        teacher_email = os.getenv('CALENDAR_ID')
        if not teacher_email:
            return

        # C. INICIO DEL PROCESO
        IS_SYNCING = True
        
        # Avisamos a TODOS que empezó (No guardamos la variable para no tener que hacer dismiss)
        await notify_all_admins('🔄 Iniciando sincronización con Google Calendar...', type='info', spinner=True)

        try:
            # --- PROCESO PESADO ---
            # El hilo sigue vivo aunque cierres la pestaña
            count = await asyncio.to_thread(sync_google_calendar_logic, teacher_email)
            
            # Actualizamos el tiempo de la última sincronización exitosa
            LAST_SYNC_TIME = time.time()

            # --- NOTIFICACIÓN FINAL ---
            if count > 0:
                await notify_all_admins(f'✅ Listo: {count} clases importadas.', type='positive')
            else:
                await notify_all_admins('✅ Calendario sincronizado (Sin cambios).', type='positive')

        except Exception as e:
            print(f"Error crítico en Auto-Sync: {e}")
            await notify_all_admins(f'❌ Error al sincronizar: {str(e)}', type='negative')
            
        finally:
            IS_SYNCING = False

    # Iniciamos el proceso (Solo se ejecutará si pasa el filtro de Cooldown)
    ui.timer(0.5, run_auto_sync, once=True)

    # =================================================================
    # 3. INTERFAZ GRÁFICA
    # =================================================================
    
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):

        with ui.column().classes('items-center mb-10 text-center'):
            ui.label(f'Bienvenido {username}!').classes('text-4xl md:text-5xl font-black text-gray-800 tracking-tight')
            ui.label('Panel de Administración').classes('text-lg text-gray-500 mt-2 font-medium')
        
        with ui.row().classes('w-full max-w-4xl justify-center gap-6 md:gap-10'):

            # Tarjeta Estudiantes
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-green-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/Students')):
                
                with ui.element('div').classes('bg-green-50 p-4 rounded-full mb-4'):
                    ui.icon('group', size='xl', color='green-600')
                
                ui.label('Gestión de Estudiantes').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Ver y administrar la lista de estudiantes registrados.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                ui.button('Ver Estudiantes', icon='arrow_forward', on_click=lambda: ui.navigate.to('/Students')) \
                    .props('rounded outline color=green').classes('w-full hover:bg-green-50')

            # Tarjeta Mis Clases
            with ui.card().classes('w-full md:w-80 p-6 items-center text-center shadow-lg hover:shadow-2xl transition-all duration-300 border-t-4 border-purple-500 rounded-xl cursor-pointer') \
                    .on('click', lambda: ui.navigate.to('/myclassesAdmin')):
                
                with ui.element('div').classes('bg-purple-50 p-4 rounded-full mb-4'):
                    ui.icon('class', size='xl', color='purple-600')
                
                ui.label('Mis Clases').classes('text-xl font-bold text-gray-800 mb-2')
                ui.label('Ver y administrar las clases asignadas a los estudiantes.').classes('text-sm text-gray-500 mb-6 leading-relaxed')
                
                ui.button('Ver Mis Clases', icon='arrow_forward', on_click=lambda: ui.navigate.to('/myclassesAdmin'))\
                    .props('rounded outline color=purple').classes('w-full hover:bg-purple-50')   
                
    with ui.footer().classes('bg-transparent text-gray-400 justify-center pb-4'):
        ui.label('© 2025 TuProfeMaria - Panel de Administración').classes('text-sm text-gray-500')