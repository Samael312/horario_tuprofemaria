from nicegui import ui, app
from datetime import datetime
import logging
import uuid
from components.header import create_main_screen
from components.headerAdmin import create_admin_screen
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import TeacherProfile, User
import os

# Configurar logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE ARCHIVOS ESTÁTICOS ---
app.add_static_files('/components', 'components')

@ui.page('/teacher')
def teacher_profile_view():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    # --- LOGICA HEADER & ROLES ---
    username = app.storage.user.get("username")
    is_admin = False
    is_client = False
    current_user_info = {'name': '', 'surname': ''}

    # --- DEFINICIÓN DE ICONOS ---
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

    if is_admin:
        create_admin_screen()
    else:
        create_main_screen()
    
    # 1. LOGICA: CARGAR DATOS
    profile_data = {}
    
    session = PostgresSession()
    try:
        db_profile = session.query(TeacherProfile).first()
        
        if db_profile:
            socials = db_profile.social_links if db_profile.social_links else {}
            reviews_list = db_profile.reviews if hasattr(db_profile, 'reviews') and db_profile.reviews else []
            gallery_data = db_profile.gallery or []
            
            logger.info(f"Galería cargada con {len(gallery_data)} elementos")

            profile_data = {
                'photo': db_profile.photo or 'https://www.gravatar.com/avatar/?d=mp',
                'name': f"{db_profile.name} {db_profile.surname}".strip(),
                'title': db_profile.title or 'Profesor de Inglés',
                'bio': db_profile.bio or 'Sin biografía disponible.',
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
            profile_data = {
                'photo': 'https://www.gravatar.com/avatar/?d=mp',
                'name': 'Perfil no configurado',
                'title': 'Docente',
                'bio': 'El profesor aún no ha configurado su perfil público.',
                'video': '', 'skills': [], 'certificates': [], 'gallery': [], 'reviews': [],
                'social_links': {'linkedin': '', 'instagram': '', 'tiktok': ''}
            }
    except Exception as e:
        logger.error(f"Error cargando perfil: {e}")
        profile_data = {'reviews': [], 'gallery': [], 'certificates': [], 'skills': [], 'social_links': {}}
    finally:
        session.close()

    # --- HELPER: REDES SOCIALES ---
    def open_social_link(url):
        if not url: return
        final_url = str(url).strip()
        if not final_url.startswith('http://') and not final_url.startswith('https://'):
            final_url = 'https://' + final_url
        
        logger.info(f"Abriendo link: {final_url}")
        ui.navigate.to(final_url, new_tab=True)

    # --- LÓGICA DE REVIEWS ---
    form_state = {'rating': 5, 'comment': ''}

    async def save_reviews_to_db(new_reviews_list):
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

        try:
            bk_session = BackupSession()
            bk_prof = bk_session.query(TeacherProfile).first()
            if not bk_prof:
                bk_prof = TeacherProfile(username='admin')
                bk_session.add(bk_prof)
            bk_prof.reviews = new_reviews_list
            bk_session.commit()
            bk_session.close()
        except Exception as e:
            logger.error(f"Error SQLite reviews: {e}")

    async def submit_review():
        if not form_state['comment'].strip():
            ui.notify('Escribe un comentario por favor.', type='warning')
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
        
        current_reviews = list(profile_data.get('reviews', []))
        current_reviews.append(review_entry)
        
        await save_reviews_to_db(current_reviews)
        profile_data['reviews'] = current_reviews
        
        ui.notify('¡Reseña publicada!', type='positive')
        form_state['comment'] = ''
        form_state['rating'] = 5
        render_reviews_area.refresh()

    async def delete_review(review_id):
        current_reviews = list(profile_data.get('reviews', []))
        updated_reviews = [r for r in current_reviews if r.get('id') != review_id]
        if len(current_reviews) == len(updated_reviews): return

        await save_reviews_to_db(updated_reviews)
        profile_data['reviews'] = updated_reviews
        ui.notify('Reseña eliminada.', type='info')
        render_reviews_area.refresh()

    # Helpers UI
    def get_youtube_id(url):
        if not url: return None
        if 'v=' in url: return url.split('v=')[-1].split('&')[0]
        elif 'youtu.be' in url: return url.split('/')[-1]
        return None

    def open_lightbox(src):
        # Lightbox sin límites restrictivos, usando 100% de viewport
        with ui.dialog() as d, ui.card().classes('w-full h-full p-0 bg-transparent shadow-none items-center justify-center relative'):
            ui.html(f'''
                
                    <img src="{src}" style="width:100%; height:100%; object-fit:contain; border-radius:20px; display:block ;box-shadow: 0 4px 6px rgba(0,0,0,0.3);" />
              
            ''', sanitize=False)
            
            # Botón cerrar flotante
            with ui.element('div').classes('absolute justify-center bottom-6 w-full flex'):
                ui.button(icon='close', on_click=d.close).props('round color=white text-color=black')
        d.open()

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-8 pb-20'):
        
        # 1. HERO SECTION (Skills movidas de aquí)
        with ui.card().classes('w-full p-8 rounded-3xl bg-white shadow-sm border border-slate-100 flex flex-col md:flex-row gap-8 items-center md:items-start'):
            # Foto
            if profile_data.get('photo') and profile_data['photo'].startswith('data:'):
                 ui.html(f'<img src="{profile_data["photo"]}" class="w-48 h-48 rounded-full object-cover border-4 border-rose-100 shadow-md flex-shrink-0 bg-slate-100" />', sanitize=False)
            else:
                 with ui.image(profile_data.get('photo', '')).classes('w-48 h-48 rounded-full object-cover border-4 border-rose-100 shadow-md flex-shrink-0 bg-slate-100'):
                    pass
            
            with ui.column().classes('flex-1 gap-1 text-center md:text-left w-full'):
                with ui.row().classes('items-center justify-center md:justify-start gap-2 mb-1'):
                    ui.icon('person', color='rose', size='xs')
                    ui.label('Conoce a tu Profesor').classes('text-xs font-bold text-rose-500 uppercase tracking-widest')
                
                ui.label(profile_data.get('name', '')).classes('text-4xl font-bold text-slate-800 leading-tight')
                ui.label(profile_data.get('title', '')).classes('text-xl text-slate-500 font-medium mb-3')
                
                # REDES SOCIALES
                sl = profile_data.get('social_links', {})
                if any(sl.values()):
                    with ui.row().classes('gap-3 justify-center md:justify-start mb-4'):
                        if sl.get('linkedin'):
                            ui.button(icon=icon_linkedin, on_click=lambda: open_social_link(sl['linkedin'])) \
                                .props('flat round dense size=md').tooltip('LinkedIn')
                        if sl.get('instagram'):
                            ui.button(icon=icon_instagram, on_click=lambda: open_social_link(sl['instagram'])) \
                                .props('flat round dense size=md').tooltip('Instagram')
                        if sl.get('tiktok'):
                            ui.button(icon=icon_tiktok, on_click=lambda: open_social_link(sl['tiktok'])) \
                                .props('flat round dense size=md').tooltip('TikTok')

        # 2. CONTENIDO PRINCIPAL
        with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-3 gap-8'):
            
            # COLUMNA IZQ (Ancha)
            with ui.column().classes('lg:col-span-2 gap-8'):
                # Bio
                with ui.card().classes('w-full p-8 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                    with ui.row().classes('items-center gap-3 mb-6'):
                        ui.icon('format_quote', color='rose', size='md')
                        ui.label('Sobre Mí').classes('text-2xl font-bold text-slate-800')
                    ui.label(profile_data.get('bio', '')).classes('text-slate-600 leading-relaxed text-lg whitespace-pre-wrap font-light')

                # Video
                vid_url = profile_data.get('video', '')
                video_id = get_youtube_id(vid_url)
                if video_id:
                    with ui.card().classes('w-full p-0 rounded-3xl shadow-lg border border-slate-100 overflow-hidden bg-black'):
                        ui.html(f'''
                            <div style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden;">
                                <iframe style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;" 
                                        src="https://www.youtube.com/embed/{video_id}" 
                                        title="YouTube video player" frameborder="0" 
                                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                                        allowfullscreen>
                                </iframe>
                            </div>
                        ''', sanitize=False).classes('w-full')
                elif vid_url:
                    with ui.card().classes('w-full p-4 rounded-xl bg-slate-100 items-center text-center'):
                        ui.link(vid_url, vid_url).classes('text-rose-500 font-bold')

            # COLUMNA DER (Lateral)
            with ui.column().classes('lg:col-span-1 gap-8'):
                
                # Certificados
                if profile_data.get('certificates'):
                    with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('workspace_premium', color='rose', size='sm')
                            ui.label('Certificaciones').classes('text-lg font-bold text-slate-800')
                        with ui.column().classes('gap-3 w-full'):
                            for cert in profile_data['certificates']:
                                with ui.row().classes('w-full items-center gap-3 bg-slate-50 p-3 rounded-xl border border-slate-100'):
                                    with ui.element('div').classes('p-2 bg-white rounded-full shadow-sm'):
                                        ui.icon('verified', color='blue-500', size='xs')
                                    with ui.column().classes('gap-0 flex-1'):
                                        ui.label(cert['title']).classes('font-bold text-slate-700 text-sm leading-tight')
                                        ui.label(cert['year']).classes('text-xs text-slate-400 mt-0.5')

                # --- SKILLS (NUEVA UBICACIÓN) ---
                if profile_data.get('skills'):
                    with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('stars', color='rose', size='sm')
                            ui.label('Habilidades').classes('text-lg font-bold text-slate-800')
                        
                        # Chips con wrap
                        with ui.row().classes('gap-2 flex-wrap'):
                            for skill in profile_data['skills']:
                                ui.chip(skill, icon='check').props('color=rose-50 text-color=rose-700 dense').classes('font-bold border border-rose-100')

                # --- GALERÍA (DEBAJO DE CERTIFICADOS Y SKILLS) ---
                gallery_imgs = profile_data.get('gallery', [])
                if gallery_imgs:
                    with ui.card().classes('w-full p-6 rounded-3xl shadow-sm border border-slate-100 bg-white'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('photo_library', color='rose', size='sm')
                            ui.label('Galería de Anexos').classes('text-lg font-bold text-slate-800')
                        
                        # Grid de 2 columnas para la barra lateral
                        with ui.grid().classes('grid-cols-2 gap-3'):
                            for i, img in enumerate(gallery_imgs):
                                with ui.card().classes('w-full h-32 p-0 rounded-xl overflow-hidden cursor-pointer group shadow-sm transition-all hover:shadow-md border border-slate-100 relative'):
                                    ui.html(f'<img src="{img}" style="width:100%; height:100%; object-fit:cover;" />', sanitize=False).classes('w-full h-full')
                                    
                                    ui.element('div').classes('absolute inset-0 z-10').on('click', lambda src=img: open_lightbox(src))
                                    
                                    with ui.element('div').classes('absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center pointer-events-none z-0'):
                                        ui.icon('zoom_in', color='white').classes('opacity-0 group-hover:opacity-100 transition-opacity')

        # 3. SECCIÓN DE REVIEWS
        ui.separator().classes('my-8 bg-slate-200')
        
        @ui.refreshable
        def render_reviews_area():
            with ui.column().classes('w-full gap-6'):
                # Header
                reviews = profile_data.get('reviews', [])
                avg_rating = sum(r['rating'] for r in reviews) / len(reviews) if reviews else 0
                
                with ui.row().classes('items-center gap-4'):
                    ui.icon('star', color='amber-400', size='lg')
                    ui.label('Reseñas de Estudiantes').classes('text-3xl font-bold text-slate-800')
                    if reviews:
                        with ui.row().classes('items-center gap-1 bg-amber-50 px-3 py-1 rounded-full border border-amber-100'):
                            ui.label(f"{avg_rating:.1f}").classes('font-bold text-amber-600')
                            ui.icon('star', size='xs', color='amber-500')
                            ui.label(f"({len(reviews)})").classes('text-xs text-amber-400')

                if not reviews:
                    ui.label('Aún no hay reseñas. ¡Sé el primero en opinar!').classes('text-slate-400 italic')
                else:
                    with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 gap-4'):
                        for rev in reversed(reviews[-6:]): 
                            with ui.card().classes('p-4 rounded-2xl border border-slate-100 shadow-sm bg-white relative group'):
                                # Botón borrar
                                if is_admin or (username and rev.get('username') == username):
                                    ui.button(icon='delete', on_click=lambda r_id=rev.get('id'): delete_review(r_id)) \
                                        .props('flat round dense color=grey-400').classes('absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity z-10')

                                with ui.row().classes('justify-between items-start w-full mb-2'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.icon('account_circle', color='slate-300', size='md')
                                        with ui.column().classes('gap-0'):
                                            full_name = f"{rev.get('name', '')} {rev.get('surname', '')}".strip()
                                            display_name = full_name if full_name else rev.get('username', 'Anónimo')
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
                        ui.label('Deja tu reseña').classes('text-lg font-bold text-rose-800 mb-4')
                        with ui.column().classes('w-full gap-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.label('Tu calificación:').classes('text-sm text-slate-600')
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
                                ui.textarea(placeholder='Escribe tu experiencia con el profesor...') \
                                    .bind_value(form_state, 'comment') \
                                    .props('outlined rounded bg-white rows=2') \
                                    .classes('w-3/4')
                                ui.button('Publicar', on_click=submit_review) \
                                    .props('unelevated rounded-xl icon=send') \
                                    .classes('flex-1 py-3 font-bold shadow-md bg-slate-800 text-white hover:bg-slate-900')
        
        render_reviews_area()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()