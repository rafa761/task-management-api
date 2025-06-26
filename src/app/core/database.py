# app/core/database.py
import asyncio
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, QueuePool

from app.core.config import settings
from app.models import BaseModel

logger = logging.getLogger(__name__)


class DatabaseConfig:
    """Database configuration and connection management"""

    def __init__(self):
        self.engine: AsyncEngine | None = None
        self.session_factory: async_sessionmaker[AsyncSession] | None = None

    def create_engine(
        self, database_url: str | None = None, echo: bool = False
    ) -> AsyncEngine:
        """
        Create database engine with optimized connection pooling.

        Args:
            database_url: Database connection URL. Uses settings if not provided.
            echo: Whether to log SQL statements (useful for debugging).

        Returns:
            Configured async SQLAlchemy engine.
        """
        if not database_url:
            database_url = settings.database_url

        # Base engine configuration
        engine_kwargs = {
            "echo": echo or settings.DEBUG,
            "pool_pre_ping": True,  # Validate connections before use
            "pool_recycle": 3600,  # Recycle connections every hour
            "connect_args": {
                "server_settings": {
                    "application_name": "task_management_api",
                }
            },
        }

        # Add pool configuration based on environment
        if settings.is_production:
            engine_kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": 10,
                    "max_overflow": 20,
                }
            )
        else:
            engine_kwargs["poolclass"] = NullPool

        engine = create_async_engine(database_url, **engine_kwargs)

        self.engine = engine
        logger.info(f"Database engine created for environment: {settings.ENVIRONMENT}")
        return engine

    def create_session_factory(
        self, engine: AsyncEngine | None = None
    ) -> async_sessionmaker[AsyncSession]:
        """
        Create session factory for database operations.

        Args:
            engine: Database engine. Uses existing engine if not provided.

        Returns:
            Session factory for creating database sessions.
        """
        if not engine and not self.engine:
            self.create_engine()

        target_engine = engine or self.engine

        if not target_engine:
            raise RuntimeError("No database engine available for session factory")

        session_factory = async_sessionmaker(
            target_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )

        self.session_factory = session_factory
        logger.info("Database session factory created successfully")
        return session_factory

    async def initialize_database(self, drop_existing: bool = False) -> None:
        """
        Initialize database schema.

        Args:
            drop_existing: Whether to drop existing tables first.
        """
        if not self.engine:
            self.create_engine()

        async with self.engine.begin() as conn:
            if drop_existing:
                logger.warning("Dropping existing database tables")
                await conn.run_sync(BaseModel.metadata.drop_all)

            logger.info("Creating database tables")
            await conn.run_sync(BaseModel.metadata.create_all)

    async def close(self) -> None:
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Global database instance
db_config = DatabaseConfig()


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """
    Async context manager for database sessions.

    Provides proper session lifecycle management with automatic cleanup.
    Use this in dependency injection for FastAPI endpoints.
    """
    if not db_config.session_factory:
        raise RuntimeError("Database session factory not initialized.")

    async with db_config.session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    FastAPI dependency for database sessions.
    """
    async with get_db_session() as session:
        yield session


async def check_database_health() -> dict[str, Any]:
    """
    Check database connectivity and health.

    Returns:
        Dictionary with health status information.
    """
    try:
        # Verify that we have an engine
        if not db_config.engine:
            return {
                "status": "unhealthy",
                "database": "error",
                "message": "Database engine not initialized",
            }

        # Verify that we have a session factory
        if not db_config.session_factory:
            return {
                "status": "unhealthy",
                "database": "error",
                "message": "Database session factory not initialized",
            }

        # Test database connectivity
        async with get_db_session() as session:
            # Simple query to test connectivity
            result = await session.execute(text("SELECT 1 as health_check"))
            health_value = result.scalar()

            if health_value != 1:
                return {
                    "status": "unhealthy",
                    "database": "error",
                    "message": "Database query returned unexpected result",
                }

        return {
            "status": "healthy",
            "database": "connected",
            "message": "Database is accessible",
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "database": "error",
            "message": f"Database connection failed: {e!s}",
        }


async def wait_for_database(max_retries: int = 5, retry_interval: float = 5.0) -> None:
    """
    Wait for database to become available with retry logic.

    Args:
        max_retries: Maximum number of connection attempts
        retry_interval: Time to wait between attempts in seconds

    Raises:
        RuntimeError: If database is not available after max_retries
    """
    logger.info("Waiting for database to become available...")

    for attempt in range(1, max_retries + 1):
        try:
            health_status = await check_database_health()
            if health_status["status"] == "healthy":
                logger.info(f"Database is ready after {attempt} attempt(s)")
                return

        except Exception as e:
            logger.debug(f"Database connection attempt {attempt} failed: {e}")

        if attempt < max_retries:
            logger.info(
                f"Database not ready, retrying in {retry_interval}s... (attempt {attempt}/{max_retries})"
            )
            await asyncio.sleep(retry_interval)
        else:
            logger.error(
                f"Database failed to become available after {max_retries} attempts"
            )

    raise RuntimeError(f"Database is not available after {max_retries} attempts")


@asynccontextmanager
async def database_lifespan():
    """
    Application lifespan context manager for database with retry logic.
    """
    # Startup
    logger.info("Initializing database connection")

    try:
        # Create engine
        db_config.create_engine()
        logger.info("Database engine created successfully")

        # Create session factory
        db_config.create_session_factory()
        logger.info("Database session factory created successfully")

        # Wait for database to be ready with retry logic
        await wait_for_database(max_retries=5, retry_interval=5.0)

        logger.info("Database initialized successfully")

        yield

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        raise
    finally:
        # Shutdown
        logger.info("Closing database connections")
        await db_config.close()
