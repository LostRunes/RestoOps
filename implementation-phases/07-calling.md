# Phase 7 — Calling: Exotel & WebRTC

> **Goal:** Build the dual calling architecture — Exotel for real PSTN phone calls and WebRTC for browser-to-browser calls. Implement the `CallService` abstraction, Exotel provider with status-callback webhook handling, WebRTC signaling via WebSockets, call state management, and the calls database. After this phase, staff can call leads via phone (through Exotel) or browser (via WebRTC).

> **Depends on:** Phase 6 (Quotes & Orders)

---

## Exotel Background

Exotel is our Twilio replacement — an Indian cloud telephony provider with a Twilio-compatible REST API structure.

### Key Differences From Twilio

| Aspect | Twilio | Exotel |
|---|---|---|
| Auth | `AccountSID:AuthToken` | `APIKey:APIToken` |
| Base URL | `api.twilio.com/2010-04-01/Accounts/{SID}/Calls` | `api.exotel.com/v1/Accounts/{SID}/Calls/connect` |
| Call Initiation | `calls.create(...)` | POST form-data to `/Calls/connect` |
| TwiML | XML response from a URL you host | Not needed for click-to-call |
| Webhook Signature Validation | HMAC-SHA1 via `RequestValidator` | No built-in signature — validate secret query param |
| Status Keys | `CallStatus`, `CallSid` | `Status`, `Sid` |

### Our Exotel Credentials

```
Account SID (SID):  restoops1
API Key:            a408902b0d23a83757cabed10fecf939d1a9487fbf3511d0
API Token:          57e00381d729c4d862fab7c161c8b9e0484b3c2029548900
Region / Subdomain: api.exotel.com  (Singapore)
Caller ID (ExoPhone): 08047284815
Trial Number:       09513886363
```

> **Trial restriction:** On Exotel trial, calls can only be made **to numbers that are registered / verified** in your Exotel account (same as Twilio trial). The verified numbers are `07667408570` and `06370099540` (visible in your dashboard screenshot).

---

## Step 7.1 — Database Models

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

provider          VARCHAR(20)    # EXOTEL, WEBRTC

direction         VARCHAR(10)    # OUTBOUND, INBOUND
from_number       VARCHAR(50), NULLABLE
to_number         VARCHAR(50), NULLABLE

status            VARCHAR(20)
# INITIATED → RINGING → IN_PROGRESS → COMPLETED → FAILED → NO_ANSWER → BUSY → CANCELLED

initiated_by      UUID, FK → users.id, NULLABLE

started_at        TIMESTAMP WITH TZ, NULLABLE
answered_at       TIMESTAMP WITH TZ, NULLABLE
ended_at          TIMESTAMP WITH TZ, NULLABLE

duration_seconds  INTEGER, NULLABLE

recording_url     TEXT, NULLABLE
exotel_call_sid   VARCHAR(100), NULLABLE, UNIQUE    # was twilio_call_sid

notes             TEXT, NULLABLE

created_at        TIMESTAMP WITH TZ
```

- Index on `organization_id`
- Index on `lead_id`
- Index on `exotel_call_sid`

### 7.1.2 — Call Events Model

**File:** `apps/api/app/models/call_event.py`

```text
Table: call_events
───────────────────
id          UUID, PK
call_id     UUID, FK → calls.id, NOT NULL

event_type  VARCHAR(50)   # INITIATED, RINGING, ANSWERED, ENDED, FAILED, RECORDING_AVAILABLE, STATUS_UPDATE
payload     JSONB, NULLABLE

source      VARCHAR(20)   # SYSTEM, EXOTEL_WEBHOOK, WEBRTC_SIGNAL

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
    from_identifier: str    # ExoPhone number or user_id
    to_identifier: str      # Destination phone number or peer user_id
    org_id: UUID
    initiated_by: UUID

@dataclass
class CallResult:
    success: bool
    call_id: str | None         # Provider-specific call ID (Exotel Sid, or room_id for WebRTC)
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

## Step 7.3 — Exotel Provider

**File:** `apps/api/app/integrations/exotel/__init__.py`  
**File:** `apps/api/app/integrations/exotel/provider.py`

### How Exotel Click-to-Call Works

Exotel's "Connect Two Numbers" API is a **click-to-call** mechanism:
1. Exotel calls **Person A** (the agent/staff member) using the ExoPhone.
2. When Person A answers, Exotel then calls **Person B** (the lead/customer).
3. Both are bridged together.

So `From` = agent's phone, `To` = lead's phone, `CallerId` = our ExoPhone (`08047284815`).

