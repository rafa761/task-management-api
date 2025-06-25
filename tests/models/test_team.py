# tests/models/test_team.py
"""
Team Model Tests

Tests model behavior including simple database operations.
Complex queries and business workflows are tested in repository/service layers.
"""

from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TeamMembershipModel, TeamModel, UserModel
from app.models.enums import TeamRoleEnum
from app.utils.dates import utc_now


class TestTeamModelBusinessLogic:
    """Test pure business logic without database dependencies"""

    def test_get_owners_returns_correct_members(self, sample_team_data):
        """Test get_owners returns only owner role members"""
        team = TeamModel(**sample_team_data)

        # Create mock memberships
        owner_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.OWNER,
            joined_at=utc_now(),
        )
        admin_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )
        member_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
        )

        team.memberships = [owner_membership, admin_membership, member_membership]

        owners = team.get_owners()
        assert len(owners) == 1
        assert owners[0].role == TeamRoleEnum.OWNER

    def test_get_admins_returns_owners_and_admins(self, sample_team_data):
        """Test get_admins returns both owners and admins"""
        team = TeamModel(**sample_team_data)

        # Create mock memberships
        owner_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.OWNER,
            joined_at=utc_now(),
        )
        admin_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )
        member_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
        )

        team.memberships = [owner_membership, admin_membership, member_membership]

        admins = team.get_admins()
        assert len(admins) == 2
        assert any(m.role == TeamRoleEnum.OWNER for m in admins)
        assert any(m.role == TeamRoleEnum.ADMIN for m in admins)

    def test_get_active_members_excludes_pending_and_deleted(self, sample_team_data):
        """Test get_active_members only returns joined, non-deleted members"""
        team = TeamModel(**sample_team_data)

        # Create mock memberships
        active_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
            deleted_at=None,
        )
        pending_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=None,  # Pending
            deleted_at=None,
        )
        deleted_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
            deleted_at=utc_now(),  # Deleted
        )

        team.memberships = [active_membership, pending_membership, deleted_membership]

        active_members = team.get_active_members()
        assert len(active_members) == 1
        assert active_members[0] == active_membership

    def test_member_count_returns_correct_count(self, sample_team_data):
        """Test member_count returns count of active members"""
        team = TeamModel(**sample_team_data)

        # Create mock memberships - 2 active, 1 pending, 1 deleted
        active1 = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            joined_at=utc_now(),
        )
        active2 = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            joined_at=utc_now(),
        )
        pending = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            joined_at=None,
        )
        deleted = TeamMembershipModel(
            user_id=uuid4(),
            team_id=team.id,
            joined_at=utc_now(),
            deleted_at=utc_now(),
        )

        team.memberships = [active1, active2, pending, deleted]

        assert team.member_count() == 2

    def test_has_member_returns_true_for_active_member(self, sample_team_data):
        """Test has_member returns True for active member"""
        team = TeamModel(**sample_team_data)
        user_id = uuid4()

        membership = TeamMembershipModel(
            user_id=user_id,
            team_id=team.id,
            joined_at=utc_now(),
            deleted_at=None,
        )
        team.memberships = [membership]

        assert team.has_member(user_id) is True

    def test_has_member_returns_false_for_pending_member(self, sample_team_data):
        """Test has_member returns False for pending member"""
        team = TeamModel(**sample_team_data)
        user_id = uuid4()

        membership = TeamMembershipModel(
            user_id=user_id,
            team_id=team.id,
            joined_at=None,  # Pending
        )
        team.memberships = [membership]

        assert team.has_member(user_id) is False

    def test_has_member_returns_false_for_deleted_member(self, sample_team_data):
        """Test has_member returns False for deleted member"""
        team = TeamModel(**sample_team_data)
        user_id = uuid4()

        membership = TeamMembershipModel(
            user_id=user_id,
            team_id=team.id,
            joined_at=utc_now(),
            deleted_at=utc_now(),  # Deleted
        )
        team.memberships = [membership]

        assert team.has_member(user_id) is False

    def test_get_member_role_returns_correct_role(self, sample_team_data):
        """Test get_member_role returns correct role for active member"""
        team = TeamModel(**sample_team_data)
        user_id = uuid4()

        membership = TeamMembershipModel(
            user_id=user_id,
            team_id=team.id,
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )
        team.memberships = [membership]

        assert team.get_member_role(user_id) == TeamRoleEnum.ADMIN

    def test_get_member_role_returns_none_for_non_member(self, sample_team_data):
        """Test get_member_role returns None for non-member"""
        team = TeamModel(**sample_team_data)
        non_member_id = uuid4()

        team.memberships = []

        assert team.get_member_role(non_member_id) is None

    def test_can_user_modify_returns_true_for_admin_roles(self, sample_team_data):
        """Test can_user_modify returns True for admin roles"""
        team = TeamModel(**sample_team_data)
        owner_id = uuid4()
        admin_id = uuid4()

        owner_membership = TeamMembershipModel(
            user_id=owner_id,
            team_id=team.id,
            role=TeamRoleEnum.OWNER,
            joined_at=utc_now(),
        )
        admin_membership = TeamMembershipModel(
            user_id=admin_id,
            team_id=team.id,
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )
        team.memberships = [owner_membership, admin_membership]

        assert team.can_user_modify(owner_id) is True
        assert team.can_user_modify(admin_id) is True

    def test_can_user_modify_returns_false_for_non_admin_roles(self, sample_team_data):
        """Test can_user_modify returns False for non-admin roles"""
        team = TeamModel(**sample_team_data)
        member_id = uuid4()
        viewer_id = uuid4()

        member_membership = TeamMembershipModel(
            user_id=member_id,
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
        )
        viewer_membership = TeamMembershipModel(
            user_id=viewer_id,
            team_id=team.id,
            role=TeamRoleEnum.VIEWER,
            joined_at=utc_now(),
        )
        team.memberships = [member_membership, viewer_membership]

        assert team.can_user_modify(member_id) is False
        assert team.can_user_modify(viewer_id) is False


