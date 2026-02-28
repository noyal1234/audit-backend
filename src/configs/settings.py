from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with env prefix."""

    PREFIX: str = "APP"

    # App
    app_name: str = Field(default="Dealer Hygiene Compliance Backend", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    environment: str = Field(default="development", description="Environment name")

    # PostgreSQL
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="audit_db", description="PostgreSQL database name")
    postgres_user: str = Field(default="postgres", description="PostgreSQL user")
    postgres_password: str = Field(default="", description="PostgreSQL password")

    # JWT
    jwt_secret_key: str = Field(default="change-me-in-production", description="JWT signing secret")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_expire_minutes: int = Field(default=60, description="Access token expiry minutes")
    jwt_refresh_expire_days: int = Field(default=7, description="Refresh token expiry days")

    # Storage (local path for image uploads)
    storage_path: str = Field(default="./uploads", description="Local storage path for uploads")

    # CORS (comma-separated origins, or "*" for all)
    cors_origins: str = Field(default="*", description="Allowed CORS origins")

    model_config = {"env_prefix": "APP_", "extra": "ignore", "env_file": ".env"}


_instance: Settings | None = None


def get_instance() -> Settings:
    """Return singleton settings instance."""
    global _instance
    if _instance is None:
        _instance = Settings()
    return _instance


@lru_cache
def get_settings() -> Settings:
    """Cached getter for dependency injection."""
    return get_instance()
