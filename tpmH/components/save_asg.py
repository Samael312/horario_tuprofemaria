from db.sqlite_db import SQLiteSession
from db.models import SchedulePref, AsignedClasses, User
from nicegui import ui, app
from auth.sync import sync_sqlite_to_postgres
import logging

logger = logging.getLogger(__name__)

def create_save_asgn_classes(button, user, table_clases, table_rangos, duration_selector, days_of_week, package_selector):

    def save_tables_to_db():
        session = SQLiteSession()
        try:
            # ============================
            #   OBTENER NOMBRE Y APELLIDO
            # ============================
            user_obj = session.query(User).filter_by(username=user).first()
            name_val = user_obj.name if user_obj else user
            surname_val = user_obj.surname if user_obj else ""

            # ======================================================
            #   TABLA 1: CLASES ASIGNADAS (MODELO: AsignedClasses)
            # ======================================================
            intervalos_guardados = set()     # evitar duplicados

            for row in table_clases.rows:

                hora_val = row.get("hora", "")
                if not hora_val:
                    continue

                if "-" in hora_val:
                    start_str, end_str = hora_val.split("-")
                else:
                    start_str = end_str = hora_val

                # Convertir a enteros sin ":"  → "06:30" → 630
                start_time = int(start_str.replace(":", ""))
                end_time   = int(end_str.replace(":", ""))

                dia = row.get("dia", "")
                dur = row.get("duration", duration_selector.value)
                fecha = row.get("fecha", "")
                paquete = package_selector.value or ""

                key = (dia, start_time, end_time, paquete)
                if key in intervalos_guardados:
                    continue

                intervalos_guardados.add(key)

                session.add(AsignedClasses(
                    username=user,
                    name=name_val,
                    surname=surname_val,
                    duration=dur,
                    date=fecha,
                    days=dia,
                    start_time=start_time,
                    end_time=end_time,
                    package=paquete
                ))

            # =====================================================
            #   TABLA 2: RANGOS HORARIOS (MODELO: SchedulePref)
            # =====================================================
            # === TABLA 2: RANGOS HORARIOS ===
            rangos_guardados = set()    # Para impedir duplicados de DÍA

            for row in table_rangos.rows:

                start_time_str = row.get("hora", "")
                if not start_time_str:
                    continue

                start_time = int(start_time_str.replace(":", ""))

                for day in days_of_week:

                    interval = row.get(day, "")
                    if not interval:
                        continue

                    if "-" in interval:
                        _, end_str = interval.split("-")
                    else:
                        end_str = start_time_str

                    end_time = int(end_str.replace(":", ""))

                    # 🚨 EVITAR GUARDAR DOS VECES EL MISMO DÍA
                    if day in rangos_guardados:
                        continue

                    rangos_guardados.add(day)

                    session.add(SchedulePref(
                        username=user,
                        name=name_val,
                        surname=surname_val,
                        duration=duration_selector.value,
                        days=day,
                        start_time=start_time,
                        end_time=end_time,
                        package=package_selector.value or ""
                    ))


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
