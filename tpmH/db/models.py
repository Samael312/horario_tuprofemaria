from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True)
    name = Column(String, unique=False)
    surname = Column(String, unique=False)
    email = Column(String, unique=True)
    time_zone = Column(String, unique=True)
    password_hash = Column(String)
