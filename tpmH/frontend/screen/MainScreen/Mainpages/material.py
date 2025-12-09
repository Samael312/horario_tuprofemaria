from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import Material, StudentMaterial
from components.header import create_main_screen 
import os

@ui.page('/materials')
def student_materials_page():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_main_screen()

    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    username = app.storage.user.get('username')

    # --- HELPER: Detectar Tipo de Archivo ---
    def get_file_type_info(filename):
        """Devuelve configuración visual según la extensión"""
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
                    'level': mat.level
                })
            return data
        except Exception as e:
            print(f"Error: {e}")
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

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-2 bg-indigo-100 rounded-xl'):
                ui.icon('school', size='lg', color='indigo-600')
            with ui.column().classes('gap-0'):
                ui.label('Mis Materiales').classes('text-2xl font-bold text-slate-800')
                ui.label('Recursos de estudio').classes('text-sm text-slate-500')

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
                    
                    # Estilo de borde si está completado
                    card_classes = 'w-full p-0 rounded-2xl shadow-sm border transition-all hover:shadow-md overflow-hidden '
                    card_classes += 'border-green-300 ring-2 ring-green-100' if is_done else 'border-slate-200 bg-white'

                    with ui.card().classes(card_classes):
                        
                        # --- ZONA DE PREVISUALIZACIÓN (PORTADA) ---
                        with ui.element('div').classes('w-full h-32 flex items-center justify-center relative'):
                            if file_info['type'] == 'image':
                                ui.image(f"/uploads/{item['file']}").classes('w-full h-full object-cover')
                            else:
                                with ui.element('div').classes(f"w-full h-full bg-{file_info['color']} flex items-center justify-center"):
                                    ui.icon(file_info['icon'], size='4xl', color=file_info['text'])
                            
                            ui.label(item['level']).classes('absolute top-2 right-2 bg-white/90 px-2 py-1 rounded-md text-xs font-bold shadow-sm')

                        # --- CONTENIDO ---
                        with ui.column().classes('p-4 w-full gap-2'):
                            ui.label(item['category']).classes('text-[10px] font-bold text-indigo-500 uppercase tracking-widest')
                            ui.label(item['title']).classes('font-bold text-slate-800 leading-tight text-sm line-clamp-2 h-10')
                            
                            ui.separator()
                            
                            # --- BARRA DE ACCIONES ---
                            with ui.row().classes('w-full justify-between items-center'):
                                
                                # Grupo de botones izquierda (Abrir y Descargar)
                                with ui.row().classes('gap-1'):
                                    # Botón Abrir
                                    ui.button('Abrir', icon='open_in_new', 
                                              on_click=lambda x=item['file']: ui.navigate.to(f'/uploads/{x}', new_tab=True)) \
                                        .props('flat dense size=sm color=slate no-caps')
                                    
                                    # Botón Descargar (NUEVO)
                                    ui.button(icon='cloud_download', 
                                              on_click=lambda x=item['file']: ui.download(f'/uploads/{x}')) \
                                        .props('flat dense size=sm color=indigo round').tooltip('Descargar archivo')

                                # Botón Estado (Derecha)
                                check_icon = 'check_circle' if is_done else 'radio_button_unchecked'
                                check_col = 'green' if is_done else 'grey'
                                
                                ui.button(icon=check_icon, 
                                          on_click=lambda i=item['link_id'], s=item['progress']: toggle_status(i, s)) \
                                    .props(f'flat round color={check_col}')

        materials_grid()