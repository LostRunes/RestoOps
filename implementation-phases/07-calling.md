# Phase 7 — Calling: Twilio & WebRTC

> **Goal:** Build the dual calling architecture — Twilio for real phone calls (trial) and WebRTC for browser-to-browser calls. Implement the CallService abstraction, Twilio provider with webhook handling, WebRTC signaling via WebSockets, call state management, and the calls database. After this phase, staff can call leads via phone or browser.

> **Depends on:** Phase 6 (Quotes & Orders)

---

## Step 7.1 — Database Models

Already created in Phase 3 as part of the schema plan. If not yet migrated:

### 7.1.1 — Calls Model

**File:** `apps/api/app/models/call.py`

```text
Table: calls
─────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NULLABLE
lead_id           UUID, FK → leads.id, NOT NULL
conversation_id   UUID, FK → conversations.id, NULLABLE

provider          VARCHAR(20)    # TWILIO, WEBRTC

direction         VARCHAR(10)    # OUTBOUND, INBOUND
from_number       VARCHAR(50), NULLABLE    # Phone number or user identifier
to_number         VARCHAR(50), NULLABLE    # Phone number or peer identifier

status            VARCHAR(20)    
# INITIATED → RINGING → IN_PROGRESS → COMPLETED → FAILED → NO_ANSWER → BUSY → CANCELLED

initiated_by      UUID, FK → users.id, NULLABLE

started_at        TIMESTAMP WITH TZ, NULLABLE
answered_at       TIMESTAMP WITH TZ, NULLABLE
ended_at          TIMESTAMP WITH TZ, NULLABLE

duration_seconds  INTEGER, NULLABLE

recording_url     TEXT, NULLABLE
twilio_call_sid   VARCHAR(100), NULLABLE, UNIQUE

notes             TEXT, NULLABLE

created_at        TIMESTAMP WITH TZ
```

- Index on `organization_id`
- Index on `lead_id`
- Index on `twilio_call_sid`

### 7.1.2 — Call Events Model

**File:** `apps/api/app/models/call_event.py`

```text
Table: call_events
───────────────────
id          UUID, PK
call_id     UUID, FK → calls.id, NOT NULL

event_type  VARCHAR(50)   # INITIATED, RINGING, ANSWERED, ENDED, FAILED, RECORDING_AVAILABLE, STATUS_UPDATE
payload     JSONB, NULLABLE

source      VARCHAR(20)   # SYSTEM, TWILIO_WEBHOOK, WEBRTC_SIGNAL

created_at  TIMESTAMP WITH TZ
```

### 7.1.3 — Migration

```bash
alembic revision --autogenerate -m "add calls and call_events tables"
alembic upgrade head
```

---

## Step 7.2 — Call Provider Abstraction

**File:** `apps/api/app/integrations/call_base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import UUID

@dataclass
class CallRequest:
    lead_id: UUID
    from_identifier: str    # Phone number or user_id
    to_identifier: str      # Phone number or peer user_id
    org_id: UUID
    initiated_by: UUID

@dataclass
class CallResult:
    success: bool
    call_id: str | None         # Provider-specific call ID
    status: str
    error: str | None = None

class CallProvider(ABC):
    @abstractmethod
    async def initiate_call(self, request: CallRequest) -> CallResult:
        """Start a call."""
    
    @abstractmethod
    async def end_call(self, provider_call_id: str) -> bool:
        """End an active call."""
    
    @abstractmethod
    async def get_call_status(self, provider_call_id: str) -> str:
        """Get current call status from provider."""
```

---

## Step 7.3 — Twilio Provider

**File:** `apps/api/app/integrations/twilio/__init__.py`
**File:** `apps/api/app/integrations/twilio/provider.py`

