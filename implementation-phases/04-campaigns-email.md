# Phase 4 — Campaigns, Email Sending & Ingestion

> **Goal:** Build the campaign system (creation, multi-step scheduling, target selection, suppression checks), email sending via Mailpit/SMTP abstraction, email ingestion (reading inbound replies), and conversation matching. After this phase, the system can run automated email campaigns, send through Mailpit, receive replies, and thread them into conversations.

> **Depends on:** Phase 3 (Leads, Verification, Scoring)

---

## Step 4.1 — Database Models

### 4.1.1 — Campaign Model

**File:** `apps/api/app/models/campaign.py`

```text
Table: campaigns
─────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NULLABLE

name              VARCHAR(255), NOT NULL
description       TEXT, NULLABLE

status            VARCHAR(20)    # DRAFT, ACTIVE, PAUSED, COMPLETED, CANCELLED

target_filters    JSONB          # e.g. {"pipeline_status": ["VERIFIED"], "priority": ["HOT", "HIGH"]}

created_by        UUID, FK → users.id
started_at        TIMESTAMP WITH TZ, NULLABLE
completed_at      TIMESTAMP WITH TZ, NULLABLE
created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

### 4.1.2 — Campaign Steps Model

**File:** `apps/api/app/models/campaign_step.py`

```text
Table: campaign_steps
──────────────────────
id              UUID, PK
campaign_id     UUID, FK → campaigns.id, NOT NULL

step_number     INTEGER, NOT NULL    # 1, 2, 3, ...
step_type       VARCHAR(20)          # EMAIL, WAIT
delay_days      INTEGER, NOT NULL    # Days after previous step

subject         TEXT, NULLABLE       # Email subject template
body            TEXT, NULLABLE       # Email body template (supports {{contact_name}}, {{company_name}}, etc.)

created_at      TIMESTAMP WITH TZ
```

- Unique constraint on `(campaign_id, step_number)`

### 4.1.3 — Campaign Leads Model (Join + Status)

**File:** `apps/api/app/models/campaign_lead.py`

```text
Table: campaign_leads
──────────────────────
id              UUID, PK
campaign_id     UUID, FK → campaigns.id, NOT NULL
lead_id         UUID, FK → leads.id, NOT NULL

current_step    INTEGER, default 0
status          VARCHAR(20)   # PENDING, IN_PROGRESS, COMPLETED, REPLIED, BOUNCED, UNSUBSCRIBED, SKIPPED

next_step_at    TIMESTAMP WITH TZ, NULLABLE

created_at      TIMESTAMP WITH TZ
updated_at      TIMESTAMP WITH TZ
```

- Unique constraint on `(campaign_id, lead_id)` — a lead can only be in a campaign once
- Index on `(campaign_id, status)`
- Index on `next_step_at` — for Celery Beat to find due steps

### 4.1.4 — Conversation Model

**File:** `apps/api/app/models/conversation.py`

```text
Table: conversations
─────────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NULLABLE
lead_id           UUID, FK → leads.id, NOT NULL

channel           VARCHAR(20)   # EMAIL, SMS, VOICE, WEBRTC
status            VARCHAR(20)   # OPEN, CLOSED, ARCHIVED

subject           VARCHAR(500), NULLABLE
message_count     INTEGER, default 0

last_message_at   TIMESTAMP WITH TZ, NULLABLE
created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

- Index on `organization_id`
- Index on `lead_id`

### 4.1.5 — Message Model

**File:** `apps/api/app/models/message.py`

```text
Table: messages
────────────────
id                UUID, PK
conversation_id   UUID, FK → conversations.id, NOT NULL

direction         VARCHAR(10)    # INBOUND, OUTBOUND
sender            VARCHAR(255)   # Email address or user name
recipient         VARCHAR(255)

subject           VARCHAR(500), NULLABLE
body              TEXT

message_id        VARCHAR(500), NULLABLE    # Email Message-ID header
in_reply_to       VARCHAR(500), NULLABLE    # Email In-Reply-To header
references        TEXT, NULLABLE            # Email References header

status            VARCHAR(20)    # SENT, DELIVERED, FAILED, RECEIVED
metadata          JSONB, NULLABLE

created_at        TIMESTAMP WITH TZ
```

- Index on `conversation_id`
- Index on `message_id` — for conversation matching

### 4.1.6 — Migration

