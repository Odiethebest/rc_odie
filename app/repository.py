"""Database operations for notification jobs."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationJob
from app.schemas import NotificationCreate


class IdempotencyConflictError(Exception):
    """Raised when an idempotency key is reused for a different request."""


@dataclass(frozen=True)
class CreateNotificationResult:
    """The stored job and whether this call created it."""

    job: NotificationJob
    created: bool


def request_matches_job(job: NotificationJob, request: NotificationCreate) -> bool:
    """Return whether a stored job has the same outbound request content."""

    return (
        job.target_url == str(request.target_url)
        and job.method == request.method.value
        and job.headers == request.headers
        and job.body == request.body
    )


async def get_notification(session: AsyncSession, notification_id: UUID) -> NotificationJob | None:
    """Load one notification by its public UUID."""

    return await session.get(NotificationJob, notification_id)


async def get_notification_by_idempotency_key(
    session: AsyncSession,
    idempotency_key: str,
) -> NotificationJob | None:
    """Load the job previously submitted with an idempotency key."""

    result = await session.execute(
        select(NotificationJob).where(NotificationJob.idempotency_key == idempotency_key)
    )
    return result.scalar_one_or_none()


async def resolve_existing_notification(
    session: AsyncSession,
    idempotency_key: str,
    request: NotificationCreate,
) -> NotificationJob | None:
    """Return an identical existing job or reject conflicting key reuse."""

    existing = await get_notification_by_idempotency_key(session, idempotency_key)
    if existing is None:
        return None
    if not request_matches_job(existing, request):
        raise IdempotencyConflictError
    return existing


async def create_notification(
    session: AsyncSession,
    request: NotificationCreate,
    idempotency_key: str | None,
) -> CreateNotificationResult:
    """Durably create a notification or return its idempotent predecessor."""

    if idempotency_key is not None:
        existing = await resolve_existing_notification(session, idempotency_key, request)
        if existing is not None:
            return CreateNotificationResult(job=existing, created=False)

    job = NotificationJob(
        idempotency_key=idempotency_key,
        target_url=str(request.target_url),
        method=request.method.value,
        headers=request.headers,
        body=request.body,
    )
    session.add(job)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        if idempotency_key is None:
            raise
        existing = await resolve_existing_notification(session, idempotency_key, request)
        if existing is None:
            raise
        return CreateNotificationResult(job=existing, created=False)

    await session.refresh(job)
    return CreateNotificationResult(job=job, created=True)