```python
from twilio.rest import Client
from twilio.request_validator import RequestValidator
from app.core.config import settings

class TwilioProvider(CallProvider):
    def __init__(self):
        self.client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.from_number = settings.TWILIO_PHONE_NUMBER
        self.validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    
    async def initiate_call(self, request: CallRequest) -> CallResult:
        """
        1. Create Twilio call:
            call = self.client.calls.create(
                to=request.to_identifier,
                from_=self.from_number,
                url=f"{settings.API_URL}/api/v1/webhooks/twilio/voice/twiml",
                status_callback=f"{settings.API_URL}/api/v1/webhooks/twilio/status",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
            )
        2. Return CallResult(success=True, call_id=call.sid, status="INITIATED")
        
        Error handling:
        - Invalid number → CallResult(success=False, error="...")
        - Twilio not configured → CallResult(success=False, error="Twilio not configured")
        - Trial restrictions → clear error message
        """
    
    async def end_call(self, provider_call_id: str) -> bool:
        """Update call status to 'completed' via Twilio API."""
    
    async def get_call_status(self, provider_call_id: str) -> str:
        """Fetch call status from Twilio API."""
    
    def validate_webhook(self, url: str, params: dict, signature: str) -> bool:
        """Validate Twilio webhook signature. CRITICAL for security."""
        return self.validator.validate(url, params, signature)
```

---

## Step 7.4 — WebRTC Provider

**File:** `apps/api/app/integrations/webrtc/provider.py`

```python
class WebRTCProvider(CallProvider):
    """
    WebRTC doesn't "initiate" calls via an external API.
    Instead, the backend manages signaling state and the browsers
    establish peer connections directly.
    """
    
    async def initiate_call(self, request: CallRequest) -> CallResult:
        """
        1. Create a call room (unique room_id)
        2. Store room state in Redis (or DB)
        3. Generate invite link/token for the peer
        4. Return CallResult with room_id
        
        The actual WebRTC connection is established via WebSocket signaling.
        """
    
    async def end_call(self, provider_call_id: str) -> bool:
        """Clean up room state, notify connected peers."""
    
    async def get_call_status(self, provider_call_id: str) -> str:
        """Check room state from Redis/DB."""
```

### WebRTC Room Manager

**File:** `apps/api/app/integrations/webrtc/room_manager.py`

```python
import redis.asyncio as redis

class WebRTCRoomManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def create_room(self, room_id: str, caller_id: str, callee_id: str) -> dict:
        """
        Store in Redis:
        Key: f"webrtc:room:{room_id}"
        Value: {"caller_id": ..., "callee_id": ..., "status": "WAITING", "created_at": ...}
        TTL: 3600 (1 hour)
        """
    
    async def join_room(self, room_id: str, user_id: str) -> dict | None:
        """Mark participant as joined. Return room info."""
    
    async def get_room(self, room_id: str) -> dict | None:
        """Get room state."""
    
    async def close_room(self, room_id: str) -> None:
        """Remove room from Redis."""
```

---

## Step 7.5 — Call Service (Facade)

**File:** `apps/api/app/services/call_service.py`

```python
class CallService:
    def __init__(self, twilio_provider: TwilioProvider, 
                 webrtc_provider: WebRTCProvider,
                 call_repo: CallRepository):
        ...
    
    async def start_call(self, org_id, lead_id, provider_type: str,
                         from_id: str, to_id: str, initiated_by: UUID) -> Call:
        """
        1. Select provider based on provider_type (TWILIO or WEBRTC)
        2. Create call record in DB (status=INITIATED)
        3. Call provider.initiate_call()
        4. Update call record with provider call ID
        5. Create call_event (INITIATED)
        6. Create lead_activity (CALL_STARTED)
        7. Create/update conversation (channel=VOICE or WEBRTC)
        8. Return call record
        """
    
    async def end_call(self, call_id: UUID, org_id: UUID) -> Call:
        """
        1. Fetch call
        2. Call provider.end_call()
        3. Update call status → COMPLETED, ended_at, duration
        4. Create call_event (ENDED)
        5. Create lead_activity (CALL_COMPLETED)
        6. Return call
        """
    
    async def handle_twilio_status(self, call_sid: str, status: str, 
                                    duration: int | None = None) -> None:
        """
        Called by Twilio webhook handler.
        1. Find call by twilio_call_sid
        2. Map Twilio status → our status
        3. Update call record
        4. Create call_event
        5. If completed: calculate duration, create notification
        """
    
    async def get_call(self, call_id, org_id) -> Call: ...
    async def list_calls(self, org_id, lead_id=None) -> list[Call]: ...
```

