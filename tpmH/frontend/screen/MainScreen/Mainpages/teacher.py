from nicegui import ui, app
from datetime import datetime
import logging
import uuid
import os

# NOTA: Asegúrate de que los módulos components y db estén disponibles y en el PYTHONPATH
# Si estás probando en local sin estos módulos, tendrás que comentar las importaciones y simular los datos.
from components.header import create_main_screen 
from components.headerAdmin import create_admin_screen
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import TeacherProfile, User 

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app.add_static_files('/components', 'components')

# --- 1. TRADUCCIONES ---
TRANSLATIONS = {
    'es': {
        'meet_teacher': 'Conoce a tu Profesor',
        'about_me': 'Sobre Mí',
        'certifications': 'Certificaciones',
        'skills': 'Habilidades',
        'gallery_title': 'Galería de Anexos',
        'reviews_title': 'Reseñas de Estudiantes',
        'no_profile_name': 'Perfil no configurado',
        'no_profile_title': 'Docente',
        'no_profile_bio': 'El profesor aún no ha configurado su perfil público.',
        'leave_review': 'Deja tu reseña',
        'your_rating': 'Tu calificación:',
        'submit_btn': 'Publicar',
        'write_experience': 'Escribe tu experiencia con el profesor...',
        'review_published': '¡Reseña publicada!',
        'review_deleted': 'Reseña eliminada.',
        'write_comment_warning': 'Escribe un comentario por favor.',
        'no_reviews': 'Aún no hay reseñas. ¡Sé el primero en opinar!',
        'anon_user': 'Anónimo',
        'error_loading': 'Error cargando perfil',
    },
    'en': {
        'meet_teacher': 'Meet Your Teacher',
        'about_me': 'About Me',
        'certifications': 'Certifications',
        'skills': 'Skills',
        'gallery_title': 'Attachment Gallery',
        'reviews_title': 'Student Reviews',
        'no_profile_name': 'Profile not configured',
        'no_profile_title': 'Teacher',
        'no_profile_bio': 'The teacher has not yet configured their public profile.',
        'leave_review': 'Leave Your Review',
        'your_rating': 'Your Rating:',
        'submit_btn': 'Submit',
        'write_experience': 'Write about your experience with the teacher...',
        'review_published': 'Review submitted!',
        'review_deleted': 'Review deleted.',
        'write_comment_warning': 'Please write a comment.',
        'no_reviews': 'No reviews yet. Be the first to rate!',
        'anon_user': 'Anonymous',
        'error_loading': 'Error loading profile',
    }
}

# Variable global para datos
profile_data = {}

