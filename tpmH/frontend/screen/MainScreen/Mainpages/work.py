from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import HWork, StudentHWork
from components.header import create_main_screen
import json

@ui.page('/StudentHomework')
def student_homework_page():
    # Estilos básicos
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_main_screen()

    # Verificar Auth
    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    username = app.storage.user.get('username')

    # 1. Función para obtener datos
    def get_tasks(view_type):
        session = PostgresSession()
        try:
            query = session.query(StudentHWork, HWork)\
                .join(HWork, StudentHWork.homework_id == HWork.id)\
                .filter(StudentHWork.username == username)
            
            if view_type == 'Pending':
                query = query.filter(StudentHWork.status == 'Pending')
                results = query.order_by(HWork.date_due.asc()).all()
            else:
                query = query.filter(StudentHWork.status != 'Pending')
                results = query.order_by(StudentHWork.id.desc()).all()
            
            data = []
            for st_hw, hw in results:
                grade_data = {}
                if st_hw.grade:
                    if isinstance(st_hw.grade, dict):
                        grade_data = st_hw.grade
                    elif isinstance(st_hw.grade, str):
                        try: grade_data = json.loads(st_hw.grade)
                        except: grade_data = {"nota": st_hw.grade}

                data.append({
                    'id': st_hw.id, 
                    'title': hw.title,
                    'content': hw.content, # Aquí traemos las instrucciones
                    'due_date': hw.date_due,
                    'status': st_hw.status,
                    'submission': st_hw.submission, # Aquí traemos la respuesta
                    'grade_info': grade_data 
                })
            return data
        except Exception as e:
            ui.notify(f"Error cargando tareas: {e}", type='negative')
            return []
        finally:
            session.close()

    # 2. Renderizar lista de pendientes
    def render_pending_list():
        tasks = get_tasks('Pending')
        if not tasks:
            with ui.column().classes('w-full items-center justify-center py-8'):
                ui.icon('check_circle', size='3xl', color='green-200')
                ui.label('¡Todo al día! No tienes tareas pendientes.').classes('text-slate-400 italic mt-2')
            return

        with ui.column().classes('w-full gap-4'):
            for t in tasks:
                with ui.card().classes('w-full p-4 rounded-xl border-l-4 border-pink-500 shadow-sm flex-row justify-between items-center bg-white'):
                    with ui.column().classes('gap-1'):
                        ui.label(t['title']).classes('font-bold text-slate-800 text-lg')
                        with ui.row().classes('items-center gap-2'):
                            with ui.row().classes('items-center gap-1 bg-slate-100 px-2 py-1 rounded text-xs text-slate-600'):
                                ui.icon('event', size='xs')
                                ui.label(f"Vence: {t['due_date']}")
                            ui.badge(t['status'], color='orange').props('outline').classes('text-xs')
                    
                    ui.button('Resolver', icon='edit', on_click=lambda x=t: open_solve_dialog(x))\
                        .classes('bg-pink-50 text-pink-600 shadow-none border border-pink-100 hover:bg-pink-100')

    # 3. Renderizar historial (AQUÍ ESTÁ EL CAMBIO PRINCIPAL)
    def render_history_list():
        tasks = get_tasks('History')
        if not tasks:
            ui.label('No hay tareas en el historial.').classes('text-slate-400 italic')
            return

        with ui.column().classes('w-full gap-4'):
            for t in tasks:
                is_graded = t['status'] == 'Graded'
                badge_col = 'green' if is_graded else 'blue'
                badge_txt = 'Calificada' if is_graded else 'Enviada'
                
                with ui.card().classes('w-full p-0 rounded-xl border border-slate-200 overflow-hidden shadow-sm'):
                    # --- Header de la tarjeta ---
                    with ui.row().classes('w-full p-4 bg-slate-50 justify-between items-center border-b border-slate-100'):
                        with ui.column().classes('gap-0'):
                            ui.label(t['title']).classes('font-bold text-slate-700 text-lg')
                            ui.label(f"Fecha límite: {t['due_date']}").classes('text-xs text-slate-400')
                        
                        with ui.row().classes('items-center gap-2'):
                            ui.badge(badge_txt, color=badge_col).classes('text-xs font-bold')
                            ui.icon('verified' if is_graded else 'send', color=badge_col, size='sm')

                    # --- Cuerpo de la tarjeta ---
                    with ui.column().classes('w-full p-4 gap-4'):
                        
                        # >>> NUEVO: SI ESTÁ CALIFICADA, MOSTRAMOS CONTENIDO Y RESPUESTA <<<
                        if is_graded:
                            with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 gap-4'):
                                # Columna 1: Instrucciones
                                with ui.column().classes('gap-1 w-full'):
                                    ui.label('Instrucciones Originales').classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider')
                                    with ui.scroll_area().classes('h-32 w-full bg-slate-50 border border-slate-100 rounded p-2'):
                                        ui.markdown(t['content'] or 'Sin contenido').classes('text-sm text-slate-600')
                                
                                # Columna 2: Respuesta del alumno
                                with ui.column().classes('gap-1 w-full'):
                                    ui.label('Tu Respuesta Enviada').classes('text-[10px] font-bold text-blue-400 uppercase tracking-wider')
                                    with ui.scroll_area().classes('h-32 w-full bg-blue-50 border border-blue-100 rounded p-2'):
                                        ui.label(t['submission']).classes('text-sm text-slate-800').style('white-space: pre-wrap;')
                            
                            ui.separator()

                        # --- Zona de Calificación ---
                        if is_graded:
                            grade_info = t.get('grade_info', {})
                            with ui.row().classes('w-full items-start gap-4'):
                                # Nota Grande
                                score = grade_info.get('score', '-')
                                with ui.column().classes('items-center justify-center bg-green-50 p-4 rounded-xl border border-green-100 min-w-[100px]'):
                                    ui.label(str(score)).classes('text-3xl font-black text-green-600 leading-none')
                                    ui.label('Nota Final').classes('text-[10px] uppercase text-green-800 font-bold')

                                # Feedback texto
                                with ui.column().classes('flex-1 gap-1'):
                                    ui.label('Retroalimentación del profesor:').classes('text-xs font-bold text-slate-500')
                                    feedback = grade_info.get('feedback', 'Sin comentarios adicionales.')
                                    ui.label(feedback).classes('text-sm text-slate-700 italic bg-white p-2 rounded w-full')
                        else:
                            # Si solo está enviada pero no calificada
                            with ui.row().classes('w-full justify-center py-2 text-slate-400 gap-2 items-center'):
                                ui.icon('hourglass_top')
                                ui.label('Esperando revisión del profesor...')

    # 4. COMPONENTE REFRESCASE
    @ui.refreshable
    def refresh_ui():
        with ui.tabs().classes('w-full text-slate-600') as tabs:
            tab_pending = ui.tab('Pendientes', icon='assignment_late')
            tab_history = ui.tab('Historial', icon='history')

        with ui.tab_panels(tabs, value=tab_pending).classes('w-full bg-transparent'):
            with ui.tab_panel(tab_pending):
                render_pending_list()
            with ui.tab_panel(tab_history):
                render_history_list()

    # 5. DIÁLOGO DE ENVÍO
    def open_solve_dialog(task):
        with ui.dialog() as d, ui.card().classes('w-full max-w-3xl p-0 rounded-2xl overflow-hidden'):
            # Header del diálogo
            with ui.row().classes('w-full bg-slate-50 p-6 border-b border-slate-100 justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label(task['title']).classes('text-xl font-bold text-slate-800')
                    ui.label('Completa la actividad a continuación').classes('text-sm text-slate-500')
                ui.button(icon='close', on_click=d.close).props('flat round color=slate')

            # Contenido scrollable
            with ui.scroll_area().classes('w-full h-[60vh] p-6'):
                ui.label('Instrucciones:').classes('font-bold text-slate-700 mb-2')
                ui.markdown(task['content']).classes('text-slate-600 bg-slate-50 p-4 rounded-xl border border-slate-100 mb-6')
                
                ui.separator().classes('mb-6')
                
                ui.label('Tu Respuesta:').classes('font-bold text-slate-700 mb-2')
                response_input = ui.textarea(placeholder='Escribe tu desarrollo aquí...').props('outlined rows=8').classes('w-full')

            # Footer con botón
            with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 justify-end'):
                def submit():
                    if not response_input.value:
                        ui.notify('Escribe una respuesta', type='warning')
                        return
                    
                    session = PostgresSession()
                    try:
                        st_hw = session.query(StudentHWork).filter(StudentHWork.id == task['id']).first()
                        if st_hw:
                            st_hw.submission = response_input.value
                            st_hw.status = "Submitted"
                            session.commit()
                            ui.notify('Tarea enviada correctamente', type='positive', icon='send')
                            d.close()
                            refresh_ui.refresh()
                    except Exception as e:
                        session.rollback()
                        ui.notify(f'Error al enviar: {e}', type='negative')
                    finally:
                        session.close()

                ui.button('Enviar Tarea', icon='send', on_click=submit)\
                    .props('unelevated color=pink-600 no-caps').classes('px-8')
        
        d.open()

    # --- LAYOUT PRINCIPAL ---
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-3 bg-orange-100 rounded-2xl'):
                ui.icon('assignment', size='md', color='orange-600')
            with ui.column().classes('gap-0'):
                ui.label('Mis Tareas').classes('text-2xl font-bold text-slate-800')
                ui.label('Resuelve tus actividades y revisa tus notas').classes('text-sm text-slate-500')

        refresh_ui()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()