# app/schemas/user.py
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base user schema with common fields."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user updates."""

    full_name: str | None = Field(None, min_length=2, max_length=100)
    email: EmailStr | None = None


class UserResponse(UserBase):
    """Schema for user responses."""

    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
