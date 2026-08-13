"""Local-only vendor API used by the offline Docker smoke test."""

from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response, status

from app.delivery import NOTIFICATION_ID_HEADER

app = FastAPI(title="Mock Notification Vendor", version="0.1.0")
received_requests: dict[str, dict[str, Any]] = {}


async def remember_request(request: Request) -> str:
    """Record safe request details and return the notification ID."""

    notification_id = request.headers.get(NOTIFICATION_ID_HEADER)
    if notification_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing {NOTIFICATION_ID_HEADER}",
        )

    body: Any = None
    if await request.body():
        try:
            body = await request.json()
        except ValueError:
            body = "<non-json body>"

    received_requests[notification_id] = {
        "notification_id": notification_id,
        "method": request.method,
        "body": body,
    }
    return notification_id


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Report that the local mock vendor process is ready."""

    return {"status": "ok"}


@app.api_route(
    "/success",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["mock delivery"],
)
async def accept_notification(request: Request) -> Response:
    """Record a notification and simulate a successful vendor response."""

    await remember_request(request)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.api_route(
    "/retryable",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    tags=["mock delivery"],
)
async def reject_temporarily(request: Request) -> dict[str, str]:
    """Record a notification and simulate a temporary vendor outage."""

    await remember_request(request)
    return {"detail": "Temporary mock outage"}


@app.api_route(
    "/permanent",
    methods=["POST", "PUT", "PATCH", "DELETE"],
    status_code=status.HTTP_400_BAD_REQUEST,
    tags=["mock delivery"],
)
async def reject_permanently(request: Request) -> dict[str, str]:
    """Record a notification and simulate a permanent request failure."""

    await remember_request(request)
    return {"detail": "Permanent mock rejection"}


@app.get("/received/{notification_id}", tags=["inspection"])
async def get_received_notification(notification_id: str) -> dict[str, Any]:
    """Return the safe details recorded for one received notification."""

    received = received_requests.get(notification_id)
    if received is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not received",
        )
    return received
