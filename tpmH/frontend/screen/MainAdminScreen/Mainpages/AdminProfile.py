import pandas as pd
from nicegui import ui, app
from components.headerAdmin import create_admin_screen
from db.sqlite_db import SQLiteSession
from db.models import User, ScheduleProf, AsignedClasses
from components.delete_all import confirm_delete


@ui.page('/adminProfile')
def profileAdmin():
    create_admin_screen()
    # Título centrado con FAB
    with ui.row().classes('w-full items-center justify-between mt-4 relative'):
        ui.label('Profile').classes('text-h4 absolute left-1/2 transform -translate-x-1/2')
        with ui.fab(icon='menu', label='Opciones'):
            ui.fab_action(icon='edit', label='Editar', on_click=lambda: ui.navigate.to('/profileA_edit'), color='positive')
            ui.fab_action(icon='delete', label='Eliminar cuenta', on_click=confirm_delete, color='negative')

    username = app.storage.user.get("username")
    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    session = SQLiteSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
                ui.label("Usuario no encontrado en DB").classes('text-negative mt-4')
            return

        # ========================
        # Datos personales
        # ========================
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
            for label_text in [
                f"Nombre: {user_obj.name}",
                f"Apellido: {user_obj.surname}",
                f"Usuario: {user_obj.username}",
                f"Zona horaria: {user_obj.time_zone if hasattr(user_obj, 'time_zone') else 'N/A'}",
                f"Correo: {user_obj.email if hasattr(user_obj, 'email') else 'N/A'}"
            ]:
                with ui.row().classes('w-full'):
                    ui.label(label_text).classes('text-base md:text-lg')

        rgh_obj = session.query(AsignedClasses).filter(AsignedClasses.username == username).first()
        if not rgh_obj:
            with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
                ui.label("Aun no tienes horario ni clases").classes('text-negative mt-4')
            return

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):
            for label_text2 in [
                f"Paquete de clases: {rgh_obj.package}"
            ]:
                with ui.row().classes('w-full'):
                    ui.label(label_text2).classes('text-base md:text-lg')
            # ========================
            # Rangos horarios como DataFrame
            # ========================
            schedule_data = session.query(ScheduleProf).filter(
                ScheduleProf.username == username
            ).all()

            if schedule_data:
                ui.label("Rangos horarios:").classes('text-h5 mt-6')

                # Crear DataFrame
                df_schedule = pd.DataFrame([{
                    'Día': s.days,
                    'Hora Inicio': f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}",
                    'Hora Fin': f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}",
                    'Disponibilidad': s.availability
                } for s in schedule_data])

                # Mostrar tabla usando ui.table
                ui.table(
                    columns=[{'field': col, 'label': col} for col in df_schedule.columns],
                    rows=df_schedule.to_dict(orient='records')
                ).classes('w-full')

            # ========================
            # Clases asignadas como DataFrame
            # ========================
            assigned_data = session.query(AsignedClasses).filter(
                AsignedClasses.username == username
            ).all()

            if assigned_data:
                ui.label("Clases asignadas:").classes('text-h5 mt-6')

                df_assigned = pd.DataFrame([{
                    'Nombre': a.name,
                    "Apellido": a.surname,
                    'Fecha': a.date,
                    'Día': a.days,
                    'Hora Inicio': f"{str(a.start_time).zfill(4)[:2]}:{str(a.start_time).zfill(4)[2:]}",
                    'Hora Fin': f"{str(a.end_time).zfill(4)[:2]}:{str(a.end_time).zfill(4)[2:]}"
                } for a in assigned_data])

                ui.table(
                    columns=[{'field': col, 'label': col} for col in df_assigned.columns],
                    rows=df_assigned.to_dict(orient='records')
                ).classes('w-full')

    finally:
        session.close()
