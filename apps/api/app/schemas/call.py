from datetime import datetime
from typing import Any
from pydantic import BaseModel, field_validator


class CallCreateRequest(BaseModel):
    lead_id: str
    provider: str               # EXOTEL or WEBRTC
    to: str                     # Lead's phone (Exotel) or peer user_id (WebRTC)
    from_number: str            # Agent's phone (Exotel) or own user_id (WebRTC)
    restaurant_id: str | None = None
    conversation_id: str | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, v: str) -> str:
        if v.upper() not in ("EXOTEL", "WEBRTC"):
            raise ValueError("provider must be EXOTEL or WEBRTC")
        return v.upper()


class CallEndRequest(BaseModel):
    notes: str | None = None


class CallEventResponse(BaseModel):
    id: str
    call_id: str
    event_type: str
    payload: dict | None
    source: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CallResponse(BaseModel):
    id: str
    organization_id: str
    lead_id: str
    restaurant_id: str | None
    conversation_id: str | None
    provider: str
    direction: str
    from_number: str | None
    to_number: str | None
    status: str
    initiated_by: str | None
    started_at: datetime | None
    answered_at: datetime | None
    ended_at: datetime | None
    duration_seconds: int | None
    recording_url: str | None
    exotel_call_sid: str | None
    notes: str | None
    created_at: datetime
    events: list[CallEventResponse] = []

    model_config = {"from_attributes": True}


class CallStatusResponse(BaseModel):
    call_id: str
    status: str
    provider: str
    duration_seconds: int | None
    exotel_call_sid: str | None


class StunServersResponse(BaseModel):
    stun_servers: list[dict[str, Any]]
