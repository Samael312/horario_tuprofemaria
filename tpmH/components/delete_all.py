from nicegui import ui, app
import logging
# --- IMPORTS ACTUALIZADOS ---
from db.postgres_db import PostgresSession  # Fuente de la verdad (Neon)
from db.sqlite_db import BackupSession       # Respaldo (SQLite)
from db.models import User, SchedulePref, AsignedClasses
# ----------------------------

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# =========================================
# FUNCIÓN QUE MUESTRA EL DIÁLOGO
# =========================================
def confirm_delete():
    with ui.dialog() as dialog:
        with ui.card().classes('p-6 w-96 gap-4'):
            ui.label("Eliminar cuenta").classes("text-h5 font-bold text-red-600")
            ui.separator()

            ui.label(
                "¿Estás seguro de que deseas eliminar tu cuenta?\n"
                "Se borrarán todos tus horarios y clases agendadas.\n"
                "Esta acción es permanente e irreversible."
            ).classes("text-body1 text-gray-700")

            with ui.row().classes('justify-end gap-4 mt-4'):
                ui.button("Cancelar", on_click=dialog.close).props('flat')
                ui.button(
                    "Eliminar Definitivamente",
                    color="negative",
                    icon="delete_forever",
                    on_click=lambda: (dialog.close(), delete_user_data())
                )

    dialog.open()

# =========================================
# FUNCIÓN QUE ELIMINA USUARIO Y DATOS
# =========================================
def delete_user_data():
    username = app.storage.user.get("username")

    if not username:
        ui.notify("Error: No hay sesión activa", color="negative")
        return

    # ================= FASE 1: BORRAR DE NEON (CRÍTICO) =================
    # Si esto falla, el usuario NO se borra.
    pg_session = PostgresSession()
    try:
        # Borrar datos hijos primero (Clases y Preferencias)
        pg_session.query(AsignedClasses).filter(AsignedClasses.username == username).delete()
        pg_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
        
        # Borrar Usuario padre
        deleted_count = pg_session.query(User).filter(User.username == username).delete()
        
        if deleted_count == 0:
            ui.notify("El usuario no existe en la nube.", type='warning')
            pg_session.close()
            return

        pg_session.commit()
        logger.info(f"✅ Usuario {username} eliminado de NEON.")

    except Exception as e:
        pg_session.rollback()
        logger.error(f"❌ Error eliminando de Neon: {e}")
        ui.notify("Error de conexión. No se pudo eliminar la cuenta.", type='negative')
        return # DETENEMOS AQUÍ. No tocamos el backup si la nube falló.
    finally:
        pg_session.close()

    # ================= FASE 2: BORRAR DE SQLITE (RESPALDO) =================
    # Solo llegamos aquí si la Fase 1 fue exitosa.
    try:
        sqlite_session = BackupSession()

        sqlite_session.query(AsignedClasses).filter(AsignedClasses.username == username).delete()
        sqlite_session.query(SchedulePref).filter(SchedulePref.username == username).delete()
        sqlite_session.query(User).filter(User.username == username).delete()

        sqlite_session.commit()
        logger.info(f"🗑️ Copia local de {username} eliminada.")
        sqlite_session.close()

    except Exception as e:
        # Si falla el backup local, no es grave. El usuario ya no puede entrar porque lo borramos de Neon.
        logger.warning(f"⚠️ Error limpiando backup local: {e}")

    # ================= LIMPIAR SESIÓN Y SALIR =================
    app.storage.user.clear()
    
    ui.notify("Tu cuenta ha sido eliminada correctamente. ¡Hasta luego!", type="positive", icon="sentiment_satisfied")
    
    # Damos un segundo para que lea el mensaje antes de sacarlo
    ui.timer(1.5, lambda: ui.navigate.to('/login'))