```python
import httpx
from app.core.config import settings
from app.integrations.call_base import CallProvider, CallRequest, CallResult


EXOTEL_BASE_URL = "https://{subdomain}/v1/Accounts/{sid}/Calls/connect"

# Exotel status → Our status mapping
EXOTEL_STATUS_MAP = {
    "queued":      "INITIATED",
    "in-progress": "IN_PROGRESS",
    "ringing":     "RINGING",
    "completed":   "COMPLETED",
    "failed":      "FAILED",
    "busy":        "BUSY",
    "no-answer":   "NO_ANSWER",
    "canceled":    "CANCELLED",
}


class ExotelProvider(CallProvider):
    def __init__(self):
        self.api_key = settings.EXOTEL_API_KEY
        self.api_token = settings.EXOTEL_API_TOKEN
        self.account_sid = settings.EXOTEL_ACCOUNT_SID
        self.caller_id = settings.EXOTEL_CALLER_ID         # 08047284815
        self.subdomain = settings.EXOTEL_SUBDOMAIN         # api.exotel.com
        self.base_url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}/Calls/connect"
    
    async def initiate_call(self, request: CallRequest) -> CallResult:
        """
        POST form-data to Exotel's /Calls/connect endpoint.
        
        From       = agent's phone number (who to call first)
        To         = lead's phone number (who to connect to)
        CallerId   = our ExoPhone number (08047284815)
        Record     = true
        StatusCallback = our webhook URL
        StatusCallbackEvents = terminal,answered
        StatusCallbackContentType = application/json
        """
        if not all([self.api_key, self.api_token, self.account_sid]):
            return CallResult(success=False, call_id=None,
                              status="FAILED", error="Exotel not configured")
        
        callback_url = (
            f"{settings.API_URL}/api/v1/webhooks/exotel/status"
            f"?secret={settings.EXOTEL_WEBHOOK_SECRET}"
        )
        
        data = {
            "From":                     request.from_identifier,   # agent phone
            "To":                       request.to_identifier,     # lead phone
            "CallerId":                 self.caller_id,
            "Record":                   "true",
            "StatusCallback":           callback_url,
            "StatusCallbackEvents":     "terminal,answered",
            "StatusCallbackContentType": "application/json",
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    data=data,
                    auth=(self.api_key, self.api_token),
                    timeout=15.0,
                )
                if response.status_code in (200, 201):
                    body = response.json()
                    call_data = body.get("Call", {})
                    sid = call_data.get("Sid")
                    raw_status = call_data.get("Status", "queued")
                    mapped_status = EXOTEL_STATUS_MAP.get(raw_status, "INITIATED")
                    return CallResult(success=True, call_id=sid, status=mapped_status)
                else:
                    error_body = response.text
                    return CallResult(success=False, call_id=None,
                                      status="FAILED", error=f"Exotel error {response.status_code}: {error_body}")
            except httpx.ConnectError:
                return CallResult(success=False, call_id=None,
                                  status="FAILED", error="Cannot connect to Exotel API")
            except httpx.TimeoutException:
                return CallResult(success=False, call_id=None,
                                  status="FAILED", error="Exotel API timeout")
    
    async def end_call(self, provider_call_id: str) -> bool:
        """
        Exotel does not have a direct "end call" REST endpoint in v1.
        The call is considered ended when Exotel sends the terminal status webhook.
        For now, we mark the call as CANCELLED in our DB and return True.
        In production you'd use Exotel's call leg hangup API if available on your plan.
        """
        return True
    
    async def get_call_status(self, provider_call_id: str) -> str:
        """
        GET /v1/Accounts/{sid}/Calls/{CallSid}.json
        Returns current Exotel status, mapped to our status.
        """
        url = f"https://{self.subdomain}/v1/Accounts/{self.account_sid}/Calls/{provider_call_id}.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                auth=(self.api_key, self.api_token),
                timeout=10.0,
            )
            if response.status_code == 200:
                body = response.json()
                raw_status = body.get("Call", {}).get("Status", "")
                return EXOTEL_STATUS_MAP.get(raw_status, "UNKNOWN")
        return "UNKNOWN"
    
    def validate_webhook_secret(self, secret: str) -> bool:
        """
        Exotel does not sign webhooks like Twilio.
        We pass a `?secret=...` query parameter in StatusCallback URL
        and validate it here.
        """
        return secret == settings.EXOTEL_WEBHOOK_SECRET
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
        1. Create a call room (unique room_id = UUID)
        2. Store room state in Redis with TTL 3600s
        3. Return CallResult with room_id as call_id
        
        The actual WebRTC connection is established via WebSocket signaling.
        """
    
    async def end_call(self, provider_call_id: str) -> bool:
        """Clean up room state, notify connected peers via WebSocket."""
    
    async def get_call_status(self, provider_call_id: str) -> str:
        """Check room state from Redis."""
```

### WebRTC Room Manager

**File:** `apps/api/app/integrations/webrtc/room_manager.py`

