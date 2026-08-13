"""Single-attempt outbound HTTP delivery without database side effects."""

from dataclasses import dataclass
from enum import StrEnum

import httpx

from app.models import NotificationJob

DELIVERY_TIMEOUT_SECONDS = 10.0
MAX_ERROR_LENGTH = 500
NOTIFICATION_ID_HEADER = "X-Notification-Id"


class DeliveryOutcome(StrEnum):
    """Possible results from one outbound delivery attempt."""

    SUCCESS = "success"
    RETRYABLE_FAILURE = "retryable_failure"
    PERMANENT_FAILURE = "permanent_failure"


@dataclass(frozen=True)
class DeliveryResult:
    """Small result used by the worker to update job state."""

    outcome: DeliveryOutcome
    status_code: int | None = None
    error: str | None = None


def classify_status_code(status_code: int) -> DeliveryOutcome:
    """Classify an external HTTP status into a delivery outcome."""

    if 200 <= status_code <= 299:
        return DeliveryOutcome.SUCCESS
    if status_code in {408, 429} or 500 <= status_code <= 599:
        return DeliveryOutcome.RETRYABLE_FAILURE
    return DeliveryOutcome.PERMANENT_FAILURE


def build_outbound_headers(job: NotificationJob) -> dict[str, str]:
    """Copy caller headers and enforce this service's stable notification ID."""

    headers = {
        name: value
        for name, value in job.headers.items()
        if name.lower() != NOTIFICATION_ID_HEADER.lower()
    }
    headers[NOTIFICATION_ID_HEADER] = str(job.id)
    return headers


def bound_error_message(message: str) -> str:
    """Limit stored delivery errors without losing the fact that text was truncated."""

    if len(message) <= MAX_ERROR_LENGTH:
        return message
    return f"{message[: MAX_ERROR_LENGTH - 3]}..."


async def deliver_notification(
    job: NotificationJob,
    client: httpx.AsyncClient,
) -> DeliveryResult:
    """Send one notification attempt and return a database-independent result."""

    try:
        response = await client.request(
            method=job.method,
            url=job.target_url,
            headers=build_outbound_headers(job),
            json=job.body,
            timeout=DELIVERY_TIMEOUT_SECONDS,
            follow_redirects=False,
        )
    except httpx.RequestError as error:
        detail = f"{type(error).__name__}: {error}"
        return DeliveryResult(
            outcome=DeliveryOutcome.RETRYABLE_FAILURE,
            error=bound_error_message(detail),
        )

    outcome = classify_status_code(response.status_code)
    error_message = None
    if outcome is not DeliveryOutcome.SUCCESS:
        error_message = f"External API returned HTTP {response.status_code}"

    return DeliveryResult(
        outcome=outcome,
        status_code=response.status_code,
        error=error_message,
    )
