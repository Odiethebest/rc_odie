"""Application settings loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration shared by the API, worker, and migrations."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Reliable HTTP Notification Service"
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notification_service"
    database_echo: bool = False
    worker_poll_interval_seconds: float = Field(default=1.0, gt=0)
    worker_batch_size: int = Field(default=10, ge=1, le=100)
    worker_lease_seconds: int = Field(default=60, ge=15)


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for the current process."""

    return Settings()
