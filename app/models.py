from .database import Base
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, ARRAY
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship


class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key = True, nullable = False)
    picture = Column(String, nullable = True)
    title = Column(String, nullable = False)
    description = Column(String, nullable = False)
    event_time = Column(DateTime, nullable = False)
    location = Column(String, nullable = False)
    created_at = Column(DateTime, nullable = False, server_default = text('now()'))
    host_id = Column(Integer, ForeignKey("users.id", ondelete = "CASCADE"), nullable = False)
    tags = Column(ARRAY(String), nullable = True)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key = True, nullable = False)
    email = Column(String, nullable = False, unique = True)
    password = Column(String, nullable = False)
    birthday = Column(Date, nullable = False)
    school = Column(String)
    bio = Column(String)
    profile_picture = Column(String, nullable = True)

class Attend(Base):
    __tablename__ = "attends"
    user_id = Column(Integer, ForeignKey("users.id", ondelete = "CASCADE"), primary_key = True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete = "CASCADE"), primary_key = True)