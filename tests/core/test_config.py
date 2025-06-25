# tests/core/test_config.py
"""
Configuration Tests - Focused on Custom Logic

Only tests custom business logic and validation that we added beyond Pydantic's built-in capabilities.
Pydantic already guarantees field types, required fields, env loading, etc.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestCustomValidationLogic:
    """Test our custom validation logic (not Pydantic's built-in validation)"""

    def test_invalid_environment_value_raises_error(self):
        """Test our custom environment validator"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="invalid")

        assert "Environment must be one of" in str(exc_info.value)

    def test_production_allows_custom_secret_key(self):
        """Test production works with custom secret key"""
        settings = Settings(
            ENVIRONMENT="production", SECRET_KEY="custom-production-secret-key"
        )
        assert settings.ENVIRONMENT == "production"


class TestCustomPropertyMethods:
    """Test our custom property methods (business logic we added)"""

    def test_allowed_hosts_list_parsing(self):
        """Test our custom list parsing logic"""
        settings = Settings(ALLOWED_HOSTS="localhost, 127.0.0.1 , example.com,")
        expected = ["localhost", "127.0.0.1", "example.com"]
        assert settings.allowed_hosts_list == expected

    def test_allowed_origins_list_parsing(self):
        """Test our custom origins list parsing"""
        settings = Settings(
            ALLOWED_ORIGINS=" http://localhost:3000 , , http://localhost:8080"
        )
        expected = ["http://localhost:3000", "http://localhost:8080"]
        assert settings.allowed_origins_list == expected

    def test_database_url_construction_from_components(self):
        """Test our custom database URL construction logic"""
        settings = Settings(
            DATABASE_URL=None,  # Force construction
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_HOST="host",
            POSTGRES_PORT=5433,
            POSTGRES_DB="mydb",
        )
        expected = "postgresql+asyncpg://user:pass@host:5433/mydb"
        assert settings.database_url == expected

    def test_test_database_url_construction(self):
        """Test our custom test database URL construction logic"""
        settings = Settings(
            TEST_DATABASE_URL=None,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_HOST="host",
            POSTGRES_PORT=5432,
            POSTGRES_DB="myapp_db",
        )
        expected = "postgresql+asyncpg://user:pass@host:5432/myapp_db_test"
        assert settings.test_database_url == expected

    def test_test_database_url_handles_existing_test_suffix(self):
        """Test our logic doesn't double-add _test suffix"""
        settings = Settings(
            TEST_DATABASE_URL=None,
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_HOST="host",
            POSTGRES_PORT=5432,
            POSTGRES_DB="myapp_db_test",  # Already has _test
        )
        expected = "postgresql+asyncpg://user:pass@host:5432/myapp_db_test"
        assert settings.test_database_url == expected

    def test_environment_detection_properties(self):
        """Test our custom environment detection properties"""
        prod_settings = Settings(ENVIRONMENT="production", SECRET_KEY="custom-key")
        dev_settings = Settings(ENVIRONMENT="development")
        staging_settings = Settings(ENVIRONMENT="staging")

        assert prod_settings.is_production is True
        assert prod_settings.is_development is False
        assert prod_settings.is_staging is False

        assert dev_settings.is_development is True
        assert dev_settings.is_production is False

        assert staging_settings.is_staging is True


class TestGetSettingsFunction:
    """Test our custom get_settings function (caching behavior)"""

    def test_get_settings_caching(self):
        """Test our LRU cache implementation works"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2  # Same object reference due to caching


class TestCriticalConfigurationScenarios:
    """Test critical configuration scenarios that could break the app"""

    def test_database_url_precedence(self):
        """Test that explicit DATABASE_URL takes precedence over components"""
        explicit_url = (
            "postgresql+asyncpg://explicit:url@explicit-host:5432/explicit_db"
        )
        settings = Settings(
            DATABASE_URL=explicit_url,
            POSTGRES_USER="component_user",  # Should be ignored
            POSTGRES_HOST="component_host",  # Should be ignored
        )
        assert settings.database_url == explicit_url

    def test_empty_list_handling(self):
        """Test our list parsing handles empty strings correctly"""
        settings = Settings(ALLOWED_HOSTS="", ALLOWED_ORIGINS="")
        assert settings.allowed_hosts_list == []
        assert settings.allowed_origins_list == []

    def test_special_characters_in_database_credentials(self):
        """Test URL construction handles special characters"""
        settings = Settings(
            DATABASE_URL=None,
            POSTGRES_USER="user@domain.com",
            POSTGRES_PASSWORD="pa$$w0rd!@#",
            POSTGRES_HOST="host",
            POSTGRES_PORT=5432,
            POSTGRES_DB="my-db",
        )
        url = settings.database_url
        # Just verify the URL contains our values (URL encoding is SQLAlchemy's job)
        assert "user@domain.com" in url
        assert "pa$$w0rd!@#" in url
        assert "my-db" in url
