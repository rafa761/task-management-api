# app/schemas/auth.py
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Login request schema."""

    email: EmailStr
    password: str


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token data schema for JWT payload."""

    user_id: int | None = None
    email: str | None = None
