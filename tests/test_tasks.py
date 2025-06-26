# tests/test_tasks.py
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def authenticated_client(client: TestClient):
    """Create authenticated client with user and token."""
    # Register user
    user_data = {
        "email": "taskuser@example.com",
        "username": "taskuser",
        "full_name": "Task User",
        "password": "taskpassword123",
    }
    client.post("/api/v1/auth/register", json=user_data)

    # Login to get token
    login_data = {"email": "taskuser@example.com", "password": "taskpassword123"}
    response = client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["access_token"]

    # Set authorization header
    client.headers.update({"Authorization": f"Bearer {token}"})

    return client


def test_create_task(authenticated_client: TestClient):
    """Test task creation."""
    task_data = {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "high",
    }

    response = authenticated_client.post("/api/v1/tasks/", json=task_data)

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == task_data["title"]
    assert data["description"] == task_data["description"]
    assert data["priority"] == task_data["priority"]
    assert data["status"] == "todo"
    assert "id" in data


def test_get_tasks(authenticated_client: TestClient):
    """Test getting user tasks."""
    # Create a task first
    task_data = {
        "title": "Get Tasks Test",
        "description": "Test task for getting tasks",
        "priority": "medium",
    }
    authenticated_client.post("/api/v1/tasks/", json=task_data)

    # Get tasks
    response = authenticated_client.get("/api/v1/tasks/")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["title"] == task_data["title"]


def test_update_task(authenticated_client: TestClient):
    """Test task update."""
    # Create a task
    task_data = {
        "title": "Update Test Task",
        "description": "Original description",
        "priority": "low",
    }
    response = authenticated_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Update task
    update_data = {
        "title": "Updated Task Title",
        "status": "in_progress",
        "priority": "high",
    }

    response = authenticated_client.put(f"/api/v1/tasks/{task_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == update_data["title"]
    assert data["status"] == update_data["status"]
    assert data["priority"] == update_data["priority"]


def test_delete_task(authenticated_client: TestClient):
    """Test task deletion."""
    # Create a task
    task_data = {"title": "Delete Test Task", "description": "Task to be deleted"}
    response = authenticated_client.post("/api/v1/tasks/", json=task_data)
    task_id = response.json()["id"]

    # Delete task
    response = authenticated_client.delete(f"/api/v1/tasks/{task_id}")

    assert response.status_code == 204

    # Verify task is deleted
    response = authenticated_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 404


def test_unauthorized_access(client: TestClient):
    """Test accessing tasks without authentication."""
    response = client.get("/api/v1/tasks/")
    assert response.status_code == 401
