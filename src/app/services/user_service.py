# app/services/user_service.py
from uuid import UUID

from fastapi import HTTPException, status

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserUpdate

from .auth_service import AuthService


class UserService:
    """Service for user operations."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    async def create_user(self, user_data: UserCreate) -> User:
        """Create a new user."""
        # Check if email already exists
        if await self.user_repository.email_exists(user_data.email):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Check if username already exists
        if await self.user_repository.username_exists(user_data.username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )

        # Hash password
        hashed_password = AuthService.hash_password(user_data.password)

        # Create user
        user = await self.user_repository.create(
            email=user_data.email,
            username=user_data.username,
            full_name=user_data.full_name,
            hashed_password=hashed_password,
        )

        return user

    async def get_user_by_id(self, user_id: UUID) -> User:
        """Get user by ID."""
        user = await self.user_repository.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def update_user(self, user_id: UUID, user_data: UserUpdate) -> User:
        """Update user information."""
        # Check if user exists
        existing_user = await self.get_user_by_id(user_id)

        # Check if new email is already taken by another user
        if user_data.email and user_data.email != existing_user.email:
            if await self.user_repository.email_exists(user_data.email):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered",
                )

        # Update user
        updated_user = await self.user_repository.update(
            user_id, **user_data.model_dump(exclude_unset=True)
        )

        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )

        return updated_user
