# tests/core/test_config.py
"""
Configuration Tests

Tests the Settings class behavior including validation, properties, and environment handling.
"""

import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings


class TestSettingsValidation:
    """Test Settings class validation logic"""

    def test_valid_environment_values(self):
        """Test that valid environment values are accepted"""
        for env in ["development", "staging", "production"]:
            settings = Settings(ENVIRONMENT=env)
            assert settings.ENVIRONMENT == env

    def test_invalid_environment_value_raises_error(self):
        """Test that invalid environment values raise ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            Settings(ENVIRONMENT="invalid")

        assert "Environment must be one of" in str(exc_info.value)

    def test_production_allows_custom_secret_key(self):
        """Test that production works with custom secret key"""
        settings = Settings(
            ENVIRONMENT="production", SECRET_KEY="custom-production-secret-key"
        )
        assert settings.ENVIRONMENT == "production"
        assert settings.SECRET_KEY == "custom-production-secret-key"

    def test_non_production_allows_default_secret_key(self):
        """Test that non-production environments allow default secret key"""
        for env in ["development", "staging"]:
            settings = Settings(
                ENVIRONMENT=env, SECRET_KEY="your-secret-key-change-in-production"
            )
            assert settings.ENVIRONMENT == env


class TestSettingsProperties:
    """Test Settings class property methods"""

    def test_allowed_hosts_list_property(self):
        """Test allowed_hosts_list converts string to list correctly"""
        settings = Settings(ALLOWED_HOSTS="localhost,127.0.0.1,example.com")
        expected = ["localhost", "127.0.0.1", "example.com"]
        assert settings.allowed_hosts_list == expected

    def test_allowed_hosts_list_handles_whitespace(self):
        """Test allowed_hosts_list handles whitespace correctly"""
        settings = Settings(ALLOWED_HOSTS=" localhost , 127.0.0.1 , example.com ")
        expected = ["localhost", "127.0.0.1", "example.com"]
        assert settings.allowed_hosts_list == expected

    def test_allowed_hosts_list_filters_empty_strings(self):
        """Test allowed_hosts_list filters out empty strings"""
        settings = Settings(ALLOWED_HOSTS="localhost,,127.0.0.1,")
        expected = ["localhost", "127.0.0.1"]
        assert settings.allowed_hosts_list == expected

    def test_allowed_origins_list_property(self):
        """Test allowed_origins_list converts string to list correctly"""
        settings = Settings(
            ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8080,https://app.example.com"
        )
        expected = [
            "http://localhost:3000",
            "http://localhost:8080",
            "https://app.example.com",
        ]
        assert settings.allowed_origins_list == expected

    def test_allowed_origins_list_handles_whitespace(self):
        """Test allowed_origins_list handles whitespace correctly"""
        settings = Settings(
            ALLOWED_ORIGINS=" http://localhost:3000 , http://localhost:8080 "
        )
        expected = ["http://localhost:3000", "http://localhost:8080"]
        assert settings.allowed_origins_list == expected

    def test_database_url_uses_provided_url(self):
        """Test database_url property returns provided DATABASE_URL when set"""
        custom_url = "postgresql+asyncpg://user:pass@custom-host:5432/custom_db"
        settings = Settings(DATABASE_URL=custom_url)
        assert settings.database_url == custom_url

    def test_database_url_constructs_from_components(self):
        """Test database_url property constructs URL from individual components"""
        settings = Settings(
            DATABASE_URL=None,  # Force construction
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="testhost",
            POSTGRES_PORT=5433,
            POSTGRES_DB="testdb",
        )
        expected = "postgresql+asyncpg://testuser:testpass@testhost:5433/testdb"
        assert settings.database_url == expected

    def test_test_database_url_uses_provided_url(self):
        """Test test_database_url property returns provided TEST_DATABASE_URL when set"""
        custom_test_url = "postgresql+asyncpg://user:pass@test-host:5432/test_db"
        settings = Settings(TEST_DATABASE_URL=custom_test_url)
        assert settings.test_database_url == custom_test_url

    def test_test_database_url_constructs_from_components(self):
        """Test test_database_url property constructs URL from components"""
        settings = Settings(
            TEST_DATABASE_URL=None,  # Force construction
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="testhost",
            POSTGRES_PORT=5433,
            POSTGRES_DB="myapp_db",
        )
        expected = "postgresql+asyncpg://testuser:testpass@testhost:5433/myapp_db_test"
        assert settings.test_database_url == expected

    def test_test_database_url_handles_existing_test_suffix(self):
        """Test test_database_url doesn't double-add _test suffix"""
        settings = Settings(
            TEST_DATABASE_URL=None,
            POSTGRES_USER="testuser",
            POSTGRES_PASSWORD="testpass",
            POSTGRES_HOST="testhost",
            POSTGRES_PORT=5433,
            POSTGRES_DB="myapp_db_test",  # Already has _test suffix
        )
        expected = "postgresql+asyncpg://testuser:testpass@testhost:5433/myapp_db_test"
        assert settings.test_database_url == expected


class TestSettingsEnvironmentDetection:
    """Test Settings environment detection properties"""

    def test_is_production_property(self):
        """Test is_production property returns correct boolean"""
        prod_settings = Settings(ENVIRONMENT="production", SECRET_KEY="custom-key")
        dev_settings = Settings(ENVIRONMENT="development")

        assert prod_settings.is_production is True
        assert dev_settings.is_production is False

    def test_is_staging_property(self):
        """Test is_staging property returns correct boolean"""
        staging_settings = Settings(ENVIRONMENT="staging")
        dev_settings = Settings(ENVIRONMENT="development")

        assert staging_settings.is_staging is True
        assert dev_settings.is_staging is False

    def test_is_development_property(self):
        """Test is_development property returns correct boolean"""
        dev_settings = Settings(ENVIRONMENT="development")
        prod_settings = Settings(ENVIRONMENT="production", SECRET_KEY="custom-key")

        assert dev_settings.is_development is True
        assert prod_settings.is_development is False


