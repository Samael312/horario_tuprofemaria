from nicegui import ui, app
from db.postgres_db import PostgresSession
from db.models import User, HWork, StudentHWork
from components.headerAdmin import create_admin_screen
from datetime import datetime
import json

@ui.page('/WorkAdmin')
def homework_page():
    # --- CONFIGURACIÓN INICIAL ---
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    create_admin_screen()

    if not app.storage.user.get('authenticated', False):
        ui.navigate.to('/login')
        return

    current_username = app.storage.user.get('username')

    # =================================================================
    # 1. PESTAÑA: DASHBOARD DE GESTIÓN (KPIs + LISTA)
    # =================================================================
    def grading_ui():
        
        state = {
            'filter': 'submitted',
            'search': ''
        }

        # --- Helper: Obtener y Clasificar Datos ---
        def get_data():
            session = PostgresSession()
            try:
                results = session.query(StudentHWork, HWork).join(HWork, StudentHWork.homework_id == HWork.id).all()
                
                pending = []
                submitted = []
                graded = []
                overdue = []

                today_str = datetime.now().strftime("%Y-%m-%d")

                for shw, hw in results:
                    grade_data = shw.grade
                    if isinstance(grade_data, str):
                        try: grade_data = json.loads(grade_data)
                        except: grade_data = {}
                    if not isinstance(grade_data, dict): grade_data = {}

                    is_overdue = (hw.date_due < today_str) and (shw.status == 'Pending')
                    
                    row = {
                        'id': shw.id, 
                        'homework_id': hw.id,
                        'student': f"{shw.name} {shw.surname}", 
                        'title': hw.title,
                        'due_date': hw.date_due, 
                        'submission': shw.submission, 
                        'status': shw.status,
                        'full_grade_json': grade_data, 
                        'is_overdue': is_overdue
                    }

                    if shw.status == 'Graded':
                        graded.append(row)
                    elif shw.status == 'Submitted':
                        submitted.append(row)
                    elif is_overdue:
                        overdue.append(row)
                    else:
                        pending.append(row)
                
                submitted.sort(key=lambda x: x['due_date'])
                pending.sort(key=lambda x: x['due_date'])
                graded.sort(key=lambda x: x['due_date'], reverse=True)

                return pending, submitted, graded, overdue
            finally:
                session.close()

        # --- Diálogo de Evaluación ---
        def open_grade_dialog(row):
            # Validación: Si está pendiente y NO está vencida, avisar y salir.
            if row['status'] == 'Pending' and not row['is_overdue']:
                ui.notify('El estudiante aún no ha realizado esta actividad.', type='warning', icon='hourglass_empty')
                return

            with ui.dialog() as d, ui.card().classes('w-full max-w-2xl p-0 rounded-2xl overflow-hidden shadow-xl'):
                
                # Header
                with ui.row().classes('w-full bg-slate-50 p-6 items-center justify-between border-b border-slate-100'):
                    with ui.row().classes('items-center gap-4'):
                        with ui.element('div').classes('bg-pink-100 p-3 rounded-full'):
                            ui.icon('school', color='pink-600', size='sm')
                        with ui.column().classes('gap-0'):
                            ui.label(row['student']).classes('text-lg font-bold text-slate-800 leading-tight')
                            ui.label(f"Tarea: {row['title']}").classes('text-sm text-slate-500')
                    ui.button(icon='close', on_click=d.close).props('flat round dense color=slate')

                # Contenido
                with ui.column().classes('w-full p-6 gap-6'):
                    
                    # --- SECCIÓN VENCIMIENTO (Solo si está vencida) ---
                    new_date_input = None 
                    if row['is_overdue']:
                        with ui.card().classes('w-full bg-red-50 border border-red-200 p-4'):
                            with ui.row().classes('items-center gap-2'):
                                ui.icon('event_busy', color='red-500')
                                ui.label('Esta tarea está vencida.').classes('text-red-700 font-bold')
                            
                            ui.label('Puedes extender la fecha límite para permitir la entrega:').classes('text-sm text-red-600 mt-1')
                            
                            with ui.input('Nueva Fecha de Vencimiento', value=row['due_date']).props('outlined dense bg-white') as new_date_input:
                                with ui.menu().props('no-parent-event') as menu:
                                    with ui.date().bind_value(new_date_input).on('input', menu.close): pass
                                with new_date_input.add_slot('append'):
                                    ui.icon('edit_calendar').classes('cursor-pointer').on('click', menu.open)

                    # --- RESPUESTA DEL ESTUDIANTE ---
                    with ui.column().classes('w-full gap-2'):
                        ui.label('Respuesta del Estudiante').classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
                        if row['submission']:
                            with ui.scroll_area().classes('h-40 w-full bg-slate-50 border border-slate-200 rounded-xl p-4'):
                                ui.label(row['submission']).classes('text-slate-700 font-medium leading-relaxed')\
                                    .style('white-space: pre-wrap; font-family: sans-serif;')
                        else:
                            msg = "Sin entrega (Vencida)" if row['is_overdue'] else "El estudiante no envió texto"
                            color_icon = "red-300" if row['is_overdue'] else "slate-300"
                            with ui.row().classes('w-full h-24 items-center justify-center bg-slate-50 rounded-xl border border-dashed'):
                                ui.icon('assignment_late', color=color_icon, size='md')
                                ui.label(msg).classes('text-slate-400 text-sm')

                    ui.separator()

                    # --- FORMULARIO DE EVALUACIÓN ---
                    existing_data = row['full_grade_json']
                    current_score = existing_data.get('score') # Devuelve None si no existe, evita ValueError
                    
                    with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 gap-4'):
                        score_input = ui.number('Nota (Max 10)', value=current_score, min=0, max=10)\
                            .props('outlined dense prepend-icon=star color=amber-800').classes('w-full')
                        
                        status_select = ui.select(['Pending', 'Submitted', 'Graded'], value='Graded', label='Estado')\
                            .props('outlined dense prepend-icon=verified color=green').classes('w-full')

                    feedback_input = ui.textarea('Retroalimentación', value=existing_data.get('feedback', ''))\
                        .props('outlined rows=3 prepend-icon=chat_bubble_outline color=indigo').classes('w-full')

                # Footer
                with ui.row().classes('w-full p-4 bg-slate-50 border-t border-slate-100 justify-end gap-3'):
                    ui.button('Cancelar', on_click=d.close).props('flat color=slate no-caps')
                    
                    def save():
                        session = PostgresSession()
                        try:
                            # 1. Actualizar Fecha
                            if new_date_input and new_date_input.value != row['due_date']:
                                hw_master = session.query(HWork).filter(HWork.id == row['homework_id']).first()
                                if hw_master:
                                    hw_master.date_due = new_date_input.value
                                    ui.notify(f'Fecha extendida a: {new_date_input.value}', type='info')
                            
                            # 2. Guardar Nota
                            item = session.query(StudentHWork).filter(StudentHWork.id == row['id']).first()
                            if item:
                                if score_input.value is not None:
                                    try:
                                        val = float(score_input.value)
                                        if val < 0 or val > 10:
                                            ui.notify('Nota inválida (0-10)', type='negative')
                                            return
                                    except: pass

                                new_grade_json = {
                                    "score": score_input.value if score_input.value is not None else "",
                                    "feedback": feedback_input.value,
                                    "graded_at": datetime.now().strftime("%Y-%m-%d %H:%M")
                                }
                                item.grade = new_grade_json
                                item.status = status_select.value
                                
                                session.commit()
                                ui.notify('Cambios guardados', type='positive', icon='check_circle')
                                refresh_dashboard.refresh()
                                d.close()
                                
                        except Exception as e:
                            ui.notify(f'Error al guardar: {e}', type='negative')
                        finally:
                            session.close()

                    ui.button('Guardar Cambios', on_click=save, icon='save')\
                        .props('unelevated color=green-600 no-caps').classes('px-6 shadow-lg shadow-green-100')
            d.open()

        # --- Componente Visual: Tarjeta de Tarea ---
        def render_task_card(task):
            try:
                dt = datetime.strptime(task['due_date'], '%Y-%m-%d')
                day = dt.strftime('%d')
                month = dt.strftime('%b')
            except: day, month = "??", "??"

            status = task['status']
            
            if status == 'Graded':
                border_col, bg_col, text_col, icon, label = 'border-green-500', 'bg-green-50', 'text-green-700', 'verified', 'Calificada'
            elif status == 'Submitted':
                border_col, bg_col, text_col, icon, label = 'border-blue-500', 'bg-blue-50', 'text-blue-700', 'send', 'Por Revisar'
            elif task['is_overdue']:
                border_col, bg_col, text_col, icon, label = 'border-red-400', 'bg-red-50', 'text-red-700', 'event_busy', 'Vencida'
            else: 
                border_col, bg_col, text_col, icon, label = 'border-orange-400', 'bg-orange-50', 'text-orange-700', 'hourglass_empty', 'Pendiente'

            with ui.card().classes('w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-row overflow-hidden group hover:shadow-md transition-all'):
                # Franja Fecha
                with ui.column().classes(f'w-24 justify-center items-center bg-slate-50 border-r-4 {border_col} p-4 gap-0'):
                    ui.label(day).classes('text-3xl font-bold text-slate-700 leading-none')
                    ui.label(month).classes('text-xs font-bold uppercase text-slate-400 mt-1')
                
                # Info Principal
                with ui.column().classes('flex-1 p-4 justify-center gap-1'):
                    with ui.row().classes('items-center gap-2 flex-wrap'):
                        ui.label(task['student']).classes('text-lg font-bold text-slate-800')
                        ui.label(label).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_col} {text_col}')
                    
                    ui.label(task['title']).classes('text-sm text-slate-500 font-medium line-clamp-1')

                    # Footer Card
                    with ui.row().classes('items-center gap-4 text-xs text-slate-400 mt-1'):
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('event', size='xs')
                            ui.label(f"Vence: {task['due_date']}")
                        
                        score = task['full_grade_json'].get('score')
                        if score:
                            with ui.row().classes('items-center gap-1 text-amber-600 font-bold'):
                                ui.icon('star', size='xs')
                                ui.label(f"Nota: {score}/10")

                # Botón Acción
                with ui.column().classes('justify-center pr-4'):
                    ui.button(icon='edit_note', on_click=lambda t=task: open_grade_dialog(t))\
                        .props('flat round color=slate size=lg')\
                        .classes('text-slate-300 hover:text-indigo-600 transition-colors')

        # --- KPI Card ---
        def render_kpi_card(label, count, icon, color_base, filter_key):
            is_active = state['filter'] == filter_key
            if is_active:
                bg = f"bg-{color_base}-600 text-white shadow-lg shadow-{color_base}-200 scale-105"
                text_c, icon_c = "text-white", "text-white"
            else:
                bg = f"bg-white text-slate-600 border border-slate-100 hover:border-{color_base}-300 hover:bg-{color_base}-50"
                text_c, icon_c = f"text-{color_base}-600", f"text-{color_base}-400"
            
            # Usamos w-full para que ocupe el ancho de la celda del grid
            with ui.card().classes(f'w-full p-4 rounded-2xl cursor-pointer transition-all duration-200 {bg}') \
                    .on('click', lambda: set_filter(filter_key)):
                with ui.row().classes('w-full justify-between items-center'):
                    with ui.column().classes('gap-0'):
                        ui.label(str(count)).classes(f'text-3xl font-black leading-none {text_count_class(is_active, color_base)}')
                        ui.label(label).classes('text-xs font-bold uppercase tracking-wider opacity-80')
                    ui.icon(icon, size='md').classes(f'{icon_c}')

        def text_count_class(active, color):
            return "text-white" if active else f"text-{color}-600"

        def set_filter(key):
            state['filter'] = key
            refresh_dashboard.refresh()

        def update_search(val):
            state['search'] = val
            refresh_dashboard.refresh()

        # --- DASHBOARD ---
        @ui.refreshable
        def refresh_dashboard():
            pending, submitted, graded, overdue = get_data()
            
            # === SOLUCIÓN DE DISEÑO AQUÍ ===
            # Cambiamos ui.row por ui.grid.
            # grid-cols-1 en móvil, 2 en tablet, 4 en PC. 
            # Esto evita que se aplasten las tarjetas.
            with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6'):
                render_kpi_card('Por Revisar', len(submitted), 'assignment_late', 'blue', 'submitted')
                render_kpi_card('Pendientes', len(pending), 'hourglass_empty', 'orange', 'pending')
                render_kpi_card('Vencidas', len(overdue), 'event_busy', 'red', 'overdue')
                render_kpi_card('Historial', len(graded), 'inventory_2', 'slate', 'history')

            with ui.row().classes('w-full items-center justify-between mb-4'):
                titles = {
                    'submitted': 'Entregas listas para calificar',
                    'pending': 'Tareas en curso (Pendientes)',
                    'overdue': 'Tareas vencidas sin entrega',
                    'history': 'Historial de calificaciones'
                }
                ui.label(titles.get(state['filter'])).classes('text-xl font-bold text-slate-700')
                ui.input(placeholder='Buscar...', on_change=lambda e: update_search(e.value))\
                    .props('outlined dense rounded prepend-icon=search').classes('w-64 bg-white')

            current_data = []
            if state['filter'] == 'submitted': current_data = submitted
            elif state['filter'] == 'pending': current_data = pending
            elif state['filter'] == 'overdue': current_data = overdue
            elif state['filter'] == 'history': current_data = graded
            
            if state['search']:
                s = state['search'].lower()
                current_data = [x for x in current_data if s in x['student'].lower() or s in x['title'].lower()]

            if not current_data:
                with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-2xl border border-dashed border-slate-200'):
                    ui.icon('inbox', size='4xl', color='slate-200')
                    ui.label('No hay tareas en esta sección').classes('text-slate-400 font-bold mt-2')
            else:
                with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-2 gap-4'):
                    for t in current_data:
                        render_task_card(t)

        refresh_dashboard()

    # =================================================================
    # 2. PESTAÑA: CREAR TAREA
    # =================================================================
    def create_homework_ui():
        with ui.column().classes('w-full max-w-4xl mx-auto gap-6'):
            with ui.card().classes('w-full bg-white p-8 rounded-2xl shadow-sm border border-slate-100'):
                ui.label('Redactar Nueva Actividad').classes('text-xl font-bold text-slate-800 mb-4')
                
                with ui.column().classes('w-full gap-4'):
                    with ui.row().classes('w-full gap-4'):
                        hw_title = ui.input('Título de la Tarea').classes('flex-grow').props('outlined dense')
                        with ui.input('Fecha Límite').classes('w-48').props('outlined dense') as date_input:
                            with ui.menu().props('no-parent-event') as menu:
                                with ui.date().bind_value(date_input).on('input', menu.close): pass
                            with date_input.add_slot('append'):
                                ui.icon('event').classes('cursor-pointer text-slate-500').on('click', menu.open)

                    hw_content = ui.textarea('Instrucciones detalladas').classes('w-full').props('rows=6 outlined')
                
                ui.separator().classes('my-4')
                ui.label('Asignar a Estudiantes').classes('font-bold text-slate-700')
                
                session = PostgresSession()
                students = session.query(User).filter(User.role == 'client').all()
                teacher_obj = session.query(User).filter(User.username == current_username).first()
                session.close()

                student_opts = {s.username: f"{s.name} {s.surname}" for s in students}
                student_select = ui.select(student_opts, multiple=True, label='Seleccionar Alumnos')\
                    .classes('w-full').props('outlined use-chips behavior=menu')

                def save_and_assign():
                    if not hw_title.value or not student_select.value:
                        ui.notify('Falta título o alumnos', type='warning')
                        return
                    
                    session = PostgresSession()
                    try:
                        master_hw = HWork(
                            username=teacher_obj.username,
                            name=teacher_obj.name or "",
                            surname=teacher_obj.surname or "",
                            title=hw_title.value,
                            content=hw_content.value,
                            date_assigned=datetime.now().strftime("%Y-%m-%d"),
                            date_due=date_input.value,
                            status="Template",
                            tagsW={}
                        )
                        session.add(master_hw)
                        session.flush() 
                        
                        count = 0
                        for username in student_select.value:
                            stu = session.query(User).filter(User.username == username).first()
                            assign = StudentHWork(
                                username=stu.username, name=stu.name, surname=stu.surname,
                                homework_id=master_hw.id, submission="", status="Pending", grade={} 
                            )
                            session.add(assign)
                            count += 1
                        
                        session.commit()
                        ui.notify(f'¡Tarea enviada a {count} alumnos!', type='positive', icon='send')
                        hw_title.value = ''
                        hw_content.value = ''
                        student_select.value = []
                    except Exception as e:
                        ui.notify(f'Error: {e}', type='negative')
                    finally:
                        session.close()

                with ui.row().classes('w-full justify-end mt-4'):
                    ui.button('Crear y Asignar', icon='send', on_click=save_and_assign)\
                        .props('unelevated color=pink-600 no-caps').classes('px-6 py-2 shadow-lg shadow-pink-100')

    # =================================================================
    # LAYOUT PRINCIPAL
    # =================================================================
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-8'):
        with ui.row().classes('items-center gap-3'):
            with ui.element('div').classes('p-3 bg-orange-100 rounded-2xl'):
                ui.icon('assignment', size='md', color='orange-600')
            with ui.column().classes('gap-0'):
                ui.label('Gestión de Tareas').classes('text-2xl font-bold text-slate-800')
                ui.label('Panel de control de actividades académicas').classes('text-sm text-slate-500')

        with ui.tabs().classes('w-full justify-start text-slate-500') \
                .props('active-color=orange indicator-color=orange align=left narrow no-caps') as main_tabs:
            mt1 = ui.tab('Panel de Gestión', icon='dashboard').classes('font-bold')
            mt2 = ui.tab('Crear Nueva Tarea', icon='add_circle').classes('font-bold')

        ui.separator()

        with ui.tab_panels(main_tabs, value=mt1).classes('w-full bg-transparent'):
            with ui.tab_panel(mt1).classes('p-0'):
                grading_ui()
            with ui.tab_panel(mt2).classes('p-0'):
                create_homework_ui()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run()