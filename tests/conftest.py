# tests/conftest.py
import asyncio
from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import get_db
from app.core.factory import create_app
from app.models.base import BaseModel

settings = get_settings()

# Test database engine
test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,
    pool_class=NullPool,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Setup test database."""
    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Create a test database session."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        yield session
        await session.rollback()


@pytest.fixture
def app(db_session: AsyncSession) -> FastAPI:
    """Create test FastAPI application."""
    test_app = create_app()

    # Override database dependency
    async def override_get_db():
        yield db_session

    test_app.dependency_overrides[get_db] = override_get_db

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)
