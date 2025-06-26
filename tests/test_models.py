# tests/test_models.py
"""
Tests for database models.
Verifies model creation, relationships, and constraints.
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, TaskPriority, TaskStatus
from app.models.user import User


class TestUserModel:
    """Test User model functionality."""

    async def test_create_user(self, test_session: AsyncSession):
        """Test basic user creation."""
        user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            hashed_password="hashed_password_here",
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert isinstance(user.created_at, datetime)
        assert isinstance(user.updated_at, datetime)

    async def test_user_defaults(self, test_session: AsyncSession):
        """Test user default values."""
        user = User(
            email="test2@example.com",
            username="testuser2",
            full_name="Test User 2",
            hashed_password="hashed_password_here",
        )

        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Test default values
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None


class TestTaskModel:
    """Test Task model functionality."""

    async def test_create_task_basic(self, test_session: AsyncSession):
        """Test basic task creation."""
        # First create a user
        user = User(
            email="owner@example.com",
            username="owner",
            full_name="Task Owner",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Create task
        task = Task(
            title="Test Task",
            description="This is a test task",
            owner_id=user.id,
        )

        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)

        assert task.id is not None
        assert task.title == "Test Task"
        assert task.description == "This is a test task"
        assert task.owner_id == user.id
        assert task.status == TaskStatus.TODO  # Default status (corrected)
        assert task.priority == TaskPriority.MEDIUM  # Default priority
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

    async def test_task_with_due_date(self, test_session: AsyncSession):
        """Test task creation with due date."""
        # Create user
        user = User(
            email="owner2@example.com",
            username="owner2",
            full_name="Task Owner 2",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Create task with due date
        due_date = datetime.now(UTC) + timedelta(days=7)
        task = Task(
            title="Task with Due Date",
            description="This task has a due date",
            owner_id=user.id,
            due_date=due_date,
            priority=TaskPriority.HIGH,
        )

        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)

        assert task.due_date == due_date
        assert task.priority == TaskPriority.HIGH

    async def test_task_status_enum(self, test_session: AsyncSession):
        """Test task status enum values."""
        # Create user
        user = User(
            email="owner3@example.com",
            username="owner3",
            full_name="Task Owner 3",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Test different status values
        for status in TaskStatus:
            task = Task(
                title=f"Task {status.value}",
                description=f"Task with status {status.value}",
                owner_id=user.id,
                status=status,
            )

            test_session.add(task)
            await test_session.commit()
            await test_session.refresh(task)

            assert task.status == status

    async def test_task_priority_enum(self, test_session: AsyncSession):
        """Test task priority enum values."""
        # Create user
        user = User(
            email="owner4@example.com",
            username="owner4",
            full_name="Task Owner 4",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Test different priority values
        for priority in TaskPriority:
            task = Task(
                title=f"Task {priority.value}",
                description=f"Task with priority {priority.value}",
                owner_id=user.id,
                priority=priority,
            )

            test_session.add(task)
            await test_session.commit()
            await test_session.refresh(task)

            assert task.priority == priority

    async def test_task_user_relationship(self, test_session: AsyncSession):
        """Test task-user relationship."""
        # Create user
        user = User(
            email="relationship@example.com",
            username="reluser",
            full_name="Relationship User",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Create multiple tasks for the user
        task1 = Task(
            title="First Task",
            description="First task for user",
            owner_id=user.id,
        )
        task2 = Task(
            title="Second Task",
            description="Second task for user",
            owner_id=user.id,
        )

        test_session.add_all([task1, task2])
        await test_session.commit()
        await test_session.refresh(task1)
        await test_session.refresh(task2)

        # Verify the relationship
        assert task1.owner_id == user.id
        assert task2.owner_id == user.id

    async def test_task_enum_values(self, test_session: AsyncSession):
        """Test that enum values are correctly set."""
        # Create user
        user = User(
            email="enum@example.com",
            username="enumuser",
            full_name="Enum User",
            hashed_password="hashed_password_here",
        )
        test_session.add(user)
        await test_session.commit()
        await test_session.refresh(user)

        # Test specific enum values exist
        available_statuses = [status for status in TaskStatus]
        available_priorities = [priority for priority in TaskPriority]

        # Verify we have the expected enum values
        assert len(available_statuses) > 0
        assert len(available_priorities) > 0

        # Test creating task with specific enum values
        task = Task(
            title="Enum Test Task",
            description="Testing enum values",
            owner_id=user.id,
            status=TaskStatus.TODO,  # Use TODO instead of PENDING
            priority=TaskPriority.HIGH,
        )

        test_session.add(task)
        await test_session.commit()
        await test_session.refresh(task)

        assert task.status == TaskStatus.TODO
        assert task.priority == TaskPriority.HIGH
