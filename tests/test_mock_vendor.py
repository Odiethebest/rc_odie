"""Tests for the local-only mock vendor used by Docker smoke tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.mock_vendor import app, received_requests


@pytest.fixture(autouse=True)
def clear_received_requests() -> None:
    """Keep the mock vendor's in-memory inspection state isolated per test."""

    received_requests.clear()


async def test_mock_vendor_health_check() -> None:
    """The container health endpoint should report readiness."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_success_endpoint_records_safe_request_details(method) -> None:
    """Every supported method should succeed and be inspectable without sensitive headers."""

    notification_id = f"notification-{method.lower()}"
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            method,
            "/success",
            headers={
                "X-Notification-Id": notification_id,
                "Authorization": "Bearer must-not-be-recorded",
            },
            json={"event": "payment.succeeded"},
        )
        inspection = await client.get(f"/received/{notification_id}")

    assert response.status_code == 204
    assert inspection.status_code == 200
    assert inspection.json() == {
        "notification_id": notification_id,
        "method": method,
        "body": {"event": "payment.succeeded"},
    }
    assert "must-not-be-recorded" not in inspection.text


@pytest.mark.parametrize(
    ("path", "expected_status"),
    [("/retryable", 503), ("/permanent", 400)],
)
async def test_failure_endpoints_return_expected_status(path, expected_status) -> None:
    """The mock should provide deterministic temporary and permanent failures."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            path,
            headers={"X-Notification-Id": "failure-test"},
            json={"event": "test"},
        )

    assert response.status_code == expected_status
    assert "failure-test" in received_requests


async def test_mock_vendor_requires_notification_id() -> None:
    """Delivery endpoints should reject requests that bypass the notification service contract."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/success", json={"event": "test"})

    assert response.status_code == 400
    assert response.json() == {"detail": "Missing X-Notification-Id"}


async def test_inspection_returns_404_for_unknown_notification() -> None:
    """An ID not received by this mock process should return HTTP 404."""

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/received/unknown")

    assert response.status_code == 404
    assert response.json() == {"detail": "Notification not received"}
