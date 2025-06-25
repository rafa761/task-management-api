# tests/models/test_project.py
"""
Project Model Tests

Tests model behavior including simple database operations.
Complex queries and business workflows are tested in repository/service layers.
"""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import ProjectModel, TaskModel, TeamModel, UserModel
from app.models.enums import ProjectStatusEnum, TaskStatusEnum
from app.utils.dates import days_ago, days_from_now, utc_now


class TestProjectModelBusinessLogic:
    """Test pure business logic without database dependencies"""

    def test_is_overdue_property_no_end_date(self, sample_project_data):
        """Test is_overdue returns False when no end date is set"""
        project = ProjectModel(**sample_project_data)
        assert project.is_overdue is False

    def test_is_overdue_property_future_end_date(self, sample_project_data):
        """Test is_overdue returns False when end date is in future"""
        data = sample_project_data.copy()
        data["end_date"] = days_from_now(5)
        project = ProjectModel(**data)
        assert project.is_overdue is False

    def test_is_overdue_property_past_end_date_active_project(
        self, sample_project_data
    ):
        """Test is_overdue returns True when end date is past and project is active"""
        data = sample_project_data.copy()
        data["end_date"] = days_ago(2)
        data["status"] = ProjectStatusEnum.ACTIVE
        project = ProjectModel(**data)
        assert project.is_overdue is True

    def test_is_overdue_property_past_end_date_inactive_project(
        self, sample_project_data
    ):
        """Test is_overdue returns False when project is inactive even if past end date"""
        data = sample_project_data.copy()
        data["end_date"] = days_ago(2)
        data["status"] = ProjectStatusEnum.COMPLETED
        project = ProjectModel(**data)
        assert project.is_overdue is False

    def test_duration_days_property_with_dates(self, sample_project_data):
        """Test duration_days calculates correctly when both dates are set"""
        data = sample_project_data.copy()
        data["start_date"] = days_ago(10)
        data["end_date"] = days_ago(5)
        project = ProjectModel(**data)
        assert project.duration_days == 5

    def test_duration_days_property_missing_dates(self, sample_project_data):
        """Test duration_days returns None when dates are missing"""
        # Test with no end date
        data = sample_project_data.copy()
        data["start_date"] = days_ago(5)
        data["end_date"] = None
        project = ProjectModel(**data)
        assert project.duration_days is None

        # Test with no start date
        data["start_date"] = None
        data["end_date"] = days_from_now(5)
        project = ProjectModel(**data)
        assert project.duration_days is None

    def test_days_remaining_property_active_project(self, sample_project_data):
        """Test days_remaining calculates correctly for active project"""
        data = sample_project_data.copy()
        data["end_date"] = days_from_now(7)
        data["status"] = ProjectStatusEnum.ACTIVE
        project = ProjectModel(**data)
        assert project.days_remaining in (6, 7)  # handle the timing variance of utc now

    def test_days_remaining_property_no_end_date(self, sample_project_data):
        """Test days_remaining returns None when no end date"""
        data = sample_project_data.copy()
        data["end_date"] = None
        project = ProjectModel(**data)
        assert project.days_remaining is None

    def test_days_remaining_property_completed_project(self, sample_project_data):
        """Test days_remaining returns None for completed project"""
        data = sample_project_data.copy()
        data["end_date"] = days_from_now(5)
        data["status"] = ProjectStatusEnum.COMPLETED
        project = ProjectModel(**data)
        assert project.days_remaining is None

    def test_days_remaining_property_overdue_project(self, sample_project_data):
        """Test days_remaining returns 0 for overdue project"""
        data = sample_project_data.copy()
        data["end_date"] = days_ago(3)
        data["status"] = ProjectStatusEnum.ACTIVE
        project = ProjectModel(**data)
        assert project.days_remaining == 0

    def test_completion_percentage_no_tasks(self, sample_project_data):
        """Test completion_percentage returns 0 when no tasks exist"""
        project = ProjectModel(**sample_project_data)
        project.tasks = []
        assert project.completion_percentage == 0.0

    def test_start_project_method(self, sample_project_data):
        """Test start_project method changes status and sets start date"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.PLANNING
        data["start_date"] = None
        project = ProjectModel(**data)

        before_start = utc_now()
        project.start_project()

        assert project.status == ProjectStatusEnum.ACTIVE
        assert project.start_date is not None
        assert project.start_date >= before_start

    def test_start_project_method_preserves_existing_start_date(
        self, sample_project_data
    ):
        """Test start_project doesn't overwrite existing start date"""
        data = sample_project_data.copy()
        original_start = days_ago(5)
        data["start_date"] = original_start
        project = ProjectModel(**data)

        project.start_project()

        assert project.status == ProjectStatusEnum.ACTIVE
        assert project.start_date == original_start

    def test_complete_project_method(self, sample_project_data):
        """Test complete_project method changes status and sets end date"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.ACTIVE
        data["end_date"] = None
        project = ProjectModel(**data)

        before_complete = utc_now()
        project.complete_project()

        assert project.status == ProjectStatusEnum.COMPLETED
        assert project.end_date is not None
        assert project.end_date >= before_complete

    def test_complete_project_preserves_existing_end_date(self, sample_project_data):
        """Test complete_project doesn't overwrite existing end date"""
        data = sample_project_data.copy()
        original_end = days_ago(1)
        data["end_date"] = original_end
        project = ProjectModel(**data)

        project.complete_project()

        assert project.status == ProjectStatusEnum.COMPLETED
        assert project.end_date == original_end

    def test_cancel_project_method(self, sample_project_data):
        """Test cancel_project method changes status and deactivates"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.ACTIVE
        data["is_active"] = True
        project = ProjectModel(**data)

        project.cancel_project()

        assert project.status == ProjectStatusEnum.CANCELLED
        assert project.is_active is False

    def test_put_on_hold_method(self, sample_project_data):
        """Test put_on_hold method changes status"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.ACTIVE
        project = ProjectModel(**data)

        project.put_on_hold()

        assert project.status == ProjectStatusEnum.ON_HOLD

    def test_resume_project_method(self, sample_project_data):
        """Test resume_project method changes status from hold to active"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.ON_HOLD
        project = ProjectModel(**data)

        project.resume_project()

        assert project.status == ProjectStatusEnum.ACTIVE

    def test_resume_project_method_ignores_non_hold_status(self, sample_project_data):
        """Test resume_project doesn't change status if not on hold"""
        data = sample_project_data.copy()
        data["status"] = ProjectStatusEnum.COMPLETED
        project = ProjectModel(**data)

        project.resume_project()

        assert project.status == ProjectStatusEnum.COMPLETED

    def test_validate_timeline_valid_dates(self, sample_project_data):
        """Test validate_timeline returns True for valid date range"""
        data = sample_project_data.copy()
        data["start_date"] = days_ago(10)
        data["end_date"] = days_ago(5)
        project = ProjectModel(**data)

        assert project.validate_timeline() is True

    def test_validate_timeline_invalid_dates(self, sample_project_data):
        """Test validate_timeline returns False when start date is after end date"""
        data = sample_project_data.copy()
        data["start_date"] = days_ago(5)
        data["end_date"] = days_ago(10)
        project = ProjectModel(**data)

        assert project.validate_timeline() is False

    def test_validate_timeline_missing_dates(self, sample_project_data):
        """Test validate_timeline returns True when dates are missing"""
        data = sample_project_data.copy()
        data["start_date"] = None
        data["end_date"] = None
        project = ProjectModel(**data)

        assert project.validate_timeline() is True

    def test_validate_timeline_same_dates(self, sample_project_data):
        """Test validate_timeline returns True when dates are the same"""
        data = sample_project_data.copy()
        same_date = days_ago(5)
        data["start_date"] = same_date
        data["end_date"] = same_date
        project = ProjectModel(**data)

        assert project.validate_timeline() is True


