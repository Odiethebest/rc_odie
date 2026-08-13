"""Tests for creating and querying notification jobs through FastAPI."""

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from httpx import ASGITransport, AsyncClient

import app.api as api_module
from app.database import get_session
from app.main import app
from app.models import NotificationJob, NotificationStatus
from app.repository import CreateNotificationResult, IdempotencyConflictError


async def override_session() -> AsyncIterator[object]:
    """Provide a harmless session placeholder when repository calls are mocked."""

    yield object()


def make_job() -> NotificationJob:
    """Build a complete pending job for API response tests."""

    now = datetime.now(UTC)
    return NotificationJob(
        id=uuid4(),
        target_url="https://vendor.example/callback",
        method="POST",
        headers={},
        body={"status": "paid"},
        status=NotificationStatus.PENDING.value,
        attempt_count=0,
        max_attempts=5,
        next_attempt_at=now,
        created_at=now,
        updated_at=now,
    )


async def test_create_notification_returns_202_after_storage(monkeypatch) -> None:
    """A stored job should return its ID and pending state with HTTP 202."""

    job = make_job()
    create_mock = AsyncMock(return_value=CreateNotificationResult(job=job, created=True))
    monkeypatch.setattr(api_module, "create_notification_job", create_mock)
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/notifications",
                headers={"Idempotency-Key": "payment-123"},
                json={
                    "target_url": "https://vendor.example/callback",
                    "method": "POST",
                    "headers": {},
                    "body": {"status": "paid"},
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.json() == {"id": str(job.id), "status": "pending"}
    assert create_mock.await_args.args[2] == "payment-123"


async def test_create_notification_marks_idempotent_replay(monkeypatch) -> None:
    """An identical repeated submission should return the original job."""

    job = make_job()
    monkeypatch.setattr(
        api_module,
        "create_notification_job",
        AsyncMock(return_value=CreateNotificationResult(job=job, created=False)),
    )
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/notifications",
                headers={"Idempotency-Key": "payment-123"},
                json={"target_url": "https://vendor.example/callback"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 202
    assert response.headers["Idempotent-Replayed"] == "true"
    assert response.json()["id"] == str(job.id)


async def test_create_notification_returns_409_for_key_conflict(monkeypatch) -> None:
    """A key reused with different content should return HTTP 409."""

    monkeypatch.setattr(
        api_module,
        "create_notification_job",
        AsyncMock(side_effect=IdempotencyConflictError),
    )
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/notifications",
                headers={"Idempotency-Key": "payment-123"},
                json={"target_url": "https://vendor.example/callback"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Idempotency-Key was already used with a different request"
    }


async def test_create_notification_does_not_accept_database_failure(monkeypatch) -> None:
    """A failed database transaction must not produce HTTP 202."""

    monkeypatch.setattr(
        api_module,
        "create_notification_job",
        AsyncMock(side_effect=RuntimeError("database write failed")),
    )
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/notifications",
                json={"target_url": "https://vendor.example/callback"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 500


async def test_create_notification_returns_422_for_invalid_request() -> None:
    """Invalid URLs and methods should be rejected before database work starts."""

    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/notifications",
                json={"target_url": "ftp://vendor.example/callback", "method": "TRACE"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert {error["loc"][-1] for error in response.json()["detail"]} == {
        "target_url",
        "method",
    }


async def test_get_notification_status_returns_job(monkeypatch) -> None:
    """A known UUID should return the stored delivery state."""

    job = make_job()
    monkeypatch.setattr(api_module, "get_notification", AsyncMock(return_value=job))
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/notifications/{job.id}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json()["id"] == str(job.id)
    assert response.json()["attempt_count"] == 0


async def test_get_notification_status_returns_404(monkeypatch) -> None:
    """An unknown but valid UUID should return HTTP 404."""

    monkeypatch.setattr(api_module, "get_notification", AsyncMock(return_value=None))
    app.dependency_overrides[get_session] = override_session

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(f"/notifications/{uuid4()}")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not found"}


async def test_notification_routes_appear_in_openapi() -> None:
    """The generated API schema should expose both notification routes."""

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        schema = (await client.get("/openapi.json")).json()

    assert "post" in schema["paths"]["/notifications"]
    assert "get" in schema["paths"]["/notifications/{notification_id}"]
