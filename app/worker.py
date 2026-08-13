"""Polling worker that delivers durable notification jobs."""

import asyncio
import logging
import signal
from collections.abc import Callable
from contextlib import suppress
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import Settings, get_settings
from app.database import session_factory
from app.delivery import deliver_notification
from app.models import NotificationJob
from app.worker_repository import (
    claim_due_notifications,
    record_delivery_result,
    recover_stale_notifications,
)

logger = logging.getLogger(__name__)
Clock = Callable[[], datetime]


async def process_claimed_notification(
    job: NotificationJob,
    *,
    client: httpx.AsyncClient,
    session_maker: async_sessionmaker[AsyncSession],
    clock: Clock,
) -> None:
    """Deliver one already-committed claim and persist its result."""

    if job.locked_at is None:
        raise ValueError("Claimed notification is missing locked_at")

    result = await deliver_notification(job, client)
    async with session_maker() as session:
        recorded = await record_delivery_result(
            session,
            notification_id=job.id,
            locked_at=job.locked_at,
            result=result,
            now=clock(),
        )
    if not recorded:
        logger.warning("Ignored a delivery result for an expired lease: %s", job.id)


async def run_worker_cycle(
    *,
    client: httpx.AsyncClient,
    session_maker: async_sessionmaker[AsyncSession],
    settings: Settings,
    clock: Clock,
) -> int:
    """Recover stale jobs, claim one batch, and process the batch concurrently."""

    now = clock()
    async with session_maker() as session:
        await recover_stale_notifications(
            session,
            stale_before=now - timedelta(seconds=settings.worker_lease_seconds),
            now=now,
        )

    async with session_maker() as session:
        jobs = await claim_due_notifications(
            session,
            limit=settings.worker_batch_size,
            now=clock(),
        )

    processing_results = await asyncio.gather(
        *(
            process_claimed_notification(
                job,
                client=client,
                session_maker=session_maker,
                clock=clock,
            )
            for job in jobs
        ),
        return_exceptions=True,
    )
    for job, processing_result in zip(jobs, processing_results, strict=True):
        if isinstance(processing_result, BaseException):
            logger.error(
                "Notification processing failed and will be recovered by lease: %s (%s)",
                job.id,
                type(processing_result).__name__,
            )
    return len(jobs)


async def wait_for_next_cycle(stop_event: asyncio.Event, seconds: float) -> None:
    """Wait for polling time to pass, while allowing immediate shutdown."""

    with suppress(TimeoutError):
        await asyncio.wait_for(stop_event.wait(), timeout=seconds)


async def worker_loop(
    stop_event: asyncio.Event,
    *,
    client: httpx.AsyncClient,
    session_maker: async_sessionmaker[AsyncSession] = session_factory,
    settings: Settings | None = None,
    clock: Clock = lambda: datetime.now(UTC),
) -> None:
    """Poll until shutdown is requested, without claiming new work afterward."""

    worker_settings = settings or get_settings()
    while not stop_event.is_set():
        await run_worker_cycle(
            client=client,
            session_maker=session_maker,
            settings=worker_settings,
            clock=clock,
        )
        if not stop_event.is_set():
            await wait_for_next_cycle(stop_event, worker_settings.worker_poll_interval_seconds)


def request_shutdown(stop_event: asyncio.Event) -> None:
    """Signal the worker loop to stop before it claims another batch."""

    stop_event.set()


def install_signal_handlers(stop_event: asyncio.Event) -> None:
    """Translate process termination signals into a graceful stop request."""

    loop = asyncio.get_running_loop()
    for process_signal in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(process_signal, request_shutdown, stop_event)


async def run_worker() -> None:
    """Create worker resources and run until SIGINT or SIGTERM."""

    stop_event = asyncio.Event()
    install_signal_handlers(stop_event)
    async with httpx.AsyncClient() as client:
        await worker_loop(stop_event, client=client)


def main() -> None:
    """Start the asynchronous worker from the command line."""

    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
