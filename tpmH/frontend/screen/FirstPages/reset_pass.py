from nicegui import ui, app
from passlib.hash import pbkdf2_sha256
from prompts.chatbot import render_floating_chatbot
# --- NUEVOS IMPORTS ---
from db.models import User
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
# ----------------------

# =====================================================
# CONFIGURACIÓN
# =====================================================
unrestricted_page_routes = {'/resetpass', '/login'}

# =====================================================
# UI PRINCIPAL (HEADER + LAYOUT GENERAL)
# =====================================================
def create_ui(content_function=None):
    """Crea la interfaz base consistente con el resto de la app."""
    ui.dark_mode().set_value(False)

    ui.add_head_html("""
    <style>
    body { background-color: #f8fafc; }
    </style>
    """)

    # HEADER
    with ui.header().classes('h-16 px-6 bg-white border-b border-gray-200 items-center justify-between shadow-sm text-gray-800'):
        with ui.row().classes('items-center gap-2 cursor-pointer').on('click', lambda: ui.navigate.to('/login')):
            ui.icon('school', color='pink-600', size='md')
            ui.label('TuProfeMaria').classes('text-xl font-black tracking-tight text-gray-800')

        # Botón volver al login
        ui.button('Cancelar', on_click=lambda: ui.navigate.to('/login')) \
            .props('flat color=grey-8 icon=close')

    # CONTENEDOR CENTRAL
    with ui.column().classes('w-full min-h-[calc(100vh-64px)] items-center justify-center p-4'):
        if content_function:
            content_function()

# =====================================================
# PÁGINA DE RESET PASSWORD
# =====================================================
@ui.page('/resetpass')
def reset_screen():
    """Pantalla para cambiar contraseña."""

    def render_reset_content():
        
        def try_reset():
            u = username_input.value.strip()
            email = email_input.value.strip()
            new_p = new_password_input.value.strip()

            if not (u and email and new_p):
                ui.notify('Por favor, completa todos los campos.', type='warning', icon='warning')
                return

            # Calcular el hash antes de abrir sesiones para no bloquear la DB con CPU
            try:
                new_hash = pbkdf2_sha256.hash(new_p)
            except Exception as e:
                ui.notify(f'Error procesando contraseña: {e}', type='negative')
                return

            # Variables de control
            success = False
            
            # FASE 1: ACTUALIZAR EN LA NUBE (NEON - PRINCIPAL)
            session_pg = PostgresSession()
            try:
                user_pg = session_pg.query(User).filter_by(username=u).first()
                
                # 1. Validaciones
                if not user_pg:
                    ui.notify('El usuario no existe.', type='negative', icon='person_off')
                    username_input.props('error error-message="Usuario no encontrado"')
                    return # Salimos y cerramos en finally

                if not (email, user_pg.email) or email.lower() != user_pg.email.lower():
                    ui.notify('El email actual es incorrecto.', type='negative', icon='gpp_bad')
                    email_input.props('error') 
                    return # Salimos y cerramos en finally

                # 2. Actualizar
                user_pg.password_hash = new_hash
                session_pg.commit()
                
                success = True # Marcamos éxito

            except Exception as e:
                session_pg.rollback()
                ui.notify(f"Error de conexión con el servidor: {str(e)}", type='negative')
                return
            finally:
                session_pg.close()

            # FASE 2: ACTUALIZAR RESPALDO (SQLITE)
            # Solo si FASE 1 fue exitosa. Hacemos esto ANTES de notificar al usuario.
            if success:
                try:
                    session_sqlite = BackupSession()
                    user_sqlite = session_sqlite.query(User).filter_by(username=u).first()
                    
                    if user_sqlite:
                        user_sqlite.password_hash = new_hash
                        session_sqlite.commit()
                        print(f"💾 Backup actualizado para usuario {u}")
                    else:
                        print(f"⚠️ El usuario {u} no existía en el backup local.")
                        
                except Exception as e:
                    # El backup falló, pero la contraseña real YA SE CAMBIÓ.
                    # Solo lo logueamos, no detenemos el flujo de la UI.
                    print(f"⚠️ Error actualizando backup local: {e}")
                finally:
                    # Aseguramos cerrar la sesión de backup si se creó
                    try:
                        session_sqlite.close()
                    except:
                        pass

                # --- NOTIFICACIÓN FINAL ---
                # Ahora que todo el trabajo pesado terminó, actualizamos la UI.
                ui.notify('¡Contraseña actualizada correctamente!', type='positive', icon='check_circle')
                
                # Deshabilitar botón para evitar doble clic mientras redirige
                username_input.disable()
                email_input.disable()
                new_password_input.disable()
                
                ui.timer(2.0, lambda: ui.navigate.to('/login'))

            # FASE 2: ACTUALIZAR RESPALDO (SQLITE - SECUNDARIO)
            # Solo si la fase 1 fue exitosa
            if success:
                try:
                    session_sqlite = BackupSession()
                    user_sqlite = session_sqlite.query(User).filter_by(username=u).first()
                    
                    if user_sqlite:
                        # Si el usuario existe en el backup, actualizamos su contraseña también
                        user_sqlite.password_hash = new_hash
                        session_sqlite.commit()
                        print(f"💾 Backup actualizado para usuario {u}")
                    else:
                        print(f"⚠️ El usuario {u} no existía en el backup local (se omitió actualización local).")
                        
                except Exception as e:
                    # Si falla el backup, NO avisamos al usuario (ya que su contraseña real sí cambió)
                    # Solo lo registramos en consola
                    print(f"⚠️ Error actualizando backup local: {e}")
                finally:
                    session_sqlite.close()

        # --- DISEÑO ---
        with ui.card().classes('w-full max-w-sm p-8 shadow-xl rounded-2xl bg-white border border-gray-100'):
            
            # Encabezado Tarjeta
            with ui.column().classes('w-full items-center mb-6 text-center'):
                with ui.element('div').classes('bg-pink-50 p-3 rounded-full mb-2'):
                    ui.icon('lock_reset', size='md', color='pink-600')
                ui.label('Cambiar Contraseña').classes('text-2xl font-bold text-gray-800')
                ui.label('Ingresa tus credenciales actuales').classes('text-sm text-gray-500')

            # Inputs
            with ui.column().classes('w-full gap-4'):
                username_input = ui.input('Usuario') \
                    .props('outlined dense') \
                    .classes('w-full')
                username_input.add_slot('prepend', '<q-icon name="account_circle" />')

                email_input = ui.input('Email') \
                    .props('outlined dense') \
                    .classes('w-full')
                email_input.add_slot('prepend', '<q-icon name="email" />')

                new_password_input = ui.input('Nueva Contraseña', password=True, password_toggle_button=True) \
                    .props('outlined dense') \
                    .classes('w-full')
                new_password_input.add_slot('prepend', '<q-icon name="lock" />')

                # Botón Acción
                ui.button('Actualizar Contraseña', on_click=try_reset) \
                    .props('unelevated color=pink-600') \
                    .classes('w-full mt-2 font-bold shadow-md hover:shadow-lg transition-shadow rounded-lg py-2')

            # Enlaces footer
            with ui.row().classes('w-full justify-center mt-6'):
                ui.link('Volver al inicio', target='/login') \
                    .classes('text-sm text-gray-500 hover:text-pink-600 transition-colors decoration-none')

            # Atajos de teclado
            for field in (username_input, email_input, new_password_input):
                field.on('keydown.enter', try_reset)

    # Renderizar UI
    create_ui(render_reset_content)
    render_floating_chatbot('reset_pass')