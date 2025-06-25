# tests/models/test_task.py
"""
Task Model Tests

Tests model behavior including simple database operations.
Complex queries and business workflows are tested in repository/service layers.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    ProjectModel,
    TaskAssignmentModel,
    TaskDependencyModel,
    TaskModel,
    TeamModel,
    UserModel,
)
from app.models.enums import TaskPriorityEnum, TaskStatusEnum
from app.utils.dates import days_ago, days_from_now, utc_now


class TestTaskModelBusinessLogic:
    """Test pure business logic without database dependencies"""

    def test_is_overdue_property_no_due_date(self):
        """Test is_overdue returns False when no due date is set"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.TODO,
        )
        assert task.is_overdue is False

    def test_is_overdue_property_future_due_date(self):
        """Test is_overdue returns False when due date is in future"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            due_date=days_from_now(5),
            status=TaskStatusEnum.TODO,
        )
        assert task.is_overdue is False

    def test_is_overdue_property_past_due_date_active_task(self):
        """Test is_overdue returns True when due date is past and task is active"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            due_date=days_ago(2),
            status=TaskStatusEnum.IN_PROGRESS,
        )
        assert task.is_overdue is True

    def test_is_overdue_property_past_due_date_completed_task(self):
        """Test is_overdue returns False when task is completed even if past due date"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            due_date=days_ago(2),
            status=TaskStatusEnum.DONE,
        )
        assert task.is_overdue is False

    def test_days_until_due_property_with_due_date(self):
        """Test days_until_due calculates correctly when due date is set"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            due_date=days_from_now(7),
            status=TaskStatusEnum.TODO,
        )
        assert task.days_until_due in (6, 7)  # Account for timing variance

    def test_days_until_due_property_no_due_date(self):
        """Test days_until_due returns None when no due date"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.TODO,
        )
        assert task.days_until_due is None

    def test_days_until_due_property_overdue_task(self):
        """Test days_until_due returns negative value for overdue task"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            due_date=days_ago(3),
            status=TaskStatusEnum.TODO,
        )
        assert task.days_until_due < 0

    def test_assignee_ids_property_no_assignments(self):
        """Test assignee_ids returns empty list when no assignments"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
        )
        task.assignments = []
        assert task.assignee_ids == []

    def test_is_blocked_property_no_dependencies(self):
        """Test is_blocked returns False when no dependencies"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
        )
        task.dependencies = []
        assert task.is_blocked is False

    def test_blocking_tasks_count_property_no_dependents(self):
        """Test blocking_tasks_count returns 0 when no dependents"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
        )
        task.dependents = []
        assert task.blocking_tasks_count == 0

    def test_start_task_method_from_todo_status(self):
        """Test start_task method changes status and sets start time"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.TODO,
        )
        task.assignments = []  # Initialize assignments

        before_start = utc_now()
        task.start_task()

        assert task.status == TaskStatusEnum.IN_PROGRESS
        assert task.started_at is not None
        assert task.started_at >= before_start

    def test_start_task_method_ignores_non_todo_status(self):
        """Test start_task doesn't change status if not TODO"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.DONE,
            started_at=None,
        )

        task.start_task()

        assert task.status == TaskStatusEnum.DONE
        assert task.started_at is None

    def test_complete_task_method(self):
        """Test complete_task method changes status and sets completion time"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.IN_PROGRESS,
        )

        before_complete = utc_now()
        task.complete_task()

        assert task.status == TaskStatusEnum.DONE
        assert task.completed_at is not None
        assert task.completed_at >= before_complete

    def test_cancel_task_method(self):
        """Test cancel_task method changes status and sets completion time"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.IN_PROGRESS,
        )

        before_cancel = utc_now()
        task.cancel_task()

        assert task.status == TaskStatusEnum.CANCELLED
        assert task.completed_at is not None
        assert task.completed_at >= before_cancel

    def test_reopen_task_method(self):
        """Test reopen_task method resets status and timestamps"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.DONE,
            completed_at=utc_now(),
            started_at=days_ago(1),
        )

        task.reopen_task()

        assert task.status == TaskStatusEnum.TODO
        assert task.completed_at is None
        assert task.started_at is None

    def test_reopen_task_method_ignores_active_task(self):
        """Test reopen_task doesn't change active task"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            status=TaskStatusEnum.IN_PROGRESS,
            started_at=days_ago(1),
        )

        task.reopen_task()

        assert task.status == TaskStatusEnum.IN_PROGRESS
        assert task.started_at is not None

    def test_set_priority_method(self):
        """Test set_priority method changes priority"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            priority=TaskPriorityEnum.LOW,
        )

        task.set_priority(TaskPriorityEnum.HIGH)

        assert task.priority == TaskPriorityEnum.HIGH

    def test_archive_method(self):
        """Test archive method sets archived flag"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            is_archived=False,
        )

        task.archive()

        assert task.is_archived is True

    def test_unarchive_method(self):
        """Test unarchive method clears archived flag"""
        team_id = uuid4()
        creator_id = uuid4()

        task = TaskModel(
            title="Test Task",
            team_id=team_id,
            creator_id=creator_id,
            is_archived=True,
        )

        task.unarchive()

        assert task.is_archived is False


class TestTaskModelWithDatabase:
    """Test model behavior that requires database interaction"""

    async def test_create_task_with_valid_data(self, db_session: AsyncSession):
        """Test creating task with valid data and relationships"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            description="Test task description",
            team_id=team.id,
            creator_id=user.id,
            status=TaskStatusEnum.TODO,
            priority=TaskPriorityEnum.MEDIUM,
        )
        db_session.add(task)
        await db_session.commit()

        # Verify task was persisted
        assert task.id is not None
        assert task.created_at is not None
        assert task.updated_at is not None
        assert task.title == "Test Task"
        assert task.team_id == team.id
        assert task.creator_id == user.id

    async def test_task_team_relationship(self, db_session: AsyncSession):
        """Test task-team relationship works correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Test relationship
        assert task.team.id == team.id
        assert task.team.name == "Test Team"

    async def test_task_creator_relationship(self, db_session: AsyncSession):
        """Test task-creator relationship works correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Test relationship
        assert task.creator.id == user.id
        assert task.creator.email == "creator@example.com"

    async def test_task_project_relationship(self, db_session: AsyncSession):
        """Test task-project relationship works correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        project = ProjectModel(name="Test Project", team_id=team.id)
        db_session.add_all([team, user])
        await db_session.commit()

        project.team_id = team.id
        db_session.add(project)
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=user.id,
            project_id=project.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Test relationship
        assert task.project.id == project.id
        assert task.project.name == "Test Project"

    async def test_task_soft_delete_persistence(self, db_session: AsyncSession):
        """Test that soft delete persists to database"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Soft delete
        task.soft_delete()
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(task)
        assert task.deleted_at is not None
        assert task.is_deleted is True

    async def test_task_status_enum_constraint(self, db_session: AsyncSession):
        """Test that valid enum values work"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create task with valid enum
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=user.id,
            status=TaskStatusEnum.IN_PROGRESS,
        )
        db_session.add(task)
        await db_session.commit()

        # Valid enum assignment should work
        task.status = TaskStatusEnum.DONE
        await db_session.commit()
        assert task.status == TaskStatusEnum.DONE

    async def test_task_defaults(self, db_session: AsyncSession):
        """Test that default values are set correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="Creator",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create minimal task
        task = TaskModel(
            title="Minimal Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Check defaults
        assert task.status == TaskStatusEnum.TODO
        assert task.priority == TaskPriorityEnum.MEDIUM
        assert task.position == 0
        assert task.is_archived is False


class TestTaskAssignmentModel:
    """Test TaskAssignmentModel behavior"""

    async def test_create_task_assignment(self, db_session: AsyncSession):
        """Test creating task assignment"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        creator = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        assignee = UserModel(
            email="assignee@example.com",
            hashed_password="hashed",
            first_name="Assignee",
            last_name="User",
        )
        db_session.add_all([team, creator, assignee])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=creator.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Create assignment
        assignment = TaskAssignmentModel(
            task_id=task.id,
            assignee_id=assignee.id,
            assigned_by_id=creator.id,
        )
        db_session.add(assignment)
        await db_session.commit()

        # Verify assignment
        assert assignment.id is not None
        assert assignment.task_id == task.id
        assert assignment.assignee_id == assignee.id
        assert assignment.assigned_by_id == creator.id
        assert assignment.assigned_at is not None

    async def test_task_assignment_relationships(self, db_session: AsyncSession):
        """Test task assignment relationships work correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        creator = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        assignee = UserModel(
            email="assignee@example.com",
            hashed_password="hashed",
            first_name="Assignee",
            last_name="User",
        )
        db_session.add_all([team, creator, assignee])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=creator.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Create assignment
        assignment = TaskAssignmentModel(
            task_id=task.id,
            assignee_id=assignee.id,
            assigned_by_id=creator.id,
        )
        db_session.add(assignment)
        await db_session.commit()

        # Test relationships
        assert assignment.task.title == "Test Task"
        assert assignment.assignee.email == "assignee@example.com"
        assert assignment.assigned_by.email == "creator@example.com"

    async def test_unique_task_assignment_constraint(self, db_session: AsyncSession):
        """Test that unique constraint prevents duplicate assignments"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        creator = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        assignee = UserModel(
            email="assignee@example.com",
            hashed_password="hashed",
            first_name="Assignee",
            last_name="User",
        )
        db_session.add_all([team, creator, assignee])
        await db_session.commit()

        # Create task
        task = TaskModel(
            title="Test Task",
            team_id=team.id,
            creator_id=creator.id,
        )
        db_session.add(task)
        await db_session.commit()

        # Create first assignment
        assignment1 = TaskAssignmentModel(
            task_id=task.id,
            assignee_id=assignee.id,
        )
        db_session.add(assignment1)
        await db_session.commit()

        # Try to create duplicate assignment (should fail)
        assignment2 = TaskAssignmentModel(
            task_id=task.id,
            assignee_id=assignee.id,
        )
        db_session.add(assignment2)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestTaskDependencyModel:
    """Test TaskDependencyModel behavior"""

    async def test_create_task_dependency(self, db_session: AsyncSession):
        """Test creating task dependency"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create tasks
        prerequisite_task = TaskModel(
            title="Prerequisite Task",
            team_id=team.id,
            creator_id=user.id,
        )
        dependent_task = TaskModel(
            title="Dependent Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add_all([prerequisite_task, dependent_task])
        await db_session.commit()

        # Create dependency
        dependency = TaskDependencyModel(
            dependent_task_id=dependent_task.id,
            prerequisite_task_id=prerequisite_task.id,
            created_by_id=user.id,
        )
        db_session.add(dependency)
        await db_session.commit()

        # Verify dependency
        assert dependency.id is not None
        assert dependency.dependent_task_id == dependent_task.id
        assert dependency.prerequisite_task_id == prerequisite_task.id
        assert dependency.created_by_id == user.id
        assert dependency.created_at is not None

    async def test_task_dependency_relationships(self, db_session: AsyncSession):
        """Test task dependency relationships work correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create tasks
        prerequisite_task = TaskModel(
            title="Prerequisite Task",
            team_id=team.id,
            creator_id=user.id,
        )
        dependent_task = TaskModel(
            title="Dependent Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add_all([prerequisite_task, dependent_task])
        await db_session.commit()

        # Create dependency
        dependency = TaskDependencyModel(
            dependent_task_id=dependent_task.id,
            prerequisite_task_id=prerequisite_task.id,
            created_by_id=user.id,
        )
        db_session.add(dependency)
        await db_session.commit()

        # Test relationships
        assert dependency.dependent_task.title == "Dependent Task"
        assert dependency.prerequisite_task.title == "Prerequisite Task"
        assert dependency.created_by.email == "creator@example.com"

    async def test_is_blocking_property(self, db_session: AsyncSession):
        """Test is_blocking property logic"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create tasks
        prerequisite_task = TaskModel(
            title="Prerequisite Task",
            team_id=team.id,
            creator_id=user.id,
            status=TaskStatusEnum.TODO,  # Not completed
        )
        dependent_task = TaskModel(
            title="Dependent Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add_all([prerequisite_task, dependent_task])
        await db_session.commit()

        # Create dependency
        dependency = TaskDependencyModel(
            dependent_task_id=dependent_task.id,
            prerequisite_task_id=prerequisite_task.id,
        )
        db_session.add(dependency)
        await db_session.commit()

        # Should be blocking since prerequisite is not completed
        assert dependency.is_blocking is True

        # Complete prerequisite task
        prerequisite_task.status = TaskStatusEnum.DONE
        await db_session.commit()
        await db_session.refresh(dependency)

        # Should no longer be blocking
        assert dependency.is_blocking is False

    async def test_unique_task_dependency_constraint(self, db_session: AsyncSession):
        """Test that unique constraint prevents duplicate dependencies"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create tasks
        prerequisite_task = TaskModel(
            title="Prerequisite Task",
            team_id=team.id,
            creator_id=user.id,
        )
        dependent_task = TaskModel(
            title="Dependent Task",
            team_id=team.id,
            creator_id=user.id,
        )
        db_session.add_all([prerequisite_task, dependent_task])
        await db_session.commit()

        # Create first dependency
        dependency1 = TaskDependencyModel(
            dependent_task_id=dependent_task.id,
            prerequisite_task_id=prerequisite_task.id,
        )
        db_session.add(dependency1)
        await db_session.commit()

        # Try to create duplicate dependency (should fail)
        dependency2 = TaskDependencyModel(
            dependent_task_id=dependent_task.id,
            prerequisite_task_id=prerequisite_task.id,
        )
        db_session.add(dependency2)

        with pytest.raises(IntegrityError):
            await db_session.commit()


class TestTaskModelValidation:
    """Test model validations and error conditions"""

    async def test_required_title_field(self, db_session: AsyncSession):
        """Test that title field is required"""
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            task = TaskModel(
                # title missing
                team_id=team.id,
                creator_id=user.id,
            )
            db_session.add(task)
            await db_session.commit()

    async def test_required_team_id_field(self, db_session: AsyncSession):
        """Test that team_id field is required"""
        user = UserModel(
            email="creator@example.com",
            hashed_password="hashed",
            first_name="Creator",
            last_name="User",
        )
        db_session.add(user)
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            task = TaskModel(
                title="Test Task",
                # team_id missing
                creator_id=user.id,
            )
            db_session.add(task)
            await db_session.commit()

    async def test_required_creator_id_field(self, db_session: AsyncSession):
        """Test that creator_id field is required"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            task = TaskModel(
                title="Test Task",
                team_id=team.id,
                # creator_id missing
            )
            db_session.add(task)
            await db_session.commit()
