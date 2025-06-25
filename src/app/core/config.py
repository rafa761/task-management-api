# app/core/config.py
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """

    # Application Settings
    ENVIRONMENT: str = Field(
        default="development",
        description="Application environment (development, staging, production)",
    )
    DEBUG: bool = Field(default=True, description="Enable debug mode")
    HOST: str = Field(default="127.0.0.1", description="Application host")
    PORT: int = Field(default=8000, description="Application port")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")

    # Security Settings
    ALLOWED_HOSTS: str = Field(
        default="localhost,127.0.0.1",
        description="Comma-separated list of allowed hosts",
    )
    ALLOWED_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins",
    )

    # Database Configuration
    DATABASE_URL: str | None = Field(
        default=None, description="Full database connection URL"
    )
    TEST_DATABASE_URL: str | None = Field(
        default=None, description="Test database connection URL"
    )

    # Individual database components (fallback if DATABASE_URL not provided)
    POSTGRES_HOST: str = Field(default="localhost", description="PostgreSQL host")
    POSTGRES_PORT: int = Field(default=5432, description="PostgreSQL port")
    POSTGRES_USER: str = Field(default="postgres", description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(
        default="postgres", description="PostgreSQL password"
    )
    POSTGRES_DB: str = Field(
        default="task_management_db", description="PostgreSQL database name"
    )

    # JWT Configuration
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="Secret key for JWT token generation",
    )
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30, description="Access token expiration time in minutes"
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=7, description="Refresh token expiration time in days"
    )

    # AWS Configuration
    AWS_REGION: str = Field(default="us-east-1", description="AWS region")
    AWS_ACCESS_KEY_ID: str | None = Field(default=None, description="AWS access key ID")
    AWS_SECRET_ACCESS_KEY: str | None = Field(
        default=None, description="AWS secret access key"
    )

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Ensure environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        if value not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return value

    @property
    def allowed_hosts_list(self) -> list[str]:
        """Convert ALLOWED_HOSTS string to list."""
        return [host.strip() for host in self.ALLOWED_HOSTS.split(",") if host.strip()]

    @property
    def allowed_origins_list(self) -> list[str]:
        """Convert ALLOWED_ORIGINS string to list."""
        return [
            origin.strip()
            for origin in self.ALLOWED_ORIGINS.split(",")
            if origin.strip()
        ]

    @property
    def database_url(self) -> str:
        """
        Get database URL. Use DATABASE_URL if provided, otherwise construct from components.
        """
        if self.DATABASE_URL:
            return self.DATABASE_URL

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def test_database_url(self) -> str:
        """
        Get test database URL. Use TEST_DATABASE_URL if provided, otherwise construct from components.
        """
        if self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL

        test_db_name = (
            f"{self.POSTGRES_DB}_test"
            if not self.POSTGRES_DB.endswith("_test")
            else self.POSTGRES_DB
        )

        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{test_db_name}"
        )

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_staging(self) -> bool:
        return self.ENVIRONMENT == "staging"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """
    Create and cache settings instance.

    :return: Settings instance.
    """
    return Settings()


settings = get_settings()
