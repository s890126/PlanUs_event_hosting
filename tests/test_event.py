import pytest
from fastapi.testclient import TestClient
from app.models import Event, Attend, User
from app.schemas import EventCreate
from app.oauth2 import create_access_token
from datetime import datetime, timedelta

# Test for GET /events/partial
def test_get_events_partial(client: TestClient, create_test_user):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    client.cookies.set("access_token", token)
    
    response = client.get("/events/partial")
    assert response.status_code == 200
    assert "events" in response.text

# Test for POST /events/create_event
def test_create_event(client: TestClient, create_test_user):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    client.cookies.set("access_token", token)

    event_data = {
        "title": "Test Event",
        "description": "This is a test event",
        "event_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
        "location": "Test Location",
        "public": True
    }
    
    response = client.post("/events/create_event", data=event_data, allow_redirects=False)
    print(f"Response status: {response.status_code}, headers: {response.headers}")  # Debug print
    assert response.status_code == 303
    assert response.headers["location"] == "/events"




# Test for GET /events/{id}
def test_get_event(client: TestClient, create_test_user, db):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    client.cookies.set("access_token", token)

    # Create a test event
    test_event = Event(
        title="Test Event",
        description="This is a test event",
        event_time=datetime.utcnow() + timedelta(days=1),
        location="Test Location",
        host_id=user.id,
        public=True,
        tags=[]  # Ensure tags is a list
    )
    db.add(test_event)
    db.commit()
    db.refresh(test_event)

    response = client.get(f"/events/{test_event.id}")
    assert response.status_code == 200
    assert "Test Event" in response.text


# Test for DELETE /events/delete/{id}
def test_delete_event(client: TestClient, create_test_user, db):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    client.cookies.set("access_token", token)

    # Create a test event
    test_event = Event(
        title="Test Event",
        description="This is a test event",
        event_time=datetime.utcnow() + timedelta(days=1),
        location="Test Location",
        host_id=user.id,
        public=True
    )
    db.add(test_event)
    db.commit()
    db.refresh(test_event)

    response = client.delete(f"/events/delete/{test_event.id}", allow_redirects=False)
    print(f"Response status: {response.status_code}, headers: {response.headers}")  # Debug print
    assert response.status_code == 303
    assert response.headers["location"] == f"/{user.id}/profile"

