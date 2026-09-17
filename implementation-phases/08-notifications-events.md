# Phase 8 — Notifications, Events & Real-Time

> **Goal:** Build the unified notification system, the internal event bus, WebSocket delivery for real-time push notifications, and the notification management API. After this phase, events across the system trigger notifications that appear in real-time on the frontend.

> **Depends on:** Phase 7 (Calling)

---

## Step 8.1 — Database Model

The `notifications` table was specified in the spec. Ensure it's created:

### 8.1.1 — Notification Model

**File:** `apps/api/app/models/notification.py`

```text
Table: notifications
─────────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
user_id           UUID, FK → users.id, NOT NULL   # Who receives this notification

type              VARCHAR(50), NOT NULL
# LEAD_REPLIED, QUOTE_REQUESTED, QUOTE_ACCEPTED, QUOTE_REJECTED, QUOTE_EXPIRED
# CALL_COMPLETED, HIGH_VALUE_LEAD, CAMPAIGN_COMPLETED, FOLLOWUP_DUE
# AI_ACTION_PROPOSED, AI_ACTION_APPROVED, AI_ACTION_REJECTED
# ORDER_CREATED, VERIFICATION_COMPLETED, LEAD_IMPORTED

title             VARCHAR(255), NOT NULL
body              TEXT, NOT NULL

entity_type       VARCHAR(50), NULLABLE    # lead, quote, order, campaign, conversation, ai_action
entity_id         UUID, NULLABLE           # ID of related entity

priority          VARCHAR(20), default 'NORMAL'   # LOW, NORMAL, HIGH, URGENT

is_read           BOOLEAN, default false
read_at           TIMESTAMP WITH TZ, NULLABLE

metadata          JSONB, NULLABLE          # Extra data (e.g., lead name, quote number)

created_at        TIMESTAMP WITH TZ
```

- Index on `(user_id, is_read)`
- Index on `(organization_id, created_at)`
- Index on `user_id` with `is_read = false` partial index (for unread count)

### 8.1.2 — Migration

```bash
alembic revision --autogenerate -m "add notifications table"
alembic upgrade head
```

---

## Step 8.2 — Internal Event Bus

**File:** `apps/api/app/core/events.py`

```python
from typing import Callable, Any
from enum import Enum

class EventType(str, Enum):
    # Leads
    LEAD_CREATED = "LEAD_CREATED"
    LEAD_UPDATED = "LEAD_UPDATED"
    LEAD_VERIFIED = "LEAD_VERIFIED"
    LEAD_REPLIED = "LEAD_REPLIED"
    LEAD_IMPORTED = "LEAD_IMPORTED"
    
    # Campaigns
    CAMPAIGN_STARTED = "CAMPAIGN_STARTED"
    CAMPAIGN_COMPLETED = "CAMPAIGN_COMPLETED"
    CAMPAIGN_PAUSED = "CAMPAIGN_PAUSED"
    
    # Quotes
    QUOTE_CREATED = "QUOTE_CREATED"
    QUOTE_SENT = "QUOTE_SENT"
    QUOTE_VIEWED = "QUOTE_VIEWED"
    QUOTE_ACCEPTED = "QUOTE_ACCEPTED"
    QUOTE_REJECTED = "QUOTE_REJECTED"
    QUOTE_EXPIRED = "QUOTE_EXPIRED"
    
    # Orders
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_COMPLETED = "ORDER_COMPLETED"
    
    # Calls
    CALL_STARTED = "CALL_STARTED"
    CALL_ANSWERED = "CALL_ANSWERED"
    CALL_ENDED = "CALL_ENDED"
    
    # AI
    AI_ACTION_PROPOSED = "AI_ACTION_PROPOSED"
    AI_ACTION_APPROVED = "AI_ACTION_APPROVED"
    AI_ACTION_REJECTED = "AI_ACTION_REJECTED"
    
    # Jobs
    VERIFICATION_COMPLETED = "VERIFICATION_COMPLETED"
    JOB_COMPLETED = "JOB_COMPLETED"
    JOB_FAILED = "JOB_FAILED"
    
    # Follow-ups
    FOLLOWUP_DUE = "FOLLOWUP_DUE"


class Event:
    def __init__(self, type: EventType, org_id: str, data: dict,
                 user_id: str | None = None):
        self.type = type
        self.org_id = org_id
        self.user_id = user_id
        self.data = data


class EventBus:
    """Simple in-process event bus with async handlers."""
    
    _handlers: dict[EventType, list[Callable]] = {}
    
    @classmethod
    def subscribe(cls, event_type: EventType, handler: Callable):
        """Register a handler for an event type."""
        if event_type not in cls._handlers:
            cls._handlers[event_type] = []
        cls._handlers[event_type].append(handler)
    
    @classmethod
    async def publish(cls, event: Event):
        """
        Publish event to all registered handlers.
        Handlers run asynchronously but errors are logged, not propagated.
        """
        handlers = cls._handlers.get(event.type, [])
        for handler in handlers:
            try:
                await handler(event)
            except Exception as e:
                # Log error but don't block the publisher
                logger.error("Event handler failed", 
                           event=event.type, error=str(e))
```

