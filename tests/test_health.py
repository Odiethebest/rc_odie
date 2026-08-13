"""Tests for the API health endpoint."""

from unittest.mock import AsyncMock

from httpx import ASGITransport, AsyncClient

import app.api as api_module
from app.main import app


async def test_health_returns_ok_when_database_is_ready(monkeypatch) -> None:
    """The endpoint should report success when the database query works."""

    monkeypatch.setattr(api_module, "database_is_ready", AsyncMock(return_value=True))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_returns_503_when_database_is_unavailable(monkeypatch) -> None:
    """The endpoint should fail clearly when PostgreSQL cannot be reached."""

    monkeypatch.setattr(api_module, "database_is_ready", AsyncMock(return_value=False))

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