class TestProjectModelWithDatabase:
    """Test model behavior that requires database interaction"""

    async def test_create_project_with_valid_data(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test creating project with valid data and team relationship"""
        # First create a team
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        # Update sample data with real team ID
        data = sample_project_data.copy()
        data["team_id"] = team.id

        project = ProjectModel(**data)
        db_session.add(project)
        await db_session.commit()

        # Verify project was persisted with auto-generated fields
        assert project.id is not None
        assert project.created_at is not None
        assert project.updated_at is not None

        # Verify our data was saved correctly
        assert project.name == sample_project_data["name"]
        assert project.description == sample_project_data["description"]
        assert project.team_id == team.id
        assert project.is_active is True

    async def test_project_team_relationship(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test project-team relationship works correctly"""
        # Create team
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        # Create project
        data = sample_project_data.copy()
        data["team_id"] = team.id
        project = ProjectModel(**data)
        db_session.add(project)
        await db_session.commit()

        # Test relationship
        assert project.team.id == team.id
        assert project.team.name == "Test Team"

    async def test_different_teams_can_have_same_project_name(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test that different teams can have projects with the same name"""
        # Create two teams
        team1 = TeamModel(name="Team One", slug="team-one")
        team2 = TeamModel(name="Team Two", slug="team-two")
        db_session.add_all([team1, team2])
        await db_session.commit()

        # Create projects with same name in different teams
        data = sample_project_data.copy()

        data["team_id"] = team1.id
        project1 = ProjectModel(**data)

        data["team_id"] = team2.id
        project2 = ProjectModel(**data)

        db_session.add_all([project1, project2])
        await db_session.commit()  # Should not raise error

        # Verify both projects exist
        assert project1.name == project2.name
        assert project1.team_id != project2.team_id

    async def test_project_soft_delete_persistence(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test that soft delete persists to database"""
        # Create team and project
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        data = sample_project_data.copy()
        data["team_id"] = team.id
        project = ProjectModel(**data)
        db_session.add(project)
        await db_session.commit()

        # Soft delete
        project.soft_delete()
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(project)
        assert project.deleted_at is not None
        assert project.is_deleted is True

    async def test_project_with_tasks_completion_percentage(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test completion percentage calculation with actual tasks"""
        # Create team and user
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="test@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create project
        data = sample_project_data.copy()
        data["team_id"] = team.id
        project = ProjectModel(**data)
        db_session.add(project)
        await db_session.commit()

        # Create tasks - 2 completed, 2 active
        task1 = TaskModel(
            title="Task 1",
            team_id=team.id,
            creator_id=user.id,
            project_id=project.id,
            status=TaskStatusEnum.DONE,
        )
        task2 = TaskModel(
            title="Task 2",
            team_id=team.id,
            creator_id=user.id,
            project_id=project.id,
            status=TaskStatusEnum.DONE,
        )
        task3 = TaskModel(
            title="Task 3",
            team_id=team.id,
            creator_id=user.id,
            project_id=project.id,
            status=TaskStatusEnum.TODO,
        )
        task4 = TaskModel(
            title="Task 4",
            team_id=team.id,
            creator_id=user.id,
            project_id=project.id,
            status=TaskStatusEnum.IN_PROGRESS,
        )

        db_session.add_all([task1, task2, task3, task4])
        await db_session.commit()

        # Load project with tasks to avoid lazy loading issues
        result = await db_session.execute(
            select(ProjectModel)
            .options(selectinload(ProjectModel.tasks))
            .where(ProjectModel.id == project.id)
        )
        project_with_tasks = result.scalar_one()

        # Should be 50% complete (2 out of 4 tasks done)
        assert project_with_tasks.completion_percentage == 50.0

        # Should be 50% complete (2 out of 4 tasks done)
        assert project.completion_percentage == 50.0

    async def test_project_status_enum_constraint(
        self, db_session: AsyncSession, sample_project_data
    ):
        """Test that valid enum values work"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        data = sample_project_data.copy()
        data["team_id"] = team.id

        # This should work with valid enum
        project = ProjectModel(**data)
        db_session.add(project)
        await db_session.commit()

        # Valid enum assignment should work
        project.status = ProjectStatusEnum.ACTIVE
        await db_session.commit()
        assert project.status == ProjectStatusEnum.ACTIVE


class TestProjectModelValidation:
    """Test model validations and error conditions"""

    async def test_required_team_id_field(self, db_session: AsyncSession):
        """Test that team_id field is required"""
        with pytest.raises((TypeError, IntegrityError)):
            project = ProjectModel(
                name="Test Project",
                # team_id missing
            )
            db_session.add(project)
            await db_session.commit()

    async def test_required_name_field(self, db_session: AsyncSession):
        """Test that name field is required"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            project = ProjectModel(
                team_id=team.id,
                # name missing
            )
            db_session.add(project)
            await db_session.commit()

    async def test_boolean_and_enum_defaults(self, db_session: AsyncSession):
        """Test that default values are set correctly"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        project = ProjectModel(name="Minimal Project", team_id=team.id)
        db_session.add(project)
        await db_session.commit()

        # Check defaults
        assert project.status == ProjectStatusEnum.PLANNING
        assert project.is_active is True
        assert project.position == 0

    async def test_color_field_length_limit(self, db_session: AsyncSession):
        """Test color field respects length limit"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        # Valid hex color should work
        project = ProjectModel(
            name="Colorful Project", team_id=team.id, color="#FF5733"
        )
        db_session.add(project)
        await db_session.commit()

        assert project.color == "#FF5733"