```bash
alembic revision --autogenerate -m "add campaigns conversations messages"
alembic upgrade head
```

---

## Step 4.2 — Email Provider Abstraction

**File:** `apps/api/app/integrations/email/__init__.py`
**File:** `apps/api/app/integrations/email/base.py`

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class EmailMessage:
    to: str
    from_addr: str
    subject: str
    body_html: str
    body_text: str | None = None
    reply_to: str | None = None
    message_id: str | None = None  # Custom Message-ID
    in_reply_to: str | None = None
    references: str | None = None
    headers: dict | None = None

@dataclass
class SendResult:
    success: bool
    message_id: str | None
    error: str | None = None

class EmailProvider(ABC):
    @abstractmethod
    async def send(self, message: EmailMessage) -> SendResult:
        """Send an email. Returns SendResult."""
    
    @abstractmethod
    async def fetch_new_messages(self) -> list[dict]:
        """Fetch unread messages from inbox. Returns raw message dicts."""
```

### Mailpit Provider

**File:** `apps/api/app/integrations/email/mailpit.py`

```python
class MailpitProvider(EmailProvider):
    def __init__(self, smtp_host: str, smtp_port: int, from_addr: str):
        ...
    
    async def send(self, message: EmailMessage) -> SendResult:
        """
        Use aiosmtplib to send via Mailpit's SMTP port (1025).
        
        Steps:
        1. Build email.mime.multipart.MIMEMultipart
        2. Set headers: From, To, Subject, Message-ID, In-Reply-To, References
        3. Attach body (text + html)
        4. Connect to SMTP
        5. Send
        6. Return SendResult with generated Message-ID
        """
    
    async def fetch_new_messages(self) -> list[dict]:
        """
        Mailpit has an HTTP API (GET /api/v1/messages).
        Fetch messages, parse them, return structured dicts.
        """
```

### SMTP Provider (Future)

**File:** `apps/api/app/integrations/email/smtp_provider.py`

```python
class SMTPProvider(EmailProvider):
    """For later: connect to a real SMTP server."""
    pass  # Placeholder, not implemented in this phase
```

### Email Service (Facade)

**File:** `apps/api/app/services/email_service.py`

```python
class EmailService:
    def __init__(self, provider: EmailProvider):
        self.provider = provider
    
    async def send_email(self, to, subject, body_html, body_text=None,
                         reply_to=None, in_reply_to=None, references=None) -> SendResult:
        """Build EmailMessage, call provider.send(), return result."""
    
    async def send_campaign_email(self, lead: Lead, step: CampaignStep, 
                                   campaign: Campaign) -> SendResult:
        """
        1. Render template with lead data ({{contact_name}}, {{company_name}})
        2. Generate unique Message-ID for threading
        3. Send via provider
        4. Return result
        """
```

---

## Step 4.3 — Template Engine

**File:** `apps/api/app/services/template_engine.py`

```python
class TemplateEngine:
    def render(self, template: str, context: dict) -> str:
        """
        Simple {{variable}} substitution.
        
        Supported variables:
        - {{contact_name}}
        - {{company_name}}
        - {{restaurant_name}}
        - {{sender_name}}
        
        Handles missing variables gracefully (empty string fallback).
        No Jinja2 needed — keep it simple.
        """
```

---

## Step 4.4 — Email Ingestion

**File:** `apps/api/app/services/email_ingestion.py`

```python
class EmailIngestionService:
    def __init__(self, email_provider: EmailProvider, conversation_matcher: ConversationMatcher):
        ...
    
    async def ingest_new_messages(self):
        """
        1. Fetch new messages from provider (Mailpit API or IMAP)
        2. For each message:
            a. Parse headers (From, To, Subject, Message-ID, In-Reply-To, References, Date)
            b. Parse body (prefer text/plain, sanitize text/html)
            c. Call conversation matcher
            d. Create Message record
            e. Update conversation (last_message_at, message_count)
            f. Update lead status if applicable
            g. Create lead activity
            h. Queue AI processing (Phase 5)
            i. Queue notification (Phase 8)
        """
```

### Conversation Matcher

**File:** `apps/api/app/services/conversation_matcher.py`

```python
class ConversationMatcher:
    async def match(self, message_headers: dict, org_id: UUID) -> Conversation:
        """
        1. Check In-Reply-To header → find message with that Message-ID
        2. Check References header → find any referenced message
        3. If found → return that message's conversation
        4. If not found → try matching by (sender email → lead → existing conversation)
        5. If still not found → create new conversation
        
        Return the Conversation record.
        """
