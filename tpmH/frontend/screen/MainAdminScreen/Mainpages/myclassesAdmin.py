from nicegui import ui, app
from datetime import datetime
import logging

# --- IMPORTS DE BASE DE DATOS ---
from db.postgres_db import PostgresSession
from db.sqlite_db import BackupSession
from db.models import AsignedClasses, User
from components.headerAdmin import create_admin_screen
from components.share_data import days_of_week

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Opciones de Estado para el Profesor
STATUS_OPTIONS = {
    'Pendiente': {'color': 'orange', 'icon': 'schedule'},
    'Completada': {'color': 'green', 'icon': 'check_circle'},
    'Cancelada': {'color': 'red', 'icon': 'cancel'},
    'No Asistió': {'color': 'grey', 'icon': 'person_off'}
}

@ui.page('/myclassesAdmin')
def my_classesAdmin():
    # Estilos globales
    ui.query('body').style('background-color: #F8FAFC; font-family: "Inter", sans-serif;')
    
    create_admin_screen()

    # 1. LOGICA DE DATOS
    def get_all_classes():
        session = PostgresSession()
        try:
            # Traemos TODAS las clases ordenadas por fecha y hora
            # Podrías agregar un filtro de fecha aquí si hay miles de registros
            all_classes = session.query(AsignedClasses).order_by(
                AsignedClasses.date.desc(), 
                AsignedClasses.start_time.asc()
            ).limit(100).all() # Limitamos a las ultimas 100 para rendimiento
            
            now_date = datetime.now().strftime('%Y-%m-%d')
            now_int = int(datetime.now().strftime("%Y%m%d%H%M"))
            
            today_classes = []
            upcoming_classes = []
            history_classes = []
            
            for c in all_classes:
                # Generamos entero de fecha/hora para ordenamiento lógico
                c_full_int = int(c.date.replace('-', '') + str(c.start_time).zfill(4))
                
                if c.date == now_date:
                    today_classes.append(c)
                elif c_full_int > now_int:
                    upcoming_classes.append(c)
                else:
                    history_classes.append(c)
            
            # Re-ordenar "Hoy" y "Próximas" para que las más tempranas salgan primero
            today_classes.sort(key=lambda x: x.start_time)
            upcoming_classes.sort(key=lambda x: (x.date, x.start_time))
            
            return today_classes, upcoming_classes, history_classes
        except Exception as e:
            logger.error(f"Error fetching admin classes: {e}")
            return [], [], []
        finally:
            session.close()

    async def update_status(c_id, new_status):
        session = PostgresSession()
        try:
            cls = session.query(AsignedClasses).filter(AsignedClasses.id == c_id).first()
            if cls:
                cls.status = new_status
                session.commit()
                 # --- Backup SQLite (CORREGIDO) ---
                try:
                    bk_sess = BackupSession()
                    # Buscamos la clase en SQLite usando los datos de la clase de Postgres (cls)
                    # No usamos ID porque pueden diferir entre bases de datos
                    bk_cls = bk_sess.query(AsignedClasses).filter(
                        AsignedClasses.username == cls.username,
                        AsignedClasses.date == cls.date,
                        AsignedClasses.start_time == cls.start_time
                    ).first()
                    
                    if bk_cls:
                        # Si existe, actualizamos el estado
                        bk_cls.status = new_status
                    else:
                        # Si no existe (por error previo), la creamos usando los datos de cls
                        bk_sess.add(AsignedClasses(
                            username=cls.username, name=cls.name, surname=cls.surname,
                            date=cls.date, days=cls.days, start_time=cls.start_time,
                            end_time=cls.end_time, duration=cls.duration, 
                            package=cls.package, status=new_status
                        ))
                    bk_sess.commit()
                    bk_sess.close()
                except Exception as e:
                    logger.error(f"Error backup sqlite: {e}")
                    pass

                ui.notify(f'Clase actualizada a: {new_status}', type='positive', icon='check')
                refresh_ui()
        except Exception as e:
            ui.notify(f"Error al actualizar: {e}", type='negative')
        finally:
            session.close()

    # 2. COMPONENTES VISUALES
    
    def render_stat_card(label, value, color):
        """Tarjeta de métricas superior"""
        with ui.card().classes('flex-1 min-w-[140px] p-4 rounded-xl shadow-sm border border-slate-100 bg-white items-center justify-between flex-row'):
            with ui.column().classes('gap-0'):
                ui.label(str(value)).classes(f'text-3xl font-bold text-{color}-600 leading-none')
                ui.label(label).classes('text-[10px] font-bold text-slate-400 uppercase tracking-wider')
            ui.icon('bar_chart', color=f'{color}-200', size='md')

    def render_admin_class_card(c, is_history=False):
        """Tarjeta de Clase para Profesor"""
        dt = datetime.strptime(c.date, '%Y-%m-%d')
        t_str = str(c.start_time).zfill(4)
        fmt_time = f"{t_str[:2]}:{t_str[2:]}"
        dur_text = f"{c.duration} min" if hasattr(c, 'duration') and c.duration else "60 min"
        
        # Configuración visual según estado
        current_status = c.status if c.status in STATUS_OPTIONS else 'Pendiente'
        status_config = STATUS_OPTIONS.get(current_status, STATUS_OPTIONS['Pendiente'])
        
        card_opacity = "opacity-60 hover:opacity-100" if is_history or current_status == 'Cancelada' else "opacity-100"
        border_l = f"border-{status_config['color']}-500" if not is_history else "border-slate-300"

        with ui.card().classes(f'w-full p-0 rounded-xl shadow-sm border border-slate-100 flex flex-col md:flex-row overflow-hidden transition-all {card_opacity}'):
            
            # 1. Bloque Izquierdo: Hora y Fecha
            with ui.row().classes(f'md:w-28 w-full justify-between md:justify-center items-center bg-slate-50 md:border-r-4 md:border-b-0 border-b-4 {border_l} p-3 gap-2'):
                # Hora Grande
                with ui.column().classes('items-center gap-0'):
                    ui.label(fmt_time).classes('text-2xl font-bold text-slate-700 leading-none')
                    ui.label(dur_text).classes('text-[10px] font-medium text-slate-400')
                
                # Fecha (visible si no es "Hoy" o en móvil)
                with ui.column().classes('items-end md:items-center gap-0'):
                    ui.label(dt.strftime('%d %b')).classes('text-xs font-bold uppercase text-slate-500')
                    ui.label(days_of_week[dt.weekday()][:3]).classes('text-[10px] text-slate-400')

            # 2. Bloque Central: Info Estudiante
            with ui.column().classes('flex-1 p-3 md:p-4 justify-center gap-1'):
                # Nombre Estudiante (Hero)
                with ui.row().classes('items-center gap-2'):
                    ui.icon('person', size='xs', color='slate-400')
                    full_name = f"{c.name} {c.surname}"
                    ui.label(full_name).classes('text-lg font-bold text-slate-800 leading-tight')
                
                # Detalles Técnicos (Plan, ID)
                with ui.row().classes('items-center gap-3 text-xs text-slate-500'):
                    ui.label(f"Plan: {c.package or 'N/A'}").classes('bg-slate-100 px-2 py-0.5 rounded')
                    ui.label(f"ID: #{c.id}").classes('text-slate-300')

            # 3. Bloque Derecho: Selector de Acción
            with ui.column().classes('p-3 md:p-4 justify-center items-end md:w-64 bg-white border-t md:border-t-0 md:border-l border-slate-50'):
                
                # Selector de Estado
                status_select = ui.select(
                    options=list(STATUS_OPTIONS.keys()),
                    value=current_status,
                    on_change=lambda e, cid=c.id: update_status(cid, e.value)
                ).props('outlined dense options-dense behavior="menu"').classes('w-full')
                
                # Colorear el selector según la selección actual (Truco visual)
                color_map = {k: v['color'] for k, v in STATUS_OPTIONS.items()}
                # Esto es un poco hacky en NiceGUI puro para cambiar el color del input, 
                # así que usaremos un label de ayuda visual
                
                with ui.row().classes('w-full justify-between items-center mt-1'):
                    ui.label('Estado Actual:').classes('text-[10px] text-slate-400')
                    with ui.row().classes('items-center gap-1'):
                        ui.icon(status_config['icon'], size='xs', color=status_config['color'])
                        ui.label(current_status).classes(f'text-xs font-bold text-{status_config["color"]}-600')

    @ui.refreshable
    def render_content():
        today, upcoming, history = get_all_classes()
        
        # Stats Rápidas
        today_pending = sum(1 for c in today if c.status == 'Pendiente')
        today_done = sum(1 for c in today if c.status == 'Completada')

        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
            
            # --- HEADER ---
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-0'):
                    ui.label('Gestión de Clases').classes('text-2xl font-bold text-slate-800')
                    ui.label('Panel del Profesor').classes('text-sm text-slate-500')
                
                ui.button(icon='refresh', on_click=refresh_ui).props('flat round color=slate')

            # --- STATS ROW ---
            with ui.row().classes('w-full gap-4 flex-wrap'):
                render_stat_card('Clases Hoy', len(today), 'blue')
                render_stat_card('Pendientes Hoy', today_pending, 'orange')
                render_stat_card('Completadas Hoy', today_done, 'green')

            # --- SECCIONES ---
            
            # 1. CLASES DE HOY (Prioridad Alta)
            if today:
                with ui.column().classes('w-full gap-3 mt-4'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('today', color='rose', size='sm')
                        ui.label('Agenda de Hoy').classes('text-lg font-bold text-slate-800')
                    
                    for c in today:
                        render_admin_class_card(c)
            elif not upcoming: # Solo mostrar mensaje si no hay nada hoy ni proximamente
                ui.label('No hay clases programadas para hoy.').classes('text-slate-400 italic mt-4')

            ui.separator().classes('bg-slate-200 my-2')

            # 2. PRÓXIMAS CLASES (Colapsable o Tabs)
            with ui.expansion('Próximas Sesiones', icon='calendar_month', value=True).classes('w-full bg-white border border-slate-100 rounded-xl shadow-sm'):
                with ui.column().classes('w-full p-4 gap-3'):
                    if not upcoming:
                        ui.label('No hay clases futuras.').classes('text-slate-400 italic')
                    for c in upcoming:
                        render_admin_class_card(c)

            # 3. HISTORIAL (Colapsable cerrado por defecto)
            with ui.expansion('Historial Reciente', icon='history').classes('w-full bg-slate-50 border border-slate-100 rounded-xl'):
                with ui.column().classes('w-full p-4 gap-3'):
                    if not history:
                        ui.label('Historial vacío.').classes('text-slate-400 italic')
                    for c in history:
                        render_admin_class_card(c, is_history=True)

    def refresh_ui():
        render_content.refresh()

    # Render inicial
    render_content()