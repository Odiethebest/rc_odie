"""Tests for one-attempt outbound HTTP delivery."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest

from app.delivery import (
    DELIVERY_TIMEOUT_SECONDS,
    MAX_ERROR_LENGTH,
    DeliveryOutcome,
    bound_error_message,
    build_outbound_headers,
    classify_status_code,
    deliver_notification,
)
from app.models import NotificationJob, NotificationStatus


def make_job(**overrides) -> NotificationJob:
    """Build a complete in-memory job for delivery tests."""

    now = datetime.now(UTC)
    values = {
        "id": uuid4(),
        "target_url": "https://vendor.example/callback",
        "method": "POST",
        "headers": {"Authorization": "Bearer secret", "X-Source": "billing"},
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


@pytest.mark.parametrize("status_code", [200, 201, 204, 299])
def test_classify_status_code_marks_2xx_success(status_code) -> None:
    """Every 2xx response should count as successful delivery."""

    assert classify_status_code(status_code) is DeliveryOutcome.SUCCESS


@pytest.mark.parametrize("status_code", [408, 429, 500, 503, 599])
def test_classify_status_code_marks_temporary_failures_retryable(status_code) -> None:
    """Timeout, rate-limit, and server errors should be retried."""

    assert classify_status_code(status_code) is DeliveryOutcome.RETRYABLE_FAILURE


@pytest.mark.parametrize("status_code", [301, 400, 401, 404, 422])
def test_classify_status_code_marks_other_failures_permanent(status_code) -> None:
    """Redirects and non-retryable client errors should not repeat unchanged."""

    assert classify_status_code(status_code) is DeliveryOutcome.PERMANENT_FAILURE


def test_build_outbound_headers_enforces_stable_notification_id() -> None:
    """Caller input must not replace the service-owned notification ID."""

    job = make_job(headers={"x-notification-id": "caller-value", "X-Source": "billing"})

    headers = build_outbound_headers(job)

    assert headers == {"X-Source": "billing", "X-Notification-Id": str(job.id)}


def test_bound_error_message_limits_stored_text() -> None:
    """Long transport errors should fit the bounded database error field policy."""

    short_message = "connection failed"
    long_message = "x" * (MAX_ERROR_LENGTH + 100)

    assert bound_error_message(short_message) == short_message
    assert len(bound_error_message(long_message)) == MAX_ERROR_LENGTH
    assert bound_error_message(long_message).endswith("...")


async def test_deliver_notification_forwards_request_with_timeout() -> None:
    """Delivery should forward method, URL, headers, and JSON with a 10-second timeout."""

    handler = AsyncMock(return_value=httpx.Response(204, content=b"ignored response body"))
    job = make_job(method="PATCH")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await deliver_notification(job, client)

    request = handler.await_args.args[0]
    assert request.method == "PATCH"
    assert str(request.url) == job.target_url
    assert request.headers["Authorization"] == "Bearer secret"
    assert request.headers["X-Notification-Id"] == str(job.id)
    assert request.extensions["timeout"] == {
        "connect": DELIVERY_TIMEOUT_SECONDS,
        "read": DELIVERY_TIMEOUT_SECONDS,
        "write": DELIVERY_TIMEOUT_SECONDS,
        "pool": DELIVERY_TIMEOUT_SECONDS,
    }
    assert request.content == b'{"status":"paid"}'
    assert result.outcome is DeliveryOutcome.SUCCESS
    assert result.status_code == 204
    assert result.error is None


@pytest.mark.parametrize(
    ("status_code", "expected_outcome"),
    [
        (429, DeliveryOutcome.RETRYABLE_FAILURE),
        (503, DeliveryOutcome.RETRYABLE_FAILURE),
        (400, DeliveryOutcome.PERMANENT_FAILURE),
    ],
)
async def test_deliver_notification_classifies_http_failures(
    status_code,
    expected_outcome,
) -> None:
    """HTTP failures should return status and classification without response content."""

    handler = AsyncMock(return_value=httpx.Response(status_code, text="sensitive vendor body"))

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await deliver_notification(make_job(), client)

    assert result.outcome is expected_outcome
    assert result.status_code == status_code
    assert result.error == f"External API returned HTTP {status_code}"
    assert "sensitive vendor body" not in repr(result)


@pytest.mark.parametrize(
    "transport_error",
    [
        httpx.ConnectError("connection failed"),
        httpx.ReadTimeout("vendor timed out"),
    ],
)
async def test_deliver_notification_converts_transport_errors_to_retryable(
    transport_error,
) -> None:
    """Expected network failures should return retryable results instead of escaping."""

    handler = AsyncMock(side_effect=transport_error)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await deliver_notification(make_job(), client)

    assert result.outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert result.status_code is None
    assert type(transport_error).__name__ in result.error


async def test_notification_id_is_unchanged_across_attempts() -> None:
    """Repeated attempts for one job should send the same downstream idempotency value."""

    handler = AsyncMock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200),
        ]
    )
    job = make_job()

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        first_result = await deliver_notification(job, client)
        second_result = await deliver_notification(job, client)

    first_request = handler.await_args_list[0].args[0]
    second_request = handler.await_args_list[1].args[0]
    assert first_request.headers["X-Notification-Id"] == str(job.id)
    assert second_request.headers["X-Notification-Id"] == str(job.id)
    assert first_result.outcome is DeliveryOutcome.RETRYABLE_FAILURE
    assert second_result.outcome is DeliveryOutcome.SUCCESS
