"""Tests for notification API request validation."""

import pytest
from pydantic import ValidationError

from app.schemas import HTTPMethod, NotificationCreate


def test_notification_create_normalizes_method_and_url() -> None:
    """Valid input should become a consistent request representation."""

    request = NotificationCreate(
        target_url="https://vendor.example/callback",
        method="post",
        headers={"X-Source": "billing"},
        body={"status": "paid"},
    )

    assert request.method is HTTPMethod.POST
    assert str(request.target_url) == "https://vendor.example/callback"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("target_url", "ftp://vendor.example/callback"),
        ("method", "TRACE"),
        ("headers", {"Bad Header": "value"}),
        ("headers", {"X-Test": "safe\r\nInjected: value"}),
        ("body", ["JSON", "array"]),
    ],
)
def test_notification_create_rejects_invalid_input(field, value) -> None:
    """Malformed URLs, methods, headers, and bodies should fail validation."""

    data = {
        "target_url": "https://vendor.example/callback",
        "method": "POST",
        "headers": {},
        "body": {"event": "created"},
    }
    data[field] = value

    with pytest.raises(ValidationError):
        NotificationCreate.model_validate(data)
