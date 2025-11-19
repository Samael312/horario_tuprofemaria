from sqlalchemy import text
from db.sqlite_db import SQLiteSession
from db.models import User, SchedulePref

def migrate_packages():
    session = SQLiteSession()
    try:
        print("1. Intentando añadir columna 'package' a la tabla 'users'...")
        # Intentamos añadir la columna (si falla es que ya existe, lo cual está bien)
        try:
            session.execute(text("ALTER TABLE users ADD COLUMN package VARCHAR"))
            session.commit()
            print("   -> Columna creada con éxito.")
        except Exception as e:
            print("   -> La columna probablemente ya existe. Continuando...")
            session.rollback()

        print("2. Copiando datos de Rangos Horarios a Usuarios...")
        
        # Obtenemos todas las preferencias de horario
        schedules = session.query(SchedulePref).all()
        
        count = 0
        for schedule in schedules:
            # Buscamos al usuario correspondiente por username
            user = session.query(User).filter_by(username=schedule.username).first()
            
            if user:
                # Si el horario tiene paquete y el usuario no (o queremos sobrescribirlo)
                if schedule.package:
                    user.package = schedule.package
                    count += 1
        
        session.commit()
        print(f"   -> Migración completada. {count} usuarios actualizados.")

    except Exception as e:
        print(f"Error durante la migración: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    migrate_packages()