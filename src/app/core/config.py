# app/core/config.py
from functools import lru_cache

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings with environment variable support.
    """

    # Application Settings
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Security Settings
    ALLOWED_HOSTS: str = Field(default="localhost,127.0.0.1")
    ALLOWED_ORIGINS: str = Field(default="http://localhost:3000,http://localhost:8080")

    # Database Configuration
    DATABASE_URL: str | None = None

    # JWT Configuration (we'll use this for authentication)
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        """Ensure environment is one of the allowed values."""
        allowed = ["development", "staging", "production"]
        if value not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if (
            self.ENVIRONMENT == "production"
            and self.SECRET_KEY == "your-secret-key-change-in-production"
        ):
            raise ValueError("SECRET_KEY must be changed in production")
        return self

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
