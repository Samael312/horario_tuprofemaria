import os
import logging
from datetime import datetime
from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import User, Material, StudentMaterial
from components.headerAdmin import create_admin_screen

logger = logging.getLogger(__name__)
UPLOAD_DIR = 'uploads'
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.add_static_files('/uploads', UPLOAD_DIR)

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
    table = None

    # --- HELPER: Detectar si es imagen ---
    def get_file_meta(filename):
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
                is_img, icon, color = get_file_meta(m.content)
                results.append({
                    'id': m.id,
                    'title': m.title,
                    'category': m.category,
                    'level': m.level,
                    'date': m.date_up,
                    'file': m.content,
                    'is_image': is_img,
                    'icon': icon,
                    'icon_color': color
                })
            return results
        finally:
            session.close()

    # --- LÓGICA DE ELIMINACIÓN (NUEVO) ---
    async def delete_material(row_data):
        session = PostgresSession()
        try:
            # 1. Eliminar de la Base de Datos
            session.query(Material).filter(Material.id == row_data['id']).delete()
            session.commit()

            # 2. Eliminar archivo físico (Opcional pero recomendado)
            file_path = os.path.join(UPLOAD_DIR, row_data['file'])
            if os.path.exists(file_path):
                os.remove(file_path)

            ui.notify('Material eliminado correctamente', type='positive')
            
            # 3. Actualizar la UI
            table.rows = get_materials()
            table.update()
            
        except Exception as e:
            ui.notify(f'Error al eliminar: {str(e)}', type='negative')
            session.rollback()
        finally:
            session.close()

    # --- UPLOAD & SAVE ---
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
            
            file_path = os.path.join(UPLOAD_DIR, filename)
            with open(file_path, 'wb') as f:
                f.write(data)
            return filename
        except Exception as ex:
            ui.notify(f'Error: {ex}', type='negative')
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
        finally:
            session.close()

    def trigger_upload():
        if not title_input.value: return
        uploader.run_method('upload')

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
                    session.add(StudentMaterial(
                        username=stu.username, name=stu.name, surname=stu.surname,
                        material_id=row_data['id'], progress="Not Started"
                    ))
                    count += 1
                session.commit()
                session.close()
                ui.notify(f'Asignado a {count}', type='positive')
                dialog.close()
            
            ui.button('Confirmar', on_click=save).props('unelevated color=pink-600').classes('w-full mt-4')
        dialog.open()

    # --- UI ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-2 bg-indigo-100 rounded-xl'):
                ui.icon('library_books', size='lg', color='indigo-600')
            with ui.column().classes('gap-0'):
                ui.label('Biblioteca de Materiales').classes('text-2xl font-bold text-slate-800')
                ui.label('Vista previa y gestión').classes('text-sm text-slate-500')

        # Formulario
        with ui.card().classes('w-full bg-white p-6 rounded-2xl shadow-sm border border-slate-100'):
            with ui.row().classes('w-full gap-6 items-start'):
                with ui.column().classes('flex-1 gap-4'):
                    title_input = ui.input('Título').classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full'):
                        category_input = ui.select(['Grammar', 'Vocabulary', 'Reading'], label='Categoría', value='Grammar').classes('w-1/2').props('outlined dense')
                        level_input = ui.select(['A1', 'A2', 'B1', 'B2'], label='Nivel', value='A1').classes('w-1/2').props('outlined dense')
                with ui.column().classes('flex-1 gap-4'):
                    uploader = ui.upload(label='Archivo', auto_upload=False, on_upload=handle_upload_event).props('flat bordered color=indigo').classes('w-full')
                    ui.button('Guardar', icon='cloud_upload', on_click=trigger_upload).classes('w-full bg-indigo-600 text-white')

        # Tabla
        cols = [
            {'name': 'preview', 'label': '', 'field': 'preview', 'align': 'center'},
            {'name': 'title', 'label': 'RECURSO', 'field': 'title', 'align': 'left'},
            {'name': 'category', 'label': 'INFO', 'field': 'category', 'align': 'left'},
            {'name': 'actions', 'label': 'ACCIONES', 'field': 'actions', 'align': 'right'},
        ]
        
        table = ui.table(columns=cols, rows=get_materials()).classes('w-full').props('flat')

        # Slots
        table.add_slot('body-cell-preview', r'''
            <q-td key="preview" :props="props" style="width: 60px">
                <div class="flex justify-center items-center">
                    <q-avatar v-if="props.row.is_image" rounded size="40px">
                        <img :src="'/uploads/' + props.row.file">
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
                <div class="text-xs text-slate-400">{{ props.row.file }}</div>
            </q-td>
        ''')

        table.add_slot('body-cell-category', r'''
            <q-td key="category" :props="props">
                <q-badge color="indigo-50" text-color="indigo-800">{{ props.row.category }}</q-badge>
                <span class="ml-2 text-xs font-bold text-slate-400">{{ props.row.level }}</span>
            </q-td>
        ''')

        # Slot MODIFICADO: Agregado botón delete
        table.add_slot('body-cell-actions', r'''
            <q-td key="actions" :props="props">
                <q-btn icon="send" flat round color="pink" size="sm" @click="$parent.$emit('assign', props.row)" />
                <q-btn icon="visibility" flat round color="grey" size="sm" :href="'/uploads/' + props.row.file" target="_blank" />
                <q-btn icon="delete" flat round color="red" size="sm" @click="$parent.$emit('delete', props.row)" />
            </q-td>
        ''')
        
        # Conexión de eventos
        table.on('assign', lambda e: open_assign_dialog(e.args))
        table.on('delete', lambda e: delete_material(e.args)) # Nuevo evento