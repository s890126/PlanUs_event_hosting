from .database import Base
from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, ARRAY, Boolean
from sqlalchemy.sql.expression import text
from sqlalchemy.orm import relationship
from datetime import datetime

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True, nullable=False)
    picture = Column(String, nullable=True)
    title = Column(String, nullable=False)
    description = Column(String, nullable=False)
    event_time = Column(DateTime, nullable=False)
    location = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=text('now()'))
    host_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tags = Column(ARRAY(String), nullable=True)
    public = Column(Boolean, nullable=False, default=True)
    messages = relationship("Message", back_populates="event", cascade="all, delete-orphan")
    invitations = relationship("Invitation", back_populates="event")

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, nullable=False)
    email = Column(String, nullable=False, unique=True)
    password = Column(String, nullable=False)
    birthday = Column(Date, nullable=False)
    school = Column(String)
    bio = Column(String)
    profile_picture = Column(String, nullable=True)
    messages = relationship("Message", back_populates="user")
    invitations = relationship("Invitation", back_populates="user")

class Attend(Base):
    __tablename__ = "attends"
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)

class Message(Base):
    __tablename__ = 'messages'
    
    id = Column(Integer, primary_key=True, index=True)
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    
    user = relationship("User", back_populates="messages")
    event = relationship("Event", back_populates="messages")

class Invitation(Base):
    __tablename__ = 'invitations'
    
    id = Column(Integer, primary_key=True, nullable=False)
    event_id = Column(Integer, ForeignKey('events.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    invited_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted = Column(Boolean, nullable=False, default=False)
    
    event = relationship("Event", back_populates="invitations")
    user = relationship("User", back_populates="invitations")