```python
import redis.asyncio as redis
import json, uuid
from datetime import datetime

class WebRTCRoomManager:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def create_room(self, caller_id: str, callee_id: str) -> dict:
        """
        Store in Redis:
        Key: f"webrtc:room:{room_id}"
        Value: {"caller_id": ..., "callee_id": ..., "status": "WAITING", "created_at": ...}
        TTL: 3600 (1 hour)
        Returns room dict with room_id.
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
    def __init__(self, exotel_provider: ExotelProvider,
                 webrtc_provider: WebRTCProvider,
                 call_repo: CallRepository):
        ...
    
    async def start_call(self, org_id, lead_id, provider_type: str,
                         from_id: str, to_id: str, initiated_by: UUID) -> Call:
        """
        provider_type: "EXOTEL" or "WEBRTC"
        
        1. Select provider
        2. Create call record in DB (status=INITIATED)
        3. Call provider.initiate_call()
        4. Update call record with provider call ID (exotel_call_sid)
        5. Create call_event (INITIATED)
        6. Create lead_activity (CALL_STARTED)
        7. Create/update conversation (channel=VOICE or WEBRTC)
        8. Return call record
        """
    
    async def end_call(self, call_id: UUID, org_id: UUID) -> Call:
        """
        1. Fetch call
        2. Call provider.end_call()
        3. Update call status → CANCELLED (manual end before completion)
        4. Create call_event (ENDED)
        5. Return call
        """
    
    async def handle_exotel_status(self, call_sid: str, status: str,
                                    duration: int | None = None,
                                    recording_url: str | None = None) -> None:
        """
        Called by Exotel status webhook handler.
        1. Find call by exotel_call_sid
        2. Map Exotel status → our status (use EXOTEL_STATUS_MAP)
        3. Update call record (status, ended_at, duration_seconds, recording_url)
        4. Create call_event (STATUS_UPDATE or ENDED)
        5. If terminal status (completed/failed/busy/no-answer): create notification
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

## Step 7.7 — Exotel Webhook Handler

**File:** `apps/api/app/api/webhooks.py`

> **Note:** Unlike Twilio, Exotel does **not** need a TwiML response URL for click-to-call. The only webhook we handle is the `StatusCallback`.

```python
from fastapi import Request, Response, HTTPException, Query
import json

@router.post("/api/v1/webhooks/exotel/status")
async def exotel_status_callback(
    request: Request,
    secret: str = Query(...),
    exotel_provider: ExotelProvider = Depends(get_exotel_provider),
    call_service: CallService = Depends(get_call_service),
):
    """
    Called by Exotel with call status updates.
    We asked for JSON format via StatusCallbackContentType=application/json.
    
    1. Validate the secret query parameter
    2. Parse JSON body
    3. Extract: Sid (CallSid), Status, Duration, RecordingUrl
    4. Call call_service.handle_exotel_status()
    5. Handle idempotency (same webhook may arrive multiple times)
    """
    # Validate shared secret
    if not exotel_provider.validate_webhook_secret(secret):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")
    
    # Exotel sends JSON when StatusCallbackContentType=application/json
    body = await request.json()
    
    call_sid     = body.get("Sid") or body.get("CallSid")
    status       = body.get("Status") or body.get("CallStatus")
    duration     = body.get("Duration") or body.get("CallDuration")
    recording    = body.get("RecordingUrl")
    
    # Idempotency: skip if already processed
    if await is_webhook_processed(call_sid, status):
        return Response(status_code=200)
    
    await call_service.handle_exotel_status(
        call_sid=call_sid,
        status=status,
        duration=int(duration) if duration else None,
        recording_url=recording,
    )
    
    return Response(status_code=200)
