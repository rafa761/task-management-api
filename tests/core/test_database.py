# tests/core/test_database.py
"""
Database Tests

Simple tests for database configuration and utility functions.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.pool import NullPool, QueuePool

from app.core.database import (
    DatabaseConfig,
    check_database_health,
    create_test_database,
    database_lifespan,
    db_config,
    drop_test_database,
)


class TestDatabaseConfig:
    """Test DatabaseConfig class"""

    def test_database_config_initialization(self):
        """Test DatabaseConfig initializes with None values"""
        config = DatabaseConfig()
        assert config.engine is None
        assert config.session_factory is None

    @patch("app.core.database.create_async_engine")
    def test_create_engine_development(self, mock_create_engine):
        """Test engine creation for development environment"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()

        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://user:pass@localhost/db"
            mock_settings.DEBUG = True
            mock_settings.is_production = False
            mock_settings.ENVIRONMENT = "development"

            result = config.create_engine()

            mock_create_engine.assert_called_once()
            args, kwargs = mock_create_engine.call_args

            assert args[0] == "postgresql+asyncpg://user:pass@localhost/db"
            assert kwargs["echo"] is True
            assert kwargs["poolclass"] == NullPool
            assert result == mock_engine

    @patch("app.core.database.create_async_engine")
    def test_create_engine_production(self, mock_create_engine):
        """Test engine creation for production environment"""
        mock_engine = MagicMock()
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig()

        with patch("app.core.database.settings") as mock_settings:
            mock_settings.database_url = "postgresql+asyncpg://user:pass@prod-host/db"
            mock_settings.DEBUG = False
            mock_settings.is_production = True
            mock_settings.ENVIRONMENT = "production"

            config.create_engine()

            args, kwargs = mock_create_engine.call_args
            assert kwargs["echo"] is False
            assert kwargs["poolclass"] == QueuePool
            assert kwargs["pool_size"] == 20
            assert kwargs["max_overflow"] == 30

    @patch("app.core.database.async_sessionmaker")
    def test_create_session_factory(self, mock_sessionmaker):
        """Test session factory creation"""
        mock_engine = MagicMock()
        mock_factory = MagicMock()
        mock_sessionmaker.return_value = mock_factory

        config = DatabaseConfig()
        result = config.create_session_factory(engine=mock_engine)

        mock_sessionmaker.assert_called_once_with(
            mock_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=True,
            autocommit=False,
        )
        assert result == mock_factory
        assert config.session_factory == mock_factory

    async def test_close_disposes_engine(self):
        """Test close method disposes engine"""
        config = DatabaseConfig()
        mock_engine = AsyncMock()
        config.engine = mock_engine

        await config.close()
        mock_engine.dispose.assert_called_once()

    async def test_close_handles_no_engine(self):
        """Test close method handles case where no engine exists"""
        config = DatabaseConfig()
        # Should not raise an exception
        await config.close()


class TestDatabaseUtilities:
    """Test database utility functions"""

    async def test_check_database_health_success(self):
        """Test database health check returns success"""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar.return_value = 1
        mock_session.execute.return_value = mock_result

        with patch("app.core.database.get_db_session") as mock_get_session:
            mock_get_session.return_value.__aenter__.return_value = mock_session
            mock_get_session.return_value.__aexit__.return_value = None

            result = await check_database_health()

            assert result["status"] == "healthy"
            assert result["database"] == "connected"
            assert "Database is accessible" in result["message"]

    async def test_check_database_health_failure(self):
        """Test database health check returns failure on exception"""
        with patch("app.core.database.get_db_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Connection failed")

            result = await check_database_health()

            assert result["status"] == "unhealthy"
            assert result["database"] == "error"
            assert "Connection failed" in result["message"]


class TestDatabaseLifespan:
    """Test database lifespan management"""

    async def test_database_lifespan_success(self):
        """Test successful database lifespan management"""
        with (
            patch("app.core.database.db_config") as mock_db_config,
            patch("app.core.database.check_database_health") as mock_health_check,
        ):
            # Mock all the methods to avoid attribute errors
            mock_db_config.create_engine = MagicMock()
            mock_db_config.create_session_factory = MagicMock()
            mock_db_config.close = AsyncMock()
            mock_health_check.return_value = {"status": "healthy"}

            async with database_lifespan():
                mock_db_config.create_engine.assert_called_once()
                mock_db_config.create_session_factory.assert_called_once()
                mock_health_check.assert_called_once()

            mock_db_config.close.assert_called_once()

    async def test_database_lifespan_health_check_failure(self):
        """Test database lifespan raises error on health check failure"""
        with (
            patch("app.core.database.db_config") as mock_db_config,
            patch("app.core.database.check_database_health") as mock_health_check,
        ):
            # Mock methods to avoid attribute errors
            mock_db_config.create_engine = MagicMock()
            mock_db_config.create_session_factory = MagicMock()
            mock_health_check.return_value = {
                "status": "unhealthy",
                "message": "Database connection failed",
            }

            with pytest.raises(RuntimeError) as exc_info:
                async with database_lifespan():
                    pass

            assert "Database initialization failed" in str(exc_info.value)


class TestDatabaseTestUtilities:
    """Test database test utility functions exist and are callable"""

    def test_create_test_database_exists(self):
        """Test create_test_database function exists and is callable"""
        assert callable(create_test_database)

    def test_drop_test_database_exists(self):
        """Test drop_test_database function exists and is callable"""
        assert callable(drop_test_database)


class TestGlobalDatabaseConfig:
    """Test the global db_config instance"""

    def test_global_db_config_exists(self):
        """Test that global db_config instance exists"""
        assert db_config is not None
        assert isinstance(db_config, DatabaseConfig)
