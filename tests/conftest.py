import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import get_db, Base
from app.main import app
from app.models import User
from app.oauth2 import create_access_token
from datetime import date

# Test database configuration
TEST_SQLALCHEMY_DATABASE_URL = 'postgresql://postgres:ss890126@localhost:5432/test_postgres'
test_engine = create_engine(TEST_SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Override the get_db dependency to use the test database
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

# Fixtures
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

@pytest.fixture(scope="module")
def db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function", autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    yield

@pytest.fixture
def create_test_user(db):
    def _create_user(email, password, birthday=date(2000, 1, 1), school=None, bio=None, profile_picture=None):
        user = User(email=email, password=password, birthday=birthday, school=school, bio=bio, profile_picture=profile_picture)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    return _create_user

@pytest.fixture
def auth_header(create_test_user, db):
    user = create_test_user("unique_email@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(scope='function', autouse=True)
def clean_db(db):
    yield
    db.query(User).delete()
    db.commit()
