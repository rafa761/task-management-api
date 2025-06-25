# app/core/database.py
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

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
                    "jit": "off",  # Disable JIT for predictable performance
                }
            },
        }

        # Add pool configuration based on environment
        if settings.is_production:
            engine_kwargs.update(
                {
                    "poolclass": QueuePool,
                    "pool_size": 20,
                    "max_overflow": 30,
                }
            )
        else:
            engine_kwargs["poolclass"] = (
                NullPool  # For development/testing - only set poolclass, no pool size params
            )

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

        session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,  # Keep objects usable after commit
            autoflush=True,  # Auto-flush changes before queries
            autocommit=False,  # Explicit transaction control
        )

        self.session_factory = session_factory
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

    Example:
        async with get_db_session() as session:
            result = await session.execute(query)
            await session.commit()
    """
    if not db_config.session_factory:
        db_config.create_session_factory()

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

    This function is used as a dependency in FastAPI route handlers
    to provide database session instances.

    Example:
        @app.get("/users/")
        async def list_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with get_db_session() as session:
        yield session


async def check_database_health() -> dict[str, str]:
    """
    Check database connectivity and health.

    Returns:
        Dictionary with health status information.
    """
    try:
        async with get_db_session() as session:
            # Simple query to test connectivity
            result = await session.execute("SELECT 1")
            result.scalar()

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


# Database lifecycle management for FastAPI application
@asynccontextmanager
async def database_lifespan():
    """
    Application lifespan context manager for database.

    Handles database initialization on startup and cleanup on shutdown.
    Use this in FastAPI lifespan events.
    """
    # Startup
    logger.info("Initializing database connection")
    db_config.create_engine()
    db_config.create_session_factory()

    # Verify database connectivity
    health_status = await check_database_health()
    if health_status["status"] != "healthy":
        raise RuntimeError(
            f"Database initialization failed: {health_status['message']}"
        )

    logger.info("Database initialized successfully")

    try:
        yield
    finally:
        # Shutdown
        logger.info("Closing database connections")
        await db_config.close()


# Utility functions for testing and development
async def create_test_database() -> None:
    """Create database schema for testing."""
    test_engine = create_async_engine(
        settings.test_database_url,
        echo=False,
        pool_class=NullPool,  # No connection pooling for tests
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    await test_engine.dispose()


async def drop_test_database() -> None:
    """Drop test database schema."""
    test_engine = create_async_engine(
        settings.test_database_url,
        echo=False,
        pool_class=NullPool,
    )

    async with test_engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)

    await test_engine.dispose()