```

### Idempotency for Webhooks

```python
async def is_webhook_processed(call_sid: str, event: str) -> bool:
    """
    Check Redis for f"webhook:exotel:{call_sid}:{event}".
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
    async def get_by_exotel_sid(self, call_sid: str) -> Call | None: ...   # was get_by_twilio_sid
    async def list_by_org(self, org_id, lead_id=None) -> list[Call]: ...
    async def update(self, call_id, **data) -> Call: ...
    
    async def add_event(self, call_id, event_type, payload=None, source="SYSTEM") -> CallEvent: ...
    async def get_events(self, call_id) -> list[CallEvent]: ...
```

---

## Step 7.9 — API Routes

### `apps/api/app/api/calls.py`

```text
POST  /api/v1/calls                → Start a call (EXOTEL or WEBRTC)
GET   /api/v1/calls                → List calls (with filters)
GET   /api/v1/calls/{id}           → Get call details (with events)
POST  /api/v1/calls/{id}/end       → End / cancel an active call
GET   /api/v1/calls/{id}/status    → Get current call status
GET   /api/v1/calls/{id}/events    → Get call events
```

### Call Create Request

```python
class CallCreateRequest(BaseModel):
    lead_id: UUID
    provider: str   # "EXOTEL" or "WEBRTC"
    to: str         # Lead's phone number (Exotel) or peer user_id (WebRTC)
    from_: str      # Agent's phone number (Exotel) or own user_id (WebRTC)
                    # field_alias="from" in schema
```

### Register Routers

```python
from app.api import calls, webhooks
from app.api.websockets import webrtc_ws

app.include_router(calls.router, prefix="/api/v1/calls", tags=["calls"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["webhooks"])
app.include_router(webrtc_ws.router)  # WebSocket registered directly
```

---

## Step 7.10 — Pydantic Schemas

**File:** `apps/api/app/schemas/call.py`

```python
# CallCreateRequest: lead_id, provider (EXOTEL|WEBRTC), to, from_
# CallResponse: all fields + events summary
# CallEventResponse: event_type, payload, source, created_at
# CallStatusResponse: status, duration, provider, exotel_call_sid
```

---

## Step 7.11 — Config Updates

### `.env` additions

```env
# Exotel Configuration (Phase 7)
EXOTEL_ACCOUNT_SID=restoops1
EXOTEL_API_KEY=a408902b0d23a83757cabed10fecf939d1a9487fbf3511d0
EXOTEL_API_TOKEN=57e00381d729c4d862fab7c161c8b9e0484b3c2029548900
EXOTEL_CALLER_ID=08047284815
EXOTEL_SUBDOMAIN=api.exotel.com
EXOTEL_WEBHOOK_SECRET=restoops-exotel-webhook-secret-change-me
```

### `apps/api/app/core/config.py` additions

```python
# Exotel
EXOTEL_ACCOUNT_SID: str = ""
EXOTEL_API_KEY: str = ""
EXOTEL_API_TOKEN: str = ""
EXOTEL_CALLER_ID: str = ""
EXOTEL_SUBDOMAIN: str = "api.exotel.com"
EXOTEL_WEBHOOK_SECRET: str = "change-me"

@property
def exotel_configured(self) -> bool:
    return bool(self.EXOTEL_API_KEY and self.EXOTEL_API_TOKEN and self.EXOTEL_ACCOUNT_SID)
```

---

## Step 7.12 — STUN Configuration (WebRTC)

For development, use Google's public STUN servers (free, no account needed):

```python
STUN_SERVERS = [
    {"urls": "stun:stun.l.google.com:19302"},
    {"urls": "stun:stun1.l.google.com:19302"},
]
```

Returned to frontend when initiating a WebRTC call so the browser can discover its public network address.

---

## Step 7.13 — Dependencies

Add to `apps/api/requirements.txt`:
```
httpx>=0.27.0       # Already present for async HTTP — used to call Exotel REST API
```

No additional package needed. Exotel's API is plain REST over HTTPS with Basic Auth —
we use `httpx` (already installed) rather than an SDK.

> **No `twilio` package needed.** Remove it from requirements if it was added.

---

## Trial Account Restrictions

On the free trial:
- Calls can **only** be placed to numbers registered in your Exotel account.
- Verified numbers from the dashboard: `07667408570` and `06370099540`.
- The ExoPhone number is `08047284815`.
- You can test by calling from `07667408570` (agent) → to `06370099540` (lead).

---

## Phase 7 Completion Checklist

- [ ] `calls` table created with `exotel_call_sid` field
- [ ] `call_events` table created
- [ ] Alembic migration applied
- [ ] Call provider abstraction: `CallProvider` base class
- [ ] Exotel provider: `initiate_call()` via REST POST to `/Calls/connect`
- [ ] Exotel provider: `get_call_status()` via REST GET
- [ ] Exotel provider: `validate_webhook_secret()` checks shared secret
- [ ] Exotel status webhook: receives JSON, validates secret, updates call
- [ ] Webhook idempotency: prevents duplicate processing via Redis
- [ ] WebRTC provider: creates rooms, manages state in Redis
- [ ] WebRTC room manager: create, join, close rooms
- [ ] WebSocket signaling: connects peers, relays offer/answer/ICE
- [ ] WebSocket authentication works
- [ ] Call service facade: `start_call()`, `end_call()`, `handle_exotel_status()`
- [ ] Call records: status transitions tracked
- [ ] Call events: logged for each state change
- [ ] Call API: start, list, get, end, status, events
- [ ] Lead activity logged on call events
- [ ] Conversation created/updated on call start
- [ ] STUN server configuration available via API
- [ ] All queries scoped to `organization_id`
- [ ] `.env` updated with Exotel credentials
- [ ] `git commit -m "Phase 7: Exotel calling, WebRTC signaling"`

---

## Transition to Phase 8

Once all boxes are checked, proceed to [08-notifications-events.md](./08-notifications-events.md).

Phase 8 will add the unified notification system, event-driven architecture, WebSocket delivery for real-time notifications, and the notification API.
