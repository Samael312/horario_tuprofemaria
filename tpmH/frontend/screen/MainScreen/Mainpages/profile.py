from nicegui import ui, app
from components.header import create_main_screen

from db.sqlite_db import SQLiteSession
from db.models import User, SchedulePref, AsignedClasses
from components.delete_all import confirm_delete


@ui.page('/profile')
def profile():
    create_main_screen()

    # Título centrado
    with ui.row().classes('w-full items-center justify-between mt-4 relative'):
        # Label centrado
        ui.label('Profile').classes('text-h4 absolute left-1/2 transform -translate-x-1/2')

        # FAB a la derecha
        with ui.fab(icon='menu', label='Opciones'):  # icon válido de Material Icons
            ui.fab_action(icon='edit', label='Editar', on_click=lambda: ui.navigate.to('/profile_edit'), color='positive')
            ui.fab_action(icon='delete', label='Eliminar cuenta', on_click=confirm_delete, color='negative')


    username = app.storage.user.get("username")
    if not username:
        ui.label("No hay usuario en sesión").classes('text-negative mt-4')
        return

    session = SQLiteSession()
    try:
        user_obj = session.query(User).filter(User.username == username).first()
        if not user_obj:
            ui.label("Usuario no encontrado en DB").classes('text-negative mt-4')
            return

        # ========================
        # Datos personales
        # ========================
        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):

            # Cada dato en su propia fila
            for label_text in [
                f"Nombre: {user_obj.name}",
                f"Apellido: {user_obj.surname}",
                f"Usuario: {user_obj.username}",
                f"Zona horaria: {user_obj.time_zone if hasattr(user_obj, 'time_zone') else 'N/A'}",
                f"Correo: {user_obj.email if hasattr(user_obj, 'email') else 'N/A'}"
            ]:
                with ui.row().classes('w-full'):
                    ui.label(label_text).classes('text-base md:text-lg')

            # ========================
            # Tabla de Rangos Horarios
            # ========================
            schedule_data = session.query(SchedulePref).filter(
                SchedulePref.username == username
            ).all()

            if schedule_data:
                # Label encima de la tabla
                ui.label("Rangos horarios:").classes('text-h5 mt-6')

                # Crear tabla y hacerla full width
                schedule_table = ui.table(
                    columns=[
                        {'field': 'day', 'label': 'Día'},
                        {'field': 'start', 'label': 'Hora Inicio'},
                        {'field': 'end', 'label': 'Hora Fin'}
                    ],
                    rows=[]
                )
                schedule_table.classes('w-full')

                for s in schedule_data:
                    start_str = str(s.start_time).zfill(4)
                    end_str = str(s.end_time).zfill(4)
                    schedule_table.add_row({
                        'day': s.days,
                        'start': f"{start_str[:2]}:{start_str[2:]}",
                        'end': f"{end_str[:2]}:{end_str[2:]}"
                    })

            # ========================
            # Tabla de Clases Asignadas
            # ========================
            assigned_data = session.query(AsignedClasses).filter(
                AsignedClasses.username == username
            ).all()

            if assigned_data:
                # Label encima de la tabla
                ui.label("Clases asignadas:").classes('text-h5 mt-6')

                # Crear tabla y hacerla full width
                assigned_table = ui.table(
                    columns=[
                        {'field': 'date', 'label': 'Fecha'},
                        {'field': 'day', 'label': 'Día'},
                        {'field': 'time', 'label': 'Hora'}
                    ],
                    rows=[]
                )
                assigned_table.classes('w-full')

                for a in assigned_data:
                    start_str = str(a.start_time).zfill(4)
                    assigned_table.add_row({
                        'date': a.date,
                        'day': a.days,
                        'time': f"{start_str[:2]}:{start_str[2:]}"
                    })

    finally:
        session.close()
