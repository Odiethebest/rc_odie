"""Tests for environment-based application settings."""

from app.config import Settings


def test_settings_reads_environment_variables(monkeypatch) -> None:
    """Environment variables should override development defaults."""

    monkeypatch.setenv("APP_NAME", "Test Notification Service")
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://test:test@localhost:5432/test_notifications",
    )
    monkeypatch.setenv("WORKER_POLL_INTERVAL_SECONDS", "2.5")
    monkeypatch.setenv("WORKER_BATCH_SIZE", "20")
    monkeypatch.setenv("WORKER_LEASE_SECONDS", "90")

    settings = Settings(_env_file=None)

    assert settings.app_name == "Test Notification Service"
    assert settings.database_url.endswith("/test_notifications")
    assert settings.worker_poll_interval_seconds == 2.5
    assert settings.worker_batch_size == 20
    assert settings.worker_lease_seconds == 90
