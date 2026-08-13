"""Validated request and response shapes for the notification API."""

import re
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from app.models import NotificationStatus

HEADER_NAME_PATTERN = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


class HTTPMethod(StrEnum):
    """HTTP methods accepted by the MVP notification API."""

    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class NotificationCreate(BaseModel):
    """A validated outbound request submitted by a business system."""

    target_url: AnyHttpUrl
    method: HTTPMethod = HTTPMethod.POST
    headers: dict[str, str] = Field(default_factory=dict, max_length=50)
    body: dict[str, Any] | None = None

    @field_validator("method", mode="before")
    @classmethod
    def normalize_method(cls, value: object) -> object:
        """Normalize a string method to uppercase before enum validation."""

        return value.upper() if isinstance(value, str) else value

    @field_validator("headers")
    @classmethod
    def validate_headers(cls, headers: dict[str, str]) -> dict[str, str]:
        """Reject malformed header names and values that could inject new headers."""

        for name, value in headers.items():
            if not HEADER_NAME_PATTERN.fullmatch(name):
                raise ValueError(f"Invalid HTTP header name: {name}")
            if "\r" in value or "\n" in value:
                raise ValueError(f"Invalid HTTP header value for: {name}")
        return headers


class NotificationAccepted(BaseModel):
    """Small response returned after a notification has been durably accepted."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: NotificationStatus


class NotificationStatusResponse(BaseModel):
    """Current delivery state returned by the status endpoint."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: NotificationStatus
    attempt_count: int
    next_attempt_at: datetime
    last_status_code: int | None
    last_error: str | None
    created_at: datetime
    updated_at: datetime
