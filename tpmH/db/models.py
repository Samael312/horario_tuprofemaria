from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base
import json
from sqlalchemy.types import JSON

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    email = Column(String, unique=True)
    role = Column(String, unique= False, default= "client")
    time_zone = Column(String, unique=False)
    package = Column(String, unique=False, default= "") 
    status = Column(String, unique=False, default="Active")
    password_hash = Column(String)

class SchedulePref(Base):
    __tablename__ = "rangos_horarios"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    duration = Column(String, unique=False)
    days = Column(String, unique=False)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    package = Column(String, unique=False)

class AsignedClasses(Base):
    __tablename__ = "clases_asignadas"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    date= Column(String, unique=False)
    duration = Column(String, unique=False)
    days = Column(String, unique=False)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    package = Column(String, unique=False)
    status = Column(String, unique=False, default="Pendiente")


class ScheduleProf(Base):
    __tablename__ = "horario_prof"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    days = Column(String, unique=False)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    availability= Column(String, unique=False, default='Available')

class ScheduleProfEsp(Base):
    __tablename__ = "horario_prof_esp"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=False)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    date = Column(String, unique=False)
    days = Column(String, unique=False)
    start_time = Column(Integer, unique=False)
    end_time = Column(Integer, unique=False)
    avai= Column(String, unique=False, default='Available')

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
