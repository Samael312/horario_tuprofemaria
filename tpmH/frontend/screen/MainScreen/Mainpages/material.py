import os
from nicegui import ui, app, run
from db.postgres_db import PostgresSession
from db.models import Material, StudentMaterial
from components.header import create_main_screen 
from prompts.chatbot import render_floating_chatbot

from api.tts_api import get_audio_url 

# Caché en memoria para evitar repintar la UI
audio_cache = {}

@ui.page('/materials')
def student_materials_page():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_main_screen()

    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    username = app.storage.user.get('username')

    def get_file_type_info(filename):
        if filename == "[Set de Audio Interactivo]":
            return {'type': 'vocab', 'icon': 'record_voice_over', 'color': 'purple-100', 'text': 'purple-600'}
            
        ext = os.path.splitext(filename)[1].lower()
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
            return {'type': 'image', 'icon': None, 'color': None}
        elif ext == '.pdf':
            return {'type': 'doc', 'icon': 'picture_as_pdf', 'color': 'red-100', 'text': 'red-600'}
        elif ext in ['.doc', '.docx']:
            return {'type': 'doc', 'icon': 'description', 'color': 'blue-100', 'text': 'blue-600'}
        elif ext in ['.ppt', '.pptx']:
            return {'type': 'doc', 'icon': 'slideshow', 'color': 'orange-100', 'text': 'orange-600'}
        else:
            return {'type': 'doc', 'icon': 'insert_drive_file', 'color': 'slate-100', 'text': 'slate-500'}

    def get_my_materials():
        session = PostgresSession()
        try:
            results = session.query(StudentMaterial, Material)\
                .join(Material, StudentMaterial.material_id == Material.id)\
                .filter(StudentMaterial.username == username)\
                .order_by(StudentMaterial.id.desc())\
                .all()
            
            data = []
            for st_mat, mat in results:
                data.append({
                    'link_id': st_mat.id, 
                    'title': mat.title,
                    'category': mat.category,
                    'file': mat.content,
                    'progress': st_mat.progress, 
                    'level': mat.level,
                    'tags': mat.tags or {}
                })
            return data
        except Exception as e:
            print(f"Error cargando materiales: {e}")
            return []
        finally:
            session.close()

    def toggle_status(item_id, current_status):
        session = PostgresSession()
        try:
            st_mat = session.query(StudentMaterial).filter(StudentMaterial.id == item_id).first()
            if st_mat:
                new_status = "Completed" if current_status == "Not Started" else "Not Started"
                st_mat.progress = new_status
                session.commit()
                ui.notify('Progreso actualizado', type='positive' if new_status == 'Completed' else 'info')
                materials_grid.refresh()
        finally:
            session.close()


    # =========================================================
    # LÓGICA DE POPUP (CON BARRA DE PORCENTAJE)
    # =========================================================
    async def open_vocab_dialog(title, words):
        # 'persistent' evita que el estudiante cierre el popup por accidente haciendo clic afuera mientras carga
        dialog = ui.dialog().props('persistent') 
        
        with dialog, ui.card().classes('min-w-[350px] max-w-[450px] p-0 rounded-2xl shadow-xl overflow-hidden'):
            
            # --- CABECERA ESTILIZADA ---
            with ui.row().classes('w-full bg-gradient-to-r from-purple-600 to-indigo-600 p-4 justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('record_voice_over', color='white', size='sm')
                    ui.label(f'Audios: {title}').classes('text-lg font-bold text-white line-clamp-1')
                # Botón de cerrar 
                ui.button(icon='close', on_click=dialog.close).props('flat round size=sm color=white')

            # --- CONTENEDOR PRINCIPAL ---
            with ui.column().classes('p-6 w-full'):
                
                # ZONA 1: Animación de carga de audios
                with ui.column().classes('items-center justify-center py-8 w-full gap-4') as loading_area:
                    # Spinner animado nativo de NiceGUI con forma de barras de audio
                    ui.spinner('audio', size='3.5em', color='purple')
                    ui.label('Generando voces de Google...').classes('text-sm text-purple-700 font-medium animate-pulse')
                    
                    # Barra de progreso minimalista (más delgada y elegante)
                    progress_bar = ui.linear_progress(value=0.0).props('color=purple rounded size=6px')
                    progress_label = ui.label('0%').classes('text-xs text-slate-400 font-bold')

                # ZONA 2: Contenedor de botones (Oculto al inicio)
                buttons_area = ui.row().classes('w-full gap-3 justify-center max-h-[50vh] overflow-y-auto')
                buttons_area.set_visibility(False)

        dialog.open()

        # --- BUCLE DE VERIFICACIÓN / DESCARGA ---
        local_urls = {}
        total_words = len(words)
        for i, word in enumerate(words):
            url = await run.io_bound(get_audio_url, word, "en-US")
            if url:
                local_urls[word] = url
            
            # Actualizamos la barra suavemente
            if total_words > 0:
                pct = (i + 1) / total_words
                progress_bar.value = pct
                progress_label.text = f"{int(pct * 100)}%"

        # Terminó la carga: Ocultamos el spinner y mostramos los botones
        loading_area.set_visibility(False)
        buttons_area.set_visibility(True)
        
        with buttons_area:
            if not words:
                ui.label('No hay palabras registradas en este set.').classes('text-sm text-slate-400 italic py-4')
            else:
                for word in words:
                    # Función asíncrona segura para la reproducción
                    async def play_word_audio(w=word):
                        final_url = await run.io_bound(get_audio_url, w, "en-US")
                        if final_url:
                            ui.run_javascript(f"new Audio('{final_url}').play()")
                        else:
                            ui.notify(f'Error al reproducir "{w}"', type='negative')

                    # --- DISEÑO DE LOS BOTONES DE PALABRAS ---
                    if word in local_urls:
                        # Le añadimos sombras y un efecto hover (escala) de Tailwind
                        ui.button(word, icon='volume_up', on_click=play_word_audio) \
                            .classes('transition-transform hover:-translate-y-1 hover:shadow-md shadow-sm') \
                            .props('rounded outline size=md color=purple no-caps')
                    else:
                        ui.button(word, icon='error_outline') \
                            .classes('shadow-sm') \
                            .props('rounded outline size=md color=red no-caps').tooltip('Fallo al descargar')


    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-2 bg-indigo-100 rounded-xl'):
                ui.icon('school', size='lg', color='indigo-600')
            with ui.column().classes('gap-0'):
                ui.label('Mis Materiales').classes('text-2xl font-bold text-slate-800')
                ui.label('Recursos de estudio y Vocabulario interactivo').classes('text-sm text-slate-500')

        @ui.refreshable
        def materials_grid():
            items = get_my_materials()

            if not items:
                ui.label('No tienes materiales asignados.').classes('text-slate-400 italic')
                return

            with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6'):
                for item in items:
                    is_done = item['progress'] == 'Completed'
                    file_info = get_file_type_info(item['file'])
                    
                    card_classes = 'w-full p-0 rounded-2xl shadow-sm border transition-all hover:shadow-md overflow-hidden flex flex-col '
                    if item['category'] == 'Vocabulary':
                        card_classes += 'border-green-300 ring-2 ring-green-100' if is_done else 'border-purple-200 bg-purple-50/30'
                    else:
                        card_classes += 'border-green-300 ring-2 ring-green-100' if is_done else 'border-slate-200 bg-white'

                    with ui.card().classes(card_classes):
                        
                        # ZONA DE PORTADA
                        with ui.element('div').classes('w-full h-24 flex items-center justify-center relative bg-white'):
                            if file_info['type'] == 'image':
                                ui.image(f"/uploads/{item['file']}").classes('w-full h-full object-cover')
                            else:
                                with ui.element('div').classes(f"w-full h-full bg-{file_info['color']} flex items-center justify-center"):
                                    ui.icon(file_info['icon'], size='4xl', color=file_info['text'])
                            
                            ui.label(item['level']).classes('absolute top-2 right-2 bg-white/90 px-2 py-1 rounded-md text-xs font-bold shadow-sm')

                        # CONTENIDO DE TARJETA
                        with ui.column().classes('p-4 w-full flex-grow gap-2'):
                            badge_color = 'text-purple-500' if item['category'] == 'Vocabulary' else 'text-indigo-500'
                            ui.label(item['category']).classes(f'text-[10px] font-bold {badge_color} uppercase tracking-widest')
                            ui.label(item['title']).classes('font-bold text-slate-800 leading-tight text-sm line-clamp-2 h-10')
                            ui.separator()
                            
                            # ==========================================
                            # ETIQUETA DE PALABRAS Y BOTÓN DE AUDIOS
                            # ==========================================
                            if item['category'] == 'Vocabulary':
                                words = item['tags'].get('words', [])
                                cantidad = len(words)
                                
                                # Lógica para mostrar las primeras palabras (Ej: apple, car, book...)
                                if cantidad > 0:
                                    preview_text = ", ".join(words[:3]) + ("..." if cantidad > 3 else "")
                                else:
                                    preview_text = "Sin palabras"
                                
                                with ui.column().classes('w-full items-center pt-2 gap-1'):
                                    # Texto con cantidad y ejemplos
                                    ui.label(f'{cantidad} palabras: {preview_text}') \
                                        .classes('text-[11px] text-slate-500 font-medium text-center line-clamp-1 w-full px-1')
                                    
                                    ui.button('Abrir Audios', icon='headphones', 
                                              on_click=lambda t=item['title'], w=words: open_vocab_dialog(t, w)) \
                                        .props('unelevated rounded size=sm color=purple no-caps w-full')
                            else:
                                # Botones Archivos
                                with ui.row().classes('w-full gap-1 pt-2'):
                                    ui.button('Abrir', icon='open_in_new', 
                                              on_click=lambda x=item['file']: ui.navigate.to(f'/uploads/{x}', new_tab=True)) \
                                        .props('flat dense size=sm color=slate no-caps')
                                    
                                    ui.button(icon='cloud_download', 
                                              on_click=lambda x=item['file']: ui.download(f'/uploads/{x}')) \
                                        .props('flat dense size=sm color=indigo round').tooltip('Descargar')
                                    
                            ui.space()

                            # --- BOTÓN DE ESTADO ---
                            with ui.row().classes('w-full justify-end items-center mt-2'):
                                check_icon = 'check_circle' if is_done else 'radio_button_unchecked'
                                check_col = 'green' if is_done else 'grey'
                                
                                ui.button(icon=check_icon, 
                                          on_click=lambda i=item['link_id'], s=item['progress']: toggle_status(i, s)) \
                                    .props(f'flat round color={check_col}')

        materials_grid()
    render_floating_chatbot('materials')