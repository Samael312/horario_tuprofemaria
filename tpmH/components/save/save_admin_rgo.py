from nicegui import ui, app
from db.sqlite_db import SQLiteSession
from db.models import User, ScheduleProf
from auth.sync import sync_sqlite_to_postgres


def create_save_schedule_admin_button(button, table, days_of_week, availability):
    """
    Crea un botón reutilizable para guardar horarios.

    Parámetros:
        table (ui.table): tabla NiceGUI que contiene los horarios.
        days_of_week (list[str]): lista de nombres de columnas (días).
        duration_selector (ui.element): selector de duración.
        package_selector (ui.element): selector de paquete.
    """

    def save_admin_rgo_schedule():
        username = app.storage.user.get("username")

        if not username:
            ui.notify("No hay usuario en sesión", color="negative")
            return

        session = SQLiteSession()
        try:
            # Obtener usuario
            user_obj = session.query(User).filter(User.username == username).first()
            if not user_obj:
                ui.notify("Usuario no encontrado en DB", color="negative")
                return

            # --- NUEVO: Guardar el paquete en el Usuario ---
            # -----------------------------------------------

            table_rows = table.rows
            rangos_guardados = set()  # Evitar duplicados de día

            for row in table_rows:
                start_time_str = row.get("hora", "")
                if not start_time_str:
                    continue

                start_time = int(start_time_str.replace(":", ""))

                for day in days_of_week:
                    interval = row.get(day, "")
                    if not interval:
                        continue

                    # Manejar intervalos "start-end" o solo "start"
                    if "-" in interval:
                        _, end_str = interval.split("-")
                    else:
                        end_str = start_time_str

                    end_time = int(end_str.replace(":", ""))

                    # 🚨 Evitar guardar el mismo día dos veces
                    if day in rangos_guardados:
                        continue
                    rangos_guardados.add(day)

                    prof = ScheduleProf(
                        username=user_obj.username,
                        name=user_obj.name,
                        surname=user_obj.surname,
                        availability=availability.value,
                        days=day,
                        start_time=start_time,
                        end_time=end_time,
                    )
                    session.add(prof)

            session.commit()

            # Sincronizar a Postgres
            sync_sqlite_to_postgres()

            ui.notify("Horarios y paquete actualizados con éxito", color="positive")

        finally:
            session.close()

    button.on('click', save_admin_rgo_schedule)
    return save_admin_rgo_schedule