# app/core/config.py
from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings


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
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1"]
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8080"]

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

    @field_validator("ALLOWED_HOSTS", "ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_comma_separated_string(cls, value: str | list[str]) -> list[str]:
        """Parse comma-separated string into list"""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        if (
            self.ENVIRONMENT == "production"
            and self.SECRET_KEY == "your-secret-key-change-in-production"
        ):
            raise ValueError("SECRET_KEY must be changed in production")
        return self

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore",
    }


@lru_cache
def get_settings() -> Settings:
    """
    Create and cache settings instance.

    :return: Settings instance.
    """
    return Settings()


settings = get_settings()