class TestSettingsDefaults:
    """Test Settings default values"""

    def test_application_defaults(self):
        """Test application setting defaults"""
        settings = Settings()

        assert settings.ENVIRONMENT == "development"
        assert settings.DEBUG is True
        assert settings.HOST == "127.0.0.1"
        assert settings.PORT == 8000
        assert settings.LOG_LEVEL == "INFO"

    def test_security_defaults(self):
        """Test security setting defaults"""
        settings = Settings()

        assert "localhost" in settings.ALLOWED_HOSTS
        assert "127.0.0.1" in settings.ALLOWED_HOSTS
        assert "http://localhost:3000" in settings.ALLOWED_ORIGINS

    def test_database_defaults(self):
        """Test database setting defaults"""
        settings = Settings()

        assert settings.POSTGRES_HOST == "localhost"
        assert settings.POSTGRES_PORT == 5432
        assert settings.POSTGRES_USER == "postgres"
        assert settings.POSTGRES_PASSWORD == "postgres"
        assert settings.POSTGRES_DB == "task_management_db"

    def test_jwt_defaults(self):
        """Test JWT configuration defaults"""
        settings = Settings()

        assert settings.SECRET_KEY == "your-secret-key-change-in-production"
        assert settings.ALGORITHM == "HS256"
        assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert settings.REFRESH_TOKEN_EXPIRE_DAYS == 7

    def test_aws_defaults(self):
        """Test AWS configuration defaults"""
        settings = Settings()

        assert settings.AWS_REGION == "us-east-1"
        assert settings.AWS_ACCESS_KEY_ID is None
        assert settings.AWS_SECRET_ACCESS_KEY is None


class TestGetSettingsFunction:
    """Test get_settings function behavior"""

    def test_get_settings_returns_settings_instance(self):
        """Test get_settings returns a Settings instance"""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_get_settings_caching(self):
        """Test get_settings returns the same instance (caching)"""
        settings1 = get_settings()
        settings2 = get_settings()
        assert settings1 is settings2  # Same object reference

    def test_get_settings_with_environment_variables(self, monkeypatch):
        """Test get_settings respects environment variables"""
        # Set environment variable
        monkeypatch.setenv("ENVIRONMENT", "staging")
        monkeypatch.setenv("PORT", "9000")

        # Clear the cache by calling get_settings.__wrapped__() directly
        settings = get_settings.__wrapped__()

        assert settings.ENVIRONMENT == "staging"
        assert settings.PORT == 9000


class TestSettingsValidationEdgeCases:
    """Test edge cases and error conditions"""

    def test_invalid_port_type(self):
        """Test that invalid port type raises ValidationError"""
        with pytest.raises(ValidationError):
            Settings(PORT="not-a-number")

    def test_invalid_boolean_type(self):
        """Test that invalid boolean type raises ValidationError"""
        with pytest.raises(ValidationError):
            Settings(DEBUG="not-a-boolean")

    def test_empty_required_string_fields(self):
        """Test behavior with empty string fields"""
        # These should work - empty strings are valid for optional fields
        settings = Settings(ALLOWED_HOSTS="", ALLOWED_ORIGINS="")
        assert settings.allowed_hosts_list == []
        assert settings.allowed_origins_list == []

    def test_very_long_string_fields(self):
        """Test behavior with very long string values"""
        long_string = "x" * 1000
        settings = Settings(POSTGRES_HOST=long_string, POSTGRES_DB=long_string)
        assert settings.POSTGRES_HOST == long_string
        assert settings.POSTGRES_DB == long_string

    def test_special_characters_in_database_credentials(self):
        """Test special characters in database credentials"""
        settings = Settings(
            POSTGRES_USER="user@domain.com",
            POSTGRES_PASSWORD="pa$$w0rd!@#$%^&*()",
            POSTGRES_DB="my-app_db.test",
        )
        # URL should be constructed correctly
        url = settings.database_url
        assert "user@domain.com" in url
        assert "pa$$w0rd!@#$%^&*()" in url
        assert "my-app_db.test" in url


class TestSettingsIntegrationWithEnvironment:
    """Test Settings integration with actual environment variables"""

    def test_env_file_loading(self, tmp_path, monkeypatch):
        """Test that Settings loads from .env file"""
        # Create temporary .env file
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ENVIRONMENT=staging\nPORT=9999\nSECRET_KEY=test-secret-key\n"
        )

        # Change to temp directory so .env is found
        monkeypatch.chdir(tmp_path)

        # Create new settings instance (bypass cache)
        settings = Settings()

        assert settings.ENVIRONMENT == "staging"
        assert settings.PORT == 9999
        assert settings.SECRET_KEY == "test-secret-key"

    def test_environment_variables_override_defaults(self, monkeypatch):
        """Test that environment variables override defaults"""
        monkeypatch.setenv("HOST", "0.0.0.0")
        monkeypatch.setenv("DEBUG", "false")
        monkeypatch.setenv("POSTGRES_PORT", "5433")

        settings = Settings()

        assert settings.HOST == "0.0.0.0"
        assert settings.DEBUG is False
        assert settings.POSTGRES_PORT == 5433

    def test_case_sensitivity(self, monkeypatch):
        """Test that environment variables are case sensitive"""
        # Set lowercase variable (should not be picked up)
        monkeypatch.setenv("environment", "production")
        monkeypatch.setenv("ENVIRONMENT", "staging")

        settings = Settings()

        # Should use the uppercase version
        assert settings.ENVIRONMENT == "staging"
