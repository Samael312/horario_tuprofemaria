from nicegui import ui, app
from components.header import create_main_screen

from db.sqlite_db import SQLiteSession
from db.postgres_db import PostgresSession
from db.models import User


@ui.page('/profile')
def profile():
    create_main_screen()

    # -----------------------------------------
    # FUNCIÓN QUE REALMENTE ELIMINA EL USUARIO
    # -----------------------------------------
    def delete_user_data():
        username = app.storage.user.get("username")

        if not username:
            ui.notify("No hay un usuario autenticado", color="negative")
            return

        # ============ SQLITE ============
        try:
            sqlite_session = SQLiteSession()
            user_sqlite = sqlite_session.query(User).filter_by(username=username).first()

            if user_sqlite:
                sqlite_session.delete(user_sqlite)
                sqlite_session.commit()

            sqlite_session.close()

        except Exception as e:
            ui.notify(f"Error en SQLite: {e}", color="warning")

        # ============ POSTGRES ============
        try:
            pg_session = PostgresSession()
            user_pg = pg_session.query(User).filter_by(username=username).first()

            if user_pg:
                pg_session.delete(user_pg)
                pg_session.commit()

            pg_session.close()

        except Exception as e:
            ui.notify(f"Error en PostgreSQL: {e}", color="warning")

        # ============ LIMPIAR SESIÓN ============
        app.storage.user.clear()

        ui.notify("Tus datos han sido eliminados correctamente", color="positive")
        ui.navigate.to('/login')

    # -----------------------------------------
    # UI
    # -----------------------------------------

    with ui.column().classes('absolute-center items-center gap-4'):
        ui.label('Página de perfil del usuario').classes('text-2xl font-bold')

        # Creamos el diálogo ANTES del botón
        with ui.dialog() as dialog:
            with ui.card().classes('p-4'):
                ui.label(
                    "¿Seguro que quieres eliminar todos tus datos?\n"
                    "Esta acción es irreversible."
                ).classes('text-center mb-3')

                with ui.row().classes('justify-around w-full'):
                    ui.button("Cancelar", on_click=dialog.close)
                    ui.button("Eliminar", color="negative",
                              on_click=lambda: (dialog.close(), delete_user_data()))

        # Botón que abre el diálogo
        ui.button(
            "Eliminar TODOS mis datos",
            color="negative",
            icon="delete_forever",
            on_click=dialog.open  # <-- ESTE SÍ FUNCIONA
        )
