from nicegui import ui, app
import logging
# --- IMPORTS (Asegúrate de que coincidan con tus nombres de archivo reales) ---
# Si tus archivos se llaman postgress.py y sqlite.py, ajusta esto.
try:
    from db.postgres_db import PostgresSession
    from db.sqlite_db import BackupSession
except ImportError:
    # Fallback por si usas los nombres del snippet anterior
    from db.postgres_db import PostgresSession
    from db.sqlite_db import BackupSession

from db.models import User, SchedulePref
# ----------------------------------------

logger = logging.getLogger(__name__)

def create_save_schedule_button(button, table, days_of_week, duration_selector, package_selector):
    """
    Guarda la configuración de horarios y el paquete seleccionado.
    Flujo: UI -> Neon (Postgres) -> SQLite (Backup).
    """

    async def save_schedule():
        username = app.storage.user.get("username")

        if not username:
            ui.notify("No hay usuario en sesión", type="negative")
            return

        # 1. Validar Inputs
        package_val = package_selector.value
        duration_val = duration_selector.value

        if not package_val:
            ui.notify("Por favor, selecciona un paquete.", type="warning")
            return

        # 2. Procesar la tabla para extraer los horarios
        new_schedules = []
        # Usamos un set para evitar duplicados EXACTOS
        seen_intervals = set()

        table_rows = table.rows
        for row in table_rows:
            # La hora de la fila (útil si no hay rango explícito)
            row_hour_str = row.get("hora", "")
            if not row_hour_str:
                continue
            
            try:
                row_start_time = int(row_hour_str.replace(":", ""))
            except ValueError:
                continue

            for day in days_of_week:
                interval_text = row.get(day, "")
                if interval_text:
                    # --- CORRECCIÓN CLAVE AQUÍ ---
                    # No confiamos ciegamente en row_start_time.
                    # Si el texto es "07:00-22:00", extraemos 07:00 como inicio real.
                    
                    real_start_time = row_start_time # Default
                    real_end_time = row_start_time   # Default

                    if "-" in interval_text:
                        parts = interval_text.split("-")
                        if len(parts) == 2:
                            try:
                                # Extraemos inicio y fin del TEXTO de la celda
                                s_str = parts[0].strip()
                                e_str = parts[1].strip()
                                real_start_time = int(s_str.replace(":", ""))
                                real_end_time = int(e_str.replace(":", ""))
                            except ValueError:
                                continue # Formato inválido, saltamos
                    else:
                        # Si no hay guion, asumimos que es una hora puntual o bloque simple
                        pass 

                    # Crear clave única para evitar duplicados
                    # (Esto evitará que la fila de las 22:00 vuelva a guardar el rango 0700-2200)
                    key = (day, real_start_time, real_end_time)
                    
                    if key not in seen_intervals:
                        new_schedules.append({
                            'days': day,
                            'start_time': real_start_time,
                            'end_time': real_end_time
                        })
                        seen_intervals.add(key)

        if not new_schedules:
            ui.notify("La tabla está vacía o no se detectaron horarios.", type="warning")
            return

        # =========================================================
        # FASE 1: GUARDAR EN NEON (POSTGRES) - PRINCIPAL
        # =========================================================
        pg_session = PostgresSession()
        user_name = "Unknown"
        user_surname = "Unknown"

        try:
            # A. Obtener Usuario
            user_pg = pg_session.query(User).filter(User.username == username).first()
            if not user_pg:
                ui.notify("Usuario no encontrado en la nube", type="negative")
                return
            
            # B. Actualizar Paquete
            user_pg.package = package_val
            
            user_name = user_pg.name
            user_surname = user_pg.surname

            # C. Borrar horarios viejos
            pg_session.query(SchedulePref).filter(SchedulePref.username == username).delete()

            # D. Insertar nuevos horarios
            for item in new_schedules:
                pref = SchedulePref(
                    username=username,
                    name=user_name,
                    surname=user_surname,
                    duration=duration_val,
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=package_val
                )
                pg_session.add(pref)

            pg_session.commit()
            ui.navigate.to('/myclasses')
            logger.info(f"✅ Horarios corregidos guardados en NEON para {username}")

        except Exception as e:
            pg_session.rollback()
            logger.error(f"❌ Error Neon: {e}")
            ui.notify(f"Error guardando en la nube: {e}", type="negative")
            return
        finally:
            pg_session.close()

        # =========================================================
        # FASE 2: GUARDAR EN SQLITE (RESPALDO)
        # =========================================================
        try:
            sq_session = BackupSession()
            
            user_sq = sq_session.query(User).filter(User.username == username).first()
            if user_sq:
                user_sq.package = package_val

            sq_session.query(SchedulePref).filter(SchedulePref.username == username).delete()

            for item in new_schedules:
                pref_sq = SchedulePref(
                    username=username,
                    name=user_name,
                    surname=user_surname,
                    duration=duration_val,
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=package_val
                )
                sq_session.add(pref_sq)

            sq_session.commit()
            logger.info("💾 Respaldo local actualizado")
            
        except Exception as e:
            logger.warning(f"⚠️ Error en respaldo local: {e}")
        finally:
            sq_session.close()

        ui.notify("Horarios actualizados correctamente (Sin duplicados)", type="positive")

    button.on('click', save_schedule)
    return save_schedule