class TestTeamModelWithDatabase:
    """Test model behavior that requires database interaction"""

    async def test_create_team_with_valid_data(
        self, db_session: AsyncSession, sample_team_data
    ):
        """Test creating team with valid data"""
        team = TeamModel(**sample_team_data)
        db_session.add(team)
        await db_session.commit()

        # Verify team was persisted with auto-generated fields
        assert team.id is not None
        assert team.created_at is not None
        assert team.updated_at is not None

        # Verify our data was saved correctly
        assert team.name == sample_team_data["name"]
        assert team.slug == sample_team_data["slug"]
        assert team.description == sample_team_data["description"]
        assert team.is_active is True

    async def test_slug_uniqueness_constraint(
        self, db_session: AsyncSession, sample_team_data
    ):
        """Test database enforces slug uniqueness"""
        # Create first team
        team1 = TeamModel(**sample_team_data)
        db_session.add(team1)
        await db_session.commit()

        # Try to create second team with same slug (should fail)
        team2_data = sample_team_data.copy()
        team2_data["name"] = "Different Team Name"
        team2 = TeamModel(**team2_data)
        db_session.add(team2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_team_soft_delete_persistence(
        self, db_session: AsyncSession, sample_team_data
    ):
        """Test that soft delete persists to database"""
        team = TeamModel(**sample_team_data)
        db_session.add(team)
        await db_session.commit()

        # Soft delete
        team.soft_delete()
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(team)
        assert team.deleted_at is not None
        assert team.is_deleted is True

    async def test_team_defaults(self, db_session: AsyncSession):
        """Test that default values are set correctly"""
        team = TeamModel(
            name="Minimal Team",
            slug="minimal-team",
        )
        db_session.add(team)
        await db_session.commit()

        # Check defaults
        assert team.is_active is True
        assert team.allow_public_signup is False
        assert team.default_task_priority == "medium"


class TestTeamMembershipModelBusinessLogic:
    """Test TeamMembershipModel pure business logic"""

    def test_is_pending_property_true_when_not_joined(self):
        """Test is_pending returns True when joined_at is None"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=None,
            deleted_at=None,
        )
        assert membership.is_pending is True

    def test_is_pending_property_false_when_joined(self):
        """Test is_pending returns False when joined_at is set"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=utc_now(),
            deleted_at=None,
        )
        assert membership.is_pending is False

    def test_is_pending_property_false_when_deleted(self):
        """Test is_pending returns False when deleted"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=None,
            deleted_at=utc_now(),
        )
        assert membership.is_pending is False

    def test_is_active_property_true_when_joined_not_deleted(self):
        """Test is_active returns True when joined and not deleted"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=utc_now(),
            deleted_at=None,
        )
        assert membership.is_active is True

    def test_is_active_property_false_when_not_joined(self):
        """Test is_active returns False when not joined"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=None,
            deleted_at=None,
        )
        assert membership.is_active is False

    def test_is_active_property_false_when_deleted(self):
        """Test is_active returns False when deleted"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=utc_now(),
            deleted_at=utc_now(),
        )
        assert membership.is_active is False

    def test_is_deleted_property_true_when_deleted_at_set(self):
        """Test is_deleted returns True when deleted_at is set"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            deleted_at=utc_now(),
        )
        assert membership.is_deleted is True

    def test_is_deleted_property_false_when_deleted_at_none(self):
        """Test is_deleted returns False when deleted_at is None"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            deleted_at=None,
        )
        assert membership.is_deleted is False

    def test_accept_invitation_sets_joined_at(self):
        """Test accept_invitation sets joined_at for pending membership"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=None,  # Pending
        )

        before_accept = utc_now()
        membership.accept_invitation()

        assert membership.joined_at is not None
        assert membership.joined_at >= before_accept

    def test_accept_invitation_ignores_non_pending(self):
        """Test accept_invitation doesn't change already joined membership"""
        original_joined_at = utc_now()
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            joined_at=original_joined_at,
        )

        membership.accept_invitation()

        assert membership.joined_at == original_joined_at

    def test_deactivate_sets_deleted_at(self):
        """Test deactivate sets deleted_at timestamp"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            deleted_at=None,
        )

        before_deactivate = utc_now()
        membership.deactivate()

        assert membership.deleted_at is not None
        assert membership.deleted_at >= before_deactivate

    def test_reactivate_clears_deleted_at(self):
        """Test reactivate clears deleted_at"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            deleted_at=utc_now(),
        )

        membership.reactivate()

        assert membership.deleted_at is None

    def test_change_role_updates_role(self):
        """Test change_role updates the role"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.MEMBER,
        )

        membership.change_role(TeamRoleEnum.ADMIN)

        assert membership.role == TeamRoleEnum.ADMIN

    def test_has_permission_true_for_higher_role(self):
        """Test has_permission returns True for higher role levels"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )

        assert membership.has_permission(TeamRoleEnum.MEMBER) is True
        assert membership.has_permission(TeamRoleEnum.VIEWER) is True

    def test_has_permission_false_for_lower_role(self):
        """Test has_permission returns False for lower role levels"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
        )

        assert membership.has_permission(TeamRoleEnum.ADMIN) is False
        assert membership.has_permission(TeamRoleEnum.OWNER) is False

    def test_has_permission_false_for_inactive_membership(self):
        """Test has_permission returns False for inactive membership"""
        membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.OWNER,
            joined_at=None,  # Not active
        )

        assert membership.has_permission(TeamRoleEnum.VIEWER) is False

    def test_can_manage_team_true_for_admin_roles(self):
        """Test can_manage_team returns True for admin roles"""
        owner_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.OWNER,
            joined_at=utc_now(),
        )
        admin_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )

        assert owner_membership.can_manage_team() is True
        assert admin_membership.can_manage_team() is True

    def test_can_manage_team_false_for_non_admin_roles(self):
        """Test can_manage_team returns False for non-admin roles"""
        member_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.MEMBER,
            joined_at=utc_now(),
        )
        viewer_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.VIEWER,
            joined_at=utc_now(),
        )

        assert member_membership.can_manage_team() is False
        assert viewer_membership.can_manage_team() is False

    def test_can_manage_members_true_for_admin_roles(self):
        """Test can_manage_members returns True for admin roles"""
        owner_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.OWNER,
            joined_at=utc_now(),
        )
        admin_membership = TeamMembershipModel(
            user_id=uuid4(),
            team_id=uuid4(),
            role=TeamRoleEnum.ADMIN,
            joined_at=utc_now(),
        )

        assert owner_membership.can_manage_members() is True
        assert admin_membership.can_manage_members() is True


class TestTeamMembershipModelWithDatabase:
    """Test TeamMembershipModel behavior that requires database interaction"""

    async def test_create_membership_with_valid_data(self, db_session: AsyncSession):
        """Test creating membership with valid data"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="user@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create membership
        membership = TeamMembershipModel(
            user_id=user.id,
            team_id=team.id,
            role=TeamRoleEnum.MEMBER,
        )
        db_session.add(membership)
        await db_session.commit()

        # Verify membership was persisted
        assert membership.id is not None
        assert membership.created_at is not None
        assert membership.user_id == user.id
        assert membership.team_id == team.id
        assert membership.invited_at is not None

    async def test_membership_relationships(self, db_session: AsyncSession):
        """Test membership relationships work correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="user@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        inviter = UserModel(
            email="inviter@example.com",
            hashed_password="hashed",
            first_name="Inviter",
            last_name="User",
        )
        db_session.add_all([team, user, inviter])
        await db_session.commit()

        # Create membership
        membership = TeamMembershipModel(
            user_id=user.id,
            team_id=team.id,
            invited_by_id=inviter.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Test relationships
        assert membership.user.email == "user@example.com"
        assert membership.team.name == "Test Team"
        assert membership.invited_by.email == "inviter@example.com"

    async def test_membership_enum_constraint(self, db_session: AsyncSession):
        """Test that valid enum values work"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="user@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create membership with valid enum
        membership = TeamMembershipModel(
            user_id=user.id,
            team_id=team.id,
            role=TeamRoleEnum.ADMIN,
        )
        db_session.add(membership)
        await db_session.commit()

        # Valid enum assignment should work
        membership.role = TeamRoleEnum.OWNER
        await db_session.commit()
        assert membership.role == TeamRoleEnum.OWNER

    async def test_membership_defaults(self, db_session: AsyncSession):
        """Test that default values are set correctly"""
        # Create prerequisites
        team = TeamModel(name="Test Team", slug="test-team")
        user = UserModel(
            email="user@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add_all([team, user])
        await db_session.commit()

        # Create minimal membership
        membership = TeamMembershipModel(
            user_id=user.id,
            team_id=team.id,
        )
        db_session.add(membership)
        await db_session.commit()

        # Check defaults
        assert membership.role == TeamRoleEnum.MEMBER
        assert membership.invited_at is not None
        assert membership.joined_at is None  # Should be pending by default


class TestTeamModelValidation:
    """Test model validations and error conditions"""

    async def test_required_name_field(self, db_session: AsyncSession):
        """Test that name field is required"""
        with pytest.raises((TypeError, IntegrityError)):
            team = TeamModel(
                # name missing
                slug="test-team",
            )
            db_session.add(team)
            await db_session.commit()

    async def test_required_slug_field(self, db_session: AsyncSession):
        """Test that slug field is required"""
        with pytest.raises((TypeError, IntegrityError)):
            team = TeamModel(
                name="Test Team",
                # slug missing
            )
            db_session.add(team)
            await db_session.commit()

    async def test_required_user_id_field_in_membership(self, db_session: AsyncSession):
        """Test that user_id field is required in membership"""
        team = TeamModel(name="Test Team", slug="test-team")
        db_session.add(team)
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            membership = TeamMembershipModel(
                # user_id missing
                team_id=team.id,
            )
            db_session.add(membership)
            await db_session.commit()

    async def test_required_team_id_field_in_membership(self, db_session: AsyncSession):
        """Test that team_id field is required in membership"""
        user = UserModel(
            email="user@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.commit()

        with pytest.raises((TypeError, IntegrityError)):
            membership = TeamMembershipModel(
                user_id=user.id,
                # team_id missing
            )
            db_session.add(membership)
            await db_session.commit()
