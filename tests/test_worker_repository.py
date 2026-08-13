"""Unit tests for worker database state transitions."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.delivery import DeliveryOutcome, DeliveryResult
from app.models import NotificationJob, NotificationStatus
from app.worker_repository import (
    LEASE_EXPIRED_ERROR,
    claim_due_notifications,
    record_delivery_result,
    recover_stale_notifications,
    retry_delay,
)


def make_job(**overrides) -> NotificationJob:
    """Build a complete in-memory job for worker repository tests."""

    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "target_url": "https://vendor.example/callback",
        "method": "POST",
        "headers": {},
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


def fake_session_with_scalars(items) -> MagicMock:
    """Create a session mock whose execute result yields the provided items."""

    scalar_result = MagicMock()
    scalar_result.__iter__.return_value = iter(items)
    execute_result = MagicMock()
    execute_result.scalars.return_value = scalar_result
    session = MagicMock()
    session.execute = AsyncMock(return_value=execute_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.mark.parametrize(
    ("attempt_count", "expected_minutes"),
    [(1, 1), (2, 2), (3, 4), (4, 8), (5, 8), (100, 8)],
)
def test_retry_delay_uses_capped_exponential_backoff(attempt_count, expected_minutes) -> None:
    """Retry delays should follow 1, 2, 4, and 8 minutes, then stay capped."""

    assert retry_delay(attempt_count) == timedelta(minutes=expected_minutes)


async def test_claim_due_notifications_marks_and_commits_jobs() -> None:
    """A claim should become durable before jobs are returned for network work."""

    now = datetime.now(UTC)
    jobs = [make_job(), make_job(status=NotificationStatus.RETRYING.value, attempt_count=2)]
    session = fake_session_with_scalars(jobs)

    claimed = await claim_due_notifications(session, limit=10, now=now)

    assert claimed == jobs
    assert all(job.status == NotificationStatus.PROCESSING.value for job in jobs)
    assert all(job.locked_at == now for job in jobs)
    assert [job.attempt_count for job in jobs] == [1, 3]
    session.commit.assert_awaited_once()


@pytest.mark.parametrize(
    ("delivery_result", "attempt_count", "expected_status", "expected_delay"),
    [
        (
            DeliveryResult(DeliveryOutcome.SUCCESS, status_code=204),
            1,
            NotificationStatus.SUCCEEDED.value,
            None,
        ),
        (
            DeliveryResult(
                DeliveryOutcome.RETRYABLE_FAILURE,
                status_code=503,
                error="External API returned HTTP 503",
            ),
            1,
            NotificationStatus.RETRYING.value,
            timedelta(minutes=1),
        ),
        (
            DeliveryResult(
                DeliveryOutcome.PERMANENT_FAILURE,
                status_code=400,
                error="External API returned HTTP 400",
            ),
            1,
            NotificationStatus.DEAD.value,
            None,
        ),
        (
            DeliveryResult(
                DeliveryOutcome.RETRYABLE_FAILURE,
                status_code=503,
                error="External API returned HTTP 503",
            ),
            5,
            NotificationStatus.DEAD.value,
            None,
        ),
    ],
)
async def test_record_delivery_result_applies_state_transition(
    delivery_result,
    attempt_count,
    expected_status,
    expected_delay,
) -> None:
    """Success, retry, permanent failure, and exhausted retry states should be exact."""

    locked_at = datetime.now(UTC) - timedelta(seconds=2)
    now = datetime.now(UTC)
    job = make_job(
        status=NotificationStatus.PROCESSING.value,
        attempt_count=attempt_count,
        locked_at=locked_at,
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=job)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    recorded = await record_delivery_result(
        session,
        notification_id=job.id,
        locked_at=locked_at,
        result=delivery_result,
        now=now,
    )

    assert recorded is True
    assert job.status == expected_status
    assert job.locked_at is None
    assert job.last_status_code == delivery_result.status_code
    assert job.last_error == delivery_result.error
    if expected_delay is not None:
        assert job.next_attempt_at == now + expected_delay
    session.commit.assert_awaited_once()


async def test_record_delivery_result_ignores_expired_lease() -> None:
    """A late worker must not overwrite a job already recovered by another worker."""

    old_lock = datetime.now(UTC) - timedelta(minutes=2)
    job = make_job(
        status=NotificationStatus.PROCESSING.value,
        locked_at=datetime.now(UTC),
        attempt_count=2,
    )
    session = MagicMock()
    session.get = AsyncMock(return_value=job)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()

    recorded = await record_delivery_result(
        session,
        notification_id=job.id,
        locked_at=old_lock,
        result=DeliveryResult(DeliveryOutcome.SUCCESS, status_code=200),
        now=datetime.now(UTC),
    )

    assert recorded is False
    assert job.status == NotificationStatus.PROCESSING.value
    session.rollback.assert_awaited_once()
    session.commit.assert_not_awaited()


async def test_recover_stale_notifications_retries_or_kills_jobs() -> None:
    """Expired leases should retry below the limit and become dead at the limit."""

    now = datetime.now(UTC)
    retry_job = make_job(
        status=NotificationStatus.PROCESSING.value,
        locked_at=now - timedelta(minutes=2),
        attempt_count=2,
    )
    dead_job = make_job(
        status=NotificationStatus.PROCESSING.value,
        locked_at=now - timedelta(minutes=2),
        attempt_count=5,
    )
    session = fake_session_with_scalars([retry_job, dead_job])

    recovered = await recover_stale_notifications(
        session,
        stale_before=now - timedelta(minutes=1),
        now=now,
    )

    assert recovered == 2
    assert retry_job.status == NotificationStatus.RETRYING.value
    assert retry_job.next_attempt_at == now
    assert dead_job.status == NotificationStatus.DEAD.value
    assert retry_job.locked_at is dead_job.locked_at is None
    assert retry_job.last_error == dead_job.last_error == LEASE_EXPIRED_ERROR
    session.commit.assert_awaited_once()
