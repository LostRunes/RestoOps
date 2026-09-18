"""
Exotel webhook handler.

Exotel does NOT sign webhooks like Twilio.
We protect the endpoint with a shared secret passed as a query parameter:
    StatusCallback = https://our-api.com/api/v1/webhooks/exotel/status?secret=<secret>

Webhook idempotency is handled via Redis — duplicate events from Exotel
(which can send the same event multiple times) are deduplicated with a 24h TTL.
"""
import json

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.integrations.exotel.provider import ExotelProvider
from app.services.call_service import CallService

router = APIRouter()


@router.get("")
async def list_webhooks() -> dict:
    """List registered webhook endpoints (informational)."""
    return {
        "webhooks": [
            {
                "name": "Exotel Status Callback",
                "method": "POST",
                "path": "/api/v1/webhooks/exotel/status",
                "description": "Receives call status updates from Exotel",
            }
        ]
    }

_redis_client: aioredis.Redis | None = None


def _get_redis() -> aioredis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


async def _is_webhook_processed(call_sid: str, event_status: str) -> bool:
    """
    Returns True if this (call_sid, status) combo was already processed.
    Uses Redis SET NX with 24h TTL for idempotency.
    """
    r = _get_redis()
    key = f"webhook:exotel:{call_sid}:{event_status}"
    # SET NX returns True if key was newly set, False if it already existed
    was_set = await r.set(key, "1", ex=86400, nx=True)
    return not was_set   # Already existed → already processed


@router.post("/exotel/status")
async def exotel_status_callback(
    request: Request,
    secret: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """
    Exotel StatusCallback webhook.

    Exotel sends JSON (we configured StatusCallbackContentType=application/json).
    Fields: Sid, Status, Duration, RecordingUrl (and more)

    Status values from Exotel:
    queued, in-progress, ringing, completed, failed, busy, no-answer, canceled
    """
    exotel = ExotelProvider()

    # 1. Validate shared secret
    if not exotel.validate_webhook_secret(secret):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    # 2. Parse body — Exotel sends JSON when configured to do so
    try:
        body: dict = await request.json()
    except Exception:
        # Fallback: try form-data (Exotel may send form-data in some edge cases)
        form = await request.form()
        body = dict(form)

    # 3. Extract fields
    call_sid: str | None = body.get("Sid") or body.get("CallSid")
    raw_status: str | None = body.get("Status") or body.get("CallStatus")
    duration_raw = body.get("Duration") or body.get("CallDuration")
    recording_url: str | None = body.get("RecordingUrl")

    if not call_sid or not raw_status:
        # Malformed webhook — return 200 to stop Exotel retrying
        return Response(status_code=200)

    duration: int | None = int(duration_raw) if duration_raw else None

    # 4. Idempotency check
    if await _is_webhook_processed(call_sid, raw_status):
        return Response(status_code=200)

    # 5. Process status update
    service = CallService(db)
    await service.handle_exotel_status(
        call_sid=call_sid,
        raw_status=raw_status,
        duration=duration,
        recording_url=recording_url,
    )

    return Response(status_code=200)
