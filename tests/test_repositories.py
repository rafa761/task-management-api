# tests/test_repositories.py
"""
Simple tests for User and Task repositories.
Tests basic CRUD operations and specific repository methods.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository


class TestUserRepository:
    """Test UserRepository functionality."""

    @pytest.fixture
    async def user_repo(self, test_session: AsyncSession) -> UserRepository:
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    async def sample_user(self, user_repo: UserRepository) -> User:
        """Create a sample user for testing."""
        return await user_repo.create(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password="hashed_password",
        )

    async def test_create_user(self, user_repo: UserRepository):
        """Test user creation."""
        user = await user_repo.create(
            email="new@example.com",
            username="newuser",
            full_name="New User",
            hashed_password="hashed_password",
        )

        assert user.id is not None
        assert user.email == "new@example.com"
        assert user.username == "newuser"
        assert user.full_name == "New User"
        assert user.is_active is True

    async def test_get_by_id(self, user_repo: UserRepository, sample_user: User):
        """Test getting user by ID."""
        found_user = await user_repo.get_by_id(sample_user.id)

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == sample_user.email

    async def test_get_by_email(self, user_repo: UserRepository, sample_user: User):
        """Test getting user by email."""
        found_user = await user_repo.get_by_email("test@example.com")

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.email == "test@example.com"

    async def test_get_by_email_not_found(self, user_repo: UserRepository):
        """Test getting user by non-existent email."""
        found_user = await user_repo.get_by_email("notfound@example.com")
        assert found_user is None

    async def test_get_by_username(self, user_repo: UserRepository, sample_user: User):
        """Test getting user by username."""
        found_user = await user_repo.get_by_username("testuser")

        assert found_user is not None
        assert found_user.id == sample_user.id
        assert found_user.username == "testuser"

    async def test_email_exists(self, user_repo: UserRepository, sample_user: User):
        """Test checking if email exists."""
        assert await user_repo.email_exists("test@example.com") is True
        assert await user_repo.email_exists("notfound@example.com") is False

    async def test_username_exists(self, user_repo: UserRepository, sample_user: User):
        """Test checking if username exists."""
        assert await user_repo.username_exists("testuser") is True
        assert await user_repo.username_exists("notfound") is False

    async def test_update_user(self, user_repo: UserRepository, sample_user: User):
        """Test updating user."""
        updated_user = await user_repo.update(
            sample_user.id, full_name="Updated Name", is_active=False
        )

        assert updated_user is not None
        assert updated_user.full_name == "Updated Name"
        assert updated_user.is_active is False
        assert updated_user.email == sample_user.email  # Unchanged

    async def test_delete_user(self, user_repo: UserRepository, sample_user: User):
        """Test deleting user."""
        deleted = await user_repo.delete(sample_user.id)
        assert deleted is True

        # Verify user is gone
        found_user = await user_repo.get_by_id(sample_user.id)
        assert found_user is None


class TestTaskRepository:
    """Test TaskRepository functionality."""

    @pytest.fixture
    async def user_repo(self, test_session: AsyncSession) -> UserRepository:
        """Create user repository instance."""
        return UserRepository(test_session)

    @pytest.fixture
    async def task_repo(self, test_session: AsyncSession) -> TaskRepository:
        """Create task repository instance."""
        return TaskRepository(test_session)

    @pytest.fixture
    async def sample_user(self, user_repo: UserRepository) -> User:
        """Create a sample user for testing."""
        return await user_repo.create(
            email="taskowner@example.com",
            username="taskowner",
            full_name="Task Owner",
            hashed_password="hashed_password",
        )

    @pytest.fixture
    async def sample_task(self, task_repo: TaskRepository, sample_user: User) -> Task:
        """Create a sample task for testing."""
        return await task_repo.create(
            title="Test Task",
            description="Test description",
            owner_id=sample_user.id,
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
        )

    async def test_create_task(self, task_repo: TaskRepository, sample_user: User):
        """Test task creation."""
        task = await task_repo.create(
            title="New Task",
            description="New task description",
            owner_id=sample_user.id,
            priority=TaskPriority.HIGH,
        )

        assert task.id is not None
        assert task.title == "New Task"
        assert task.description == "New task description"
        assert task.owner_id == sample_user.id
        assert task.status == TaskStatus.TODO  # Default
        assert task.priority == TaskPriority.HIGH

    async def test_get_by_id(self, task_repo: TaskRepository, sample_task: Task):
        """Test getting task by ID."""
        found_task = await task_repo.get_by_id(sample_task.id)

        assert found_task is not None
        assert found_task.id == sample_task.id
        assert found_task.title == sample_task.title

    async def test_get_by_owner(
        self, task_repo: TaskRepository, sample_user: User, sample_task: Task
    ):
        """Test getting tasks by owner."""
        # Create another task for the same user
        await task_repo.create(
            title="Second Task",
            description="Second task description",
            owner_id=sample_user.id,
        )

        tasks = await task_repo.get_by_owner(sample_user.id)

        assert len(tasks) == 2
        assert all(task.owner_id == sample_user.id for task in tasks)

    async def test_get_by_owner_and_id(
        self, task_repo: TaskRepository, sample_user: User, sample_task: Task
    ):
        """Test getting specific task by owner and task ID."""
        found_task = await task_repo.get_by_owner_and_id(sample_user.id, sample_task.id)

        assert found_task is not None
        assert found_task.id == sample_task.id
        assert found_task.owner_id == sample_user.id

    async def test_get_by_owner_and_id_not_found(
        self, task_repo: TaskRepository, sample_user: User
    ):
        """Test getting non-existent task by owner and task ID."""
        # Create another user
        other_user = await UserRepository(task_repo.session).create(
            email="other@example.com",
            username="otheruser",
            full_name="Other User",
            hashed_password="hashed_password",
        )

        # Create task for other user
        other_task = await task_repo.create(
            title="Other Task",
            description="Task for other user",
            owner_id=other_user.id,
        )

        # Try to get other user's task with sample_user.id
        found_task = await task_repo.get_by_owner_and_id(sample_user.id, other_task.id)

        assert found_task is None

    async def test_get_by_status(self, task_repo: TaskRepository, sample_user: User):
        """Test getting tasks by status."""
        # Create tasks with different statuses
        await task_repo.create(
            title="Todo Task",
            description="Todo task",
            owner_id=sample_user.id,
            status=TaskStatus.TODO,
        )

        await task_repo.create(
            title="In Progress Task",
            description="In progress task",
            owner_id=sample_user.id,
            status=TaskStatus.IN_PROGRESS,
        )

        await task_repo.create(
            title="Completed Task",
            description="Completed task",
            owner_id=sample_user.id,
            status=TaskStatus.COMPLETED,
        )

        # Test getting tasks
        todo_tasks = await task_repo.get_by_status(sample_user.id, TaskStatus.TODO)
        assert len(todo_tasks) == 1
        assert todo_tasks[0].status == TaskStatus.TODO

        # Test getting IN_PROGRESS tasks
        in_progress_tasks = await task_repo.get_by_status(
            sample_user.id, TaskStatus.IN_PROGRESS
        )
        assert len(in_progress_tasks) == 1
        assert in_progress_tasks[0].status == TaskStatus.IN_PROGRESS

    async def test_update_task(self, task_repo: TaskRepository, sample_task: Task):
        """Test updating task."""
        updated_task = await task_repo.update(
            sample_task.id,
            title="Updated Task",
            status=TaskStatus.COMPLETED,
            priority=TaskPriority.LOW,
        )

        assert updated_task is not None
        assert updated_task.title == "Updated Task"
        assert updated_task.status == TaskStatus.COMPLETED
        assert updated_task.priority == TaskPriority.LOW
        assert updated_task.description == sample_task.description  # Unchanged

    async def test_delete_task(self, task_repo: TaskRepository, sample_task: Task):
        """Test deleting task."""
        deleted = await task_repo.delete(sample_task.id)
        assert deleted is True

        # Verify task is gone
        found_task = await task_repo.get_by_id(sample_task.id)
        assert found_task is None

    async def test_pagination(self, task_repo: TaskRepository, sample_user: User):
        """Test pagination in get_by_owner."""
        # Create multiple tasks
        for i in range(5):
            await task_repo.create(
                title=f"Task {i}",
                description=f"Description {i}",
                owner_id=sample_user.id,
            )

        # Test pagination
        first_page = await task_repo.get_by_owner(sample_user.id, skip=0, limit=2)
        second_page = await task_repo.get_by_owner(sample_user.id, skip=2, limit=2)

        assert len(first_page) == 2
        assert len(second_page) == 2
        assert first_page[0].id != second_page[0].id
