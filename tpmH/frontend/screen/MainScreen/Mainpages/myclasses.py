from nicegui import ui, app
from datetime import datetime
import logging
from db.sqlite_db import BackupSession

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.models import AsignedClasses, User
from components.header import create_main_screen
# --- IMPORTS SHARE DATA & ALCABALA ---
from components.share_data import days_of_week, PACKAGE_LIMITS, pack_of_classes, t_val
# -------------------------------------

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# 1. TRADUCCIONES (My Classes)
# =====================================================
MC_TRANSLATIONS = {
    'es': {
        # Header / General
        'page_title': 'Mis Clases',
        'welcome': 'Bienvenido, {}',
        # Stats Cards
        'upcoming_label': 'Próximas',
        'history_label': 'Historial',
        'total_label': 'Total Clases',
        'plan_prefix': 'Plan',
        'classes_suffix': 'de {} clases',
        # Tabs
        'tab_upcoming': 'Próximas',
        'tab_history': 'Historial',
        # Empty States
        'all_clear_title': 'Todo despejado',
        'all_clear_msg': 'No tienes clases agendadas próximamente.',
        'no_history': 'Aún no tienes historial de clases.',
        # Class Card Labels
        'trial_class': 'Clase de Prueba',
        'regular_class': 'Clase Regular',
        'history_tag': 'Historial',
        'class_num': 'Clase {}',
        'total_num': 'Total #{}',
        'general_english': 'Inglés General',
        # Dialogs / Actions
        'btn_schedule': 'Agendar Nueva',
        'btn_renew': 'Actualizar Suscripción',
        'cancel_title': '¿Cancelar esta clase?',
        'cancel_msg': 'Esta acción no se puede deshacer.',
        'btn_back': 'Volver',
        'btn_confirm_cancel': 'Confirmar Cancelación',
        # Notificaciones
        'cancel_success': 'Clase cancelada exitosamente',
        'cancel_error': 'No se encontró la clase a cancelar.',
        'cancel_fail': 'Error al cancelar: {}',
        # Mapeo de Estados (Visual)
        'status_map': {
            'Pendiente': 'Pendiente',
            'Prueba_Pendiente': 'Prueba Pendiente',
            'Agendada': 'Agendada',
            'Completada': 'Completada',
            'Finalizada': 'Finalizada',
            'No Asistió': 'No Asistió',
            'Cancelada': 'Cancelada'
        }
    },
    'en': {
        # Header / General
        'page_title': 'My Classes',
        'welcome': 'Welcome, {}',
        # Stats Cards
        'upcoming_label': 'Upcoming',
        'history_label': 'History',
        'total_label': 'Total Classes',
        'plan_prefix': 'Plan',
        'classes_suffix': 'of {} classes',
        # Tabs
        'tab_upcoming': 'Upcoming',
        'tab_history': 'History',
        # Empty States
        'all_clear_title': 'All Clear',
        'all_clear_msg': 'You have no upcoming scheduled classes.',
        'no_history': 'No class history yet.',
        # Class Card Labels
        'trial_class': 'Trial Class',
        'regular_class': 'Regular Class',
        'history_tag': 'History',
        'class_num': 'Class {}',
        'total_num': 'Total #{}',
        'general_english': 'General English',
        # Dialogs / Actions
        'btn_schedule': 'Schedule New',
        'btn_renew': 'Renew Subscription',
        'cancel_title': 'Cancel this class?',
        'cancel_msg': 'This action cannot be undone.',
        'btn_back': 'Back',
        'btn_confirm_cancel': 'Confirm Cancellation',
        # Notifications
        'cancel_success': 'Class cancelled successfully',
        'cancel_error': 'Class to cancel not found.',
        'cancel_fail': 'Error cancelling: {}',
        # Status Map
        'status_map': {
            'Pendiente': 'Pending',
            'Prueba_Pendiente': 'Trial Pending',
            'Agendada': 'Scheduled',
            'Completada': 'Completed',
            'Finalizada': 'Finished',
            'No Asistió': 'No Show',
            'Cancelada': 'Cancelled'
        }
    }
}

