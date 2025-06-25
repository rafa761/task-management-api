# tests/conftest.py
"""
Test configuration for Task Management API.

Simple setup with SQLite in-memory database for fast, isolated tests.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models import BaseModel


@pytest_asyncio.fixture
async def db_session():
    """
    Create an in-memory SQLite database session for testing.

    Each test gets a fresh database with all tables created.
    Tests are isolated - no cleanup needed between tests.
    """
    # Create in-memory SQLite database
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    # Create session factory
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    # Provide session for test
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def sample_user_data():
    """Sample user data for tests."""
    return {
        "email": "test@example.com",
        "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBkpx5NNOp7QUW",
        "first_name": "Meg",
        "last_name": "Ferreira",
        "timezone": "UTC",
        "is_active": True,
        "is_verified": True,
    }