---

## Step 8.3 — Notification Service

**File:** `apps/api/app/services/notification_service.py`

```python
class NotificationService:
    def __init__(self, notification_repo: NotificationRepository,
                 ws_manager: NotificationWSManager):
        ...
    
    async def create_notification(self, org_id, user_id, type, title, body,
                                   entity_type=None, entity_id=None,
                                   priority="NORMAL", metadata=None) -> Notification:
        """
        1. Create notification record in DB
        2. Push to WebSocket if user is connected
        3. Return notification
        """
    
    async def create_for_org_admins(self, org_id, type, title, body, **kwargs):
        """Create notification for all OWNER/ADMIN users in the org."""
    
    async def create_for_org_role(self, org_id, role: str, type, title, body, **kwargs):
        """Create notification for all users with a specific role."""
    
    async def mark_read(self, notification_id, user_id) -> None:
        """Mark single notification as read."""
    
    async def mark_all_read(self, user_id) -> None:
        """Mark all unread notifications as read."""
    
    async def get_unread_count(self, user_id) -> int:
        """Fast count of unread notifications."""
    
    async def list_notifications(self, user_id, page=1, page_size=20,
                                  unread_only=False) -> tuple[list, int]:
        """Paginated list of notifications."""
    
    async def delete_notification(self, notification_id, user_id) -> None: ...
```

---

## Step 8.4 — Notification Event Handlers

**File:** `apps/api/app/services/notification_handlers.py`

```python
"""
Register event handlers that create notifications.
These are the bridges between the event bus and the notification service.
"""

async def on_lead_replied(event: Event):
    """
    Event: LEAD_REPLIED
    Notify: All ADMIN/MANAGER/AGENT users in the org
    Title: "New reply from {lead.contact_name}"
    Body: "Lead {lead.company_name} replied to your email."
    Entity: lead, lead_id
    Priority: HIGH
    """

async def on_quote_accepted(event: Event):
    """
    Event: QUOTE_ACCEPTED
    Notify: OWNER, ADMIN, quote creator
    Title: "Quote {quote_number} accepted!"
    Body: "{lead.company_name} accepted the quote for {guest_count} guests."
    Entity: quote, quote_id
    Priority: URGENT
    """

async def on_ai_action_proposed(event: Event):
    """
    Event: AI_ACTION_PROPOSED
    Notify: ADMIN, MANAGER
    Title: "AI suggested: {action_description}"
    Body: "Review and approve the AI's recommendation."
    Entity: ai_action, action_id
    Priority: HIGH
    """

async def on_call_completed(event: Event):
    """
    Event: CALL_ENDED
    Notify: Call initiator
    Title: "Call completed with {lead.contact_name}"
    Body: "Duration: {duration} seconds"
    Entity: call, call_id
    """

async def on_campaign_completed(event: Event):
    """
    Event: CAMPAIGN_COMPLETED
    Notify: Campaign creator, ADMIN
    Title: "Campaign '{campaign.name}' completed"
    Body: "{total} leads contacted, {replied} replies received."
    Entity: campaign, campaign_id
    """

async def on_verification_completed(event: Event):
    """
    Event: VERIFICATION_COMPLETED
    Notify: Job creator
    Title: "Verification job completed"
    Body: "{valid} valid, {invalid} invalid, {risky} risky out of {total}"
    Entity: job, job_id
    """

async def on_followup_due(event: Event):
    """
    Event: FOLLOWUP_DUE
    Notify: Assigned agent/manager
    Title: "Follow-up due: {lead.company_name}"
    Body: "Scheduled follow-up for {lead.contact_name} is due now."
    Entity: lead, lead_id
    Priority: HIGH
    """

async def on_quote_expired(event: Event):
    """
    Event: QUOTE_EXPIRED
    Notify: Quote creator, ADMIN
    Title: "Quote {quote_number} expired"
    Body: "Quote for {lead.company_name} has expired without a response."
    """

# Registration:
def register_notification_handlers():
    EventBus.subscribe(EventType.LEAD_REPLIED, on_lead_replied)
    EventBus.subscribe(EventType.QUOTE_ACCEPTED, on_quote_accepted)
    EventBus.subscribe(EventType.AI_ACTION_PROPOSED, on_ai_action_proposed)
    EventBus.subscribe(EventType.CALL_ENDED, on_call_completed)
    EventBus.subscribe(EventType.CAMPAIGN_COMPLETED, on_campaign_completed)
    EventBus.subscribe(EventType.VERIFICATION_COMPLETED, on_verification_completed)
    EventBus.subscribe(EventType.FOLLOWUP_DUE, on_followup_due)
    EventBus.subscribe(EventType.QUOTE_EXPIRED, on_quote_expired)
```