```

---

## Step 4.5 — Campaign Service

**File:** `apps/api/app/services/campaign_service.py`

```python
class CampaignService:
    async def create_campaign(self, org_id, **data) -> Campaign:
        """Create campaign with steps."""
    
    async def start_campaign(self, campaign_id, org_id) -> Campaign:
        """
        1. Validate campaign has steps
        2. Find eligible leads matching target_filters
        3. For each lead:
            a. Check suppression list → skip if suppressed
            b. Check verification status → skip INVALID
            c. Create campaign_lead record (status=PENDING)
            d. Set next_step_at = now() for step 1
        4. Update campaign status → ACTIVE
        5. Queue first batch execution
        """
    
    async def pause_campaign(self, campaign_id, org_id) -> Campaign: ...
    async def cancel_campaign(self, campaign_id, org_id) -> Campaign: ...
    
    async def get_campaign_analytics(self, campaign_id, org_id) -> dict:
        """
        Returns:
        {
            "total_leads": int,
            "pending": int,
            "in_progress": int,
            "completed": int,
            "replied": int,
            "bounced": int,
            "unsubscribed": int,
        }
        """
```

---

## Step 4.6 — Celery Workers

### Campaign Step Executor

**File:** `apps/api/app/workers/campaign_worker.py`

```python
@celery_app.task(bind=True, max_retries=3)
def execute_campaign_step(self, campaign_id: str, org_id: str):
    """
    1. Find all campaign_leads where:
        - campaign_id matches
        - status = PENDING or IN_PROGRESS
        - next_step_at <= now()
    2. For each campaign_lead:
        a. Get the current step template
        b. Render email template with lead data
        c. Check suppression list again (lead may have been suppressed since start)
        d. Send email via EmailService
        e. Create message record (direction=OUTBOUND)
        f. Update campaign_lead:
            - current_step += 1
            - If more steps exist: next_step_at = now() + step.delay_days
            - If last step: status = COMPLETED
        g. Create lead_activity record
        h. Update lead pipeline_status → CONTACTED (if first email)
    3. Handle failures: retry with backoff
    """
```

### Email Ingestion Worker

**File:** `apps/api/app/workers/email_ingestion_worker.py`

```python
@celery_app.task
def ingest_emails():
    """
    Periodic task (called by Celery Beat every 60 seconds).
    Calls EmailIngestionService.ingest_new_messages().
    """
```

### Celery Beat Schedule

**Add to:** `apps/api/app/workers/celery_app.py`

```python
celery_app.conf.beat_schedule = {
    "ingest-emails-every-minute": {
        "task": "app.workers.email_ingestion_worker.ingest_emails",
        "schedule": 60.0,
    },
    "execute-due-campaign-steps": {
        "task": "app.workers.campaign_worker.check_due_steps",
        "schedule": 300.0,  # Every 5 minutes
    },
}
```

---

## Step 4.7 — Repositories

### `apps/api/app/repositories/campaign_repo.py`

```python
class CampaignRepository:
    async def create(self, org_id, **data) -> Campaign: ...
    async def get_by_id(self, campaign_id, org_id) -> Campaign | None: ...
    async def list_by_org(self, org_id) -> list[Campaign]: ...
    async def update(self, campaign_id, org_id, **data) -> Campaign: ...
    
    async def add_step(self, campaign_id, **step_data) -> CampaignStep: ...
    async def get_steps(self, campaign_id) -> list[CampaignStep]: ...
    
    async def add_lead(self, campaign_id, lead_id) -> CampaignLead: ...
    async def get_campaign_leads(self, campaign_id, status=None) -> list[CampaignLead]: ...
    async def get_due_leads(self, campaign_id) -> list[CampaignLead]: ...
    async def update_campaign_lead(self, cl_id, **data) -> None: ...
```

### `apps/api/app/repositories/conversation_repo.py`

```python
class ConversationRepository:
    async def create(self, org_id, lead_id, channel, **data) -> Conversation: ...
    async def get_by_id(self, conv_id, org_id) -> Conversation | None: ...
    async def list_by_org(self, org_id, filters=None) -> list[Conversation]: ...
    async def get_by_lead(self, lead_id, org_id, channel=None) -> Conversation | None: ...
    async def update(self, conv_id, **data) -> None: ...
