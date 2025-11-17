from nicegui import ui, app
from components.header import create_main_screen
from components.delete_all import delete_user_data
from db.sqlite_db import SQLiteSession
from db.models import User, SchedulePref, AsignedClasses
from auth.sync import sync_sqlite_to_postgres

# ------------------------
# Subpage de edición del perfil
# ------------------------
@ui.page('/profile_edit')
def profile_edit():
    create_main_screen()
    ui.label('Editar Perfil').classes('text-h4 mt-4 text-center')

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

        with ui.column().classes('w-full max-w-5xl mx-auto p-4 md:p-8 gap-3'):

            # Campos personales
            personal_inputs = {}
            for field, value in [
                ('name', user_obj.name),
                ('surname', user_obj.surname),
                ('username', user_obj.username),
                ('time_zone', user_obj.time_zone if hasattr(user_obj, 'time_zone') else ''),
                ('email', user_obj.email if hasattr(user_obj, 'email') else '')
            ]:
                with ui.row().classes('w-full gap-2'):
                    ui.label(f"{field.capitalize()}:").classes('w-1/4')
                    personal_inputs[field] = ui.input(value=value).classes('w-3/4')

            # Rangos horarios
            schedule_data = session.query(SchedulePref).filter(SchedulePref.username == username).all()
            schedule_inputs = []
            if schedule_data:
                ui.label("Rangos horarios:").classes('text-h5 mt-4')
                for s in schedule_data:
                    with ui.row().classes('w-full gap-2'):
                        day_input = ui.input(value=s.days)
                        start_input = ui.input(value=f"{str(s.start_time).zfill(4)[:2]}:{str(s.start_time).zfill(4)[2:]}")
                        end_input = ui.input(value=f"{str(s.end_time).zfill(4)[:2]}:{str(s.end_time).zfill(4)[2:]}")
                        schedule_inputs.append((s.id, day_input, start_input, end_input))

            # Clases asignadas
            assigned_data = session.query(AsignedClasses).filter(AsignedClasses.username == username).all()
            assigned_inputs = []
            if assigned_data:
                ui.label("Clases asignadas:").classes('text-h5 mt-4')
                for a in assigned_data:
                    with ui.row().classes('w-full gap-2'):
                        date_input = ui.input(value=a.date)
                        day_input = ui.input(value=a.days)
                        time_input = ui.input(value=f"{str(a.start_time).zfill(4)[:2]}:{str(a.start_time).zfill(4)[2:]}")
                        assigned_inputs.append((a.id, date_input, day_input, time_input))

            # Botón Guardar
            def save_changes():
                session = SQLiteSession()
                try:
                    user_obj = session.query(User).filter(User.username == username).first()
                    user_obj.name = personal_inputs['name'].value
                    user_obj.surname = personal_inputs['surname'].value
                    user_obj.time_zone = personal_inputs['time_zone'].value
                    user_obj.email = personal_inputs['email'].value
                    session.commit()

                    for id_, day_input, start_input, end_input in schedule_inputs:
                        s = session.query(SchedulePref).get(id_)
                        s.days = day_input.value
                        s.start_time = int(start_input.value.replace(":", ""))
                        s.end_time = int(end_input.value.replace(":", ""))
                    for id_, date_input, day_input, time_input in assigned_inputs:
                        a = session.query(AsignedClasses).get(id_)
                        a.date = date_input.value
                        a.days = day_input.value
                        a.start_time = int(time_input.value.replace(":", ""))
                    session.commit()

                    sync_sqlite_to_postgres()

                    ui.notify("Datos actualizados correctamente", color='positive')
                    ui.navigate('/profile')  # Regresa a la página de perfil

                finally:
                    session.close()

            ui.button("Guardar Cambios", on_click=save_changes, color='primary')

    finally:
        session.close()
