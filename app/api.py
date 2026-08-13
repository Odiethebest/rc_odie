"""HTTP endpoints exposed by the service."""

from typing import Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.database import database_is_ready

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
