from nicegui import ui, app
import logging
# --- IMPORTS ARQUITECTURA HÍBRIDA ---
from db.postgres_db import PostgresSession  # Fuente de la verdad
from db.sqlite_db import BackupSession       # Respaldo
from db.models import SchedulePref, AsignedClasses, User
# ------------------------------------

logger = logging.getLogger(__name__)

def create_save_asgn_classes(button, user, table_clases, table_rangos, duration_selector, days_of_week, package_selector):
    """
    Guarda Clases Asignadas (y opcionalmente Rangos Horarios) siguiendo el flujo:
    1. Neon (Postgres) -> Principal
    2. SQLite -> Respaldo
    """

    async def save_tables_to_db():
        username = app.storage.user.get("username")

        if not username:
            ui.notify("No hay usuario en sesión", type="negative")
            return

        # 1. Recolectar Datos de la UI (Antes de abrir DB)
        package_val = package_selector.value or ""
        duration_val = duration_selector.value
        
        # --- PREPARAR DATOS: CLASES ASIGNADAS ---
        clases_data = []
        intervalos_clases = set()
        
        if table_clases:
            for row in table_clases.rows:
                hora_val = row.get("hora", "")
                if not hora_val: continue

                if "-" in hora_val:
                    start_str, end_str = hora_val.split("-")
                else:
                    start_str = end_str = hora_val

                try:
                    start_time = int(start_str.replace(":", ""))
                    end_time = int(end_str.replace(":", ""))
                except ValueError: continue

                dia = row.get("dia", "")
                # Usamos la duración de la fila si existe, si no la del selector global
                dur = row.get("duration", duration_val)
                fecha = row.get("fecha", "")

                # Evitar duplicados exactos en la misma lista de guardado
                key = (dia, start_time, end_time, package_val, fecha)
                if key in intervalos_clases:
                    continue
                intervalos_clases.add(key)

                clases_data.append({
                    'username': username,
                    'duration': dur,
                    'date': fecha,
                    'days': dia,
                    'start_time': start_time,
                    'end_time': end_time,
                    'package': package_val
                })

        # --- PREPARAR DATOS: RANGOS HORARIOS (Si aplica) ---
        rangos_data = []
        dias_guardados_rango = set()
        
        if table_rangos:
            for row in table_rangos.rows:
                start_time_str = row.get("hora", "")
                if not start_time_str: continue
                
                try:
                    start_time = int(start_time_str.replace(":", ""))
                except ValueError: continue

                for day in days_of_week:
                    interval = row.get(day, "")
                    if not interval: continue

                    if "-" in interval:
                        parts = interval.split("-")
                        end_str = parts[1] if len(parts) > 1 else start_time_str
                    else:
                        end_str = start_time_str
                    
                    try:
                        end_time = int(end_str.replace(":", ""))
                    except ValueError: continue

                    # 🚨 TU LÓGICA ORIGINAL: Evitar guardar el mismo día dos veces
                    if day in dias_guardados_rango:
                        continue
                    dias_guardados_rango.add(day)

                    rangos_data.append({
                        'username': username,
                        'duration': duration_val,
                        'days': day,
                        'start_time': start_time,
                        'end_time': end_time,
                        'package': package_val
                    })

        if not clases_data and not rangos_data:
             ui.notify("No hay datos para guardar.", type="warning")
             return

        # =========================================================
        # FASE 1: GUARDAR EN NEON (POSTGRES)
        # =========================================================
        pg_session = PostgresSession()
        user_name = ""
        user_surname = ""
        
        try:
            # A. Obtener Usuario y Actualizar Paquete
            user_pg = pg_session.query(User).filter_by(username=username).first()
            if not user_pg:
                ui.notify("Usuario no encontrado en la nube", type="negative")
                return
            
            user_pg.package = package_val
            user_name = user_pg.name
            user_surname = user_pg.surname

            # B. Insertar Clases Asignadas
            # Nota: Asumimos 'append' (agregar), no borramos historial de clases asignadas
            for item in clases_data:
                pg_session.add(AsignedClasses(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    duration=item['duration'],
                    date=item['date'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=item['package'],
                    status="Pendiente" # Estado por defecto
                ))

            # C. Insertar Rangos Horarios
            # Nota: Asumimos 'append' según tu lógica, aunque normalmente los rangos se resetean.
            # Si quisieras resetear, descomenta: 
            # pg_session.query(SchedulePref).filter_by(username=username).delete()
            for item in rangos_data:
                pg_session.add(SchedulePref(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    duration=item['duration'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=item['package']
                ))

            pg_session.commit()
            ui.navigate.to('/myclasses')
            logger.info("✅ Datos guardados en NEON")

        except Exception as e:
            pg_session.rollback()
            logger.error(f"❌ Error Neon: {e}")
            ui.notify(f"Error guardando en la nube: {e}", type="negative")
            return
        finally:
            pg_session.close()

        # =========================================================
        # FASE 2: RESPALDO EN SQLITE
        # =========================================================
        try:
            sq_session = BackupSession()
            
            # A. Actualizar Paquete Local
            user_sq = sq_session.query(User).filter_by(username=username).first()
            if user_sq:
                user_sq.package = package_val

            # B. Replicar Clases
            for item in clases_data:
                sq_session.add(AsignedClasses(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    duration=item['duration'],
                    date=item['date'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=item['package'],
                    status="Pendiente"
                ))

            # C. Replicar Rangos
            for item in rangos_data:
                sq_session.add(SchedulePref(
                    username=item['username'],
                    name=user_name,
                    surname=user_surname,
                    duration=item['duration'],
                    days=item['days'],
                    start_time=item['start_time'],
                    end_time=item['end_time'],
                    package=item['package']
                ))

            sq_session.commit()
            logger.info("💾 Respaldo local actualizado")

        except Exception as e:
            logger.warning(f"⚠️ Error en respaldo local: {e}")
        finally:
            sq_session.close()

        ui.notify("Información guardada correctamente", type="positive")

    button.on("click", save_tables_to_db)
    return save_tables_to_db