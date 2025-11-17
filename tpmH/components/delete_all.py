from nicegui import ui, app
from db.sqlite_db import SQLiteSession
from db.postgres_db import PostgresSession
import logging
from db.models import User, SchedulePref, AsignedClasses


# =========================================
# FUNCIÓN QUE MUESTRA EL DIÁLOGO
# =========================================
def confirm_delete():
    with ui.dialog() as dialog:
        with ui.card().classes('p-6 w-96 gap-4'):
            ui.label("Eliminar cuenta").classes("text-h5 font-bold")
            ui.separator()

            ui.label(
                "¿Estás seguro de que deseas eliminar tu cuenta?\n"
                "Esta acción es permanente."
            ).classes("text-body1 text-negative")

            with ui.row().classes('justify-end gap-4 mt-4'):
                ui.button("Cancelar", on_click=dialog.close)
                ui.button(
                    "Eliminar",
                    color="negative",
                    on_click=lambda: (dialog.close(), delete_user_data())
                )

    dialog.open()

# =========================================
# FUNCIÓN QUE ELIMINA USUARIO Y DATOS
# =========================================
def delete_user_data():
    username = app.storage.user.get("username")

    if not username:
        ui.notify("No hay un usuario autenticado", color="negative")
        return

    # ================= SQLITE =================
    try:
        sqlite_session = SQLiteSession()

        sqlite_session.query(AsignedClasses).filter(
            AsignedClasses.username == username
        ).delete(synchronize_session=False)

        sqlite_session.query(SchedulePref).filter(
            SchedulePref.username == username
        ).delete(synchronize_session=False)

        sqlite_session.query(User).filter(
            User.username == username
        ).delete(synchronize_session=False)

        sqlite_session.commit()
        sqlite_session.close()

    except Exception as e:
        ui.notify(f"Error en SQLite: {e}", color="warning")
        logging.exception("Error al eliminar datos en SQLite")

    # ================= POSTGRES =================
    try:
        pg_session = PostgresSession()

        pg_session.query(AsignedClasses).filter(
            AsignedClasses.username == username
        ).delete(synchronize_session=False)

        pg_session.query(SchedulePref).filter(
            SchedulePref.username == username
        ).delete(synchronize_session=False)

        pg_session.query(User).filter(
            User.username == username
        ).delete(synchronize_session=False)

        pg_session.commit()
        pg_session.close()

    except Exception as e:
        ui.notify(f"Error en PostgreSQL: {e}", color="warning")
        logging.exception("Error al eliminar datos en PostgreSQL")

    # ================= LIMPIAR SESIÓN =================
    app.storage.user.clear()

    ui.notify("Tus datos han sido eliminados correctamente", color="positive")
    ui.navigate.to('/login')
