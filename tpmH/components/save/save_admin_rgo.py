from nicegui import ui, app
import logging
# --- IMPORTS DE ARQUITECTURA HÍBRIDA ---
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
from db.models import User, ScheduleProf  # OJO: Usamos ScheduleProf aquí
# ---------------------------------------

logger = logging.getLogger(__name__)

def create_save_schedule_admin_button(button, table, days_of_week, availability):
    """
    Guarda el horario del ADMINISTRADOR/PROFESOR.
    Modelo: ScheduleProf
    Flujo: Neon -> SQLite
    """

    async def save_admin_rgo_schedule():
        username = app.storage.user.get("username")

        if not username:
            ui.notify("No hay usuario en sesión", type="negative")
            return
        
        # 1. Recolectar datos de la UI antes de abrir transacciones
        avail_val = availability.value
        if not avail_val:
            ui.notify("Selecciona la disponibilidad (Available/Busy)", type="warning")
            return

        new_schedules = []
        rangos_guardados = set() # Mantenemos tu lógica de evitar duplicados por día

        rows = table.rows
        for row in rows:
            start_time_str = row.get("hora", "")
            if not start_time_str: continue

            try:
                start_time = int(start_time_str.replace(":", ""))
            except ValueError: continue

            for day in days_of_week:
                interval = row.get(day, "")
                if not interval: continue

                # Parsear intervalo "HH:MM-HH:MM"
                if "-" in interval:
                    parts = interval.split("-")
                    end_str = parts[1] if len(parts) > 1 else start_time_str
                else:
                    end_str = start_time_str # Si no hay rango, fin = inicio
                
                try:
                    end_time = int(end_str.replace(":", ""))
                except ValueError: continue

                # 🚨 TU LÓGICA ORIGINAL: 
                # Si ya guardamos un rango para este día en este clic, saltamos.
                if day in rangos_guardados:
                    continue
                rangos_guardados.add(day)

                new_schedules.append({
                    'days': day,
                    'start_time': start_time,
                    'end_time': end_time,
                    'availability': avail_val
                })

        if not new_schedules:
            ui.notify("No se detectaron horarios para guardar.", type="warning")
            return

        # =========================================================
        # FASE 1: GUARDAR EN NEON (POSTGRES) - PRINCIPAL
        # =========================================================
        pg_session = PostgresSession()
        user_name = ""
        user_surname = ""

        try:
            # A. Obtener datos del usuario
            user_pg = pg_session.query(User).filter(User.username == username).first()
            if not user_pg:
                ui.notify("Usuario no encontrado en la nube", type="negative")
                return
            
            user_name = user_pg.name
            user_surname = user_pg.surname

            # B. Limpiar horarios antiguos del PROFESOR
            pg_session.query(ScheduleProf).filter(ScheduleProf.username == username).delete()

            # C. Insertar nuevos
            for item in new_schedules:
                prof_entry = ScheduleProf(
                    username=username,
                    name=user_name,
                    surname=user_surname,
                    availability=item['availability'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time']
                )
                pg_session.add(prof_entry)

            pg_session.commit()
            logger.info(f"✅ Horario Admin guardado en NEON para {username}")

        except Exception as e:
            pg_session.rollback()
            logger.error(f"❌ Error Neon Admin: {e}")
            ui.notify(f"Error guardando en la nube: {e}", type="negative")
            return
        finally:
            pg_session.close()

        # =========================================================
        # FASE 2: GUARDAR EN SQLITE (RESPALDO)
        # =========================================================
        try:
            sq_session = BackupSession()
            
            # A. Limpiar
            sq_session.query(ScheduleProf).filter(ScheduleProf.username == username).delete()

            # B. Insertar
            for item in new_schedules:
                prof_entry_sq = ScheduleProf(
                    username=username,
                    name=user_name,
                    surname=user_surname,
                    availability=item['availability'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time']
                )
                sq_session.add(prof_entry_sq)

            sq_session.commit()
            logger.info("💾 Respaldo Admin guardado en SQLITE")

        except Exception as e:
            logger.warning(f"⚠️ Error backup local Admin: {e}")
        finally:
            sq_session.close()

        ui.notify("Horarios de Profesor actualizados con éxito", type="positive")

    button.on('click', save_admin_rgo_schedule)
    return save_admin_rgo_schedule