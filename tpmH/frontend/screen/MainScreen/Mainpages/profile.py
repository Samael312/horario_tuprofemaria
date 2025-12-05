from nicegui import ui, app
import pandas as pd
from components.header import create_main_screen
from db.postgres_db import PostgresSession
from db.models import User, SchedulePref, AsignedClasses
from components.delete_all import confirm_delete
# --- IMPORT NUEVO PARA TRADUCCIÓN DE DATOS ---
from components.share_data import t_val 
# ---------------------------------------------
from sqlalchemy import or_
import logging

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- 1. TRADUCCIONES ---
TRANSLATIONS = {
    'es': {
        'user_not_found': 'Usuario no encontrado',
        'header_title': 'Mi Perfil',
        'header_sub': 'Gestiona tu información y plan',
        'fab_label': 'Opciones',
        'fab_edit': 'Editar',
        'fab_delete': 'Eliminar cuenta',
        'card_info_title': 'Información Personal',
        'label_fullname': 'Nombre Completo',
        'label_user': 'Usuario',
        'label_email': 'Email',
        'label_timezone': 'Zona Horaria',
        'card_plan_title': 'Plan Activo',
        'plan_active_sub': 'Suscripción vigente',
        'plan_none_title': 'Sin plan activo',
        'tab_classes': 'Tus Clases',
        'tab_prefs': 'Mis Preferencias',
        'empty_classes': 'No tienes historial de clases.',
        'empty_prefs': 'No has guardado preferencias de horario.',
        'prefs_title': 'Tus horarios preferidos',
        # Columnas Tabla Clases
        'col_date': 'Fecha',
        'col_day': 'Día',
        'col_hour': 'Hora',
        'col_status': 'Estado',
        # Columnas Tabla Preferencias
        'col_start': 'Inicio',
        'col_end': 'Fin',
        # Mapeo de estados para mostrar en UI (Backend -> UI)
        'status_map': {
            'Pendiente': 'Pendiente',
            'Prueba_Pendiente': 'Prueba Pendiente',
            'Agendada': 'Agendada',
            'Completada': 'Completada',
            'Finalizada': 'Finalizada'
        }
    },
    'en': {
        'user_not_found': 'User not found',
        'header_title': 'My Profile',
        'header_sub': 'Manage your info and plan',
        'fab_label': 'Options',
        'fab_edit': 'Edit',
        'fab_delete': 'Delete account',
        'card_info_title': 'Personal Information',
        'label_fullname': 'Full Name',
        'label_user': 'Username',
        'label_email': 'Email',
        'label_timezone': 'Time Zone',
        'card_plan_title': 'Active Plan',
        'plan_active_sub': 'Active subscription',
        'plan_none_title': 'No active plan',
        'tab_classes': 'Your Classes',
        'tab_prefs': 'My Preferences',
        'empty_classes': 'No class history found.',
        'empty_prefs': 'No schedule preferences saved.',
        'prefs_title': 'Your preferred schedules',
        # Columnas Tabla Clases
        'col_date': 'Date',
        'col_day': 'Day',
        'col_hour': 'Time',
        'col_status': 'Status',
        # Columnas Tabla Preferencias
        'col_start': 'Start',
        'col_end': 'End',
        # Mapeo de estados
        'status_map': {
            'Pendiente': 'Pending',
            'Prueba_Pendiente': 'Trial Pending',
            'Agendada': 'Scheduled',
            'Completada': 'Completed',
            'Finalizada': 'Finished'
        }
    }
}

