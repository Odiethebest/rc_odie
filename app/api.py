"""HTTP endpoints exposed by the service."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import database_is_ready, get_session
from app.repository import IdempotencyConflictError, get_notification
from app.repository import create_notification as create_notification_job
from app.schemas import NotificationAccepted, NotificationCreate, NotificationStatusResponse

router = APIRouter()


class HealthResponse(BaseModel):
    """Successful health-check response."""

    status: Literal["ok"]
    database: Literal["ok"]


@router.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    """Report healthy only when the API can reach PostgreSQL."""

    if not await database_is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
    return HealthResponse(status="ok", database="ok")


@router.post(
    "/notifications",
    response_model=NotificationAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["notifications"],
)
async def create_notification(
    request: NotificationCreate,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_session)],
    idempotency_key: Annotated[
        str | None,
        Header(alias="Idempotency-Key", min_length=1, max_length=255),
    ] = None,
) -> NotificationAccepted:
    """Store a notification and return only after the transaction commits."""

    normalized_key = idempotency_key.strip() if idempotency_key is not None else None
    if idempotency_key is not None and not normalized_key:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Idempotency-Key cannot be blank",
        )

    try:
        result = await create_notification_job(session, request, normalized_key)
    except IdempotencyConflictError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key was already used with a different request",
        ) from error

    if not result.created:
        response.headers["Idempotent-Replayed"] = "true"
    return NotificationAccepted.model_validate(result.job)


@router.get(
    "/notifications/{notification_id}",
    response_model=NotificationStatusResponse,
    tags=["notifications"],
)
async def get_notification_status(
    notification_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> NotificationStatusResponse:
    """Return the current state of one notification job."""

    job = await get_notification(session, notification_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )
    return NotificationStatusResponse.model_validate(job)
