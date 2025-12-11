from nicegui import ui, app
import base64
import logging
import os
import uuid
import shutil
from components.headerAdmin import create_admin_screen
from db.postgres_db import PostgresSession
from db.models import Base, TeacherProfile, User 

# Configurar logger
logger = logging.getLogger(__name__)

# =====================================================
# CORRECCIÓN DE RUTA DE ESCRITURA (CRÍTICO)
# =====================================================
# Detectamos dónde estamos ejecutando para encontrar la carpeta 'tpmH'
# y guardar los archivos EXACTAMENTE donde main.py los va a buscar.

current_working_dir = os.getcwd()

if os.path.exists(os.path.join(current_working_dir, 'tpmH')):
    # Estamos en Render (o ejecutando desde raíz), entramos a tpmH
    UPLOAD_DIR = os.path.abspath(os.path.join(current_working_dir, 'tpmH', 'uploads'))
else:
    # Estamos dentro de la carpeta o entorno local simple
    UPLOAD_DIR = os.path.abspath(os.path.join(current_working_dir, 'uploads'))

# Crear la carpeta física si no existe
os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"📂 [TeacherEdit] Guardando archivos en: {UPLOAD_DIR}")

# NOTA: NO usamos app.add_static_files aquí. main.py ya lo hace.
# =====================================================

# Habilidades predefinidas
PRESET_SKILLS = [
    "Gramática", "Conversación", "Pronunciación", "Vocabulario", 
    "Inglés de Negocios", "Preparación IELTS", "Preparación TOEFL", 
    "Inglés para Niños", "Inglés para Viajes", "Redacción", 
    "Comprensión Auditiva", "Nivel Principiante", "Nivel Avanzado"
]