---

## Step 7.6 — WebSocket Signaling Server

**File:** `apps/api/app/api/websockets/webrtc_ws.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
import json

class WebRTCSignalingManager:
    """Manages WebSocket connections for WebRTC signaling."""
    
    def __init__(self):
        self.rooms: dict[str, dict[str, WebSocket]] = {}
        # rooms[room_id][user_id] = websocket
    
    async def connect(self, websocket: WebSocket, room_id: str, user_id: str):
        """
        1. Accept WebSocket
        2. Add to room
        3. Notify other participant(s) of join
        """
    
    async def disconnect(self, room_id: str, user_id: str):
        """Remove from room, notify peers."""
    
    async def relay_message(self, room_id: str, sender_id: str, message: dict):
        """
        Relay signaling messages to other participants in the room.
        
        Message types:
        - offer: SDP offer
        - answer: SDP answer
        - ice-candidate: ICE candidate
        - hangup: Call ended
        """

signaling_manager = WebRTCSignalingManager()

# WebSocket endpoint
@router.websocket("/ws/webrtc/{room_id}")
async def webrtc_signaling(websocket: WebSocket, room_id: str):
    """
    1. Authenticate user from query params or first message
    2. Connect to room
    3. Loop: receive messages, relay to peers
    4. On disconnect: clean up
    
    Message protocol:
    {
        "type": "offer" | "answer" | "ice-candidate" | "hangup",
        "payload": {...},  # SDP or ICE candidate data
        "from": "user_id"
    }
    """
    # Authenticate
    user_id = await authenticate_ws(websocket)
    await signaling_manager.connect(websocket, room_id, user_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            await signaling_manager.relay_message(room_id, user_id, message)
    except WebSocketDisconnect:
        await signaling_manager.disconnect(room_id, user_id)
```

---

## Step 7.7 — Twilio Webhook Handlers

**File:** `apps/api/app/api/webhooks.py`

```python
from fastapi import Request, Response
from twilio.twiml.voice_response import VoiceResponse

@router.post("/api/v1/webhooks/twilio/voice/twiml")
async def twilio_voice_twiml(request: Request):
    """
    Called when Twilio connects the call.
    Returns TwiML instructions.
    
    1. Validate webhook signature (CRITICAL)
    2. Return TwiML:
        <Response>
            <Say>Connecting your call...</Say>
            <Dial>
                <Number>{to_number}</Number>
            </Dial>
        </Response>
    """
    # Validate signature
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    if not twilio_provider.validate_webhook(str(request.url), dict(form_data), signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    
    response = VoiceResponse()
    response.say("Connecting your call from RestoOps.")
    response.dial(form_data.get("To"))
    
    return Response(content=str(response), media_type="application/xml")

@router.post("/api/v1/webhooks/twilio/status")
async def twilio_status_callback(request: Request):
    """
    Called by Twilio with call status updates.
    
    1. Validate webhook signature
    2. Extract: CallSid, CallStatus, CallDuration
    3. Call CallService.handle_twilio_status()
    4. Handle idempotency (same webhook may arrive multiple times)
    """
    form_data = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    
    if not twilio_provider.validate_webhook(str(request.url), dict(form_data), signature):
        raise HTTPException(status_code=403, detail="Invalid webhook signature")
    
    call_sid = form_data.get("CallSid")
    status = form_data.get("CallStatus")
    duration = form_data.get("CallDuration")
    
    await call_service.handle_twilio_status(call_sid, status, int(duration) if duration else None)
    
    return Response(status_code=200)
```

