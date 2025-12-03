from nicegui import ui, app
from datetime import datetime
import logging
from db.sqlite_db import BackupSession

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.models import AsignedClasses
from components.header import create_main_screen
from components.share_data import days_of_week

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

    # 2. LOGICA DE DATOS
    def get_user_classes():
        session = PostgresSession()
        try:
            # Traemos todas las clases NO canceladas
            all_classes = session.query(AsignedClasses).filter(
                AsignedClasses.username == username,
                AsignedClasses.status != 'Cancelled'
            ).all()
            
            # Clasificación Temporal
            now_int = int(datetime.now().strftime("%Y%m%d%H%M"))
            
            upcoming = []
            history = []
            
            for c in all_classes:
                # Convertimos fecha y hora a entero para comparar fácil (YYYYMMDDHHMM)
                c_dt_str = c.date.replace('-', '') + str(c.start_time).zfill(4)
                
                if int(c_dt_str) >= now_int:
                    upcoming.append(c)
                else:
                    history.append(c)
            
            # Ordenar: Próximas (más cercana primero), Historial (más reciente primero)
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
            # 1. Primero buscamos la clase para obtener sus datos antes de borrarla
            # Necesitamos estos datos para encontrar la coincidencia en SQLite
            class_to_delete = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            
            if class_to_delete:
                # Guardamos los datos clave en variables temporales
                c_username = class_to_delete.username
                c_date = class_to_delete.date
                c_start_time = class_to_delete.start_time
                
                # 2. Borramos de Postgres
                session.delete(class_to_delete)
                session.commit()

                # 3. Backup SQLite (CORREGIDO)
                # Ahora usamos los datos guardados para borrar también en el respaldo
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
                refresh_ui() # Recargar la interfaz
            else:
                ui.notify("No se encontró la clase a cancelar.", type='warning')
                
        except Exception as e:
            ui.notify(f"Error al cancelar: {e}", type='negative')
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

    def render_class_card(c, is_history=False):
        """Renderiza una tarjeta de clase individual"""
        dt = datetime.strptime(c.date, '%Y-%m-%d')
        t_str = str(c.start_time).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        duration_txt = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
        
        # Colores según estado
        if is_history:
            border_color = "border-slate-300"
            bg_badge = "bg-slate-100 text-slate-500"
            status_txt = "Finalizada"
            opacity = "opacity-75 hover:opacity-100 transition-opacity"
        else:
            border_color = "border-rose-500"
            bg_badge = "bg-rose-50 text-rose-600"
            status_txt = "Agendada"
            opacity = ""

        with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-row overflow-hidden group {opacity}'):
            
            # Columna Izquierda: Fecha Visual
            with ui.column().classes(f'w-24 justify-center items-center bg-slate-50 border-r-4 {border_color} p-4 gap-0'):
                ui.label(dt.strftime('%d')).classes('text-3xl font-bold text-slate-700 leading-none')
                ui.label(dt.strftime('%b')).classes('text-xs font-bold uppercase text-slate-400 mt-1')
                ui.label(dt.strftime('%Y')).classes('text-[10px] text-slate-300')

            # Columna Central: Detalles
            with ui.column().classes('flex-1 p-4 justify-center gap-1'):
                with ui.row().classes('items-center gap-2'):
                    ui.label(f"{days_of_week[dt.weekday()]} • {fmt_time}").classes('text-lg font-bold text-slate-800')
                    ui.label(status_txt).classes(f'text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wide {bg_badge}')
                
                with ui.row().classes('items-center gap-4 text-sm text-slate-500'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('schedule', size='xs')
                        ui.label(duration_txt)
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('school', size='xs')
                        ui.label('Inglés General')

            # Columna Derecha: Acciones (Solo si no es historial)
            if not is_history:
                with ui.column().classes('h-full items-center justify-center pr-4'):
                    # Botón cancelar
                    btn = ui.button(icon='delete_outline', color='slate').props('flat round')
                    btn.classes('my-auto text-slate-400 hover:text-red-500 transition-colors')
                    
                    # Dialogo de confirmación local
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

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-8'):
            
            # --- HEADER SECTION ---
            with ui.row().classes('w-full justify-between items-end'):
                with ui.column().classes('gap-1'):
                    ui.label('Mis Clases').classes('text-3xl font-bold text-slate-800')
                    ui.label(f'Bienvenido, {username}').classes('text-slate-500 font-medium')
                
                # Botón para ir a agendar
                ui.button('Agendar Nueva', icon='add', on_click=lambda: ui.navigate.to('/ScheduleMaker')) \
                    .props('unelevated color=rose-600').classes('rounded-xl px-4 py-2 shadow-md shadow-rose-200 hover:shadow-lg transition-all')

            # --- STATS WIDGETS ---
            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('event', 'Próximas', len(upcoming), 'bg-rose-500', 'text-rose-600')
                render_stat_card('history', 'Historial', len(history), 'bg-purple-500', 'text-purple-600')
                render_stat_card('school', 'Total Clases', total_count, 'bg-slate-500', 'text-slate-600')

            # --- TABS & LISTS ---
            with ui.card().classes('w-full rounded-2xl shadow-sm border border-slate-100 p-0 overflow-hidden bg-transparent shadow-none border-none'):
                
                # Definición de Tabs
                with ui.tabs().classes('w-full justify-start text-slate-500 bg-transparent') \
                        .props('active-color=rose indicator-color=rose align=left narrow') as tabs:
                    t_upcoming = ui.tab('Próximas').classes('capitalize font-bold')
                    t_history = ui.tab('Historial').classes('capitalize font-bold')

                ui.separator().classes('mb-4')

                # Paneles de contenido
                with ui.tab_panels(tabs, value=t_upcoming).classes('w-full bg-transparent'):
                    
                    # PANEL PRÓXIMAS
                    with ui.tab_panel(t_upcoming).classes('p-0 gap-4 flex flex-col'):
                        if not upcoming:
                            with ui.column().classes('w-full items-center justify-center py-16 bg-white rounded-xl border border-dashed border-slate-300'):
                                ui.icon('event_available', size='4xl', color='slate-300')
                                ui.label("Todo despejado").classes('text-slate-500 font-bold mt-4')
                                ui.label("No tienes clases agendadas próximamente.").classes('text-sm text-slate-400')
                        else:
                            for c in upcoming:
                                render_class_card(c, is_history=False)

                    # PANEL HISTORIAL
                    with ui.tab_panel(t_history).classes('p-0 gap-4 flex flex-col'):
                        if not history:
                            with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                                ui.label("Aún no tienes historial de clases.").classes('text-sm italic')
                        else:
                            for c in history:
                                render_class_card(c, is_history=True)

    def refresh_ui():
        render_content.refresh()

    # Renderizar el contenido inicial
    render_content()