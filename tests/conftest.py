# tests/conftest.py
import asyncio
import logging
from collections.abc import AsyncGenerator

import asyncpg
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.database import get_db
from app.core.factory import create_app
from app.models.base import BaseModel

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

# Test database engine
test_engine = create_async_engine(
    settings.test_database_url,
    echo=False,
    poolclass=NullPool,
)


async def create_test_database_if_not_exists() -> None:
    """Create the test database"""
    test_db_name = settings.POSTGRES_DB + "_test"

    # URL para conectar ao banco postgres padrão (para criar outros bancos)
    admin_url = (
        f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"
    )

    conn = None
    try:
        conn = await asyncpg.connect(admin_url)

        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", test_db_name
        )

        if not result:
            logger.info(f"Creating the test database: {test_db_name}")
            await conn.execute(f'CREATE DATABASE "{test_db_name}"')
            logger.info(f"Test database created: {test_db_name}")
        else:
            logger.info(f"Test database already exists: {test_db_name}")

    except asyncpg.exceptions.DuplicateDatabaseError:
        logger.info(f"Test database already exists: {test_db_name}")
    except Exception as e:
        logger.error(f"Error creating test database: {e}")
        raise
    finally:
        if conn:
            await conn.close()


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Setup test database."""
    await create_test_database_if_not_exists()

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    try:
        await test_engine.dispose()

    except Exception as e:
        logger.warning(f"Erro durante cleanup: {e}")


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession]:
    """Create a test database session."""
    async with AsyncSession(test_engine, expire_on_commit=False) as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            await transaction.rollback()


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
