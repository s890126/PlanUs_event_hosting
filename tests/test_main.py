from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from app.oauth2 import create_access_token
import pytest

def test_get_general_profile(client, create_test_user):
    user = create_test_user("unique_generaluser@example.com", "password123")
    response = client.get(f"/{user.id}/general_profile")
    assert response.status_code == 200

    soup = BeautifulSoup(response.content, "html.parser")
    email_h2 = soup.find("h2", {"class": "text-3xl font-bold text-gray-800 mb-4"})
    assert email_h2 is not None
    assert email_h2.text.strip() == "unique_generaluser@example.com"

def test_get_create_event_form(client, create_test_user):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    cookies = {"access_token": token}
    response = client.get("/create_event", cookies=cookies)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200

def test_get_profile(client, create_test_user):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    cookies = {"access_token": token}
    response = client.get(f"/{user.id}/profile", cookies=cookies)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200

def test_user_chatrooms(client, create_test_user):
    user = create_test_user("testuser@example.com", "password123")
    token = create_access_token(data={"user_id": user.id})
    cookies = {"access_token": token}
    response = client.get("/chatrooms", cookies=cookies)
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 200
