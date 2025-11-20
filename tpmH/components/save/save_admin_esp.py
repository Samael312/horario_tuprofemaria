from db.sqlite_db import SQLiteSession
from db.models import ScheduleProf, ScheduleProfEsp, User
from nicegui import ui, app
from auth.sync import sync_sqlite_to_postgres
import logging

logger = logging.getLogger(__name__)

def create_save_asgn_classes_admin(button, user, table, avai, days_of_week):

    def save_tables_to_db():
        session = SQLiteSession()
        try:
            # ============================
            #   OBTENER NOMBRE Y APELLIDO
            # ============================
            user_obj = session.query(User).filter_by(username=user).first()

            name_val = user_obj.name if user_obj else user
            surname_val = user_obj.surname if user_obj else ""

            # Aquí había un error: estabas guardando Surname como disponibilidad
            avai_val = avai.value if hasattr(avai, "value") else str(avai)

            # ======================================================
            #   TABLA 1: CLASES ASIGNADAS (MODELO: ScheduleProfEsp)
            # ======================================================
            horarios_prof_esp = set()  # evitar duplicados

            for row in table.rows:

                if not isinstance(row, dict):
                    continue

                hora_val = row.get("hora", "")
                if not hora_val:
                    continue

                # =====================
                #   PROCESAR HORARIO
                # =====================
                if "-" in hora_val:
                    start_str, end_str = hora_val.split("-")
                else:
                    start_str = end_str = hora_val

                start_time = int(start_str.replace(":", ""))
                end_time = int(end_str.replace(":", ""))

                dia = row.get("dia", "")
                fecha = row.get("fecha", "")

                # disponibilidad (si la fila no trae valor → usar el del ComboBox)
                disponibilidad = row.get("disponibilidad", avai_val)

                key = (dia, start_time, end_time)
                if key in horarios_prof_esp:
                    continue

                horarios_prof_esp.add(key)

                session.add(
                    ScheduleProfEsp(
                        username=user,
                        name=name_val,
                        surname=surname_val,
                        avai=disponibilidad,
                        date=fecha,
                        days=dia,
                        start_time=start_time,
                        end_time=end_time,
                    )
                )

            # =====================
            #   GUARDAR CAMBIOS
            # =====================
            session.commit()
            sync_sqlite_to_postgres()
            ui.notify("Información guardada correctamente", type="positive")
            logger.info("Datos guardados correctamente")

        except Exception as e:
            session.rollback()
            ui.notify(f"Error al guardar: {e}", type="negative")
            logger.exception(e)

        finally:
            session.close()

    button.on("click", save_tables_to_db)
    return save_tables_to_db
