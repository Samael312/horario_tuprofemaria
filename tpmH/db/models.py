from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
from sqlalchemy.types import JSON

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    email = Column(String, unique=True)
    goal = Column(String, unique=False, default="") 
    role = Column(String, unique=False, default="client")
    time_zone = Column(String, unique=False, default="UTC") # Zona horaria del usuario
    package = Column(String, unique=False, default="") 
    status = Column(String, unique=False, default="Active")
    password_hash = Column(String)
    class_count = Column(String, unique=False) # Ej: "1/12", "5/8"
    total_classes = Column(Integer, unique=False, default=0)
    renovations = Column(Integer, unique=False, default= 0)
    payment_info = Column(JSON, unique=False) # Información de pago (puede ser JSON)
    price = Column(Integer, unique=False, default=10) # Precio del plan


class SchedulePref(Base):
    __tablename__ = "rangos_horarios"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    duration = Column(String, unique=False)
    days = Column(String, unique=False)
    # Horario Estudiante (Local)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    # Horario Profesora (Calculado)
    start_prof_time = Column(Integer, unique=False) # NUEVO
    end_prof_time = Column(Integer, unique=False)   # NUEVO
    package = Column(String, unique=False)


class AsignedClasses(Base):
    __tablename__ = "clases_asignadas"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    date = Column(String, unique=False) # Fecha del estudiante
    duration = Column(String, unique=False)
    days = Column(String, unique=False)
    # Horario Estudiante (Local)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    # Horario Profesora (Calculado)
    start_prof_time = Column(Integer, unique=False) # NUEVO
    end_prof_time = Column(Integer, unique=False)   # NUEVO
    # Fecha Profesora (Puede cambiar si hay diferencia grande de zona)
    date_prof = Column(String, unique=False)        # NUEVO (Recomendado)
    package = Column(String, unique=False)
    status = Column(String, unique=False, default="Pendiente")
    class_count = Column(String, unique=False) # Ej: "1/12", "5/8"
    total_classes = Column(Integer, unique=False, default=0)
    payment_info = Column(JSON, unique=False) # Información de pago (puede ser JSON)

class ScheduleProf(Base):
    __tablename__ = "horario_prof"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    days = Column(String, unique=False)
    # Horario Profesora (Base)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    availability = Column(String, unique=False, default='Available')

class ScheduleProfEsp(Base):
    __tablename__ = "horario_prof_esp"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    date = Column(String, unique=False)
    days = Column(String, unique=False)
    # Horario Profesora (Base)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    avai = Column(String, unique=False, default='Available')

class TeacherProfile(Base):
    __tablename__ = "teacher_profile"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    bio = Column(String, unique=False)
    photo = Column(String, unique=False)
    title = Column(String, unique=False)
    skills = Column(JSON, unique=False)
    video = Column(String, unique=False)
    gallery = Column(JSON, unique=False)
    certificates = Column(JSON, unique=False)
    social_links = Column(JSON, unique=False)
    reviews = Column(JSON, unique=False)

class Material(Base):
    __tablename__ = "materials"
    id = Column(Integer, primary_key=True)
    title = Column(String, unique=False)
    content = Column(String, unique=False)
    date_up= Column(String, unique=False)
    category = Column(String, unique=False)
    level = Column(String, unique=False)
    tags = Column(JSON, unique=False)

class HWork(Base):
    __tablename__ = "homework"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    title = Column(String, unique=False)
    content = Column(String, unique=False)
    date_assigned = Column(String, unique=False)
    date_due = Column(String, unique=False)
    status = Column(String, unique=False, default="Pending")
    tagsW = Column(JSON, unique=False)

class StudentMaterial(Base):
    __tablename__ = "student_materials"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    material_id = Column(Integer, unique=False)
    progress = Column(String, unique=False, default="Not Started")

class StudentHWork(Base):
    __tablename__ = "student_homework"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    homework_id = Column(Integer, unique=False)
    submission = Column(String, unique=False)
    status = Column(String, unique=False, default="Pending")
    grade = Column(JSON, unique=False, default="")