Call `register_notification_handlers()` in the FastAPI lifespan startup.

---

## Step 8.5 — WebSocket Notification Delivery

**File:** `apps/api/app/api/websockets/notification_ws.py`

```python
from fastapi import WebSocket, WebSocketDisconnect

class NotificationWSManager:
    """Manages WebSocket connections for real-time notification delivery."""
    
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = {}
        # connections[user_id] = [ws1, ws2, ...]  (user may have multiple tabs)
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.connections:
            self.connections[user_id].remove(websocket)
            if not self.connections[user_id]:
                del self.connections[user_id]
    
    async def push_notification(self, user_id: str, notification: dict):
        """
        Push notification to all connected WebSockets for this user.
        
        Message format:
        {
            "type": "notification",
            "data": {
                "id": "...",
                "type": "LEAD_REPLIED",
                "title": "...",
                "body": "...",
                "entity_type": "lead",
                "entity_id": "...",
                "priority": "HIGH",
                "created_at": "..."
            }
        }
        """
        if user_id in self.connections:
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json({
                        "type": "notification",
                        "data": notification,
                    })
                except Exception:
                    # Connection broken, will be cleaned up on disconnect
                    pass
    
    async def push_job_progress(self, user_id: str, job_id: str, progress: dict):
        """
        Push job progress update to connected user.
        
        Message format:
        {
            "type": "job_progress",
            "data": {
                "job_id": "...",
                "processed": 8000,
                "total": 10000,
                "failed": 50,
                "status": "RUNNING"
            }
        }
        """

notification_ws_manager = NotificationWSManager()

@router.websocket("/ws/notifications")
async def notification_websocket(websocket: WebSocket):
    """
    1. Authenticate user from token (query param or first message)
    2. Register connection
    3. Send unread count on connect
    4. Keep alive: receive pings, send pongs
    5. On disconnect: unregister
    """
    user_id = await authenticate_ws(websocket)
    await notification_ws_manager.connect(websocket, str(user_id))
    
    # Send initial unread count
    unread_count = await notification_service.get_unread_count(user_id)
    await websocket.send_json({"type": "unread_count", "data": {"count": unread_count}})
    
    try:
        while True:
            # Keep connection alive, handle client messages
            data = await websocket.receive_text()
            # Client can send: {"type": "ping"} or {"type": "mark_read", "id": "..."}
    except WebSocketDisconnect:
        await notification_ws_manager.disconnect(websocket, str(user_id))
```

---

## Step 8.6 — Integrate Events Throughout the System

Go back through ALL previous phases and add `EventBus.publish()` calls at the right places:

### Phase 3 additions:
```python
# After lead creation:
await EventBus.publish(Event(EventType.LEAD_CREATED, org_id, {"lead_id": str(lead.id)}))

# After verification complete:
await EventBus.publish(Event(EventType.LEAD_VERIFIED, org_id, {"lead_id": ..., "status": ...}))

# After bulk verification job completes:
await EventBus.publish(Event(EventType.VERIFICATION_COMPLETED, org_id, {"job_id": ..., "results": ...}))
```

### Phase 4 additions:
```python
# After campaign starts:
await EventBus.publish(Event(EventType.CAMPAIGN_STARTED, org_id, {"campaign_id": ...}))

# After email received (ingestion):
await EventBus.publish(Event(EventType.LEAD_REPLIED, org_id, {"lead_id": ..., "conversation_id": ...}))
```

