# tests/test_auth.py
from fastapi.testclient import TestClient


def test_register_user(client: TestClient):
    """Test user registration."""
    user_data = {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
    }

    response = client.post("/api/v1/auth/register", json=user_data)

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == user_data["email"]
    assert data["username"] == user_data["username"]
    assert data["full_name"] == user_data["full_name"]
    assert "id" in data
    assert "created_at" in data


def test_register_duplicate_email(client: TestClient):
    """Test registration with duplicate email."""
    user_data = {
        "email": "duplicate@example.com",
        "username": "user1",
        "full_name": "User One",
        "password": "password123",
    }

    # First registration
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201

    # Try to register with same email
    user_data["username"] = "user2"
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
    assert "Email already registered" in response.json()["detail"]


def test_login_success(client: TestClient):
    """Test successful login."""
    # Register user first
    user_data = {
        "email": "login@example.com",
        "username": "loginuser",
        "full_name": "Login User",
        "password": "loginpassword123",
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Login
    login_data = {"email": "login@example.com", "password": "loginpassword123"}

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client: TestClient):
    """Test login with invalid credentials."""
    login_data = {"email": "nonexistent@example.com", "password": "wrongpassword"}

    response = client.post("/api/v1/auth/login", json=login_data)

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]
