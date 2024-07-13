from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings
import os

SQLALCHEMY_DATABASE_URL = (
    f"postgresql://{os.getenv('DATABASE_USERNAME')}:"
    f"{os.getenv('DATABASE_PASSWORD')}@"
    f"{os.getenv('DATABASE_HOSTNAME')}:"
    f"{os.getenv('DATABASE_PORT')}/"
    f"{os.getenv('DATABASE_NAME')}?sslmode=require"
)
#SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'
#SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:ss890126@localhost/planus'
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit = False, autoflush = False, bind = engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()