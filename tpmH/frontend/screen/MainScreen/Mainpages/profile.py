from nicegui import ui, app
import pandas as pd
from components.header import create_main_screen
from db.postgres_db import PostgresSession
from db.models import User, SchedulePref, AsignedClasses
from components.delete_all import confirm_delete
from sqlalchemy import or_
import logging

# Configuración de logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@ui.page('/profile')
def profile():
    create_main_screen()

    # Verificar sesión
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    session = PostgresSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        
        if not user_obj:
            ui.notify("Usuario no encontrado", type='negative')
            return

        # --- UI PRINCIPAL ---
        # Usamos un contenedor ancho (max-w-6xl) para aprovechar el grid
        with ui.column().classes('w-full max-w-6xl mx-auto p-4 md:p-8 gap-6'):
            
            # HEADER CON TITULO Y FAB
            with ui.row().classes('w-full items-center justify-between mb-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('account_circle', size='lg', color='pink-600')
                    with ui.column().classes('gap-0'):
                        ui.label('Mi Perfil').classes('text-3xl font-bold text-gray-800 leading-none')
                        ui.label('Gestiona tu información y plan').classes('text-sm text-gray-500')
                
                with ui.fab(icon='settings', label='Opciones', color='pink-600', direction='left') :
                    ui.fab_action(icon='edit', label='Editar', on_click=lambda: ui.navigate.to('/profile_edit'), color='blue')
                    ui.fab_action(icon='delete_forever', label='Eliminar cuenta', on_click=confirm_delete, color='red')

            # --- GRID LAYOUT (Responsive) ---
            # CAMBIO CLAVE: lg:grid-cols-[auto_1fr] 
            # Esto significa: "En pantallas grandes, la 1ra columna es automática (según contenido) y la 2da llena el resto".
            with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-[auto_1fr] gap-6 items-start'):
                
                # === COLUMNA IZQUIERDA (Info + Plan) ===
                # CAMBIO: Quitamos 'lg:col-span-1' y 'w-full'. 
                # Ponemos 'min-w-[300px]' para asegurar que no sea demasiado estrecha si no hay datos.
                with ui.column().classes('w-full lg:w-auto min-w-[300px] gap-6'):
                    
                    # 1. Tarjeta Datos Personales
                    with ui.card().classes('w-full p-0 shadow-md rounded-xl overflow-hidden border border-gray-100'):
                        with ui.row().classes('w-full bg-gray-50 p-4 items-center gap-3 border-b border-gray-100'):
                            ui.icon('badge', size='sm', color='gray-500')
                            ui.label("Información Personal").classes('text-lg font-bold text-gray-700')

                        with ui.column().classes('w-full p-5 gap-4'):
                            def info_item(label, value, icon):
                                # Usamos no-wrap para que el texto no fuerce saltos de linea extraños y defina el ancho
                                with ui.row().classes('w-full items-center gap-3'):
                                    with ui.element('div').classes('p-2 bg-pink-50 rounded-full shrink-0'): # shrink-0 evita que el icono se aplaste
                                        ui.icon(icon, color='pink-500', size='xs')
                                    with ui.column().classes('gap-0'):
                                        ui.label(label).classes('text-[10px] font-bold text-gray-400 uppercase tracking-wide whitespace-nowrap')
                                        ui.label(str(value)).classes('text-sm text-gray-800 font-medium break-all')
                            
                            info_item('Nombre Completo', f"{user_obj.name} {user_obj.surname}", 'face')
                            info_item('Usuario', user_obj.username, 'alternate_email')
                            info_item('Email', getattr(user_obj, 'email', 'N/A'), 'mail')
                            info_item('Objetivo', getattr(user_obj, 'goal', 'Objetivo'), 'assignment')
                            info_item('Zona Horaria', getattr(user_obj, 'time_zone', 'UTC'), 'public')

                    # 2. Tarjeta Paquete
                    rgh_obj = session.query(SchedulePref).filter(SchedulePref.username == username).first()
                    with ui.card().classes('w-full p-0 shadow-md rounded-xl overflow-hidden border border-gray-100'):
                        if rgh_obj and rgh_obj.package:
                            with ui.row().classes('w-full p-4 bg-pink-600 items-center justify-between'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.icon('card_membership', color='white')
                                    # whitespace-nowrap asegura que este titulo dicte el ancho minimo si es muy largo
                                    ui.label("Plan Activo").classes('text-white font-bold whitespace-nowrap')
                                ui.icon('verified', color='white')
                            
                            with ui.column().classes('w-full p-6 items-center text-center'):
                                ui.label(rgh_obj.package).classes('text-2xl font-black text-gray-800 uppercase tracking-wide whitespace-nowrap')
                                ui.label('Suscripción vigente').classes('text-xs text-green-700 font-bold bg-green-100 px-3 py-1 rounded-full mt-2 whitespace-nowrap')
                        else:
                            with ui.column().classes('w-full p-8 items-center text-center bg-gray-50'):
                                ui.icon('sentiment_dissatisfied', size='lg', color='gray-400')
                                ui.label("Sin plan activo").classes('text-gray-500 font-medium mt-2 whitespace-nowrap')
                # === COLUMNA DERECHA (Tabs) ===
                # CAMBIO: Quitamos 'lg:col-span-2' y agregamos 'min-w-0'.
                # 'min-w-0' es CRÍTICO para que las tablas no rompan el diseño responsive.
                with ui.column().classes('w-full gap-6 min-w-0'):
                    
                    with ui.card().classes('w-full shadow-md rounded-xl overflow-hidden border border-gray-100 p-0 min-h-[400px]'):
                        # Tabs Header
                        with ui.tabs().classes('w-full text-gray-500 bg-gray-50 border-b border-gray-200') \
                            .props('active-color="pink-600" indicator-color="pink-600" align="justify"') as tabs:
                            t_assigned = ui.tab('Tus Clases', icon='school')
                            t_schedule = ui.tab('Mis Preferencias', icon='tune')

                        # Panels
                        with ui.tab_panels(tabs, value=t_assigned).classes('w-full p-0'):
                            
                            # PANEL: TUS CLASES
                            with ui.tab_panel(t_assigned).classes('p-0'):
                                # Consulta
                                assigned_data = session.query(AsignedClasses).filter(
                                    AsignedClasses.username == username,
                                    AsignedClasses.status.in_([
                                        'Pendiente', 
                                        'Prueba_Pendiente',
                                        'Agendada', 
                                        'Completada', 
                                        'Finalizada'
                                    ])
                                ).order_by(AsignedClasses.date.desc(), AsignedClasses.start_time.desc()).all()
                                
                                if not assigned_data:
                                    with ui.column().classes('w-full items-center justify-center py-16 text-gray-400'):
                                        ui.icon('event_busy', size='4xl', color='gray-300')
                                        ui.label("No tienes historial de clases.").classes('mt-4 text-sm')
                                else:
                                    # Preparar datos
                                    rows_a = []
                                    for a in assigned_data:
                                        h_start = f"{str(a.start_time).zfill(4)[:2]}:{str(a.start_time).zfill(4)[2:]}"
                                        status_clean = a.status.replace('_', ' ')
                                        
                                        rows_a.append({
                                            'Fecha': a.date,
                                            'Día': a.days,
                                            'Hora': h_start,
                                            'Estado': status_clean,
                                            'raw_status': a.status
                                        })
                                    
                                    cols_a = [
                                        {'name': 'fecha', 'label': 'Fecha', 'field': 'Fecha', 'align': 'left', 'sortable': True},
                                        {'name': 'dia', 'label': 'Día', 'field': 'Día', 'align': 'left'},
                                        {'name': 'hora', 'label': 'Hora', 'field': 'Hora', 'align': 'center'},
                                        {'name': 'estado', 'label': 'Estado', 'field': 'Estado', 'align': 'center'}
                                    ]
                                    
                                    table_a = ui.table(columns=cols_a, rows=rows_a, pagination={'rowsPerPage': 8})\
                                        .classes('w-full').props('flat bordered separator=horizontal')
                                    
                                    # Slot coloreado
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
                                schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
                                if not schedule_data:
                                    with ui.column().classes('w-full items-center justify-center py-12 text-gray-400'):
                                        ui.icon('edit_calendar', size='4xl', color='gray-300')
                                        ui.label("No has guardado preferencias de horario.").classes('mt-4 text-sm')
                                else:
                                    ui.label("Tus horarios preferidos").classes('text-lg font-bold text-gray-800 mb-4')
                                    
                                    rows_s = [{
                                        'Día': s.days,
                                        'Inicio': f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}",
                                        'Fin': f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}"
                                    } for s in schedule_data]
                                    
                                    cols_s = [
                                        {'name': 'dia', 'label': 'Día', 'field': 'Día', 'align': 'left'},
                                        {'name': 'ini', 'label': 'Inicio', 'field': 'Inicio', 'align': 'center'},
                                        {'name': 'fin', 'label': 'Fin', 'field': 'Fin', 'align': 'center'}
                                    ]
                                    
                                    ui.table(columns=cols_s, rows=rows_s).classes('w-full border border-gray-200 rounded-lg').props('flat')

    finally:
        session.close()