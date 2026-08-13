"""Unit tests for notification persistence rules."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

import app.repository as repository
from app.models import NotificationJob, NotificationStatus
from app.repository import IdempotencyConflictError
from app.schemas import NotificationCreate


def make_job(**overrides) -> NotificationJob:
    """Build a complete in-memory job for repository tests."""

    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "target_url": "https://vendor.example/callback",
        "method": "POST",
        "headers": {"X-Source": "billing"},
        "body": {"status": "paid"},
        "status": NotificationStatus.PENDING.value,
        "attempt_count": 0,
        "max_attempts": 5,
        "next_attempt_at": now,
        "created_at": now,
        "updated_at": now,
    }
    values.update(overrides)
    return NotificationJob(**values)


def test_request_matches_job_compares_outbound_content() -> None:
    """Idempotency comparison should cover every outbound request field."""

    request = NotificationCreate(
        target_url="https://vendor.example/callback",
        method="POST",
        headers={"X-Source": "billing"},
        body={"status": "paid"},
    )

    assert repository.request_matches_job(make_job(), request) is True
    assert repository.request_matches_job(make_job(body={"status": "cancelled"}), request) is False


async def test_resolve_existing_notification_rejects_different_request(monkeypatch) -> None:
    """A reused key with a different payload should raise a conflict."""

    existing = make_job(body={"status": "cancelled"})
    monkeypatch.setattr(
        repository,
        "get_notification_by_idempotency_key",
        AsyncMock(return_value=existing),
    )
    request = NotificationCreate(
        target_url="https://vendor.example/callback",
        method="POST",
        headers={"X-Source": "billing"},
        body={"status": "paid"},
    )

    with pytest.raises(IdempotencyConflictError):
        await repository.resolve_existing_notification(MagicMock(), "payment-123", request)


async def test_create_notification_commits_before_returning(monkeypatch) -> None:
    """A new job should not be returned until commit and refresh succeed."""

    monkeypatch.setattr(
        repository,
        "resolve_existing_notification",
        AsyncMock(return_value=None),
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    request = NotificationCreate(
        target_url="https://vendor.example/callback",
        method="POST",
        body={"status": "paid"},
    )

    result = await repository.create_notification(session, request, "payment-123")

    assert result.created is True
    session.add.assert_called_once_with(result.job)
    session.commit.assert_awaited_once()
    session.refresh.assert_awaited_once_with(result.job)
