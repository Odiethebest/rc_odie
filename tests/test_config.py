"""Tests for environment-based application settings."""

from app.config import Settings


def test_settings_reads_environment_variables(monkeypatch) -> None:
    """Environment variables should override development defaults."""

    monkeypatch.setenv("APP_NAME", "Test Notification Service")
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:5432/test_notifications",
    )
    monkeypatch.setenv("DATABASE_ECHO", "true")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Notification Service"
    assert settings.environment == "test"
    assert settings.database_url.endswith("/test_notifications")
    assert settings.database_echo is True
