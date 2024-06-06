from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date
from typing import Optional, List



class EventBase(BaseModel):
    title : str
    description : str
    event_time : datetime
    location : str
    picture: Optional[str] = None
    
    class Config:
        orm_mode = True

class EventCreate(EventBase):
    pass

class EventResponse(BaseModel):
    id : int
    title : str
    description : str
    event_time : datetime
    location : str
    host_id : int
    created_at : datetime
    picture: Optional[str] = None

    class Config:
        orm_mode = True

class Participant(BaseModel):
    id: int

    class Config:
        orm_mode = True

class EventWithParticipants(BaseModel):
    event : EventResponse
    participants: int
    participants_ids: Optional[List[int]]

    class Config:
        orm_mode = True


class User(BaseModel):
    id: int
    email: str
    profile_picture: str = None

    class Config:
        orm_mode = True

class UserCreate(BaseModel):
    email : EmailStr
    password : str
    birthday : date

class UserOut(BaseModel):
    id : int
    email : EmailStr
    birthday : date
    school : Optional[str] = None
    bio : Optional[str] = None

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email : EmailStr
    password : str

class Token(BaseModel):
    access_token : str
    token_type : str

class TokenData(BaseModel):
    id : Optional[str] = None

class Attend(BaseModel):
    event_id : int