from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import HWork, StudentHWork
from components.header import create_main_screen
import json

@ui.page('/StudentHomework')
def student_homework_page():
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_main_screen()

    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    username = app.storage.user.get('username')

    # --- HELPER: Obtener Tareas ---
    def get_tasks(view_type):
        session = PostgresSession()
        try:
            # view_type: 'Pending' o 'History'
            query = session.query(StudentHWork, HWork)\
                .join(HWork, StudentHWork.homework_id == HWork.id)\
                .filter(StudentHWork.username == username)
            
            if view_type == 'Pending':
                # Solo traemos las que están estrictamente pendientes
                query = query.filter(StudentHWork.status == 'Pending')
            else:
                # Historial: Enviadas, Completadas o Calificadas
                query = query.filter(StudentHWork.status != 'Pending')
            
            # Ordenar: Pendientes por fecha de vencimiento más cercana, Historial por ID desc
            if view_type == 'Pending':
                results = query.order_by(HWork.date_due.asc()).all()
            else:
                results = query.order_by(StudentHWork.id.desc()).all()
            
            data = []
            for st_hw, hw in results:
                # Manejo seguro del JSON Grade
                grade_data = {}
                if st_hw.grade:
                    if isinstance(st_hw.grade, dict):
                        grade_data = st_hw.grade
                    elif isinstance(st_hw.grade, str):
                        try:
                            grade_data = json.loads(st_hw.grade)
                        except:
                            grade_data = {"nota": st_hw.grade} # Fallback si era string antiguo

                data.append({
                    'id': st_hw.id, 
                    'title': hw.title,
                    'content': hw.content,
                    'due_date': hw.date_due,
                    'status': st_hw.status,
                    'submission': st_hw.submission,
                    'grade_info': grade_data 
                })
            return data
        finally:
            session.close()

    # --- ACCIÓN: Enviar Tarea ---
    def open_solve_dialog(task):
        with ui.dialog() as d, ui.card().classes('w-full max-w-2xl p-6 rounded-2xl'):
            # Header
            with ui.row().classes('justify-between w-full items-start'):
                with ui.column().classes('gap-1'):
                    ui.label(task['title']).classes('text-xl font-bold text-slate-800')
                    ui.label(f"Vence el: {task['due_date']}").classes('text-sm text-red-500 font-medium')
                ui.button(icon='close', on_click=d.close).props('flat round color=slate')

            ui.separator().classes('my-4')
            
            ui.label('Instrucciones:').classes('font-bold text-slate-600')
            with ui.scroll_area().classes('h-32 w-full bg-slate-50 p-4 rounded-lg border border-slate-100 mb-4'):
                ui.markdown(task['content'])
            
            ui.label('Tu Respuesta:').classes('font-bold text-slate-600')
            response_input = ui.textarea(placeholder='Escribe aquí tu respuesta...').props('outlined rows=6').classes('w-full')

            def submit():
                if not response_input.value:
                    ui.notify('Escribe una respuesta antes de enviar', type='warning')
                    return
                
                session = PostgresSession()
                try:
                    st_hw = session.query(StudentHWork).filter(StudentHWork.id == task['id']).first()
                    if st_hw:
                        st_hw.submission = response_input.value
                        # --- CAMBIO IMPORTANTE: Al enviar pasa a 'Submitted' ---
                        st_hw.status = "Submitted" 
                        session.commit()
                        ui.notify('¡Tarea enviada! Se ha movido al historial.', type='positive')
                        d.close()
                        refresh_ui() # Esto hará que desaparezca de Pendientes y salga en Historial
                finally:
                    session.close()

            ui.button('Enviar y Marcar como Completada', icon='send', on_click=submit).classes('w-full bg-pink-600 text-white mt-2')
        d.open()

    # --- LISTA PENDIENTES ---
    def render_pending_list():
        tasks = get_tasks('Pending')
        if not tasks:
            with ui.column().classes('w-full items-center justify-center py-8'):
                ui.icon('check_circle', size='3xl', color='green-200')
                ui.label('¡Todo al día! No tienes tareas pendientes.').classes('text-slate-400 italic mt-2')
            return

        with ui.column().classes('w-full gap-4'):
            for t in tasks:
                # Tarjeta Pendiente
                with ui.card().classes('w-full p-4 rounded-xl border-l-4 border-pink-500 shadow-sm flex-row justify-between items-center bg-white'):
                    with ui.column().classes('gap-1'):
                        ui.label(t['title']).classes('font-bold text-slate-800 text-lg')
                        
                        # --- CAMBIO: Fecha y Estado juntos ---
                        with ui.row().classes('items-center gap-2'):
                            # Fecha
                            with ui.row().classes('items-center gap-1 bg-slate-100 px-2 py-1 rounded text-xs text-slate-600'):
                                ui.icon('event', size='xs')
                                ui.label(f"Vence: {t['due_date']}")
                            
                            # Estado (Siempre será Pending aquí, pero lo mostramos)
                            ui.badge(t['status'], color='orange').props('outline').classes('text-xs')
                    
                    ui.button('Resolver', icon='edit', on_click=lambda x=t: open_solve_dialog(x))\
                        .classes('bg-pink-50 text-pink-600 shadow-none border border-pink-100 hover:bg-pink-100')

    # --- LISTA HISTORIAL ---
    def render_history_list():
        tasks = get_tasks('History')
        if not tasks:
            ui.label('No hay tareas en el historial.').classes('text-slate-400 italic')
            return

        with ui.column().classes('w-full gap-4'):
            for t in tasks:
                is_graded = t['status'] == 'Graded'
                # Color del badge según estado
                if is_graded: 
                    badge_col, badge_txt = 'green', 'Calificada'
                else: 
                    badge_col, badge_txt = 'blue', 'Enviada'
                
                with ui.card().classes(f'w-full p-4 rounded-xl border border-slate-100 bg-slate-50'):
                    # Cabecera Card
                    with ui.row().classes('justify-between items-start w-full'):
                        with ui.column().classes('gap-1'):
                            ui.label(t['title']).classes('font-bold text-slate-700')
                            # Fecha y Estado juntos también en historial
                            with ui.row().classes('items-center gap-2'):
                                ui.label(f"Enviada el: {t['due_date']}").classes('text-xs text-slate-400') # O fecha de submission si la tuvieras
                                ui.badge(badge_txt, color=badge_col).classes('text-xs')
                        
                        # Icono decorativo
                        ui.icon('verified' if is_graded else 'send', color=badge_col, size='md').classes('opacity-20')
                    
                    # Si está calificada, mostramos el JSON desglosado
                    if is_graded:
                        ui.separator().classes('my-2')
                        grade_info = t.get('grade_info', {})
                        
                        # Asumimos que el JSON tiene claves como 'nota', 'feedback', etc.
                        # Si no tiene estructura fija, iteramos:
                        with ui.column().classes('w-full bg-white p-3 rounded border border-green-100 gap-1'):
                            ui.label('Retroalimentación de la Profesora:').classes('text-xs font-bold text-green-800 mb-1')
                            
                            if not grade_info:
                                ui.label("Sin detalles adicionales.").classes('text-sm text-slate-500')
                            else:
                                for key, val in grade_info.items():
                                    with ui.row().classes('items-start gap-2 w-full'):
                                        # Capitalizamos la clave (ej: nota -> Nota)
                                        ui.label(f"{key.capitalize()}:").classes('text-xs font-bold text-slate-600 w-24')
                                        ui.label(str(val)).classes('text-sm text-slate-800 flex-1')

    # --- REFRESCADOR DE UI ---
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

    # --- LAYOUT PRINCIPAL ---
    with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-2 bg-orange-100 rounded-xl'):
                ui.icon('assignment', size='lg', color='orange-600')
            with ui.column().classes('gap-0'):
                ui.label('Mis Tareas').classes('text-2xl font-bold text-slate-800')
                ui.label('Resuelve tus actividades y revisa tus notas').classes('text-sm text-slate-500')

        refresh_ui()