from db.sqlite_db import SQLiteSession
from db.postgres_db import PostgresSession
from db.models import User
from nicegui import ui
import logging

logger = logging.getLogger(__name__)

def sync_sqlite_to_postgres():
    sqlite_sess = SQLiteSession()
    pg_sess = PostgresSession()

    try:
        users = sqlite_sess.query(User).all()
        count = 0
        for u in users:
            if not pg_sess.query(User).filter_by(email=u.email).first():
                pg_sess.add(User(
                    username=u.username,
                    email=u.email,
                    password_hash=u.password_hash
                ))
                count += 1
        pg_sess.commit()
        ui.notify(f"Sincronización completada: {count} usuarios enviados a PostgreSQL", type="positive")
        logger.info(f"{count} usuarios sincronizados a PostgreSQL")
    except Exception as ex:
        ui.notify(f"Error sincronizando usuarios: {ex}", type="negative")
        logger.exception(ex)
    finally:
        sqlite_sess.close()
        pg_sess.close()
