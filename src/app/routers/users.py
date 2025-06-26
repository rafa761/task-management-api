# app/routers/users.py
from fastapi import APIRouter

from app.dependencies import CurrentUser, UserServiceDep
from app.schemas.user import UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate, current_user: CurrentUser, user_service: UserServiceDep
) -> UserResponse:
    """Update current user information."""
    updated_user = await user_service.update_user(current_user.id, user_data)
    return UserResponse.model_validate(updated_user)
