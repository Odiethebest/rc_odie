"""Database state transitions used by the notification worker."""

from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.delivery import DeliveryOutcome, DeliveryResult, bound_error_message
from app.models import NotificationJob, NotificationStatus

RETRY_DELAYS_MINUTES = (1, 2, 4, 8)
LEASE_EXPIRED_ERROR = "Worker lease expired before delivery result was recorded"


def retry_delay(attempt_count: int) -> timedelta:
    """Return the capped retry delay after a failed delivery attempt."""

    index = min(max(attempt_count - 1, 0), len(RETRY_DELAYS_MINUTES) - 1)
    return timedelta(minutes=RETRY_DELAYS_MINUTES[index])


async def claim_due_notifications(
    session: AsyncSession,
    *,
    limit: int,
    now: datetime,
) -> list[NotificationJob]:
    """Lock, mark, and commit a batch of due notification jobs."""

    result = await session.execute(
        select(NotificationJob)
        .where(
            NotificationJob.status.in_(
                [NotificationStatus.PENDING.value, NotificationStatus.RETRYING.value]
            ),
            NotificationJob.next_attempt_at <= now,
        )
        .order_by(NotificationJob.next_attempt_at, NotificationJob.created_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars())

    for job in jobs:
        job.status = NotificationStatus.PROCESSING.value
        job.locked_at = now
        job.attempt_count += 1

    await session.commit()
    return jobs


async def record_delivery_result(
    session: AsyncSession,
    *,
    notification_id: UUID,
    locked_at: datetime,
    result: DeliveryResult,
    now: datetime,
) -> bool:
    """Apply one delivery result only if the worker still owns the lease."""

    job = await session.get(NotificationJob, notification_id, with_for_update=True)
    if (
        job is None
        or job.status != NotificationStatus.PROCESSING.value
        or job.locked_at != locked_at
    ):
        await session.rollback()
        return False

    job.last_status_code = result.status_code
    job.last_error = bound_error_message(result.error) if result.error else None
    job.locked_at = None

    if result.outcome is DeliveryOutcome.SUCCESS:
        job.status = NotificationStatus.SUCCEEDED.value
    elif (
        result.outcome is DeliveryOutcome.PERMANENT_FAILURE or job.attempt_count >= job.max_attempts
    ):
        job.status = NotificationStatus.DEAD.value
    else:
        job.status = NotificationStatus.RETRYING.value
        job.next_attempt_at = now + retry_delay(job.attempt_count)

    await session.commit()
    return True


async def recover_stale_notifications(
    session: AsyncSession,
    *,
    stale_before: datetime,
    now: datetime,
    limit: int = 100,
) -> int:
    """Recover jobs whose worker lease expired before recording a result."""

    result = await session.execute(
        select(NotificationJob)
        .where(
            NotificationJob.status == NotificationStatus.PROCESSING.value,
            or_(NotificationJob.locked_at.is_(None), NotificationJob.locked_at <= stale_before),
        )
        .order_by(NotificationJob.locked_at)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    jobs = list(result.scalars())

    for job in jobs:
        job.locked_at = None
        job.last_error = LEASE_EXPIRED_ERROR
        if job.attempt_count >= job.max_attempts:
            job.status = NotificationStatus.DEAD.value
        else:
            job.status = NotificationStatus.RETRYING.value
            job.next_attempt_at = now

    await session.commit()
    return len(jobs)
