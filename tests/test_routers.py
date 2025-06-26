# tests/test_routers.py
"""
Tests for router endpoints.
"""

from uuid import uuid4

from httpx import AsyncClient
from starlette import status


class TestAuthRouter:
    """Test authentication endpoints."""

    async def test_register_success(self, client: AsyncClient, test_user_data):
        """Test successful user registration."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert "password" not in data
        assert "hashed_password" not in data
        assert data["is_active"] is True
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient, test_user_data):
        """Test registration with duplicate email fails."""
        # First registration
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Second registration with same email
        duplicate_data = {**test_user_data, "username": "different_username"}
        response = await client.post("/api/v1/auth/register", json=duplicate_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_register_duplicate_username(
        self, client: AsyncClient, test_user_data
    ):
        """Test registration with duplicate username fails."""
        # First registration
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Second registration with same username
        duplicate_data = {**test_user_data, "email": "different@example.com"}
        response = await client.post("/api/v1/auth/register", json=duplicate_data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_register_invalid_email(self, client: AsyncClient, test_user_data):
        """Test registration with invalid email fails."""
        invalid_data = {**test_user_data, "email": "invalid-email"}
        response = await client.post("/api/v1/auth/register", json=invalid_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_login_success(self, client: AsyncClient, test_user_data):
        """Test successful login."""
        # Register user first
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Login
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: AsyncClient, test_user_data):
        """Test login with wrong password fails."""
        # Register user first
        await client.post("/api/v1/auth/register", json=test_user_data)

        # Login with wrong password
        login_data = {
            "email": test_user_data["email"],
            "password": "wrong_password",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_login_nonexistent_user(self, client: AsyncClient):
        """Test login with non-existent user fails."""
        login_data = {
            "email": "nonexistent@example.com",
            "password": "any_password",
        }
        response = await client.post("/api/v1/auth/login", json=login_data)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    async def test_refresh_token_success(self, client: AsyncClient, test_user_data):
        """Test successful token refresh."""
        # Register and login
        await client.post("/api/v1/auth/register", json=test_user_data)
        login_data = {
            "email": test_user_data["email"],
            "password": test_user_data["password"],
        }
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        tokens = login_response.json()

        # Refresh token
        response = await client.post(
            "/api/v1/auth/refresh",
            params={"refresh_token": tokens["refresh_token"]},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Test refresh with invalid token fails."""
        response = await client.post(
            "/api/v1/auth/refresh", params={"refresh_token": "invalid_token"}
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestTasksRouter:
    """Test task endpoints."""

    async def test_create_task_success(
        self, client: AsyncClient, auth_headers, sample_task_data
    ):
        """Test successful task creation."""
        response = await client.post(
            "/api/v1/tasks/", json=sample_task_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["title"] == sample_task_data["title"]
        assert data["description"] == sample_task_data["description"]
        assert data["priority"] == sample_task_data["priority"]
        assert data["status"] == "todo"  # Default status
        assert "id" in data
        assert "created_at" in data

    async def test_create_task_unauthorized(
        self, client: AsyncClient, sample_task_data
    ):
        """Test task creation without authentication fails."""
        response = await client.post("/api/v1/tasks/", json=sample_task_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_create_task_invalid_data(self, client: AsyncClient, auth_headers):
        """Test task creation with invalid data fails."""
        invalid_data = {"description": "Missing title"}
        response = await client.post(
            "/api/v1/tasks/", json=invalid_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_get_tasks_empty(self, client: AsyncClient, auth_headers):
        """Test getting tasks when user has no tasks."""
        response = await client.get("/api/v1/tasks/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == []

    async def test_get_tasks_with_data(
        self, client: AsyncClient, auth_headers, sample_task_data
    ):
        """Test getting tasks when user has tasks."""
        # Create a task first
        await client.post("/api/v1/tasks/", json=sample_task_data, headers=auth_headers)

        # Get tasks
        response = await client.get("/api/v1/tasks/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == sample_task_data["title"]

    async def test_get_tasks_with_status_filter(
        self, client: AsyncClient, auth_headers
    ):
        """Test getting tasks with status filter."""
        # Create tasks with different statuses
        todo_task = {"title": "Todo Task", "description": "Todo"}
        await client.post("/api/v1/tasks/", json=todo_task, headers=auth_headers)

        # Get tasks with status filter
        response = await client.get(
            "/api/v1/tasks/", params={"status_filter": "todo"}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 1
        assert data[0]["status"] == "todo"

    async def test_get_tasks_pagination(self, client: AsyncClient, auth_headers):
        """Test task pagination."""
        # Create multiple tasks
        for i in range(3):
            task_data = {"title": f"Task {i}", "description": f"Description {i}"}
            await client.post("/api/v1/tasks/", json=task_data, headers=auth_headers)

        # Test pagination
        response = await client.get(
            "/api/v1/tasks/", params={"skip": 1, "limit": 2}, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data) == 2

    async def test_get_task_by_id_success(
        self, client: AsyncClient, auth_headers, sample_task_data
    ):
        """Test getting specific task by ID."""
        # Create task
        create_response = await client.post(
            "/api/v1/tasks/", json=sample_task_data, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        # Get task by ID
        response = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == task_id
        assert data["title"] == sample_task_data["title"]

    async def test_get_task_by_id_not_found(self, client: AsyncClient, auth_headers):
        """Test getting non-existent task fails."""
        valid_uuid = uuid4()
        response = await client.get(f"/api/v1/tasks/{valid_uuid}", headers=auth_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_update_task_success(
        self, client: AsyncClient, auth_headers, sample_task_data
    ):
        """Test successful task update."""
        # Create task
        create_response = await client.post(
            "/api/v1/tasks/", json=sample_task_data, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        # Update task
        update_data = {
            "title": "Updated Task",
            "status": "completed",
            "priority": "high",
        }
        response = await client.put(
            f"/api/v1/tasks/{task_id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["title"] == "Updated Task"
        assert data["status"] == "completed"
        assert data["priority"] == "high"

    async def test_update_task_not_found(self, client: AsyncClient, auth_headers):
        """Test updating non-existent task fails."""
        update_data = {"title": "Updated Task"}
        valid_uuid = uuid4()
        response = await client.put(
            f"/api/v1/tasks/{valid_uuid}", json=update_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_task_success(
        self, client: AsyncClient, auth_headers, sample_task_data
    ):
        """Test successful task deletion."""
        # Create task
        create_response = await client.post(
            "/api/v1/tasks/", json=sample_task_data, headers=auth_headers
        )
        task_id = create_response.json()["id"]

        # Delete task
        response = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify task is deleted
        get_response = await client.get(
            f"/api/v1/tasks/{task_id}", headers=auth_headers
        )
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    async def test_delete_task_not_found(self, client: AsyncClient, auth_headers):
        """Test deleting non-existent task fails."""
        valid_uuid = uuid4()
        response = await client.delete(
            f"/api/v1/tasks/{valid_uuid}", headers=auth_headers
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_tasks_unauthorized(self, client: AsyncClient, sample_task_data):
        """Test all task endpoints require authentication."""
        # Test all endpoints without auth headers
        endpoints = [
            ("GET", "/api/v1/tasks/"),
            ("GET", "/api/v1/tasks/1"),
            ("PUT", "/api/v1/tasks/1"),
            ("DELETE", "/api/v1/tasks/1"),
        ]

        for method, url in endpoints:
            response = await client.request(
                method, url, json=sample_task_data if method in ["PUT"] else None
            )
            assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_user_cannot_access_other_users_tasks(
        self, client: AsyncClient, test_user_data
    ):
        """Test users cannot access other users' tasks."""
        # Create first user and task
        user1_data = test_user_data
        await client.post("/api/v1/auth/register", json=user1_data)

        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user1_data["email"], "password": user1_data["password"]},
        )
        user1_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

        # Create task for user1
        task_response = await client.post(
            "/api/v1/tasks/",
            json={"title": "User1 Task", "description": "Task for user1"},
            headers=user1_headers,
        )
        task_id = task_response.json()["id"]

        # Create second user
        user2_data = {
            "email": "user2@example.com",
            "username": "user2",
            "full_name": "User Two",
            "password": "password123",
        }
        await client.post("/api/v1/auth/register", json=user2_data)

        login_response2 = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        user2_headers = {
            "Authorization": f"Bearer {login_response2.json()['access_token']}"
        }

        # User2 tries to access User1's task
        response = await client.get(f"/api/v1/tasks/{task_id}", headers=user2_headers)
        assert response.status_code == status.HTTP_404_NOT_FOUND  # Should not find task


class TestUsersRouter:
    """Test user endpoints."""

    async def test_get_current_user_success(
        self, client: AsyncClient, auth_headers, test_user_data
    ):
        """Test getting current user information."""
        response = await client.get("/api/v1/users/me", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == test_user_data["email"]
        assert data["username"] == test_user_data["username"]
        assert data["full_name"] == test_user_data["full_name"]
        assert data["is_active"] is True
        assert "password" not in data
        assert "hashed_password" not in data
        assert "id" in data

    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """Test getting current user without authentication fails."""
        response = await client.get("/api/v1/users/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_current_user_success(self, client: AsyncClient, auth_headers):
        """Test successful user update."""
        update_data = {"full_name": "Updated Name", "username": "updated_username"}

        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Updated Name"
        assert data["username"] == "updated_username"

    async def test_update_current_user_partial(
        self, client: AsyncClient, auth_headers, test_user_data
    ):
        """Test partial user update."""
        update_data = {"full_name": "Only Name Changed"}

        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["full_name"] == "Only Name Changed"
        assert data["username"] == test_user_data["username"]  # Unchanged
        assert data["email"] == test_user_data["email"]  # Unchanged

    async def test_update_current_user_unauthorized(self, client: AsyncClient):
        """Test updating user without authentication fails."""
        update_data = {"full_name": "Updated Name"}

        response = await client.put("/api/v1/users/me", json=update_data)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    async def test_update_user_invalid_data(self, client: AsyncClient, auth_headers):
        """Test updating user with invalid data fails."""
        update_data = {"email": "invalid-email"}  # Invalid email format

        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=auth_headers
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_update_user_duplicate_username(
        self, client: AsyncClient, test_user_data
    ):
        """Test updating to duplicate username fails."""
        # Create first user
        user1_data = test_user_data
        await client.post("/api/v1/auth/register", json=user1_data)

        # Create second user
        user2_data = {
            "email": "user2@example.com",
            "username": "user2",
            "full_name": "User Two",
            "password": "password123",
        }
        await client.post("/api/v1/auth/register", json=user2_data)

        # Login as user2
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        user2_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

        # Try to update user2's username to user1's username
        update_data = {"username": user1_data["username"]}
        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=user2_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_update_user_duplicate_email(
        self, client: AsyncClient, test_user_data
    ):
        """Test updating to duplicate email fails."""
        # Create first user
        user1_data = test_user_data
        await client.post("/api/v1/auth/register", json=user1_data)

        # Create second user
        user2_data = {
            "email": "user2@example.com",
            "username": "user2",
            "full_name": "User Two",
            "password": "password123",
        }
        await client.post("/api/v1/auth/register", json=user2_data)

        # Login as user2
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": user2_data["email"], "password": user2_data["password"]},
        )
        user2_headers = {
            "Authorization": f"Bearer {login_response.json()['access_token']}"
        }

        # Try to update user2's email to user1's email
        update_data = {"email": user1_data["email"]}
        response = await client.put(
            "/api/v1/users/me", json=update_data, headers=user2_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    async def test_user_consistency_after_update(
        self, client: AsyncClient, auth_headers
    ):
        """Test that user data is consistent after update."""
        # Get original user data
        original_response = await client.get("/api/v1/users/me", headers=auth_headers)
        original_data = original_response.json()

        # Update user
        update_data = {"full_name": "New Full Name"}
        await client.put("/api/v1/users/me", json=update_data, headers=auth_headers)

        # Get updated user data
        updated_response = await client.get("/api/v1/users/me", headers=auth_headers)
        updated_data = updated_response.json()

        # Verify consistency
        assert updated_data["id"] == original_data["id"]
        assert updated_data["email"] == original_data["email"]
        assert updated_data["username"] == original_data["username"]
        assert updated_data["full_name"] == "New Full Name"
        assert updated_data["is_active"] == original_data["is_active"]