@ui.page('/myclasses')
def my_classes():
    # Estilos globales consistentes
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
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

    async def cancel_class(c_id, dialog, t):
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

                ui.notify(t['cancel_success'], type='positive', icon='check')
                dialog.close()
                render_content.refresh() # Refrescar UI completa
            else:
                ui.notify(t['cancel_error'], type='warning')
                
        except Exception as e:
            ui.notify(t['cancel_fail'].format(e), type='negative')
        finally:
            session.close()

    # 3. COMPONENTES VISUALES
    
    def render_stat_card(icon, label, value, color_class, text_color):
        """Tarjeta pequeña de estadísticas"""
        with ui.card().classes('flex-1 p-4 rounded-xl shadow-sm border border-slate-100 items-center justify-between flex-row min-w-[150px]'):
            with ui.column().classes('gap-1'):
                ui.label(str(value)).classes(f'text-3xl font-bold {text_color} leading-none')
                ui.label(label).classes('text-xs font-bold text-slate-400 uppercase tracking-wider')
            
            with ui.element('div').classes(f'p-3 rounded-full {color_class}'):
                ui.icon(icon, color='white', size='sm')

    # 4. RENDER PRINCIPAL (REFRESHABLE)
    @ui.refreshable
    def render_content():
        lang = app.storage.user.get('lang', 'es')
        t = MC_TRANSLATIONS[lang]

        upcoming, history = get_user_classes()
        total_count = len(upcoming) + len(history)
        
        curr = user_state['current']
        limit = user_state['limit']
        pkg_name = user_state['package']
        
        # ALCABALA: Traducir nombre del paquete
        pkg_display = t_val(pkg_name, lang) if pkg_name != 'None' else "—"

        def render_class_card(c, is_history=False):
            """Renderiza una tarjeta de clase individual (Interna para acceder a 't')"""
            dt = datetime.strptime(c.date, '%Y-%m-%d')
            t_str = str(c.start_time).zfill(4)
            fmt_time = f"{t_str[:2]}:{t_str[2:]}"
            duration_txt = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
            
            # ALCABALA: Traducir día
            # days_of_week[dt.weekday()] nos da "Lunes" (interno) -> t_val lo pasa a "Monday"
            day_display = t_val(days_of_week[dt.weekday()], lang)

            # Lógica de Colores y Etiquetas
            # ALCABALA: Traducir estado visualmente
            status_display = t['status_map'].get(c.status, c.status)

            if is_history:
                border_color = "border-slate-300"
                bg_badge = "bg-slate-100 text-slate-500"
                type_txt = t['history_tag']
                opacity = "opacity-75 hover:opacity-100 transition-opacity"
                
                if c.status == 'Completada':
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
                
                if c.status == 'Prueba_Pendiente':
                    type_txt = t['trial_class']
                    bg_badge = "bg-purple-100 text-purple-700"
                    border_color = "border-purple-500"
                else:
                    type_txt = t['regular_class']
                    bg_badge = "bg-rose-100 text-rose-700"
                    border_color = "border-rose-500"

            with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-row overflow-hidden group {opacity}'):
                
                with ui.column().classes(f'w-24 justify-center items-center bg-slate-50 border-r-4 {border_color} p-4 gap-0'):
                    ui.label(dt.strftime('%d')).classes('text-3xl font-bold text-slate-700 leading-none')
                    ui.label(dt.strftime('%b')).classes('text-xs font-bold uppercase text-slate-400 mt-1')
                    ui.label(dt.strftime('%Y')).classes('text-[10px] text-slate-300')

                with ui.column().classes('flex-1 p-4 justify-center gap-1'):
                    with ui.row().classes('items-center gap-2 flex-wrap'):
                        ui.label(f"{day_display} • {fmt_time}").classes('text-lg font-bold text-slate-800')
                        
                        ui.label(status_display).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')
                        
                        if not is_history:
                            ui.label(type_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')

                        if hasattr(c, 'class_count') and c.class_count:
                            ui.label(t['class_num'].format(c.class_count)).classes('text-[10px] font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full border border-blue-100')

                        if hasattr(c, 'total_classes') and c.total_classes:
                            ui.label(t['total_num'].format(c.total_classes)).classes('text-[10px] font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded-full border border-amber-100')

                    with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('schedule', size='xs')
                            ui.label(duration_txt)
                        with ui.row().classes('items-center gap-1'):
                            ui.icon('school', size='xs')
                            ui.label(t['general_english'])

                if not is_history:
                    with ui.column().classes('h-full items-center justify-center pr-4'):
                        btn = ui.button(icon='delete_outline', color='slate').props('flat round')
                        btn.classes('my-auto text-slate-400 hover:text-red-500 transition-colors')
                        
                        def open_confirm(c_id=c.id):
                            with ui.dialog() as d, ui.card().classes('rounded-xl p-6 w-80'):
                                ui.label(t['cancel_title']).classes('text-lg font-bold text-slate-800')
                                ui.label(t['cancel_msg']).classes('text-sm text-slate-500 mb-4')
                                with ui.row().classes('w-full justify-end gap-2'):
                                    ui.button(t['btn_back'], on_click=d.close).props('flat text-color=slate')
                                    cancel_btn = ui.button(t['btn_confirm_cancel'], on_click=lambda: cancel_class(c_id, d, t))
                                    cancel_btn.props('unelevated color=red')
                            d.open()
                        
                        btn.on('click', open_confirm)

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
            
            with ui.row().classes('w-full justify-between items-end'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('book', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t['page_title']).classes('text-3xl font-bold text-slate-800')
                        ui.label(t['welcome'].format(username)).classes('text-slate-500 font-medium')
                
                # LÓGICA DE BOTÓN
                if limit > 0 and curr >= limit:
                    # Enrutamos al perfil para renovar (o donde tengas esa lógica)
                    ui.button(t['btn_renew'], icon='published_with_changes', on_click=lambda: ui.navigate.to('/profile')) \
                        .props('unelevated color=amber-600').classes('rounded-xl px-4 py-2 shadow-md shadow-amber-200 hover:shadow-lg transition-all animate-bounce')
                else:
                    ui.button(t['btn_schedule'], icon='add', on_click=lambda: ui.navigate.to('/ScheduleMaker')) \
                        .props('unelevated color=rose-600').classes('rounded-xl px-4 py-2 shadow-md shadow-rose-200 hover:shadow-lg transition-all')

            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('event', t['upcoming_label'], len(upcoming), 'bg-rose-500', 'text-rose-600')
                render_stat_card('history', t['history_label'], len(history), 'bg-purple-500', 'text-purple-600')
                
                if limit > 0:
                    prog_color = 'bg-green-500' if curr < limit else 'bg-amber-500'
                    text_prog = 'text-green-600' if curr < limit else 'text-amber-600'
                    render_stat_card('inventory_2', f"{t['plan_prefix']} {pkg_display}", f"{curr}/{limit}", prog_color, text_prog)
                else:
                    render_stat_card('school', t['total_label'], total_count, 'bg-slate-500', 'text-slate-600')

            with ui.card().classes('w-full rounded-2xl shadow-sm border border-slate-100 p-0 overflow-hidden bg-transparent shadow-none border-none'):
                
                with ui.tabs().classes('w-full justify-start text-slate-500 bg-transparent') \
                        .props('active-color=rose indicator-color=rose align=left narrow') as tabs:
                    t_upcoming = ui.tab(t['tab_upcoming']).classes('capitalize font-bold')
                    t_history = ui.tab(t['tab_history']).classes('capitalize font-bold')

                ui.separator().classes('mb-4')

                with ui.tab_panels(tabs, value=t_upcoming).classes('w-full bg-transparent'):
                    
                    with ui.tab_panel(t_upcoming).classes('p-0 gap-4 flex flex-col'):
                        if not upcoming:
                            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                                ui.icon('event_available', size='4xl', color='slate-300')
                                ui.label(t['all_clear_title']).classes('text-slate-500 font-bold mt-4')
                                ui.label(t['all_clear_msg']).classes('text-sm text-slate-400')
                        else:
                            for c in upcoming:
                                render_class_card(c, is_history=False)

                    with ui.tab_panel(t_history).classes('p-0 gap-4 flex flex-col'):
                        if not history:
                            with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                                ui.label(t['no_history']).classes('text-sm italic')
                        else:
                            for c in history:
                                render_class_card(c, is_history=True)

    # 5. INICIALIZACIÓN
    # Pasamos el callback al header para que pueda refrescar este contenido
    create_main_screen(page_refresh_callback=render_content.refresh)
    
    # Renderizamos contenido inicial
    render_content()