@ui.page('/teacher')
def teacher_profile_view():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    # --- LOGICA HEADER & ROLES ---
    username = app.storage.user.get("username")
    is_admin = False
    is_client = False
    current_user_info = {'name': '', 'surname': ''}

    icon_instagram = 'img:components/icon/instagram.png'
    icon_tiktok = 'img:components/icon/tik-tok.png' 
    icon_linkedin = 'img:components/icon/linkedin.png'

    if username:
        session = PostgresSession()
        try:
            user_obj = session.query(User).filter(User.username == username).first()
            if user_obj:
                current_user_info['name'] = user_obj.name or ''
                current_user_info['surname'] = user_obj.surname or ''
                if user_obj.role == 'admin':
                    is_admin = True
                elif user_obj.role == 'client':
                    is_client = True
        except Exception as e:
            logger.error(f"Error verificando rol: {e}")
        finally:
            session.close()

    # --- HELPER: Obtener traducciones actuales ---
    def get_t():
        lang = app.storage.user.get('lang', 'es')
        return TRANSLATIONS[lang]

    # --- 1. LOGICA: CARGAR DATOS ---
    global profile_data
    
    session = PostgresSession()
    try:
        db_profile = session.query(TeacherProfile).first()
        
        if db_profile:
            socials = db_profile.social_links if db_profile.social_links else {}
            reviews_list = getattr(db_profile, 'reviews', [])
            gallery_data = db_profile.gallery or []

            # IMPORTANTE: Aquí NO traducimos. Si el campo está vacío en DB, lo dejamos como None.
            # La traducción se aplicará en el momento de renderizar (render_review_content).
            profile_data = {
                'photo': db_profile.photo or None, 
                'name': f"{db_profile.name} {db_profile.surname}".strip() if db_profile.name else None,
                'title': db_profile.title or None,
                'bio': db_profile.bio or None,
                'video': db_profile.video or '',
                'skills': db_profile.skills or [],
                'certificates': db_profile.certificates or [],
                'gallery': gallery_data,
                'reviews': reviews_list,
                'social_links': {
                    'linkedin': socials.get('linkedin', ''),
                    'instagram': socials.get('instagram', ''),
                    'tiktok': socials.get('tiktok', '')
                }
            }
        else:
            # Si no hay perfil, establecemos los campos clave en None
            profile_data = {
                'photo': None,
                'name': None,  # Se traducirá al pintar
                'title': None, # Se traducirá al pintar
                'bio': None,   # Se traducirá al pintar
                'video': '', 'skills': [], 'certificates': [], 'gallery': [], 'reviews': [],
                'social_links': {'linkedin': '', 'instagram': '', 'tiktok': ''}
            }
    except Exception as e:
        logger.error(f"Error cargando perfil: {e}")
        # En caso de error, aseguramos estructura mínima
        profile_data = {'reviews': [], 'gallery': [], 'certificates': [], 'skills': [], 'social_links': {}, 'name': None, 'bio': None}
    finally:
        session.close()


    def open_social_link(url):
        if not url: return
        final_url = str(url).strip()
        if not final_url.startswith('http://') and not final_url.startswith('https://'):
            final_url = 'https://' + final_url
        ui.navigate.to(final_url, new_tab=True)

    # --- LÓGICA DE REVIEWS ---
    form_state = {'rating': 5, 'comment': ''}

    async def save_reviews_to_db(new_reviews_list):
        # ... (Tu lógica existente de guardado en DB) ...
        pg_session = PostgresSession()
        try:
            pg_prof = pg_session.query(TeacherProfile).first()
            if pg_prof:
                pg_prof.reviews = new_reviews_list
                pg_session.commit()
        except Exception as e:
            logger.error(f"Error Postgres reviews: {e}")
        finally:
            pg_session.close()
        # (Aquí iría la lógica de SQLite backup si la necesitas)

    async def submit_review():
        t = get_t() # Obtenemos traducción fresca para notificaciones
        if not form_state['comment'].strip():
            ui.notify(t['write_comment_warning'], type='warning')
            return
        
        review_entry = {
            'id': str(uuid.uuid4()),
            'username': username,
            'name': current_user_info['name'],
            'surname': current_user_info['surname'],
            'rating': form_state['rating'],
            'comment': form_state['comment'],
            'date': datetime.now().strftime("%Y-%m-%d")
        }
        
        global profile_data
        current_reviews = list(profile_data.get('reviews', []))
        current_reviews.append(review_entry)
        
        await save_reviews_to_db(current_reviews)
        profile_data['reviews'] = current_reviews
        
        ui.notify(t['review_published'], type='positive')
        form_state['comment'] = ''
        form_state['rating'] = 5
        render_reviews_area.refresh()
        # Reset visual del textarea
        ui.query('.q-textarea textarea').props('value=""') 

    async def delete_review(review_id):
        t = get_t()
        global profile_data
        current_reviews = list(profile_data.get('reviews', []))
        updated_reviews = [r for r in current_reviews if r.get('id') != review_id]
        if len(current_reviews) == len(updated_reviews): return

        await save_reviews_to_db(updated_reviews)
        profile_data['reviews'] = updated_reviews
        ui.notify(t['review_deleted'], type='info')
        render_reviews_area.refresh()

    def get_youtube_id(url):
        if not url: return None
        if 'v=' in url: return url.split('v=')[-1].split('&')[0]
        elif 'youtu.be' in url: return url.split('/')[-1]
        return None

    @ui.refreshable
    def open_lightbox(src):
        with ui.dialog() as d, ui.card().classes('w-full h-full p-0 bg-transparent shadow-none items-center justify-center relative'):
            ui.html(f'<img src="{src}" style="width:100%; height:100%; object-fit:contain; border-radius:20px;" />', sanitize=False)
            with ui.element('div').classes('absolute justify-center bottom-6 w-full flex'):
                ui.button(icon='close', on_click=d.close).props('round color=white text-color=black')
        d.open()

    # --- 3. SECCIÓN DE REVIEWS ---
    @ui.refreshable 
    def render_reviews_area():
        t = get_t() # Actualizamos idioma
        
        with ui.column().classes('w-full gap-6'):
            global profile_data
            reviews = profile_data.get('reviews', [])
            avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
            
            with ui.row().classes('items-center gap-4'):
                ui.icon('star', color='amber-400', size='lg')
                ui.label(t['reviews_title']).classes('text-3xl font-bold text-slate-800')
                if reviews:
                    with ui.row().classes('items-center gap-1 bg-amber-50 px-3 py-1 rounded-full border border-amber-100'):
                        ui.label(f"{avg_rating:.1f}").classes('font-bold text-amber-600')
                        ui.icon('star', size='xs', color='amber-500')
                        ui.label(f"({len(reviews)})").classes('text-xs text-amber-400')

            if not reviews:
                ui.label(t['no_reviews']).classes('text-slate-400 italic')
            else:
                with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 gap-4'):
                    for rev in reversed(reviews[-6:]): 
                        with ui.card().classes('p-4 rounded-2xl border border-slate-100 shadow-sm bg-white relative group'):
                            if is_admin or (username and rev.get('username') == username):
                                ui.button(icon='delete', on_click=lambda r_id=rev.get('id'): delete_review(r_id)) \
                                    .props('flat round dense color=grey-400').classes('absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10')

                            with ui.row().classes('justify-between items-start w-full mb-2'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('account_circle', color='slate-300', size='md')
                                    with ui.column().classes('gap-0'):
                                        full_name = f"{rev.get('name', '')} {rev.get('surname', '')}".strip()
                                        display_name = full_name if full_name else rev.get('username', t['anon_user'])
                                        ui.label(display_name).classes('font-bold text-slate-700 text-sm')
                                        ui.label(rev.get('date', '')).classes('text-[10px] text-slate-400')
                                with ui.row().classes('gap-0'):
                                    for i in range(5):
                                        icon_name = 'star' if i < int(rev.get('rating', 0)) else 'star_border'
                                        ui.icon(icon_name, color='amber-400', size='xs')
                            ui.label(rev.get('comment', '')).classes('text-slate-600 text-sm italic')

            # Formulario
            if is_client and username:
                with ui.card().classes('w-full mt-6 p-6 rounded-2xl border border-rose-100 bg-rose-50/30'):
                    ui.label(t['leave_review']).classes('text-lg font-bold text-rose-800 mb-4')
                    with ui.column().classes('w-full gap-4'):
                        with ui.row().classes('items-center gap-2'):
                            ui.label(t['your_rating']).classes('text-sm text-slate-600')
                            @ui.refreshable
                            def render_stars_input():
                                with ui.row().classes('gap-1'):
                                    for i in range(1, 6):
                                        icon_name = 'star' if i <= form_state['rating'] else 'star_border'
                                        def set_rating(r=i):
                                            form_state['rating'] = r
                                            render_stars_input.refresh()
                                        ui.icon(icon_name, color='amber-400', size='md').classes('cursor-pointer hover:scale-110 transition-transform').on('click', set_rating)
                            render_stars_input()

                        with ui.row().classes('w-full items-start gap-4'):
                            review_textarea = ui.textarea(placeholder=t['write_experience']) \
                                .bind_value(form_state, 'comment') \
                                .props('outlined rounded bg-white rows=2') \
                                .classes('w-3/4')
                            
                            async def submit_and_clear():
                                await submit_review()
                                review_textarea.value = ''
                                
                            ui.button(t['submit_btn'], on_click=submit_and_clear) \
                                .props('unelevated rounded-xl icon=send') \
                                .classes('flex-1 py-3 font-bold shadow-md bg-slate-800 text-white hover:bg-slate-900')

    # --- 2. CONTENIDO PRINCIPAL ---
    @ui.refreshable
    def render_review_content():
        # 1. Obtener idioma actual
        t = get_t() 
        global profile_data
        
        # 2. LOGICA DE FALLBACK (Aquí ocurre la magia de la traducción automática)
        # Si profile_data['key'] es None, usa t['fallback_key']
        display_photo = profile_data.get('photo') or 'https://www.gravatar.com/avatar/?d=mp'
        display_name = profile_data.get('name') or t['no_profile_name']
        display_title = profile_data.get('title') or t['no_profile_title']
        display_bio = profile_data.get('bio') or t['no_profile_bio']

        # --- UI PRINCIPAL ---
        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-8 pb-20'):
            
            # 1. HERO SECTION
            with ui.card().classes('w-full p-8 rounded-3xl bg-white shadow-sm border border-slate-100 flex flex-col md:flex-row gap-8 items-center md:items-start'):
                # Foto
                if display_photo.startswith('data:'):
                    ui.html(f'<img src="{display_photo}" class="w-48 h-48 rounded-full object-cover border-4 border-rose-100 shadow-md flex-shrink-0 bg-slate-100" />', sanitize=False)
                else:
                    with ui.image(display_photo).classes('w-48 h-48 rounded-full object-cover border-4 border-rose-100 shadow-md flex-shrink-0 bg-slate-100'):
                        pass
                
                with ui.column().classes('flex-1 gap-1 text-center md:text-left w-full'):
                    with ui.row().classes('items-center justify-center md:justify-start gap-2 mb-1'):
                        ui.icon('person', color='rose', size='xs')
                        ui.label(t['meet_teacher']).classes('text-xs font-bold text-rose-500 uppercase tracking-widest')
                    
                    # Usamos las variables calculadas (display_name, display_title)
                    ui.label(display_name).classes('text-4xl font-bold text-slate-800 leading-tight')
                    ui.label(display_title).classes('text-xl text-slate-500 font-medium mb-3')
                    
                    sl = profile_data.get('social_links', {})
                    if any(sl.values()):
                        with ui.row().classes('gap-3 justify-center md:justify-start mb-4'):
                            if sl.get('linkedin'):
                                ui.button(icon=icon_linkedin, on_click=lambda: open_social_link(sl['linkedin'])).props('flat round dense size=md').tooltip('LinkedIn')
                            if sl.get('instagram'):
                                ui.button(icon=icon_instagram, on_click=lambda: open_social_link(sl['instagram'])).props('flat round dense size=md').tooltip('Instagram')
                            if sl.get('tiktok'):
                                ui.button(icon=icon_tiktok, on_click=lambda: open_social_link(sl['tiktok'])).props('flat round dense size=md').tooltip('TikTok')

            # 2. CONTENIDO PRINCIPAL GRID
            with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-3 gap-8'):
                
                # COLUMNA IZQ
                with ui.column().classes('lg:col-span-2 gap-8'):
                    with ui.card().classes('w-full p-8 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                        with ui.row().classes('items-center gap-3 mb-6'):
                            ui.icon('format_quote', color='rose', size='md')
                            ui.label(t['about_me']).classes('text-2xl font-bold text-slate-800')
                        # Usamos display_bio
                        ui.label(display_bio).classes('text-slate-600 leading-relaxed text-lg whitespace-pre-wrap font-light')

                    # Video
                    vid_url = profile_data.get('video', '')
                    video_id = get_youtube_id(vid_url)
                    if video_id:
                        with ui.card().classes('w-full p-0 rounded-3xl shadow-lg border border-slate-100 overflow-hidden bg-black'):
                            ui.html(f'''<div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;"><iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" src="https://www.youtube.com/embed/{video_id}" title="YouTube video player" frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe></div>''', sanitize=False).classes('w-full')
                    elif vid_url:
                        with ui.card().classes('w-full p-4 rounded-xl bg-slate-100 items-center text-center'):
                            ui.link(vid_url, vid_url).classes('text-rose-500 font-bold')

                # COLUMNA DER
                with ui.column().classes('lg:col-span-1 gap-8'):
                    if profile_data.get('certificates'):
                        with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('workspace_premium', color='rose', size='sm')
                                ui.label(t['certifications']).classes('text-lg font-bold text-slate-800')
                            with ui.column().classes('gap-3 w-full'):
                                for cert in profile_data['certificates']:
                                    with ui.row().classes('w-full items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100'):
                                        with ui.element('div').classes('p-2 bg-white rounded-full shadow-sm'):
                                            ui.icon('verified', color='blue-500', size='xs')
                                        with ui.column().classes('gap-0 flex-1'):
                                            ui.label(cert['title']).classes('font-bold text-slate-700 text-sm leading-tight')
                                            ui.label(cert['year']).classes('text-xs text-slate-400 mt-0.5')

                    if profile_data.get('skills'):
                        with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('stars', color='rose', size='sm')
                                ui.label(t['skills']).classes('text-lg font-bold text-slate-800')
                            with ui.row().classes('gap-2 flex-wrap'):
                                for skill in profile_data['skills']:
                                    ui.chip(skill, icon='check').props('color=rose-50 text-color=rose-700 dense').classes('font-bold border border-rose-100')

                    gallery_imgs = profile_data.get('gallery', [])
                    if gallery_imgs:
                        with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                            with ui.row().classes('items-center gap-2 mb-4'):
                                ui.icon('photo_library', color='rose', size='sm')
                                ui.label(t['gallery_title']).classes('text-lg font-bold text-slate-800')
                            with ui.grid().classes('grid-cols-2 gap-3'):
                                for i, img in enumerate(gallery_imgs):
                                    with ui.card().classes('w-full h-32 p-0 rounded-xl overflow-hidden cursor-pointer group shadow-sm transition-all hover:shadow-md border border-slate-100 relative'):
                                        ui.html(f'<img src="{img}" style="width:100%; height:100%; object-fit:cover;" />', sanitize=False).classes('w-full h-full')
                                        ui.element('div').classes('absolute inset-0 z-10').on('click', lambda src=img: open_lightbox(src))
                                        with ui.element('div').classes('absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center pointer-events-none z-0'):
                                            ui.icon('zoom_in', color='white').classes('opacity-0 group-hover:opacity-100 transition-opacity')

            # 3. SECCIÓN DE REVIEWS
            ui.separator().classes('my-8 bg-slate-200')
            render_reviews_area() 


    # 4. DISPOSICIÓN FINAL
    if is_admin:
        create_admin_screen(page_refresh_callback=render_review_content.refresh)
    else:
        create_main_screen(page_refresh_callback=render_review_content.refresh)
    
    render_review_content() 

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()