import os
import re
import logging
from datetime import datetime
from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import User, Material, StudentMaterial
from components.headerAdmin import create_admin_screen
from sqlalchemy.orm.attributes import flag_modified

logger = logging.getLogger(__name__)

# =====================================================
# CORRECCIÓN DE RUTAS (SOLUCIÓN DEFINITIVA)
# =====================================================
current_working_dir = os.getcwd()

if os.path.exists(os.path.join(current_working_dir, 'tpmH')):
    UPLOAD_DIR = os.path.abspath(os.path.join(current_working_dir, 'tpmH', 'uploads'))
else:
    UPLOAD_DIR = os.path.abspath(os.path.join(current_working_dir, 'uploads'))

os.makedirs(UPLOAD_DIR, exist_ok=True)
logger.info(f"📂 [MaterialAdmin] Guardando archivos en: {UPLOAD_DIR}")
# =====================================================

@ui.page('/MaterialsAdmin')
def materials_page():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_admin_screen()

    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    # Variables
    title_input = None
    category_input = None
    level_input = None
    uploader = None
    
    vocab_title = None
    vocab_level = None
    vocab_words = None
    
    table = None

    # --- HELPER: Metadatos para la UI ---
    def get_file_meta(filename, category):
        if category == 'Vocabulary':
            return False, 'volume_up', 'purple'
            
        if not filename: return False, 'description', 'grey'
        ext = os.path.splitext(filename)[1].lower()
        is_img = ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']
        icon = 'description'
        color = 'grey'
        if ext == '.pdf': icon, color = 'picture_as_pdf', 'red'
        elif ext in ['.doc', '.docx']: icon, color = 'description', 'blue'
        return is_img, icon, color

    def get_materials():
        session = PostgresSession()
        try:
            mats = session.query(Material).order_by(Material.id.desc()).all()
            results = []
            for m in mats:
                is_img, icon, color = get_file_meta(m.content, m.category)
                
                file_display = m.content
                if m.category == 'Vocabulary':
                    word_count = len(m.tags.get('words', [])) if m.tags else 0
                    file_display = f"{word_count} palabras"

                results.append({
                    'id': m.id,
                    'title': m.title,
                    'category': m.category,
                    'level': m.level,
                    'date': m.date_up,
                    'file': file_display,
                    'raw_content': m.content, 
                    'is_image': is_img,
                    'icon': icon,
                    'icon_color': color,
                    'tags': m.tags or {}
                })
            return results
        finally:
            session.close()

    # --- LÓGICA DE ELIMINACIÓN ---
    async def delete_material(row_data):
        session = PostgresSession()
        try:
            session.query(Material).filter(Material.id == row_data['id']).delete()
            session.commit()

            if row_data['category'] != 'Vocabulary' and row_data['raw_content']:
                file_path = os.path.join(UPLOAD_DIR, row_data['raw_content'])
                if os.path.exists(file_path):
                    os.remove(file_path)

            ui.notify('Material eliminado correctamente', type='positive')
            table.rows = get_materials()
            table.update()
        except Exception as e:
            ui.notify(f'Error al eliminar: {str(e)}', type='negative')
            session.rollback()
        finally:
            session.close()

    # --- LÓGICA DE SUBIDA DE ARCHIVOS ---
    async def process_upload_to_disk(e):
        try:
            filename = "unknown"
            data = None
            if hasattr(e, 'file'): 
                filename = e.file.name
                data = await e.file.read()
            elif hasattr(e, 'content'):
                filename = getattr(e, 'name', 'file')
                data = e.content.read()
            
            filename = os.path.basename(filename)
            file_path = os.path.join(UPLOAD_DIR, filename)
            
            with open(file_path, 'wb') as f:
                f.write(data)
            return filename
        except Exception as ex:
            ui.notify(f'Error subiendo archivo: {ex}', type='negative')
            return None

    async def handle_upload_event(e):
        if not title_input.value:
            ui.notify('Escribe un título primero', type='warning')
            return
        
        filename = await process_upload_to_disk(e)
        if not filename: return 

        session = PostgresSession()
        try:
            new_mat = Material(
                title=title_input.value, content=filename,
                date_up=datetime.now().strftime("%Y-%m-%d"),
                category=category_input.value, level=level_input.value, tags={}
            )
            session.add(new_mat)
            session.commit()
            ui.notify(f'Guardado: {filename}', type='positive')
            title_input.value = ''
            uploader.reset()
            table.rows = get_materials()
            table.update()
        except Exception as err:
            ui.notify(f'Error DB: {err}', type='negative')
            session.rollback()
        finally:
            session.close()

    def trigger_upload():
        if not title_input.value: 
            ui.notify('Falta el título', type='warning')
            return
        uploader.run_method('upload')

    # --- LÓGICA DE CREACIÓN DE VOCABULARIO ---
    def save_vocabulary():
        if not vocab_title.value or not vocab_words.value:
            ui.notify('Por favor completa el título y las palabras', type='warning')
            return
        
        # APLICAMOS CAPITALIZE A CADA PALABRA AL CREAR EL SET
        words_list = [w.strip().capitalize() for w in re.split(r'[,\n]+', vocab_words.value) if w.strip()]
        
        if not words_list:
            ui.notify('No se detectaron palabras válidas', type='warning')
            return

        session = PostgresSession()
        try:
            new_vocab = Material(
                title=vocab_title.value,
                content="[Set de Audio Interactivo]", 
                date_up=datetime.now().strftime("%Y-%m-%d"),
                category="Vocabulary",
                level=vocab_level.value,
                tags={"words": words_list}
            )
            session.add(new_vocab)
            session.commit()
            ui.notify(f'Vocabulario guardado con {len(words_list)} palabras', type='positive')
            
            vocab_title.value = ''
            vocab_words.value = ''
            table.rows = get_materials()
            table.update()
        except Exception as err:
            ui.notify(f'Error DB: {err}', type='negative')
            session.rollback()
        finally:
            session.close()

    # --- DIÁLOGO DE EDICIÓN DE PALABRAS (CORREGIDO) ---
    def open_edit_words_dialog(row_data):
        tags = row_data.get('tags', {})
        words_list = tags.get('words', [])
        
        # Capturamos el ID del cliente actual para las notificaciones
        client = ui.context.client 

        with ui.dialog() as dialog, ui.card().classes('w-[400px] p-6 rounded-2xl flex flex-col gap-4 bg-white'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('edit_note', size='sm', color='purple')
                    ui.label(f"Editar: {row_data['title']}").classes('text-lg font-bold text-slate-800 line-clamp-1')
                ui.button(icon='close', on_click=dialog.close).props('flat round size=sm color=slate')

            ui.separator()
            words_container = ui.column().classes('w-full max-h-[40vh] overflow-y-auto gap-2 pr-2')

            def save_to_db():
                session = PostgresSession()
                try:
                    mat = session.query(Material).filter_by(id=row_data['id']).first()
                    if mat:
                        mat.tags = {"words": words_list}
                        flag_modified(mat, "tags")
                        session.commit()
                finally: 
                    session.close()
                # Actualizamos la tabla principal
                table.rows = get_materials()
                table.update()

            def render_words():
                words_container.clear()
                with words_container:
                    if not words_list:
                        ui.label('Sin palabras.').classes('text-slate-400 italic text-sm py-4 w-full text-center')
                    for w in words_list:
                        with ui.row().classes('w-full justify-between items-center bg-slate-50 p-2 px-3 rounded-lg border border-slate-100'):
                            ui.label(w).classes('font-medium text-slate-700')
                            # Usamos el cliente capturado para evitar el RuntimeError
                            ui.button(icon='delete', on_click=lambda x=w: remove_word(x)).props('flat round color=red size=sm')

            def add_individual_word():
                new_w = new_word_input.value.strip().capitalize()
                if not new_w: return
                if new_w not in words_list:
                    words_list.append(new_w)
                    save_to_db()
                    render_words()
                    new_word_input.value = ''
                    # Notificación dirigida explícitamente al cliente
                    with client:
                        ui.notify(f'"{new_w}" añadida', type='positive')
                else:
                    with client:
                        ui.notify('Ya existe', type='warning')

            def remove_word(word_to_remove):
                if word_to_remove in words_list:
                    words_list.remove(word_to_remove)
                    save_to_db()
                    render_words()
                    # Notificación dirigida explícitamente al cliente
                    with client:
                        ui.notify('Palabra eliminada', type='info')

            render_words()
            ui.separator()
            with ui.row().classes('w-full items-center gap-2'):
                new_word_input = ui.input('Añadir palabra').classes('flex-grow').props('outlined dense')
                new_word_input.on('keydown.enter', add_individual_word)
                ui.button(icon='add', on_click=add_individual_word).props('unelevated round color=purple')
        
        dialog.open()
        
    # --- LÓGICA DE ASIGNACIÓN ---
    def open_assign_dialog(row_data):
        session = PostgresSession()
        students = session.query(User).filter(User.role == 'client').all()
        session.close()
        options = {s.username: f"{s.name} {s.surname}" for s in students}

        with ui.dialog() as dialog, ui.card().classes('w-96 p-6 rounded-xl'):
            ui.label('Asignar Material').classes('text-xl font-bold')
            ui.label(f"Recurso: {row_data['title']}").classes('text-sm text-gray-500 mb-4')
            select = ui.select(options, multiple=True, label='Estudiantes').classes('w-full').props('use-chips outlined')
            
            def save():
                if not select.value: return
                session = PostgresSession()
                count = 0
                for u in select.value:
                    stu = session.query(User).filter(User.username == u).first()
                    exists = session.query(StudentMaterial).filter_by(username=stu.username, material_id=row_data['id']).first()
                    if not exists:
                        session.add(StudentMaterial(
                            username=stu.username, name=stu.name, surname=stu.surname,
                            material_id=row_data['id'], progress="Not Started"
                        ))
                        count += 1
                session.commit()
                session.close()
                ui.notify(f'Asignado a {count} estudiantes', type='positive')
                dialog.close()
            
            ui.button('Confirmar', on_click=save).props('unelevated color=pink-600').classes('w-full mt-4')
        dialog.open()

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        with ui.row().classes('items-center gap-3 mb-2'):
            with ui.element('div').classes('p-2 bg-indigo-100 rounded-xl'):
                ui.icon('library_books', size='lg', color='indigo-600')
            with ui.column().classes('gap-0'):
                ui.label('Centro de Materiales').classes('text-2xl font-bold text-slate-800')
                ui.label('Crea, sube y asigna recursos a tus alumnos').classes('text-sm text-slate-500')

        # --- PESTAÑAS DE CREACIÓN (MANTENIDAS) ---
        with ui.tabs().classes('w-full') as tabs:
            file_tab = ui.tab('Subir Documentos', icon='upload_file')
            vocab_tab = ui.tab('Crear Vocabulario', icon='record_voice_over')
            
        with ui.tab_panels(tabs, value=file_tab).classes('w-full bg-transparent p-0'):
            
            # PANEL 1: ARCHIVOS
            with ui.tab_panel(file_tab).classes('p-0'):
                with ui.card().classes('w-full bg-white p-6 rounded-2xl shadow-sm border border-slate-100'):
                    with ui.row().classes('w-full gap-6 items-start'):
                        with ui.column().classes('flex-1 gap-4'):
                            title_input = ui.input('Título del Documento').classes('w-full').props('outlined dense')
                            with ui.row().classes('w-full'):
                                category_input = ui.select(['Grammar', 'Reading', 'Exercises'], label='Categoría', value='Grammar').classes('w-1/2').props('outlined dense')
                                level_input = ui.select(['A1', 'A2', 'B1', 'B2', 'C1'], label='Nivel', value='A1').classes('w-1/2').props('outlined dense')
                        with ui.column().classes('flex-1 gap-4'):
                            uploader = ui.upload(label='Archivo PDF, DOC o Imagen', auto_upload=False, on_upload=handle_upload_event).props('flat bordered color=indigo').classes('w-full')
                            ui.button('Subir Archivo', icon='cloud_upload', on_click=trigger_upload).classes('w-full bg-indigo-600 text-white')

            # PANEL 2: VOCABULARIO
            with ui.tab_panel(vocab_tab).classes('p-0'):
                with ui.card().classes('w-full bg-white p-6 rounded-2xl shadow-sm border border-purple-100'):
                    with ui.row().classes('w-full gap-6 items-start'):
                        with ui.column().classes('flex-1 gap-4'):
                            vocab_title = ui.input('Título del Set de Vocabulario').classes('w-full').props('outlined dense')
                            vocab_level = ui.select(['A1', 'A2', 'B1', 'B2', 'C1'], label='Nivel del Vocabulario', value='A1').classes('w-full').props('outlined dense')
                        with ui.column().classes('flex-1 gap-4'):
                            vocab_words = ui.textarea('Palabras (Separadas por comas o saltos de línea)').classes('w-full').props('outlined')
                            ui.button('Guardar Vocabulario', icon='record_voice_over', on_click=save_vocabulary).classes('w-full bg-purple-600 text-white')


        # --- TABLA GLOBAL ---
        ui.label('Biblioteca Global').classes('text-lg font-bold text-slate-700 mt-4')
        
        cols = [
            {'name': 'preview', 'label': '', 'field': 'preview', 'align': 'center'},
            {'name': 'title', 'label': 'RECURSO', 'field': 'title', 'align': 'left'},
            {'name': 'category', 'label': 'INFO', 'field': 'category', 'align': 'left'},
            {'name': 'actions', 'label': 'ACCIONES', 'field': 'actions', 'align': 'right'},
        ]
        
        table = ui.table(columns=cols, rows=get_materials()).classes('w-full').props('flat bordered')

        table.add_slot('body-cell-preview', r'''
            <q-td key="preview" :props="props" style="width: 60px">
                <div class="flex justify-center items-center">
                    <q-avatar v-if="props.row.is_image" rounded size="40px">
                        <img :src="'/uploads/' + props.row.raw_content">
                    </q-avatar>
                    <q-avatar v-else rounded size="40px" :color="props.row.icon_color + '-1'" :text-color="props.row.icon_color">
                        <q-icon :name="props.row.icon" />
                    </q-avatar>
                </div>
            </q-td>
        ''')

        table.add_slot('body-cell-title', r'''
            <q-td key="title" :props="props">
                <div class="font-bold text-slate-700">{{ props.row.title }}</div>
                <div v-if="props.row.category === 'Vocabulary'" class="text-xs text-purple-600 font-medium">{{ props.row.file }}</div>
                <div v-else class="text-xs text-slate-400">{{ props.row.file }}</div>
            </q-td>
        ''')

        table.add_slot('body-cell-category', r'''
            <q-td key="category" :props="props">
                <q-badge :color="props.row.category === 'Vocabulary' ? 'purple-50' : 'indigo-50'" 
                         :text-color="props.row.category === 'Vocabulary' ? 'purple-800' : 'indigo-800'">
                    {{ props.row.category }}
                </q-badge>
                <span class="ml-2 text-xs font-bold text-slate-400">{{ props.row.level }}</span>
            </q-td>
        ''')

        table.add_slot('body-cell-actions', r'''
            <q-td key="actions" :props="props">
                <q-btn icon="send" flat round color="pink" size="sm" @click="$parent.$emit('assign', props.row)">
                    <q-tooltip>Asignar</q-tooltip>
                </q-btn>
                <q-btn v-if="props.row.category === 'Vocabulary'" icon="edit_note" flat round color="purple" size="sm" @click="$parent.$emit('edit_words', props.row)">
                    <q-tooltip>Editar palabras</q-tooltip>
                </q-btn>
                <q-btn v-else icon="visibility" flat round color="grey" size="sm" :href="'/uploads/' + props.row.raw_content" target="_blank">
                    <q-tooltip>Ver archivo</q-tooltip>
                </q-btn>
                <q-btn icon="delete" flat round color="red" size="sm" @click="$parent.$emit('delete', props.row)">
                    <q-tooltip>Eliminar</q-tooltip>
                </q-btn>
            </q-td>
        ''')
        
        table.on('assign', lambda e: open_assign_dialog(e.args))
        table.on('edit_words', lambda e: open_edit_words_dialog(e.args))
        table.on('delete', lambda e: delete_material(e.args))