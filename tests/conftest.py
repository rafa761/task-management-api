# tests/conftest.py
"""
Test configuration and fixtures for the FastAPI application.
Provides database setup, test client, and authentication fixtures.
"""

from collections.abc import AsyncGenerator
from typing import Any

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db
from app.core.factory import create_app
from app.models import BaseModel

# Test settings
settings = get_settings()


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    test_database_url = settings.test_database_url

    # Create engine for test database
    engine = create_async_engine(
        test_database_url,
        echo=False,  # Set to True for SQL debugging
        pool_pre_ping=True,
        pool_recycle=3600,  # Recycle connections after 1 hour
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield engine

    # Clean up
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def test_session(test_engine) -> AsyncGenerator[AsyncSession]:
    """Create a test database session with transaction rollback."""
    connection = await test_engine.connect()
    transaction = await connection.begin()

    # Create session bound to the connection
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        autoflush=True,
        autocommit=False,
    )

    try:
        yield session
    finally:
        await session.close()
        # Rollback transaction to clean up
        await transaction.rollback()
        await connection.close()


@pytest_asyncio.fixture
async def app_with_test_db(test_session: AsyncSession):
    """Create FastAPI app with test database dependency override."""
    app = create_app()

    # Override database dependency
    async def get_test_db() -> AsyncGenerator[AsyncSession]:
        yield test_session

    app.dependency_overrides[get_db] = get_test_db

    yield app

    # Clean up
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client(app_with_test_db) -> AsyncGenerator[AsyncClient]:
    """Create async HTTP client for testing."""
    async with AsyncClient(
        transport=ASGITransport(app=app_with_test_db), base_url="http://test"
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "full_name": "Test User",
        "password": "testpassword123",
    }


@pytest_asyncio.fixture
async def create_test_user(
    client: AsyncClient, test_user_data: dict[str, Any]
) -> dict[str, Any]:
    """Create a test user and return user data with ID."""
    response = await client.post("/api/v1/auth/register", json=test_user_data)
    assert response.status_code == 201

    user_response = response.json()
    return {**test_user_data, "id": user_response["id"]}


@pytest_asyncio.fixture
async def auth_headers(
    client: AsyncClient, test_user_data: dict[str, Any]
) -> dict[str, str]:
    """Get authentication headers for test user."""
    # First register the user
    await client.post("/api/v1/auth/register", json=test_user_data)

    # Then login to get token
    login_data = {
        "email": test_user_data["email"],
        "password": test_user_data["password"],
    }

    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200

    token_data = response.json()
    return {"Authorization": f"Bearer {token_data['access_token']}"}


@pytest_asyncio.fixture
async def sample_task_data() -> dict[str, Any]:
    """Sample task data for testing."""
    return {
        "title": "Test Task",
        "description": "This is a test task",
        "priority": "medium",
        "due_date": "2024-12-31T23:59:59",
    }


# Database cleanup fixture to ensure clean state
@pytest_asyncio.fixture(autouse=True)
async def clean_database(test_session: AsyncSession):
    """Clean database before each test."""
    # This runs before each test
    yield

    # This runs after each test
    try:
        # Clean up any remaining data
        for table in reversed(BaseModel.metadata.sorted_tables):
            await test_session.execute(text(f"TRUNCATE TABLE {table.name} CASCADE"))
        await test_session.commit()
    except Exception:
        await test_session.rollback()