### Idempotency for Webhooks

```python
async def is_webhook_processed(call_sid: str, event: str) -> bool:
    """
    Check Redis for f"webhook:{call_sid}:{event}".
    If exists → already processed, skip.
    If not → set with TTL 24h, process.
    """
```

---

## Step 7.8 — Call Repository

**File:** `apps/api/app/repositories/call_repo.py`

```python
class CallRepository:
    async def create(self, **data) -> Call: ...
    async def get_by_id(self, call_id, org_id) -> Call | None: ...
    async def get_by_twilio_sid(self, call_sid: str) -> Call | None: ...
    async def list_by_org(self, org_id, lead_id=None) -> list[Call]: ...
    async def update(self, call_id, **data) -> Call: ...
    
    async def add_event(self, call_id, event_type, payload=None, source="SYSTEM") -> CallEvent: ...
    async def get_events(self, call_id) -> list[CallEvent]: ...
```

---

## Step 7.9 — API Routes

### `apps/api/app/api/calls.py`

```text
POST  /api/v1/calls                → Start a call (phone or browser)
GET   /api/v1/calls                → List calls (with filters)
GET   /api/v1/calls/{id}           → Get call details (with events)
POST  /api/v1/calls/{id}/end       → End an active call
GET   /api/v1/calls/{id}/status    → Get current call status
GET   /api/v1/calls/{id}/events    → Get call events
```

### Call Create Request

```python
class CallCreateRequest(BaseModel):
    lead_id: UUID
    provider: str   # "TWILIO" or "WEBRTC"
    to: str         # Phone number (Twilio) or user_id (WebRTC)
```

### Register Routers

```python
from app.api import calls, webhooks
from app.api.websockets import webrtc_ws

app.include_router(calls.router, prefix="/api/v1/calls", tags=["calls"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])

# WebSocket route registered directly on app
app.include_router(webrtc_ws.router)
```

---

## Step 7.10 — Pydantic Schemas

**File:** `apps/api/app/schemas/call.py`

```python
# CallCreateRequest: lead_id, provider (TWILIO|WEBRTC), to
# CallResponse: all fields + events summary
# CallEventResponse: event_type, payload, source, created_at
# CallStatusResponse: status, duration, provider
```

---

## Step 7.11 — STUN Configuration

For development, use Google's public STUN server:

```python
STUN_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
]
```

These are returned to the frontend when initiating a WebRTC call so the browser knows where to discover its network info.

---

## Phase 7 Completion Checklist

- [ ] `calls` table created with all fields
- [ ] `call_events` table created
- [ ] Alembic migration applied
- [ ] Call provider abstraction: `CallProvider` base class
- [ ] Twilio provider: can initiate calls via Twilio API
- [ ] Twilio provider: can end calls
- [ ] Twilio provider: webhook signature validation works
- [ ] Twilio TwiML endpoint: returns valid TwiML for call connect
- [ ] Twilio status callback: processes status updates
- [ ] Webhook idempotency: prevents duplicate processing
- [ ] WebRTC provider: creates rooms, manages state in Redis
- [ ] WebRTC room manager: create, join, close rooms
- [ ] WebSocket signaling: connects peers, relays offer/answer/ICE
- [ ] WebSocket authentication works
- [ ] Call service facade: start_call(), end_call(), handle_twilio_status()
- [ ] Call records: status transitions tracked
- [ ] Call events: logged for each state change
- [ ] Call API: start, list, get, end, status, events
- [ ] Lead activity logged on call events
- [ ] Conversation created/updated on call start
- [ ] STUN server configuration available
- [ ] All queries scoped to organization_id
- [ ] `git commit -m "Phase 7: Twilio calling, WebRTC, signaling"`

---

## Transition to Phase 8

Once all boxes are checked, proceed to [08-notifications-events.md](./08-notifications-events.md).

Phase 8 will add the unified notification system, event-driven architecture, WebSocket delivery for real-time notifications, and the notification API.
