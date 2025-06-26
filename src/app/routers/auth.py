# app/routers/auth.py
from fastapi import APIRouter, HTTPException, status

from app.dependencies import AuthServiceDep, UserServiceDep
from app.schemas.auth import LoginRequest, Token
from app.schemas.user import UserCreate, UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user_data: UserCreate, user_service: UserServiceDep) -> UserResponse:
    """
    Register a new user.

    - **email**: Valid email address
    - **username**: Unique username (3-50 characters)
    - **full_name**: User's full name (2-100 characters)
    - **password**: Strong password (minimum 8 characters)
    """
    user = await user_service.create_user(user_data)
    return UserResponse.model_validate(user)


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, auth_service: AuthServiceDep) -> Token:
    """
    Login user and return access/refresh tokens.

    - **email**: User's email address
    - **password**: User's password
    """
    tokens = await auth_service.login(login_data.email, login_data.password)
    return Token(**tokens)


@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, auth_service: AuthServiceDep) -> Token:
    """
    Refresh access token using refresh token.

    - **refresh_token**: Valid refresh token
    """
    # Decode refresh token to get user info
    try:
        token_data = auth_service.decode_token(refresh_token)
        user = await auth_service.user_repository.get_by_id(token_data.user_id)

        if not user or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            ) from None

        # Generate new tokens
        new_token_data = {"sub": user.id, "email": user.email}
        access_token = auth_service.create_access_token(new_token_data)
        new_refresh_token = auth_service.create_refresh_token(new_token_data)

        return Token(access_token=access_token, refresh_token=new_refresh_token)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        ) from e
