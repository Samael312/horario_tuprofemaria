from nicegui import ui, app
from datetime import datetime
import logging
from db.sqlite_db import BackupSession

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.models import AsignedClasses, User
from components.header import create_main_screen
from components.share_data import days_of_week, PACKAGE_LIMITS, pack_of_classes

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@ui.page('/myclasses')
def my_classes():
    # Estilos globales consistentes
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_main_screen()

    # 1. VERIFICAR SESIÓN
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # Estados que obligan a mover la clase al historial
    HISTORY_STATUSES = {'Finalizada', 'Completada', 'No Asistió', 'Cancelada'}

    # Variable para almacenar info del usuario (se llena en get_user_classes)
    user_state = {
        'package': 'None', 
        'class_count_str': '0/0', 
        'current': 0, 
        'limit': 0
    }

    # 2. LOGICA DE DATOS
    def get_user_classes():
        session = PostgresSession()
        try:
            # A. Obtener Datos del Usuario (Para validar suscripción)
            user = session.query(User).filter(User.username == username).first()
            if user:
                user_state['package'] = user.package
                user_state['class_count_str'] = user.class_count or "0/0"
                
                # Parsear "X/Y"
                try:
                    curr, lim = map(int, str(user_state['class_count_str']).split('/'))
                    user_state['current'] = curr
                    user_state['limit'] = lim
                except:
                    user_state['current'] = 0
                    user_state['limit'] = PACKAGE_LIMITS.get(user.package, 0)

            # B. Actualizar estados (Auto-Finalizar clases pasadas)
            now = datetime.now()
            now_int = int(now.strftime("%Y%m%d%H%M"))
            
            # Buscamos clases activas (Pendientes o Prueba)
            active_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status.in_(['Pendiente', 'Prueba_Pendiente'])
            ).all()
            
            updates = False
            for c in active_classes:
                # Construir entero de fecha/hora: YYYYMMDDHHMM
                c_dt_int = int(c.date.replace('-', '') + str(c.start_time).zfill(4))
                if c_dt_int < now_int:
                    c.status = 'Finalizada'
                    updates = True
            
            if updates:
                session.commit()

            # C. Obtener listas para mostrar
            all_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username
            ).all()
            
            upcoming = []
            history = []
            
            for c in all_classes:
                c_dt_int = int(c.date.replace('-', '') + str(c.start_time).zfill(4))
                
                # CRITERIO DE HISTORIAL:
                is_history_status = c.status in HISTORY_STATUSES
                is_past_time = c_dt_int < now_int

                if is_history_status or is_past_time:
                    history.append(c)
                else:
                    if c.status != 'Cancelada':
                        upcoming.append(c)
            
            upcoming.sort(key=lambda x: (x.date, x.start_time))
            history.sort(key=lambda x: (x.date, x.start_time), reverse=True)
            
            return upcoming, history
        except Exception as e:
            logger.error(f"Error fetching classes: {e}")
            return [], []
        finally:
            session.close()

    async def cancel_class(c_id, dialog):
        session = PostgresSession()
        try:
            class_to_delete = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            
            if class_to_delete:
                c_username = class_to_delete.username
                c_date = class_to_delete.date
                c_start_time = class_to_delete.start_time
                
                session.delete(class_to_delete)
                session.commit()

                # Backup SQLite
                try:
                    bk_sess = BackupSession()
                    bk_cls = bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == c_username,
                        AsignedClasses.date == c_date,
                        AsignedClasses.start_time == c_start_time
                    ).first()
                    if bk_cls:
                        bk_sess.delete(bk_cls)
                        bk_sess.commit()
                    bk_sess.close()
                except Exception as e:
                    logger.error(f"Error backup sqlite delete: {e}")

                ui.notify('Clase cancelada exitosamente', type='positive', icon='check')
                dialog.close()
                refresh_ui() 
            else:
                ui.notify("No se encontró la clase a cancelar.", type='warning')
                
        except Exception as e:
            ui.notify(f"Error al cancelar: {e}", type='negative')
        finally:
            session.close()

    # --- LÓGICA DE RENOVACIÓN DE SUSCRIPCIÓN ---
    async def renew_subscription(new_plan_name):
        session = PostgresSession()
        try:
            u = session.query(User).filter(User.username == username).first()
            if u:
                # 1. Actualizar Plan
                u.package = new_plan_name
                
                # 2. Obtener nuevo límite
                new_limit = PACKAGE_LIMITS.get(new_plan_name, 0)
                new_count_str = f"0/{new_limit}"
                
                # 3. RESETEAR CONTADORES A 0 EN USER
                u.class_count = new_count_str
                u.total_classes = 0 
                
                # 4. ELIMINAR TODAS LAS CLASES (Reset total)
                # Borramos el historial para que el conteo de completadas empiece de cero real
                session.query(AsignedClasses).filter(
                    AsignedClasses.username == username
                ).delete(synchronize_session=False)

                session.commit()

                # Backup SQLite
                try:
                    bk_sess = BackupSession()
                    
                    # Update User in Backup
                    bk_u = bk_sess.query(User).filter(User.username == username).first()
                    if bk_u:
                        bk_u.package = new_plan_name
                        bk_u.class_count = new_count_str
                        bk_u.total_classes = 0
                    
                    # Delete Classes in Backup
                    bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == username
                    ).delete(synchronize_session=False)
                    
                    bk_sess.commit()
                    bk_sess.close()
                except Exception as ex_bk:
                    logger.error(f"Error backup update: {ex_bk}")

                ui.notify(f"Suscripción actualizada a {new_plan_name}. Historial eliminado y reiniciado.", type='positive', icon='verified')
                refresh_ui()
            else:
                ui.notify("Usuario no encontrado", type='negative')
        except Exception as e:
            ui.notify(f"Error renovando: {e}", type='negative')
        finally:
            session.close()

    def open_renewal_dialog():
        current_plan = user_state['package']
        
        with ui.dialog() as d, ui.card().classes('w-96 p-6 rounded-2xl'):
            ui.label('Actualizar Suscripción').classes('text-xl font-bold text-slate-800 mb-2')
            ui.label('Has completado todas las clases de tu paquete actual.').classes('text-sm text-slate-500 mb-4')
            
            # --- MANEJADORES ASÍNCRONOS ---
            async def handle_repeat():
                d.close()
                await renew_subscription(current_plan)

            # Opción 1: Repetir
            ui.button(f'Repetir {current_plan}', 
                      icon='replay', 
                      on_click=handle_repeat
            ).props('unelevated color=blue-600 w-full').classes('mb-3')
            
            ui.separator().classes('mb-3')
            
            # Opción 2: Cambiar
            ui.label('O cambiar a otro plan:').classes('text-xs font-bold text-slate-400 uppercase mb-2')
            
            available_plans = sorted([p for p in pack_of_classes if p != 'None'])
            select_plan = ui.select(available_plans, label='Seleccionar Plan').props('outlined dense w-full').classes('w-full mb-4')
            
            async def handle_change():
                if select_plan.value:
                    d.close()
                    await renew_subscription(select_plan.value)
                else:
                    ui.notify('Selecciona un plan', type='warning')

            ui.button('Cambiar Plan', 
                      icon='switch_access_shortcut', 
                      on_click=handle_change
            ).props('outline color=slate w-full')

        d.open()

    # 3. COMPONENTES VISUALES
    
    def render_stat_card(icon, label, value, color_class, text_color):
        """Tarjeta pequeña de estadísticas"""
        with ui.card().classes('flex-1 p-4 rounded-xl shadow-sm border border-slate-100 items-center justify-between flex-row min-w-[150px]'):
            with ui.column().classes('gap-1'):
                ui.label(str(value)).classes(f'text-3xl font-bold {text_color} leading-none')
                ui.label(label).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
            
            with ui.element('div').classes(f'p-3 rounded-full {color_class}'):
                ui.icon(icon, color='white', size='sm')

    def render_class_card(c, is_history=False):
        """Renderiza una tarjeta de clase individual"""
        dt = datetime.strptime(c.date, '%Y-%m-%d')
        t_str = str(c.start_time).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        duration_txt = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
        
        # Lógica de Colores y Etiquetas
        if is_history:
            border_color = "border-slate-300"
            bg_badge = "bg-slate-100 text-slate-500"
            status_txt = c.status.replace('_', ' ')
            type_txt = "Historial"
            opacity = "opacity-75 hover:opacity-100 transition-opacity"
            
            if c.status == 'Completada':
                status_txt = "Completada"
                bg_badge = "bg-green-100 text-green-700"
                border_color = "border-green-500"
            elif c.status == 'No Asistió':
                bg_badge = "bg-gray-200 text-gray-700"
                border_color = "border-gray-400"
            elif c.status == 'Cancelada':
                bg_badge = "bg-red-100 text-red-700"
                border_color = "border-red-400"

        else:
            opacity = ""
            status_txt = "Agendada"
            
            if c.status == 'Prueba_Pendiente':
                type_txt = "Clase de Prueba"
                bg_badge = "bg-purple-100 text-purple-700"
                border_color = "border-purple-500"
            else:
                type_txt = "Clase Regular"
                bg_badge = "bg-rose-100 text-rose-700"
                border_color = "border-rose-500"

        with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-row overflow-hidden group {opacity}'):
            
            with ui.column().classes(f'w-24 justify-center items-center bg-slate-50 border-r-4 {border_color} p-4 gap-0'):
                ui.label(dt.strftime('%d')).classes('text-3xl font-bold text-slate-700 leading-none')
                ui.label(dt.strftime('%b')).classes('text-xs font-bold uppercase text-slate-400 mt-1')
                ui.label(dt.strftime('%Y')).classes('text-[10px] text-slate-300')

            with ui.column().classes('flex-1 p-4 justify-center gap-1'):
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    ui.label(f"{days_of_week[dt.weekday()]} • {fmt_time}").classes('text-lg font-bold text-slate-800')
                    
                    ui.label(status_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')
                    
                    if not is_history:
                        ui.label(type_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')

                    if hasattr(c, 'class_count') and c.class_count:
                        ui.label(f"Clase {c.class_count}").classes('text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100')

                    if hasattr(c, 'total_classes') and c.total_classes:
                        ui.label(f"Total #{c.total_classes}").classes('text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100')

                with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('schedule', size='xs')
                        ui.label(duration_txt)
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('school', size='xs')
                        ui.label('Inglés General')

            if not is_history:
                with ui.column().classes('h-full items-center justify-center pr-4'):
                    btn = ui.button(icon='delete_outline', color='slate').props('flat round')
                    btn.classes('my-auto text-slate-400 hover:text-red-500 transition-colors')
                    
                    def open_confirm(c_id=c.id):
                        with ui.dialog() as d, ui.card().classes('rounded-xl p-6 w-80'):
                            ui.label('¿Cancelar esta clase?').classes('text-lg font-bold text-slate-800')
                            ui.label('Esta acción no se puede deshacer.').classes('text-sm text-slate-500 mb-4')
                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Volver', on_click=d.close).props('flat text-color=slate')
                                cancel_btn = ui.button('Confirmar Cancelación', on_click=lambda: cancel_class(c_id, d))
                                cancel_btn.props('unelevated color=red')
                        d.open()
                    
                    btn.on('click', open_confirm)

    @ui.refreshable
    def render_content():
        upcoming, history = get_user_classes()
        total_count = len(upcoming) + len(history)
        
        curr = user_state['current']
        limit = user_state['limit']
        pkg_name = user_state['package']

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
            
            with ui.row().classes('w-full justify-between items-end'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('book', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Mis Clases').classes('text-3xl font-bold text-slate-800')
                        ui.label(f'Bienvenido, {username}').classes('text-slate-500 font-medium')
                    
                # LÓGICA DE BOTÓN
                if limit > 0 and curr >= limit:
                    ui.button('Actualizar Suscripción', icon='published_with_changes', on_click=open_renewal_dialog) \
                        .props('unelevated color=amber-600').classes('rounded-xl px-4 py-2 shadow-md shadow-amber-200 hover:shadow-lg transition-all animate-bounce')
                else:
                    ui.button('Agendar Nueva', icon='add', on_click=lambda: ui.navigate.to('/ScheduleMaker')) \
                        .props('unelevated color=rose-600').classes('rounded-xl px-4 py-2 shadow-md shadow-rose-200 hover:shadow-lg transition-all')

            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('event', 'Próximas', len(upcoming), 'bg-rose-500', 'text-rose-600')
                render_stat_card('history', 'Historial', len(history), 'bg-purple-500', 'text-purple-600')
                
                if limit > 0:
                    prog_color = 'bg-green-500' if curr < limit else 'bg-amber-500'
                    text_prog = 'text-green-600' if curr < limit else 'text-amber-600'
                    render_stat_card('inventory_2', f'Plan {pkg_name}', f"{curr}/{limit}", prog_color, text_prog)
                else:
                    render_stat_card('school', 'Total Clases', total_count, 'bg-slate-500', 'text-slate-600')

            with ui.card().classes('w-full rounded-2xl shadow-sm border border-slate-100 p-0 overflow-hidden bg-transparent shadow-none border-none'):
                
                with ui.tabs().classes('w-full justify-start text-slate-500 bg-transparent') \
                        .props('active-color=rose indicator-color=rose align=left narrow') as tabs:
                    t_upcoming = ui.tab('Próximas').classes('capitalize font-bold')
                    t_history = ui.tab('Historial').classes('capitalize font-bold')

                ui.separator().classes('mb-4')

                with ui.tab_panels(tabs, value=t_upcoming).classes('w-full bg-transparent'):
                    
                    with ui.tab_panel(t_upcoming).classes('p-0 gap-4 flex flex-col'):
                        if not upcoming:
                            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                                ui.icon('event_available', size='4xl', color='slate-300')
                                ui.label("Todo despejado").classes('text-slate-500 font-bold mt-4')
                                ui.label("No tienes clases agendadas próximamente.").classes('text-sm text-slate-400')
                        else:
                            for c in upcoming:
                                render_class_card(c, is_history=False)

                    with ui.tab_panel(t_history).classes('p-0 gap-4 flex flex-col'):
                        if not history:
                            with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                                ui.label("Aún no tienes historial de clases.").classes('text-sm italic')
                        else:
                            for c in history:
                                render_class_card(c, is_history=True)

    def refresh_ui():
        render_content.refresh()

    render_content()