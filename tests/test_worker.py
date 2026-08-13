"""Unit tests for worker orchestration and graceful shutdown."""

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import httpx
import pytest

import app.worker as worker_module
from app.config import Settings
from app.models import NotificationJob, NotificationStatus


class FakeSessionContext:
    """Minimal async context manager returned by a fake session maker."""

    async def __aenter__(self):
        return MagicMock()

    async def __aexit__(self, exc_type, exc_value, traceback):
        return False


def fake_session_maker():
    """Return a new fake async session context."""

    return FakeSessionContext()


def make_claimed_job() -> NotificationJob:
    """Build a processing job that has already been durably claimed."""

    now = datetime.now(UTC)
    return NotificationJob(
        id=uuid4(),
        target_url="https://vendor.example/callback",
        method="POST",
        headers={},
        body={"status": "paid"},
        status=NotificationStatus.PROCESSING.value,
        attempt_count=1,
        max_attempts=5,
        next_attempt_at=now,
        locked_at=now,
        created_at=now,
        updated_at=now,
    )


async def test_process_claimed_notification_delivers_then_records(monkeypatch) -> None:
    """A claimed job should perform the network call before recording its result."""

    events = []
    job = make_claimed_job()

    async def fake_deliver(notification, client):
        events.append("delivered")
        return MagicMock()

    async def fake_record(session, **kwargs):
        events.append("recorded")
        assert kwargs["notification_id"] == job.id
        assert kwargs["locked_at"] == job.locked_at
        return True

    monkeypatch.setattr(worker_module, "deliver_notification", fake_deliver)
    monkeypatch.setattr(worker_module, "record_delivery_result", fake_record)

    await worker_module.process_claimed_notification(
        job,
        client=MagicMock(),
        session_maker=fake_session_maker,
        clock=lambda: datetime.now(UTC),
    )

    assert events == ["delivered", "recorded"]


async def test_run_worker_cycle_claims_before_network(monkeypatch) -> None:
    """The claim function must finish its commit before delivery begins."""

    events = []
    job = make_claimed_job()

    async def fake_recover(session, **kwargs):
        events.append("recovered")
        return 0

    async def fake_claim(session, **kwargs):
        events.append("claim_committed")
        return [job]

    async def fake_process(notification, **kwargs):
        assert events[-1] == "claim_committed"
        events.append("network_started")

    monkeypatch.setattr(worker_module, "recover_stale_notifications", fake_recover)
    monkeypatch.setattr(worker_module, "claim_due_notifications", fake_claim)
    monkeypatch.setattr(worker_module, "process_claimed_notification", fake_process)

    processed = await worker_module.run_worker_cycle(
        client=MagicMock(),
        session_maker=fake_session_maker,
        settings=Settings(_env_file=None),
        clock=lambda: datetime.now(UTC),
    )

    assert processed == 1
    assert events == ["recovered", "claim_committed", "network_started"]


async def test_run_worker_cycle_processes_claimed_batch_concurrently(monkeypatch) -> None:
    """Every job in a claimed batch should start before one slow request can block the rest."""

    jobs = [make_claimed_job(), make_claimed_job()]
    both_started = asyncio.Event()
    started_count = 0

    async def fake_recover_for_concurrency(session, **kwargs):
        return 0

    async def fake_claim_for_concurrency(session, **kwargs):
        return jobs

    async def blocking_process(notification, **kwargs):
        nonlocal started_count
        started_count += 1
        if started_count == len(jobs):
            both_started.set()
        await asyncio.wait_for(both_started.wait(), timeout=0.2)

    monkeypatch.setattr(
        worker_module,
        "recover_stale_notifications",
        fake_recover_for_concurrency,
    )
    monkeypatch.setattr(
        worker_module,
        "claim_due_notifications",
        fake_claim_for_concurrency,
    )
    monkeypatch.setattr(worker_module, "process_claimed_notification", blocking_process)

    processed = await worker_module.run_worker_cycle(
        client=MagicMock(),
        session_maker=fake_session_maker,
        settings=Settings(_env_file=None),
        clock=lambda: datetime.now(UTC),
    )

    assert processed == 2
    assert started_count == 2


async def test_worker_loop_does_not_claim_after_stop(monkeypatch) -> None:
    """A stop request during a cycle should prevent another polling cycle."""

    stop_event = asyncio.Event()
    run_cycle = AsyncMock()

    async def stop_during_first_cycle(**kwargs):
        stop_event.set()
        return 0

    run_cycle.side_effect = stop_during_first_cycle
    monkeypatch.setattr(worker_module, "run_worker_cycle", run_cycle)
    monkeypatch.setattr(worker_module, "wait_for_next_cycle", AsyncMock())

    await worker_module.worker_loop(
        stop_event,
        client=MagicMock(),
        session_maker=fake_session_maker,
        settings=Settings(_env_file=None),
    )

    run_cycle.assert_awaited_once()
    worker_module.wait_for_next_cycle.assert_not_awaited()


async def test_worker_loop_with_preexisting_stop_does_nothing(monkeypatch) -> None:
    """A worker started with a stop request must not claim any work."""

    stop_event = asyncio.Event()
    stop_event.set()
    run_cycle = AsyncMock()
    monkeypatch.setattr(worker_module, "run_worker_cycle", run_cycle)

    await worker_module.worker_loop(stop_event, client=MagicMock())

    run_cycle.assert_not_awaited()


async def test_wait_for_next_cycle_wakes_on_stop() -> None:
    """The polling wait should end immediately when shutdown is requested."""

    stop_event = asyncio.Event()

    async def request_stop():
        await asyncio.sleep(0)
        stop_event.set()

    await asyncio.gather(
        worker_module.wait_for_next_cycle(stop_event, seconds=60),
        request_stop(),
    )

    assert stop_event.is_set()


async def test_process_claimed_notification_requires_lease() -> None:
    """Programming errors must not send jobs that were never properly claimed."""

    job = make_claimed_job()
    job.locked_at = None

    async with httpx.AsyncClient() as client:
        with pytest.raises(ValueError, match="missing locked_at"):
            await worker_module.process_claimed_notification(
                job,
                client=client,
                session_maker=fake_session_maker,
                clock=lambda: datetime.now(UTC),
            )
