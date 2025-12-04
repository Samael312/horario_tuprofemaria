import pandas as pd
from nicegui import ui, app
from components.headerAdmin import create_admin_screen
# --- CAMBIO IMPORTANTE: Usamos Postgres para leer datos reales ---
from db.postgres_db import PostgresSession
# ---------------------------------------------------------------
from db.models import User, ScheduleProf, AsignedClasses, ScheduleProfEsp
from components.delete_all import confirm_delete

@ui.page('/adminProfile')
def profileAdmin():
    create_admin_screen()
    
    # Verificar sesión
    username = app.storage.user.get("username")
    if not username:
        ui.navigate.to('/login')
        return

    # --- UI PRINCIPAL ---
    with ui.column().classes('w-full max-w-7xl mx-auto p-4 md:p-8 gap-6'):
        
        # 1. Encabezado con FAB (Botón flotante de acciones)
        with ui.row().classes('w-full items-center justify-between mb-2 relative'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('admin_panel_settings', size='lg', color='pink-600')
                with ui.column().classes('gap-0'):
                    ui.label('Perfil de Administrador').classes('text-3xl font-bold text-gray-800')
                    ui.label('Gestiona tus datos y visualiza tu carga horaria').classes('text-sm text-gray-500')
            
            # FAB (Menú de opciones)
            with ui.fab(icon='settings', label='Ajustes').props('color=pink-600 glossary ="settings" direction="left"'):
                ui.fab_action(icon='edit', label='Editar Perfil', on_click=lambda: ui.navigate.to('/profileA_edit'), color='blue')
                ui.fab_action(icon= 'public', label='Perfil Público', on_click=lambda: ui.navigate.to('/teacher_edit'), color='orange')
                # Este confirm_delete ya fue actualizado para borrar de Neon primero
                ui.fab_action(icon='delete_forever', label='Eliminar Cuenta', on_click=confirm_delete, color='red')

        # --- CONEXIÓN A NEON (NUBE) ---
        session = PostgresSession()
        try:
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                ui.notify("Error: Usuario no encontrado en la nube", type='negative')
                return

            # 2. Tarjeta de Datos Personales
            with ui.card().classes('w-full shadow-md rounded-xl p-0 border border-gray-200'):
                with ui.row().classes('w-full bg-gray-50 p-4 border-b border-gray-200 items-center gap-2'):
                    ui.icon('badge', color='gray-600')
                    ui.label('Información Personal').classes('text-lg font-bold text-gray-700')

                with ui.grid(columns=3).classes('w-full p-6 gap-6'):
                    def info_item(label, value, icon):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes('bg-pink-50 p-2 rounded-full'):
                                ui.icon(icon, color='pink-500', size='sm')
                            with ui.column().classes('gap-0'):
                                ui.label(label).classes('text-xs font-bold text-gray-400 uppercase')
                                ui.label(str(value)).classes('text-md font-medium text-gray-800')

                    info_item("Nombre Completo", f"{user_obj.name} {user_obj.surname}", "person")
                    info_item("Usuario", user_obj.username, "account_circle")
                    info_item("Correo", getattr(user_obj, 'email', 'N/A'), "email")
                    info_item("Zona Horaria", getattr(user_obj, 'time_zone', 'N/A'), "schedule")
                    
                    # Paquete (Opcional, si el admin también se asigna paquetes a sí mismo)
                    # rgh_obj = session.query(AsignedClasses).filter(AsignedClasses.username == username).first()
                    # package_txt = rgh_obj.package if rgh_obj else "Sin asignar"
                    # info_item("Paquete Activo", package_txt, "inventory_2")


            # 3. Sección de Tablas (Tabs)
            with ui.card().classes('w-full shadow-lg rounded-xl overflow-hidden border border-gray-200 p-0'):
                
                with ui.tabs().classes('w-full text-gray-600 bg-gray-50 border-b border-gray-200') \
                    .props('active-color="pink-600" indicator-color="pink-600" align="justify"') as tabs:
                    t_classes = ui.tab('Clases Pendientes', icon='pending_actions')
                    t_general = ui.tab('Horario General', icon='update')
                    t_specific = ui.tab('Fechas Específicas', icon='event_note')

                with ui.tab_panels(tabs, value=t_classes).classes('w-full p-0'):
                    
                    # --- PANEL 1: CLASES ASIGNADAS (PENDIENTES) ---
                    with ui.tab_panel(t_classes).classes('p-6'):
                        # Filtramos por status='Pendiente' (o lo que aplique para tu lógica de admin)
                        # Si quieres ver TODAS las clases del sistema pendientes, quita el filtro de username
                        # Si quieres ver solo las asignadas AL admin, deja el username.
                        # Asumo que quieres ver las asignadas a este usuario admin específicamente.
                        status_classes = ['Pendiente', 'Prueba_Pendiente']

                        assigned_data = (
                            session.query(AsignedClasses)
                            .filter(AsignedClasses.status.in_(status_classes))
                            .all()
                        )
                        
                        if not assigned_data:
                            show_empty_state("No tienes clases pendientes de aprobación.")
                        else:
                            df_assigned = pd.DataFrame([{
                                'Fecha': a.date,
                                'Día': a.days,
                                'Hora': f"{str(a.start_prof_time).zfill(4)[:2]}:{str(a.start_prof_time).zfill(4)[2:]} - {str(a.end_prof_time).zfill(4)[:2]}:{str(a.end_prof_time).zfill(4)[2:]}",
                                'Estudiante': f"{a.name} {a.surname}",
                                'Status': a.status
                            } for a in assigned_data])

                            cols_assigned = [
                                {'name': 'Fecha', 'label': 'FECHA', 'field': 'Fecha', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-blue-50 text-blue-900 font-bold'},
                                {'name': 'Día', 'label': 'DÍA', 'field': 'Día', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Hora', 'label': 'HORARIO', 'field': 'Hora', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Estudiante', 'label': 'ESTUDIANTE', 'field': 'Estudiante', 'align': 'left', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Status', 'label': 'ESTADO', 'field': 'Status', 'align': 'center', 'headerClasses': 'bg-yellow-50 text-yellow-900 font-bold'},
                            ]
                            
                            ui.table(columns=cols_assigned, rows=df_assigned.to_dict(orient='records'), pagination=5).classes('w-full').props('flat bordered separator=cell')

                    # --- PANEL 2: HORARIO GENERAL ---
                    with ui.tab_panel(t_general).classes('p-6'):
                        schedule_data = session.query(ScheduleProf).filter(ScheduleProf.username == username).all()
                        
                        if not schedule_data:
                             show_empty_state("No has configurado un horario general.")
                        else:
                            df_schedule = pd.DataFrame([{
                                'Día': s.days,
                                'Inicio': f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}",
                                'Fin': f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}",
                                'Disponibilidad': s.availability
                            } for s in schedule_data])

                            cols_sched = [
                                {'name': 'Día', 'label': 'DÍA', 'field': 'Día', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-pink-50 text-pink-900 font-bold'},
                                {'name': 'Inicio', 'label': 'INICIO', 'field': 'Inicio', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Fin', 'label': 'FIN', 'field': 'Fin', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Disponibilidad', 'label': 'TIPO', 'field': 'Disponibilidad', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                            ]
                            ui.table(columns=cols_sched, rows=df_schedule.to_dict(orient='records'), pagination=5).classes('w-full').props('flat bordered separator=cell')

                    # --- PANEL 3: FECHAS ESPECÍFICAS ---
                    with ui.tab_panel(t_specific).classes('p-6'):
                        fechas_apar = session.query(ScheduleProfEsp).filter(ScheduleProfEsp.username == username).all()
                        
                        if not fechas_apar:
                             show_empty_state("No hay fechas específicas configuradas.")
                        else:
                            df_esp = pd.DataFrame([{
                                'Fecha': d.date,
                                'Día': d.days,
                                'Horario': f"{str(d.start_time).zfill(4)[:2]}:{str(d.start_time).zfill(4)[2:]} - {str(d.end_time).zfill(4)[:2]}:{str(d.end_time).zfill(4)[2:]}",
                                'Disponibilidad': d.avai
                            } for d in fechas_apar])

                            cols_esp = [
                                {'name': 'Fecha', 'label': 'FECHA', 'field': 'Fecha', 'align': 'left', 'sortable': True, 'headerClasses': 'bg-purple-50 text-purple-900 font-bold'},
                                {'name': 'Día', 'label': 'DÍA', 'field': 'Día', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Horario', 'label': 'HORARIO', 'field': 'Horario', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                                {'name': 'Disponibilidad', 'label': 'ESTADO', 'field': 'Disponibilidad', 'align': 'center', 'headerClasses': 'bg-gray-100 font-bold'},
                            ]
                            ui.table(columns=cols_esp, rows=df_esp.to_dict(orient='records'), pagination=5).classes('w-full').props('flat bordered separator=cell')

        finally:
            session.close()

def show_empty_state(message):
    """Helper para mostrar estado vacío consistente"""
    with ui.column().classes('w-full items-center justify-center py-8 text-gray-400'):
        ui.icon('inbox', size='xl')
        ui.label(message).classes('text-sm italic')