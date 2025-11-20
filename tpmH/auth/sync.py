from db.sqlite_db import SQLiteSession
from db.postgres_db import PostgresSession
from db.models import User, SchedulePref, AsignedClasses, ScheduleProf, ScheduleProfEsp
from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def sync_sqlite_to_postgres():
    sqlite_sess = SQLiteSession()
    pg_sess = PostgresSession()

    try:
        total_users = 0
        total_rangos = 0
        total_clases = 0
        total_hgen = 0
        total_hesp = 0

        # -----------------------------
        # SYNC USERS
        # -----------------------------
        sqlite_users = sqlite_sess.query(User).all()
        for u in sqlite_users:
            if not pg_sess.query(User).filter_by(email=u.email).first():
                pg_sess.add(User(
                    username=u.username,
                    name=u.name,
                    surname=u.surname,
                    email=u.email,
                    role=u.role,
                    time_zone=u.time_zone,
                    password_hash=u.password_hash
                ))
                total_users += 1

        # -----------------------------
        # SYNC RANGOS_HORARIOS
        # -----------------------------
        sqlite_rangos = sqlite_sess.query(SchedulePref).all()
        for r in sqlite_rangos:
            exists = pg_sess.query(SchedulePref).filter_by(
                username=r.username,
                start_time=r.start_time,
                end_time=r.end_time
            ).first()

            if not exists:
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
        
        # -----------------------------
        # SYNC HORARIO_PROF
        # -----------------------------
        sqlite_clases = sqlite_sess.query(ScheduleProf).all()
        for d in sqlite_clases:
            exists = pg_sess.query(ScheduleProf).filter_by(
                username=d.username,
                start_time=d.start_time,
                end_time=d.end_time
            ).first()

            if not exists:
                pg_sess.add(ScheduleProf(
                    username=d.username,
                    name=d.name,
                    surname=d.surname,
                    days=d.days,
                    start_time=d.start_time,
                    end_time=d.end_time,
                    availability=d.availability
                ))
                total_hgen += 1
        
         # -----------------------------
        # SYNC HORARIO_PROF
        # -----------------------------
        sqlite_clases = sqlite_sess.query(ScheduleProfEsp).all()
        for g in sqlite_clases:
            exists = pg_sess.query(ScheduleProfEsp).filter_by(
                username=g.username,
                start_time=g.start_time,
                end_time=g.end_time
            ).first()

            if not exists:
                pg_sess.add(ScheduleProfEsp(
                    username=g.username,
                    name=g.name,
                    surname=g.surname,
                    date= g.date,
                    days=g.days,
                    start_time=g.start_time,
                    end_time=g.end_time,
                    avai=g.avai
                ))
                total_hesp += 1

        # COMMIT FINAL
        pg_sess.commit()

        # -----------------------------
        # NOTIFICACIONES
        # -----------------------------
        msg = (
            f"Sincronización completa:\n"
            f"• {total_users} usuarios\n"
            f"• {total_rangos} rangos horarios\n"
            f"• {total_clases} clases asignadas\n"
            f"• {total_hesp} horarios especificos\n"
            f"• {total_hgen} horarios generales"
        )
        ui.notify(msg, type="positive")
        logger.info(msg)

    except Exception as ex:
        ui.notify(f"Error sincronizando datos: {ex}", type="negative")
        logger.exception(ex)

    finally:
        sqlite_sess.close()
        pg_sess.close()
