from db.sqlite_db import SQLiteSession
from db.postgres_db import PostgresSession
from db.models import User, SchedulePref, AsignedClasses
from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def sync_sqlite_to_postgres_edit():
    sqlite_sess = SQLiteSession()
    pg_sess = PostgresSession()

    try:
        total_users = 0
        total_rangos = 0
        total_clases = 0

        # -----------------------------
        # SYNC USERS (solo actualiza)
        # -----------------------------
        sqlite_users = sqlite_sess.query(User).all()
        for u in sqlite_users:
            pg_user = pg_sess.query(User).filter_by(username=u.username).first()
            if pg_user:
                # Actualiza datos existentes
                pg_user.name = u.name
                pg_user.surname = u.surname
                pg_user.email = u.email
                pg_user.time_zone = u.time_zone
                pg_user.role = u.role
                pg_user.password_hash = u.password_hash
                total_users += 1
            else:
                # No se crea usuario nuevo aquí (solo edit-profile)
                logger.info(f"Usuario {u.username} no existe en PG, se omite para no sobrescribir sign-up")
     

       # -----------------------------
        # SYNC RANGOS_HORARIOS
        # -----------------------------
        sqlite_rangos = sqlite_sess.query(SchedulePref).all()

        # Primero, borrar los rangos existentes en PostgreSQL
        for r in set(u.username for u in sqlite_rangos):  # usuarios que tienen rangos en SQLite
            pg_sess.query(SchedulePref).filter(SchedulePref.username == r).delete()

        # Luego, agregar todos los rangos de SQLite
        for r in sqlite_rangos:
            pg_sess.add(SchedulePref(
                username=r.username,
                name=r.name,
                surname=r.surname,
                duration=r.duration,
                days=r.days,
                start_time=r.start_time,
                end_time=r.end_time,
                package=r.package
            ))
            total_rangos += 1

        # -----------------------------
        # SYNC CLASES_ASIGNADAS
        # -----------------------------
        sqlite_clases = sqlite_sess.query(AsignedClasses).all()
        for c in sqlite_clases:
            exists = pg_sess.query(AsignedClasses).filter_by(
                username=c.username,
                date=c.date,
                start_time=c.start_time
            ).first()

            if not exists:
                pg_sess.add(AsignedClasses(
                    username=c.username,
                    name=c.name,
                    surname=c.surname,
                    date=c.date,
                    duration=c.duration,
                    days=c.days,
                    start_time=c.start_time,
                    end_time=c.end_time,
                    package=c.package
                ))
                total_clases += 1

        # COMMIT FINAL
        pg_sess.commit()

        # -----------------------------
        # NOTIFICACIONES
        # -----------------------------
        msg = (
            f"Sincronización completa:\n"
            f"• {total_users} usuarios\n"
            f"• {total_rangos} rangos horarios\n"
            f"• {total_clases} clases asignadas"
        )
        ui.notify(msg, type="positive")
        logger.info(msg)

    except Exception as ex:
        ui.notify(f"Error sincronizando datos: {ex}", type="negative")
        logger.exception(ex)

    finally:
        sqlite_sess.close()
        pg_sess.close()