### Phase 5 additions:
```python
# After AI proposes action:
await EventBus.publish(Event(EventType.AI_ACTION_PROPOSED, org_id, {"action_id": ..., "description": ...}))

# After AI action approved:
await EventBus.publish(Event(EventType.AI_ACTION_APPROVED, org_id, {"action_id": ...}))
```

### Phase 6 additions:
```python
# After quote sent:
await EventBus.publish(Event(EventType.QUOTE_SENT, org_id, {"quote_id": ..., "lead_id": ...}))

# After quote accepted:
await EventBus.publish(Event(EventType.QUOTE_ACCEPTED, org_id, {"quote_id": ..., "lead_id": ...}))

# After order created:
await EventBus.publish(Event(EventType.ORDER_CREATED, org_id, {"order_id": ..., "total": ...}))
```

### Phase 7 additions:
```python
# After call started:
await EventBus.publish(Event(EventType.CALL_STARTED, org_id, {"call_id": ..., "lead_id": ...}))

# After call ended:
await EventBus.publish(Event(EventType.CALL_ENDED, org_id, {"call_id": ..., "duration": ...}))
```

---

## Step 8.7 — Notification Repository

**File:** `apps/api/app/repositories/notification_repo.py`

```python
class NotificationRepository:
    async def create(self, **data) -> Notification: ...
    async def get_by_id(self, notification_id, user_id) -> Notification | None: ...
    async def list_by_user(self, user_id, page=1, page_size=20, 
                           unread_only=False) -> tuple[list, int]: ...
    async def mark_read(self, notification_id, user_id) -> None: ...
    async def mark_all_read(self, user_id) -> None: ...
    async def get_unread_count(self, user_id) -> int: ...
    async def delete(self, notification_id, user_id) -> None: ...
```

---

## Step 8.8 — API Routes

### `apps/api/app/api/notifications.py`

```text
GET    /api/v1/notifications              → List notifications (paginated, filter: unread_only)
GET    /api/v1/notifications/count        → Get unread count
POST   /api/v1/notifications/{id}/read    → Mark as read
POST   /api/v1/notifications/read-all     → Mark all as read
DELETE /api/v1/notifications/{id}         → Delete notification
```

### Pydantic Schemas

**File:** `apps/api/app/schemas/notification.py`

```python
# NotificationResponse: id, type, title, body, entity_type, entity_id, priority, is_read, created_at
# NotificationListResponse: notifications, total, unread_count
# UnreadCountResponse: count
```

### Register Router

```python
from app.api import notifications
app.include_router(notifications.router, prefix="/api/v1/notifications", tags=["notifications"])
```

---

## Step 8.9 — Job Progress via WebSocket

Update the Celery workers (verification, campaign) to publish progress through Redis pub/sub, which the WebSocket manager picks up and pushes to connected clients:

**File:** `apps/api/app/core/progress.py`

```python
import redis.asyncio as redis
import json

class ProgressPublisher:
    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
    
    async def publish_progress(self, job_id: str, user_id: str, progress: dict):
        """
        Publish to Redis channel: f"job_progress:{user_id}"
        The WebSocket notification handler subscribes to this channel.
        """
        await self.redis.publish(
            f"job_progress:{user_id}",
            json.dumps({"job_id": job_id, **progress})
        )
```

---

## Phase 8 Completion Checklist

- [ ] `notifications` table created with indexes
- [ ] Alembic migration applied
- [ ] Event bus: EventBus class with subscribe/publish
- [ ] Event types: all defined (LEAD_CREATED, QUOTE_ACCEPTED, etc.)
- [ ] Notification service: create, create_for_org_admins, mark_read, mark_all_read
- [ ] Notification handlers registered for all key events
- [ ] WebSocket notification manager: connect, disconnect, push
- [ ] WebSocket endpoint: /ws/notifications with auth
- [ ] Initial unread count sent on WebSocket connect
- [ ] Notifications pushed in real-time to connected users
- [ ] EventBus.publish() calls added throughout Phases 3-7
- [ ] Job progress published via Redis → WebSocket
- [ ] Notification API: list, count, mark read, mark all read, delete
- [ ] Notification priorities: LOW, NORMAL, HIGH, URGENT
- [ ] All queries scoped to authenticated user
- [ ] `git commit -m "Phase 8: Notifications, events, real-time"`

---

## Transition to Phase 9

Once all boxes are checked, proceed to [09-frontend.md](./09-frontend.md).

Phase 9 is the big one — the Next.js frontend dashboard with all pages, components, real-time updates, and the WebRTC call interface.