@ui.page('/profile')
def profile():
    
    # Verificar sesión antes de renderizar nada
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # Conexión a DB (Una sola vez para obtener los datos crudos)
    session = PostgresSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        
        # Validar usuario
        if not user_obj:
            lang_err = app.storage.user.get('lang', 'es')
            ui.notify(TRANSLATIONS[lang_err]['user_not_found'], type='negative')
            return

        # Consultas de Datos (Data Fetching)
        rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
        
        assigned_data_objs = session.query(AsignedClasses).filter(
            AsignedClasses.username == username,
            AsignedClasses.status.in_([
                'Pendiente', 
                'Prueba_Pendiente', 
                'Agendada', 
                'Completada', 
                'Finalizada'
            ])
        ).order_by(AsignedClasses.date.desc(), AsignedClasses.start_time.desc()).all()

        schedule_data_objs = session.query(SchedulePref).filter(SchedulePref.username == username).all()

    except Exception as e:
        logger.error(f"Error fetching profile data: {e}")
        ui.notify("Error loading profile", type='negative')
        session.close()
        return
    finally:
        session.close()

    # --- 2. CONTENIDO REFRESHABLE ---
    @ui.refreshable
    def render_profile_content():
        lang = app.storage.user.get('lang', 'es')
        t = TRANSLATIONS[lang]
        
        # --- UI PRINCIPAL ---
        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
            
            # HEADER CON TITULO Y FAB
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('account_circle', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label(t['header_title']).classes('text-3xl font-bold text-gray-800 leading-none')
                        ui.label(t['header_sub']).classes('text-sm text-gray-500')
                
                with ui.fab(icon='settings', label=t['fab_label'], color='pink-600', direction='left') :
                    ui.fab_action(icon='edit', label=t['fab_edit'], on_click=lambda: ui.navigate.to('/profile_edit'), color='blue')
                    ui.fab_action(icon='delete_forever', label=t['fab_delete'], on_click=confirm_delete, color='red')

            # --- GRID LAYOUT (Responsive) ---
            with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-3 gap-6 items-start'):
                
                # === COLUMNA IZQUIERDA (Info + Plan) ===
                with ui.column().classes('w-full gap-6 lg:col-span-1'):
                    
                    # 1. Tarjeta Datos Personales
                    with ui.card().classes('w-full p-0 shadow-md rounded-xl overflow-hidden border border-gray-100'):
                        with ui.row().classes('w-full bg-gray-50 p-4 items-center gap-3 border-b border-gray-100'):
                            ui.icon('badge', size='sm', color='gray-500')
                            ui.label(t['card_info_title']).classes('text-lg font-bold text-gray-700')

                        with ui.column().classes('w-full p-5 gap-4'):
                            def info_item(label, value, icon):
                                with ui.row().classes('w-full items-center gap-3'):
                                    with ui.element('div').classes('p-2 bg-pink-50 rounded-full'):
                                        ui.icon(icon, color='pink-500', size='xs')
                                    with ui.column().classes('gap-0'):
                                        ui.label(label).classes('text-[10px] font-bold text-gray-400 uppercase tracking-wide')
                                        ui.label(str(value)).classes('text-sm text-gray-800 font-medium break-all')
                            
                            info_item(t['label_fullname'], f"{user_obj.name} {user_obj.surname}", 'face')
                            info_item(t['label_user'], user_obj.username, 'alternate_email')
                            info_item(t['label_email'], getattr(user_obj, 'email', 'N/A'), 'mail')
                            info_item(t['label_timezone'], getattr(user_obj, 'time_zone', 'UTC'), 'public')

                    # 2. Tarjeta Paquete
                    with ui.card().classes('w-full p-0 shadow-md rounded-xl overflow-hidden border border-gray-100'):
                        if rgh_obj and rgh_obj.package:
                            # ALCABALA: Traducir nombre del paquete (Ej: Básico -> Basic)
                            pkg_display = t_val(rgh_obj.package, lang)

                            with ui.row().classes('w-full p-4 bg-pink-600 items-center justify-between'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('card_membership', color='white')
                                    ui.label(t['card_plan_title']).classes('text-white font-bold')
                                ui.icon('verified', color='white')
                            
                            with ui.column().classes('w-full p-6 items-center text-center'):
                                ui.label(pkg_display).classes('text-2xl font-black text-gray-800 uppercase tracking-wide')
                                ui.label(t['plan_active_sub']).classes('text-xs text-green-700 font-bold bg-green-100 px-3 py-1 rounded-full mt-2')
                        else:
                            with ui.column().classes('w-full p-8 items-center text-center bg-gray-50'):
                                ui.icon('sentiment_dissatisfied', size='lg', color='gray-400')
                                ui.label(t['plan_none_title']).classes('text-gray-500 font-medium mt-2')

                # === COLUMNA DERECHA (Tabs) ===
                with ui.column().classes('w-full gap-6 lg:col-span-2'):
                    
                    with ui.card().classes('w-full shadow-md rounded-xl overflow-hidden border border-gray-100 p-0 min-h-[400px]'):
                        # Tabs Header
                        with ui.tabs().classes('w-full text-gray-500 bg-gray-50 border-b border-gray-200') \
                            .props('active-color="pink-600" indicator-color="pink-600" align="justify"') as tabs:
                            t_assigned = ui.tab(t['tab_classes'], icon='school')
                            t_schedule = ui.tab(t['tab_prefs'], icon='tune')

                        # Panels
                        with ui.tab_panels(tabs, value=t_assigned).classes('w-full p-0'):
                            
                            # PANEL: TUS CLASES
                            with ui.tab_panel(t_assigned).classes('p-0'):
                                if not assigned_data_objs:
                                    with ui.column().classes('w-full items-center justify-center py-16 text-gray-400'):
                                        ui.icon('event_busy', size='4xl', color='gray-300')
                                        ui.label(t['empty_classes']).classes('mt-4 text-sm')
                                else:
                                    # Preparar datos para tabla (ALCABALA: Traducir días y estados)
                                    rows_a = []
                                    for a in assigned_data_objs:
                                        h_start = f"{str(a.start_time).zfill(4)[:2]}:{str(a.start_time).zfill(4)[2:]}"
                                        
                                        # Traducir el estado para mostrar
                                        status_display = t['status_map'].get(a.status, a.status.replace('_', ' '))
                                        # Traducir el día (Lunes -> Monday)
                                        day_display = t_val(a.days, lang)

                                        rows_a.append({
                                            'Fecha': a.date,
                                            'Día': day_display, # Valor traducido
                                            'Hora': h_start,
                                            'Estado': status_display, # Valor traducido
                                            'raw_status': a.status    # Valor original DB para lógica de colores
                                        })
                                    
                                    cols_a = [
                                        {'name': 'fecha', 'label': t['col_date'], 'field': 'Fecha', 'align': 'left', 'sortable': True},
                                        {'name': 'dia', 'label': t['col_day'], 'field': 'Día', 'align': 'left'},
                                        {'name': 'hora', 'label': t['col_hour'], 'field': 'Hora', 'align': 'center'},
                                        {'name': 'estado', 'label': t['col_status'], 'field': 'Estado', 'align': 'center'}
                                    ]
                                    
                                    table_a = ui.table(columns=cols_a, rows=rows_a, pagination={'rowsPerPage': 8})\
                                        .classes('w-full').props('flat bordered separator=horizontal')
                                    
                                    # Slot para colorear el estado (Usa raw_status que no cambia con el idioma)
                                    table_a.add_slot('body-cell-estado', '''
                                        <q-td key="estado" :props="props">
                                            <q-badge :color="
                                                (props.row.raw_status.includes('Pendiente')) ? 'orange' : 
                                                (props.row.raw_status === 'Completada' || props.row.raw_status === 'Finalizada') ? 'green' : 'red'
                                            ">
                                                {{ props.value }}
                                            </q-badge>
                                        </q-td>
                                    ''')

                            # PANEL: MIS PREFERENCIAS
                            with ui.tab_panel(t_schedule).classes('p-6'):
                                if not schedule_data_objs:
                                    with ui.column().classes('w-full items-center justify-center py-12 text-gray-400'):
                                        ui.icon('edit_calendar', size='4xl', color='gray-300')
                                        ui.label(t['empty_prefs']).classes('mt-4 text-sm')
                                else:
                                    ui.label(t['prefs_title']).classes('text-lg font-bold text-gray-800 mb-4')
                                    
                                    # ALCABALA: Traducir días de preferencias
                                    rows_s = [{
                                        'Día': t_val(s.days, lang), # Traducción aquí
                                        'Inicio': f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}",
                                        'Fin': f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                                    } for s in schedule_data_objs]
                                    
                                    cols_s = [
                                        {'name': 'dia', 'label': t['col_day'], 'field': 'Día', 'align': 'left'},
                                        {'name': 'ini', 'label': t['col_start'], 'field': 'Inicio', 'align': 'center'},
                                        {'name': 'fin', 'label': t['col_end'], 'field': 'Fin', 'align': 'center'}
                                    ]
                                    
                                    ui.table(columns=cols_s, rows=rows_s).classes('w-full border border-gray-200 rounded-lg').props('flat')

    # --- 3. INICIALIZACIÓN ---
    # Pasamos el callback para que el Header pueda refrescar este contenido
    create_main_screen(page_refresh_callback=render_profile_content.refresh)
    
    # Renderizamos el contenido
    render_profile_content()