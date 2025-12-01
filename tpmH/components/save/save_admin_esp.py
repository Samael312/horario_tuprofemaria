from nicegui import ui, app
import logging
# --- IMPORTS ARQUITECTURA HÍBRIDA ---
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
from db.models import ScheduleProfEsp, User
# ------------------------------------

logger = logging.getLogger(__name__)

def create_save_asgn_classes_admin(button, user, table, avai, days_of_week):
    """
    Guarda horarios específicos/excepciones del Profesor (ScheduleProfEsp).
    Flujo: Neon (Postgres) -> SQLite (Backup)
    """

    async def save_tables_to_db():
        # Validar usuario
        if not user:
            ui.notify("No hay usuario definido para guardar.", type="negative")
            return

        # 1. RECOLECCIÓN DE DATOS (UI)
        # Extraemos los datos de la tabla antes de abrir cualquier transacción
        
        # Obtener valor de disponibilidad global del selector
        avai_val = avai.value if hasattr(avai, "value") else str(avai)
        if not avai_val:
            ui.notify("Selecciona una disponibilidad (Available/Busy)", type="warning")
            return

        items_to_save = []
        horarios_procesados = set() # Para evitar duplicados en el mismo clic

        for row in table.rows:
            if not isinstance(row, dict): continue

            hora_val = row.get("hora", "")
            if not hora_val: continue

            # Parsear Horas
            if "-" in hora_val:
                start_str, end_str = hora_val.split("-")
            else:
                start_str = end_str = hora_val

            try:
                start_time = int(start_str.replace(":", ""))
                end_time = int(end_str.replace(":", ""))
            except ValueError: continue

            dia = row.get("dia", "")
            fecha = row.get("fecha", "")
            
            # Disponibilidad: Prioridad a la fila, si no, al global
            disponibilidad = row.get("disponibilidad", avai_val)

            # Clave única para esta tanda
            key = (dia, start_time, end_time, fecha)
            if key in horarios_procesados:
                continue
            horarios_procesados.add(key)

            items_to_save.append({
                'username': user,
                'avai': disponibilidad,
                'date': fecha,
                'days': dia,
                'start_time': start_time,
                'end_time': end_time
            })

        if not items_to_save:
            ui.notify("No hay datos válidos en la tabla para guardar.", type="warning")
            return

        # =========================================================
        # FASE 1: GUARDAR EN NEON (POSTGRES) - PRINCIPAL
        # =========================================================
        pg_session = PostgresSession()
        user_name = ""
        user_surname = ""

        try:
            # A. Obtener datos del usuario (Nombre/Apellido)
            user_pg = pg_session.query(User).filter_by(username=user).first()
            if user_pg:
                user_name = user_pg.name
                user_surname = user_pg.surname
            else:
                # Si el usuario no existe en la nube, es un problema de integridad
                ui.notify(f"El usuario {user} no existe en la base de datos de la nube.", type="negative")
                return

            # B. Insertar Nuevos Registros
            # Nota: Al ser clases específicas/excepciones, generalmente se agregan (append).
            # Si quisieras borrar todo lo anterior para este usuario, descomenta:
            # pg_session.query(ScheduleProfEsp).filter_by(username=user).delete()

            for item in items_to_save:
                new_entry = ScheduleProfEsp(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    avai=item['avai'],
                    date=item['date'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time']
                )
                pg_session.add(new_entry)

            pg_session.commit()
            logger.info(f"✅ Excepciones de horario guardadas en NEON para {user}")

        except Exception as e:
            pg_session.rollback()
            logger.error(f"❌ Error Neon Admin Esp: {e}")
            ui.notify(f"Error guardando en la nube: {e}", type="negative")
            return # Abortar si falla la nube
        finally:
            pg_session.close()

        # =========================================================
        # FASE 2: GUARDAR EN SQLITE (RESPALDO)
        # =========================================================
        try:
            sq_session = BackupSession()
            
            # Replicar la inserción
            for item in items_to_save:
                new_entry_sq = ScheduleProfEsp(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    avai=item['avai'],
                    date=item['date'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time']
                )
                sq_session.add(new_entry_sq)

            sq_session.commit()
            logger.info("💾 Respaldo Admin Esp guardado en SQLITE")

        except Exception as e:
            logger.warning(f"⚠️ Error backup local Admin Esp: {e}")
        finally:
            sq_session.close()

        ui.notify("Información guardada correctamente", type="positive")

    button.on("click", save_tables_to_db)
    return save_tables_to_db