```

### `apps/api/app/repositories/message_repo.py`

```python
class MessageRepository:
    async def create(self, conversation_id, **data) -> Message: ...
    async def list_by_conversation(self, conversation_id) -> list[Message]: ...
    async def get_by_message_id(self, message_id_header: str) -> Message | None: ...
    async def find_by_references(self, references: list[str]) -> Message | None: ...
```

---

## Step 4.8 — API Routes

### `apps/api/app/api/campaigns.py`

```text
POST   /api/v1/campaigns                 → Create campaign (with steps)
GET    /api/v1/campaigns                  → List campaigns
GET    /api/v1/campaigns/{id}             → Get campaign (with steps, analytics)
PATCH  /api/v1/campaigns/{id}             → Update campaign

POST   /api/v1/campaigns/{id}/start       → Start campaign
POST   /api/v1/campaigns/{id}/pause       → Pause campaign
POST   /api/v1/campaigns/{id}/cancel      → Cancel campaign

GET    /api/v1/campaigns/{id}/leads       → List campaign leads + their status
GET    /api/v1/campaigns/{id}/analytics   → Campaign performance stats
```

### `apps/api/app/api/conversations.py`

```text
GET  /api/v1/conversations                → List conversations (with filters)
GET  /api/v1/conversations/{id}           → Get conversation details
GET  /api/v1/conversations/{id}/messages  → Get messages in conversation

POST /api/v1/conversations/{id}/messages  → Send reply (manual email)
```

### Register Routers

Add to `main.py`:
```python
from app.api import campaigns, conversations
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["conversations"])
```

---

## Step 4.9 — Pydantic Schemas

**File:** `apps/api/app/schemas/campaign.py`

```python
# CampaignCreate: name, description, target_filters, steps: list[CampaignStepCreate]
# CampaignStepCreate: step_number, step_type, delay_days, subject, body
# CampaignResponse: all fields + steps + analytics summary
# CampaignLeadResponse: lead info + current_step + status
```

**File:** `apps/api/app/schemas/conversation.py`

```python
# ConversationResponse: all fields + lead info + last message preview
# ConversationListResponse: paginated list
```

**File:** `apps/api/app/schemas/message.py`

```python
# MessageResponse: all fields
# MessageCreate: body (for manual reply)
```

---

## Phase 4 Completion Checklist

- [ ] `campaigns` table created
- [ ] `campaign_steps` table created
- [ ] `campaign_leads` table created (with indexes on next_step_at)
- [ ] `conversations` table created
- [ ] `messages` table created (with index on message_id)
- [ ] Alembic migration applied
- [ ] Email provider abstraction: `EmailProvider` base class
- [ ] Mailpit provider: can send emails via SMTP
- [ ] Mailpit provider: can fetch messages via HTTP API
- [ ] Email service facade: `send_email()`, `send_campaign_email()`
- [ ] Template engine: `{{variable}}` substitution works
- [ ] Campaign CRUD API works
- [ ] Campaign start: finds eligible leads, creates campaign_leads, queues steps
- [ ] Campaign pause/cancel works
- [ ] Suppression check during campaign execution
- [ ] Campaign step executor: sends templated emails, records messages
- [ ] Campaign analytics: counts by status
- [ ] Email ingestion: fetches new messages from Mailpit
- [ ] Email parsing: extracts headers, body, Message-ID, In-Reply-To
- [ ] Conversation matcher: matches replies to existing conversations
- [ ] New conversations created for unmatched messages
- [ ] Message records created for both inbound and outbound
- [ ] Lead activity logged on email events
- [ ] Celery Beat: email ingestion runs every 60s
- [ ] Celery Beat: campaign step check runs every 5 min
- [ ] Conversation API: list, get, get messages, send reply
- [ ] Manual reply from conversation sends email
- [ ] All queries scoped to organization_id
- [ ] `git commit -m "Phase 4: Campaigns, email, conversations"`

---

## Transition to Phase 5

Once all boxes are checked, proceed to [05-conversations-ai.md](./05-conversations-ai.md).

Phase 5 will add the AI agent layer using Ollama — conversation classification, intent detection, structured outputs, tool calling, and the human-in-the-loop approval system.
