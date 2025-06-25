"""
Tests for User model.

Focuses on testing business logic, properties, and basic database operations
"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import UserModel


class TestUserModel:
    """Test User model functionality"""

    async def test_create_user(self, db_session: AsyncSession, sample_user_data):
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Verify user was created with correct data
        assert user.id is not None
        assert user.email == "test@example.com"
        assert user.first_name == "Meg"
        assert user.last_name == "Ferreira"
        assert user.is_active is True
        assert user.is_verified is True

    async def test_update_last_login(self, db_session: AsyncSession, sample_user_data):
        """Test updating last login timestamp"""
        user = UserModel(**sample_user_data)
        db_session.add(user)
        await db_session.commit()

        # Initially None
        assert user.last_login_at is None

        # Update login time
        user.update_last_login()
        assert user.last_login_at is not None
        assert isinstance(user.last_login_at, datetime)