@ui.page('/teacher_edit')
def teacherAdmin():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_admin_screen()
    
    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # 2. ESTADO INICIAL
    profile = {
        'photo': '',
        'name': '',
        'surname': '',
        'display_name': '',
        'title': '',
        'bio': '',
        'video_url': '', # Youtube URL
        'skills': [],
        'new_skill': '',
        'certificates': [],
        'gallery': [], # Lista de rutas: "/uploads/archivo.mp4"
        'social_links': { 
            'linkedin': '',
            'tiktok': '',
            'instagram': '',
            'phone': '', # Nuevo campo
        }
    }

    # 3. CARGAR DATOS
    def load_profile():
        session = PostgresSession()
        try:
            user_obj = session.query(User).filter(User.username == username).first()
            if user_obj:
                profile['name'] = user_obj.name or ''
                profile['surname'] = user_obj.surname or ''
                profile['display_name'] = f"{user_obj.name} {user_obj.surname}".strip()

            db_profile = session.query(TeacherProfile).filter(TeacherProfile.username == username).first()
            if db_profile:
                profile['photo'] = db_profile.photo or ''
                profile['title'] = db_profile.title or ''
                profile['bio'] = db_profile.bio or ''
                profile['video_url'] = db_profile.video or ''
                profile['skills'] = db_profile.skills if db_profile.skills is not None else []
                profile['certificates'] = db_profile.certificates if db_profile.certificates is not None else []
                profile['gallery'] = db_profile.gallery if db_profile.gallery is not None else []
                
                # Cargar redes sociales y teléfono de forma segura
                socials = db_profile.social_links if db_profile.social_links is not None else {}
                profile['social_links'].update(socials)
                
                ui.notify('Datos cargados correctamente', type='positive', icon='cloud_download')
            else:
                profile['skills'] = []
                profile['certificates'] = []
                profile['gallery'] = []
                
        except Exception as e:
            ui.notify(f'Error cargando perfil: {str(e)}', type='negative')
            logger.error(f"Load Error: {e}")
        finally:
            session.close()

    load_profile()

    # 4. LÓGICA DE GUARDADO
    async def save_profile():
        session = PostgresSession()
        try:
            db_profile = session.query(TeacherProfile).filter(TeacherProfile.username == username).first()
            
            if not db_profile:
                db_profile = TeacherProfile(username=username)
                session.add(db_profile)
            
            db_profile.name = profile['name']
            db_profile.surname = profile['surname']
            db_profile.photo = profile['photo']
            db_profile.title = profile['title']
            db_profile.bio = profile['bio']
            db_profile.video = profile['video_url']
            db_profile.skills = profile['skills']
            db_profile.certificates = profile['certificates']
            db_profile.gallery = profile['gallery']
            db_profile.social_links = profile['social_links']
            
            session.commit()
            ui.notify('Perfil público guardado correctamente', type='positive', icon='cloud_done')
            ui.timer(1, lambda: ui.navigate.to('/teacher'))
            
        except Exception as e:
            session.rollback()
            ui.notify(f'Error al guardar: {str(e)}', type='negative')
        finally:
            session.close()

    # Helpers UI
    def add_certificate():
        profile['certificates'].append({'title': '', 'year': ''})
        render_certs.refresh()

    def remove_certificate(idx):
        if 0 <= idx < len(profile['certificates']):
            profile['certificates'].pop(idx)
            render_certs.refresh()
            
    def remove_gallery_item(idx):
        if 0 <= idx < len(profile['gallery']):
            profile['gallery'].pop(idx)
            render_gallery.refresh()

    # --- LÓGICA DE UPLOAD (AVATAR) ---
    async def handle_photo_upload_b64(e):
        try:
            # Para el avatar seguimos usando Base64 (es pequeño y directo)
            if hasattr(e, 'content'):
                data = e.content.read()
            elif hasattr(e, 'file'): # Fallback
                data = await e.file.read()
            else:
                return

            b64_data = base64.b64encode(data).decode('utf-8')
            # Intentar adivinar mime simple
            mime = 'image/jpeg'
            if hasattr(e, 'type') and e.type: mime = e.type
            elif hasattr(e, 'name') and e.name.endswith('.png'): mime = 'image/png'

            profile['photo'] = f"data:{mime};base64,{b64_data}"
            render_avatar.refresh()
            ui.notify('Foto actualizada', type='positive')
        except Exception as ex:
            ui.notify(f'Error foto: {ex}', type='negative')

    # --- LÓGICA DE UPLOAD ROBUSTA (GALERÍA - DISCO) ---
    async def handle_gallery_disk_upload(e):
        try:
            # 1. Extracción de datos segura
            filename = "unknown_file"
            data = None

            # Caso 1: NiceGUI standard wrapper
            if hasattr(e, 'name') and hasattr(e, 'content'):
                filename = e.name
                data = e.content.read()
            
            # Caso 2: Objeto File de Starlette/FastAPI subyacente
            elif hasattr(e, 'file'):
                filename = getattr(e.file, 'name', 'unknown')
                if hasattr(e.file, 'read'):
                    try:
                        data = await e.file.read()
                    except:
                        data = e.file.read() # Sync fallback

            # Caso 3: Fallback de nombre con UUID
            if not filename or filename == 'unknown' or filename == 'unknown_file':
                ext = ".bin"
                if hasattr(e, 'type'):
                    if 'video' in e.type: ext = '.mp4'
                    elif 'image' in e.type: ext = '.jpg'
                filename = f"upload_{uuid.uuid4()}{ext}"

            if not data:
                raise Exception("No se pudieron leer los datos del archivo.")

            # 2. Guardar en disco (Ruta absoluta segura UPLOAD_DIR)
            # Limpiamos el nombre de espacios
            filename = filename.replace(" ", "_")
            filepath = os.path.join(UPLOAD_DIR, filename)
            
            with open(filepath, 'wb') as f:
                f.write(data)
            
            # 3. Guardar ruta relativa en el perfil
            file_url = f"/uploads/{filename}"
            profile['gallery'].append(file_url)
            
            render_gallery.refresh()
            ui.notify(f'Archivo subido: {filename}', type='positive')
            
        except Exception as ex:
            ui.notify(f'Error subiendo archivo: {str(ex)}', type='negative')
            logger.error(f"Gallery Upload Error: {ex}")


    # 5. INTERFAZ VISUAL
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8 pb-24'):
        
        # --- HEADER ---
        with ui.row().classes('w-full justify-between items-end'):
            with ui.column().classes('gap-1'):
                ui.label('Editor de Perfil Público').classes('text-3xl font-bold text-slate-800')
                ui.label('Completa los campos para configurar tu página pública').classes('text-slate-500')
            
            ui.button('Ver Perfil Público', icon='visibility', on_click=lambda: ui.navigate.to('/teacher')) \
                .props('flat color=rose')

        # --- GRID PRINCIPAL ---
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-3 gap-8'):

            # COLUMNA IZQUIERDA (Foto y Datos Básicos)
            with ui.column().classes('lg:col-span-1 gap-6'):
                
                with ui.card().classes('w-full p-6 items-center text-center rounded-2xl shadow-sm border border-slate-100 bg-white'):
                    ui.label('Foto de Perfil').classes('text-xs font-bold text-slate-400 uppercase mb-2')
                    
                    @ui.refreshable
                    def render_avatar():
                        src = profile['photo'] if profile['photo'] else 'https://www.gravatar.com/avatar/?d=mp'
                        with ui.image(src).classes('w-48 h-48 rounded-full object-cover border-4 border-rose-100 mb-4 shadow-sm bg-slate-100'):
                            pass
                    render_avatar()
                    
                    ui.upload(
                        label="Subir Foto (JPG/PNG)", 
                        auto_upload=True, 
                        max_files=1, 
                        on_upload=handle_photo_upload_b64
                    ).props('accept=".jpg, .jpeg, .png" flat color=rose dense w-full').classes('w-full max-w-[200px]')
                    
                    ui.separator().classes('my-4')
                    
                    ui.input('Nombre (Cuenta)', value=profile['display_name']) \
                        .bind_value(profile, 'display_name') \
                        .props('outlined dense readonly filled').classes('w-full font-bold')
                    
                    ui.input('Título Profesional', value=profile['title']).bind_value(profile, 'title') \
                        .props('outlined dense placeholder="Ej. Experta en IELTS"').classes('w-full text-sm')

                # --- REDES SOCIALES Y CONTACTO ---
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100 bg-white'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('share', color='rose', size='sm')
                        ui.label('Contacto y Redes').classes('text-lg font-bold text-slate-800')
                    
                    with ui.column().classes('w-full gap-3'):
                        # Input Teléfono
                        ui.input('WhatsApp / Teléfono', value=profile['social_links']['phone']) \
                            .bind_value(profile['social_links'], 'phone') \
                            .props('outlined dense rounded prepend-icon=phone placeholder="+34 600..."').classes('w-full')
                        
                        ui.separator().classes('my-2')

                        ui.input('LinkedIn URL', value=profile['social_links']['linkedin']) \
                            .bind_value(profile['social_links'], 'linkedin') \
                            .props('outlined dense rounded placeholder="https://linkedin.com/..."').classes('w-full')
                        
                        ui.input('Instagram URL', value=profile['social_links']['instagram']) \
                            .bind_value(profile['social_links'], 'instagram') \
                            .props('outlined dense rounded placeholder="https://instagram.com/..."').classes('w-full')
                        
                        ui.input('TikTok URL', value=profile['social_links']['tiktok']) \
                            .bind_value(profile['social_links'], 'tiktok') \
                            .props('outlined dense rounded placeholder="https://tiktok.com/..."').classes('w-full')

            # COLUMNA DERECHA (Detalles)
            with ui.column().classes('lg:col-span-2 gap-6'):

                # 1. SOBRE MÍ
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('edit_note', color='rose', size='sm')
                        ui.label('Sobre Mí').classes('text-lg font-bold text-slate-800')
                    
                    ui.textarea(value=profile['bio']).bind_value(profile, 'bio') \
                        .props('outlined rounded rows=4 placeholder="Cuéntales a tus alumnos sobre tu experiencia..."').classes('w-full')

                # 2. VIDEO PRESENTACIÓN
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('play_circle', color='rose', size='sm')
                        ui.label('Video de Presentación (YouTube)').classes('text-lg font-bold text-slate-800')
                    
                    ui.input('Enlace de YouTube', value=profile['video_url']).bind_value(profile, 'video_url') \
                        .props('outlined rounded prefix="URL" placeholder="https://youtube.com/..."').classes('w-full')

                # 3. HABILIDADES
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.row().classes('items-center gap-2 mb-4'):
                        ui.icon('stars', color='rose', size='sm')
                        ui.label('Habilidades').classes('text-lg font-bold text-slate-800')

                    ui.select(
                        options=PRESET_SKILLS,
                        label='Selecciona o escribe habilidades',
                        multiple=True,
                        new_value_mode='add-unique'
                    ).bind_value(profile, 'skills').props('use-chips use-input outlined color=rose behavior="menu"').classes('w-full')

                # 4. CERTIFICADOS
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.row().classes('items-center justify-between w-full mb-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('workspace_premium', color='rose', size='sm')
                            ui.label('Certificados').classes('text-lg font-bold text-slate-800')
                        ui.button('Añadir', icon='add', on_click=add_certificate).props('flat dense color=rose size=sm')

                    @ui.refreshable
                    def render_certs():
                        if not profile['certificates']:
                            ui.label('No hay certificados.').classes('text-sm text-slate-400 italic')
                        with ui.column().classes('w-full gap-3'):
                            for idx, cert in enumerate(profile['certificates']):
                                with ui.row().classes('w-full gap-2 items-center bg-slate-50 p-2 rounded-lg'):
                                    ui.input(value=cert['title']).bind_value(cert, 'title').props('dense borderless placeholder="Nombre"').classes('flex-1 font-medium')
                                    ui.separator().props('vertical')
                                    ui.input(value=cert['year']).bind_value(cert, 'year').props('dense borderless placeholder="Año"').classes('w-20 text-center')
                                    ui.button(icon='delete', on_click=lambda i=idx: remove_certificate(i)).props('flat dense color=red size=sm rounded')
                    render_certs()

                # 5. GALERÍA (FOTOS Y VIDEOS)
                with ui.card().classes('w-full p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.icon('perm_media', color='rose', size='sm')
                            ui.label('Galería (Fotos y Videos)').classes('text-lg font-bold text-slate-800')
                        
                        # Uploader que llama a la función robusta
                        ui.upload(
                            label="Subir Archivos (IMG / MP4)", 
                            auto_upload=True, 
                            multiple=True, 
                            on_upload=handle_gallery_disk_upload
                        ).props('accept=".jpg, .jpeg, .png, .mp4" flat color=rose dense bordered').classes('w-full border-2 border-dashed border-rose-200 rounded-lg p-2 bg-rose-50')
                    
                    @ui.refreshable
                    def render_gallery():
                        if not profile['gallery']:
                            ui.label('No hay contenido en la galería.').classes('text-sm text-slate-400 italic mt-2')
                            return
                            
                        with ui.row().classes('w-full gap-4 flex-wrap mt-4'):
                            for idx, resource_url in enumerate(profile['gallery']):
                                with ui.card().classes('w-40 h-40 p-0 relative group overflow-hidden border border-slate-200 rounded-lg shadow-sm bg-black'):
                                    
                                    # Determinar tipo
                                    is_video = resource_url.lower().endswith('.mp4')
                                    
                                    if is_video:
                                        # Vista previa video
                                        ui.video(resource_url).classes('w-full h-full object-cover')
                                        ui.icon('play_circle', color='white').classes('absolute top-2 right-2 drop-shadow-md z-10')
                                    else:
                                        # Vista previa imagen
                                        ui.image(resource_url).classes('w-full h-full object-cover')
                                    
                                    # Botón eliminar
                                    with ui.column().classes('absolute inset-0 bg-black/50 items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity z-20'):
                                        ui.button(icon='delete', on_click=lambda i=idx: remove_gallery_item(i)) \
                                            .props('flat round color=white')
                    render_gallery()

    # --- FOOTER ---
    with ui.footer().classes('bg-white/90 backdrop-blur-md border-t border-slate-200 p-4 justify-end gap-4'):
        ui.button('Descartar', on_click=lambda: ui.navigate.to('/myclassesAdmin')).props('flat color=slate')
        ui.button('Publicar Cambios', icon='save', on_click=save_profile) \
            .props('unelevated color=green-600').classes('shadow-lg shadow-rose-200 px-6')

# Ejecutar
if __name__ in {"__main__", "__mp_main__"}:
    ui.run()