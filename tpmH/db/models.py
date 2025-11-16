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
    role = Column(String, unique= False, default= "client")
    time_zone = Column(String, unique=False)
    password_hash = Column(String)
