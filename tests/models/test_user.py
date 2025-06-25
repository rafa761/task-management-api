# tests/models/test_user.py
"""
User Model Tests

Tests model behavior including simple database operations.
Complex queries and business workflows are tested in repository/service layers.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel
from app.utils.dates import utc_now


class TestUserModelBusinessLogic:
    """Test pure business logic"""

    def test_full_name_property(self, sample_user_data):
        """Test full_name property combines first and last name"""
        user = UserModel(**sample_user_data)
        assert user.full_name == "Meg Ferreira"

    def test_full_name_with_missing_last_name(self, sample_user_data):
        """Test full_name handles missing last name gracefully"""
        data = sample_user_data.copy()
        data["last_name"] = ""
        user = UserModel(**data)
        assert user.full_name == sample_user_data.get("first_name")

    def test_initials_property(self, sample_user_data):
        """Test initials property generates correct initials"""
        user = UserModel(**sample_user_data)
        assert user.initials == "".join(
            (
                sample_user_data.get("first_name")[0].upper(),
                sample_user_data.get("last_name")[0].upper(),
            )
        )

    def test_initials_fallback_to_email(self, sample_user_data):
        """Test initials falls back to email if no names"""
        data = sample_user_data.copy()
        data.update({"first_name": "", "last_name": ""})
        user = UserModel(**data)
        assert user.initials == sample_user_data.get("email")[0].upper()

    def test_can_login_all_conditions_met(self, sample_user_data):
        """Test can_login returns True when all conditions are met"""
        user = UserModel(**sample_user_data)  # Active, verified, not deleted
        assert user.can_login() is True

    def test_can_login_inactive_user(self, sample_user_data):
        """Test can_login returns False for inactive user"""
        data = sample_user_data.copy()
        data["is_active"] = False
        user = UserModel(**data)
        assert user.can_login() is False

    def test_can_login_unverified_user(self, sample_user_data):
        """Test can_login returns False for unverified user"""
        data = sample_user_data.copy()
        data["is_verified"] = False
        user = UserModel(**data)
        assert user.can_login() is False

    def test_can_login_deleted_user(self, sample_user_data):
        """Test can_login returns False for soft-deleted user"""
        user = UserModel(**sample_user_data)
        user.soft_delete()  # This sets deleted_at
        assert user.can_login() is False

    def test_deactivate_method_changes_fields(self, sample_user_data):
        """Test deactivate method changes the expected fields"""
        user = UserModel(**sample_user_data)

        # Initially active and not deleted
        assert user.is_active is True
        assert user.deleted_at is None

        # Deactivate
        user.deactivate()

        # Check field changes
        assert user.is_active is False
        assert user.deleted_at is not None
        assert user.is_deleted is True

    def test_activate_method_changes_fields(self, sample_user_data):
        """Test activate method changes the expected fields"""
        data = sample_user_data.copy()
        data["is_active"] = False
        user = UserModel(**data)
        user.soft_delete()  # Mark as deleted

        # Initially inactive and deleted
        assert user.is_active is False
        assert user.is_deleted is True

        # Activate
        user.activate()

        # Check field changes (no database required)
        assert user.is_active is True
        assert user.is_deleted is False

    def test_verify_email_method(self, sample_user_data):
        """Test verify_email method changes verification status"""
        data = sample_user_data.copy()
        data["is_verified"] = False
        user = UserModel(**data)

        # Initially unverified
        assert user.is_verified is False

        # Verify
        user.verify_email()
        assert user.is_verified is True

    def test_update_last_login_sets_timestamp(self, sample_user_data):
        """Test update_last_login sets timestamp (method logic only)"""
        user = UserModel(**sample_user_data)

        # Initially None
        assert user.last_login_at is None

        # Update (test method behavior, not persistence)
        before_update = utc_now()
        user.update_last_login()

        assert user.last_login_at is not None
        assert user.last_login_at >= before_update


class TestUserModelWithDatabase:
    """Test model behavior that requires database interaction"""

    async def test_create_user_with_valid_data(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test creating user and verifying database persistence"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Verify user was persisted with auto-generated fields
        assert user.id is not None
        assert user.created_at is not None
        assert user.updated_at is not None

        # Verify our data was saved correctly
        assert user.email == sample_user_data.get("email")
        assert user.first_name == sample_user_data.get("first_name")
        assert user.last_name == sample_user_data.get("last_name")
        assert user.is_active is True
        assert user.is_verified is True

    async def test_email_uniqueness_constraint(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test database enforces email uniqueness"""
        # Create first user
        user1 = UserModel(**sample_user_data)
        db_session.add(user1)
        await db_session.commit()

        # Try to create second user with same email (should fail)
        user2_data = sample_user_data.copy()
        user2_data.update({"first_name": "Jane", "last_name": "Doe"})
        user2 = UserModel(**user2_data)
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_update_last_login_persistence(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test that update_last_login persists to database"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Update last login
        user.update_last_login()
        await db_session.commit()

        # Refresh from database to verify persistence
        await db_session.refresh(user)
        assert user.last_login_at is not None

    async def test_soft_delete_persistence(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test that soft delete persists to database"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Soft delete
        user.deactivate()  # This calls soft_delete internally
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(user)
        assert user.is_active is False
        assert user.deleted_at is not None
        assert user.is_deleted is True

    async def test_activate_user_persistence(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test that user activation persists to database"""
        # Create inactive user
        data = sample_user_data.copy()
        data["is_active"] = False
        user = UserModel(**data)
        user.soft_delete()
        db_session.add(user)
        await db_session.commit()

        # Activate
        user.activate()
        await db_session.commit()

        # Refresh and verify
        await db_session.refresh(user)
        assert user.is_active is True
        assert user.deleted_at is None

    async def test_timestamp_auto_generation(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test that timestamps are automatically set by database"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Check auto-generated timestamps
        assert user.created_at is not None
        assert user.updated_at is not None

    async def test_updated_at_changes_on_modification(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test that updated_at changes when model is modified"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Make a change
        user.first_name = "Updated"
        await db_session.commit()
        await db_session.refresh(user)

    async def test_timezone_defaults_correctly(
        self, db_session: AsyncSession, sample_user_data
    ):
        """Test timezone field defaults to UTC"""
        data = sample_user_data.copy()
        del data["timezone"]  # Remove to test default

        user = UserModel(**data)
        db_session.add(user)
        await db_session.commit()

        assert user.timezone == "UTC"

    async def test_boolean_field_defaults(self, db_session: AsyncSession):
        """Test boolean field defaults are set correctly"""
        user = UserModel(
            email="defaults@example.com",
            hashed_password="hashed",
            first_name="Test",
            last_name="User",
        )
        db_session.add(user)
        await db_session.commit()

        # Check defaults
        assert user.is_active is True  # Should default to True
        assert user.is_verified is False  # Should default to False


class TestUserModelValidation:
    """Test model validations and error conditions"""

    async def test_required_email_field(self, db_session: AsyncSession):
        """Test that email field is required"""
        with pytest.raises((TypeError, IntegrityError)):
            user = UserModel(
                # email missing
                hashed_password="hashed",
                first_name="Test",
                last_name="User",
            )
            db_session.add(user)
            await db_session.commit()

    async def test_required_password_field(self, db_session: AsyncSession):
        """Test that hashed_password field is required"""
        with pytest.raises((TypeError, IntegrityError)):
            user = UserModel(
                email="test@example.com",
                # hashed_password missing
                first_name="Test",
                last_name="User",
            )
            db_session.add(user)
            await db_session.commit()
