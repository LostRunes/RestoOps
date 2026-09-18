# Phase 6 — Quotes, Orders & Revenue Pipeline

> **Goal:** Build the quote system (creation, line items, pricing calculations, sending via email, customer acceptance/rejection, expiration handling) and the order system (quote→order conversion, order status tracking, revenue calculations). This completes the business pipeline: Lead → Campaign → Conversation → Quote → Order → Revenue.

> **Depends on:** Phase 5 (AI Agent & Human-in-the-Loop)

---

## Step 6.1 — Database Models

### 6.1.1 — Quote Model

**File:** `apps/api/app/models/quote.py`

```text
Table: quotes
──────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NOT NULL
lead_id           UUID, FK → leads.id, NOT NULL
conversation_id   UUID, FK → conversations.id, NULLABLE
ai_run_id         UUID, FK → ai_runs.id, NULLABLE  # If AI-generated

event_date        DATE, NOT NULL
event_type        VARCHAR(100), NULLABLE   # Lunch, Dinner, Reception, etc.
guest_count       INTEGER, NOT NULL

subtotal          DECIMAL(12, 2), default 0
tax_rate          DECIMAL(5, 4), default 0.0  # e.g. 0.18 for 18%
tax               DECIMAL(12, 2), default 0
delivery_fee      DECIMAL(12, 2), default 0
discount          DECIMAL(12, 2), default 0
total             DECIMAL(12, 2), default 0

notes             TEXT, NULLABLE
terms             TEXT, NULLABLE

status            VARCHAR(20)
# DRAFT → PENDING_APPROVAL → SENT → VIEWED → ACCEPTED → REJECTED → EXPIRED

quote_number      VARCHAR(20), UNIQUE    # e.g. Q-2026-0001

valid_until        DATE, NULLABLE
expires_at        TIMESTAMP WITH TZ, NULLABLE

sent_at           TIMESTAMP WITH TZ, NULLABLE
viewed_at         TIMESTAMP WITH TZ, NULLABLE
accepted_at       TIMESTAMP WITH TZ, NULLABLE
rejected_at       TIMESTAMP WITH TZ, NULLABLE

created_by        UUID, FK → users.id, NULLABLE
created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

- Index on `organization_id`
- Index on `lead_id`
- Index on `status`
- Auto-generate `quote_number` (org-scoped sequential)

### 6.1.2 — Quote Items Model

**File:** `apps/api/app/models/quote_item.py`

```text
Table: quote_items
───────────────────
id          UUID, PK
quote_id    UUID, FK → quotes.id, NOT NULL, ON DELETE CASCADE

name        VARCHAR(255), NOT NULL
description TEXT, NULLABLE
category    VARCHAR(50), NULLABLE   # FOOD, BEVERAGE, SERVICE, EQUIPMENT, OTHER

quantity    INTEGER, NOT NULL
unit_price  DECIMAL(10, 2), NOT NULL
total       DECIMAL(12, 2), NOT NULL  # quantity × unit_price

sort_order  INTEGER, default 0

created_at  TIMESTAMP WITH TZ
```

### 6.1.3 — Order Model

**File:** `apps/api/app/models/order.py`

```text
Table: orders
──────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NOT NULL
lead_id           UUID, FK → leads.id, NOT NULL
quote_id          UUID, FK → quotes.id, UNIQUE, NOT NULL

order_number      VARCHAR(20), UNIQUE    # e.g. ORD-2026-0001

event_date        DATE, NOT NULL
guest_count       INTEGER, NOT NULL

total             DECIMAL(12, 2), NOT NULL

status            VARCHAR(20)
# CONFIRMED → PREPARING → IN_TRANSIT → DELIVERED → COMPLETED → CANCELLED

special_instructions  TEXT, NULLABLE

confirmed_at     TIMESTAMP WITH TZ, NULLABLE
completed_at     TIMESTAMP WITH TZ, NULLABLE
cancelled_at     TIMESTAMP WITH TZ, NULLABLE

created_at       TIMESTAMP WITH TZ
updated_at       TIMESTAMP WITH TZ
```

- Index on `organization_id`
- Index on `lead_id`
- Index on `quote_id` (unique)

### 6.1.4 — Order Items Model

**File:** `apps/api/app/models/order_item.py`

```text
Table: order_items
───────────────────
id          UUID, PK
order_id    UUID, FK → orders.id, NOT NULL, ON DELETE CASCADE

name        VARCHAR(255), NOT NULL
description TEXT, NULLABLE
quantity    INTEGER, NOT NULL
unit_price  DECIMAL(10, 2), NOT NULL
total       DECIMAL(12, 2), NOT NULL

created_at  TIMESTAMP WITH TZ
```

### 6.1.5 — Migration

```bash
alembic revision --autogenerate -m "add quotes and orders tables"
alembic upgrade head
```

---

## Step 6.2 — Quote Service

**File:** `apps/api/app/services/quote_service.py`

```python
class QuoteService:
    async def create_quote(self, org_id, restaurant_id, lead_id, 
                           event_date, guest_count, items: list[dict],
                           **kwargs) -> Quote:
        """
        1. Generate quote_number (Q-YYYY-NNNN, org-scoped)
        2. Create quote record (status=DRAFT)
        3. Create quote_items
        4. Calculate pricing:
            subtotal = sum(item.quantity × item.unit_price)
            tax = subtotal × tax_rate
            total = subtotal + tax + delivery_fee - discount
        5. Update quote totals
        6. Create lead_activity (QUOTE_CREATED)
        7. Return quote with items
        """
    
    async def update_quote(self, quote_id, org_id, **data) -> Quote:
        """Update quote fields. Recalculate totals if items changed."""
    
    async def add_item(self, quote_id, org_id, **item_data) -> QuoteItem:
        """Add an item. Recalculate totals."""
    
    async def remove_item(self, quote_id, org_id, item_id) -> None:
        """Remove item. Recalculate totals."""
    
    async def recalculate_totals(self, quote_id) -> Quote:
        """
        subtotal = sum(items.total)
        tax = subtotal × tax_rate
        total = subtotal + tax + delivery_fee - discount
        """
    
    async def submit_for_approval(self, quote_id, org_id) -> Quote:
        """DRAFT → PENDING_APPROVAL. Requires MANAGER+ role."""
    
    async def approve_quote(self, quote_id, org_id, user_id) -> Quote:
        """PENDING_APPROVAL → ready to send. ADMIN+ role."""
    
    async def send_quote(self, quote_id, org_id) -> Quote:
        """
        1. Validate status allows sending
        2. Render quote email (HTML with items table, totals, terms)
        3. Send via EmailService
        4. Update status → SENT, sent_at = now()
        5. Set expires_at if valid_until is set
        6. Create message record in conversation
        7. Create lead_activity (QUOTE_SENT)
        8. Update lead pipeline_status → QUOTE_SENT
        9. Create audit log
        """
    
    async def accept_quote(self, quote_id, org_id) -> Quote:
        """
        SENT/VIEWED → ACCEPTED.
        1. Update quote status + accepted_at
        2. Create order (see OrderService)
        3. Update lead pipeline_status → WON
        4. Create notifications
        5. Create audit log
        """
    
    async def reject_quote(self, quote_id, org_id) -> Quote:
        """SENT/VIEWED → REJECTED. Update lead pipeline_status → LOST (optionally)."""
    
    async def mark_viewed(self, quote_id) -> Quote:
        """SENT → VIEWED. Update viewed_at."""
    
    async def check_expirations(self):
        """
        Called by Celery Beat.
        Find quotes where status=SENT and expires_at < now().
        Update status → EXPIRED.
        Create notifications.
        """
```

---

## Step 6.3 — Quote Email Template

**File:** `apps/api/app/services/quote_email_renderer.py`

```python
class QuoteEmailRenderer:
    def render(self, quote: Quote, items: list[QuoteItem], 
              lead: Lead, restaurant: Restaurant) -> tuple[str, str]:
        """
        Returns (html_body, text_body).
        
        HTML includes:
        - Restaurant branding (name, contact info)
        - Quote number, date
        - Customer details
        - Event info (date, guest count, type)
        - Items table (name, qty, unit price, total)
        - Subtotal, tax, delivery, discount, TOTAL
        - Terms & conditions
        - Valid until date
        - Accept/Reject links (pointing to a quote response page)
        
        Text includes a plain-text version of the same.
        """
```

---

## Step 6.4 — Order Service

**File:** `apps/api/app/services/order_service.py`

```python
class OrderService:
    async def create_from_quote(self, quote: Quote, org_id: UUID) -> Order:
        """
        USE TRANSACTION:
        1. Create order record from quote data
        2. Copy quote_items → order_items
        3. Generate order_number (ORD-YYYY-NNNN)
        4. Set status = CONFIRMED
        5. Update quote status → ACCEPTED
        6. Update lead pipeline_status → WON
        7. Create lead_activity (ORDER_CREATED)
        8. Create audit log
        9. Return order
        
        This MUST be atomic — if any step fails, roll back everything.
        """
    
    async def update_status(self, order_id, org_id, new_status) -> Order:
        """
        Validate status transitions:
        CONFIRMED → PREPARING → IN_TRANSIT → DELIVERED → COMPLETED
        Any status → CANCELLED
        """
    
    async def get_revenue(self, org_id, start_date=None, end_date=None) -> dict:
        """
        Returns:
        {
            "total_revenue": Decimal,
            "order_count": int,
            "average_order_value": Decimal,
            "by_status": {"COMPLETED": Decimal, ...},
            "by_month": [{"month": "2026-09", "revenue": Decimal}, ...],
        }
        """
    
    async def get_order(self, order_id, org_id) -> Order: ...
    async def list_orders(self, org_id, filters=None) -> list[Order]: ...
```

---

## Step 6.5 — Quote Number Generator

**File:** `apps/api/app/services/number_generator.py`

```python
class NumberGenerator:
    async def next_quote_number(self, org_id: UUID, db: AsyncSession) -> str:
        """
        Pattern: Q-{YEAR}-{NNNN}
        Example: Q-2026-0001, Q-2026-0002
        
        Query: SELECT COUNT(*) FROM quotes WHERE organization_id = org_id AND EXTRACT(YEAR FROM created_at) = current_year
        Increment + format.
        
        Handle race conditions with a SELECT FOR UPDATE or a separate sequence table.
        """
    
    async def next_order_number(self, org_id: UUID, db: AsyncSession) -> str:
        """Pattern: ORD-{YEAR}-{NNNN}"""
```

---

## Step 6.6 — Repositories

### `apps/api/app/repositories/quote_repo.py`

```python
class QuoteRepository:
    async def create(self, **data) -> Quote: ...
    async def get_by_id(self, quote_id, org_id) -> Quote | None: ...
    async def list_by_org(self, org_id, filters=None) -> list[Quote]: ...
    async def list_by_lead(self, lead_id, org_id) -> list[Quote]: ...
    async def update(self, quote_id, org_id, **data) -> Quote: ...
    async def get_expired_quotes(self) -> list[Quote]: ...
    
    async def add_item(self, quote_id, **item) -> QuoteItem: ...
    async def get_items(self, quote_id) -> list[QuoteItem]: ...
    async def remove_item(self, item_id, quote_id) -> None: ...
```

### `apps/api/app/repositories/order_repo.py`

```python
class OrderRepository:
    async def create(self, **data) -> Order: ...
    async def get_by_id(self, order_id, org_id) -> Order | None: ...
    async def list_by_org(self, org_id, filters=None) -> list[Order]: ...
    async def update(self, order_id, org_id, **data) -> Order: ...
    
    async def add_item(self, order_id, **item) -> OrderItem: ...
    async def get_items(self, order_id) -> list[OrderItem]: ...
    
    async def get_revenue_stats(self, org_id, start_date=None, end_date=None) -> dict: ...
```

---

## Step 6.7 — Celery Workers

### Quote Expiration Checker

**File:** `apps/api/app/workers/quote_worker.py`

```python
@celery_app.task
def check_quote_expirations():
    """
    Called by Celery Beat daily.
    Finds SENT quotes past expires_at → updates to EXPIRED.
    Creates notification for assigned users.
    """
```

### Add to Celery Beat Schedule

```python
celery_app.conf.beat_schedule.update({
    "check-quote-expirations-daily": {
        "task": "app.workers.quote_worker.check_quote_expirations",
        "schedule": crontab(hour=0, minute=0),  # Daily at midnight
    },
})
```

---

## Step 6.8 — API Routes

### `apps/api/app/api/quotes.py`

```text
POST   /api/v1/quotes                 → Create quote (with items)
GET    /api/v1/quotes                  → List quotes (with filters)
GET    /api/v1/quotes/{id}             → Get quote (with items, lead info)
PATCH  /api/v1/quotes/{id}             → Update quote

POST   /api/v1/quotes/{id}/items       → Add item
DELETE /api/v1/quotes/{id}/items/{item_id}  → Remove item

POST   /api/v1/quotes/{id}/submit      → Submit for approval
POST   /api/v1/quotes/{id}/approve     → Approve quote (ADMIN+)
POST   /api/v1/quotes/{id}/send        → Send quote to customer
POST   /api/v1/quotes/{id}/accept      → Mark as accepted (trigger order creation)
POST   /api/v1/quotes/{id}/reject      → Mark as rejected
```

### `apps/api/app/api/orders.py`

```text
GET    /api/v1/orders                  → List orders
GET    /api/v1/orders/{id}             → Get order (with items)
PATCH  /api/v1/orders/{id}/status      → Update order status

GET    /api/v1/orders/revenue          → Revenue statistics
```

### Pydantic Schemas

**File:** `apps/api/app/schemas/quote.py`

```python
# QuoteCreate: restaurant_id, lead_id, event_date, guest_count, event_type, 
#              items: list[QuoteItemCreate], tax_rate, delivery_fee, discount, notes, terms
# QuoteItemCreate: name, description, category, quantity, unit_price
# QuoteResponse: all fields + items + lead info
# QuoteUpdate: event_date, guest_count, notes, terms (all optional)
```

**File:** `apps/api/app/schemas/order.py`

```python
# OrderResponse: all fields + items
# OrderStatusUpdate: status
# RevenueResponse: total_revenue, order_count, avg_value, by_status, by_month
```

### Register Routers

```python
from app.api import quotes, orders
app.include_router(quotes.router, prefix="/api/v1/quotes", tags=["quotes"])
app.include_router(orders.router, prefix="/api/v1/orders", tags=["orders"])
```

---

## Step 6.9 — Wire AI Quote Suggestions

Connect the AI agent's `create_quote` tool to the QuoteService:

**Update:** `apps/api/app/agents/tools.py`

```python
async def ai_create_quote(org_id, restaurant_id, lead_id, 
                          event_date, guest_count, items, **kwargs):
    """
    AI tool handler for create_quote.
    Creates a DRAFT quote from AI-suggested data.
    """
    return await quote_service.create_quote(
        org_id=org_id,
        restaurant_id=restaurant_id,
        lead_id=lead_id,
        event_date=event_date,
        guest_count=guest_count,
        items=items,
    )

ToolRegistry.register(
    name="create_quote",
    description="Create a catering quote for a lead",
    handler=ai_create_quote,
    requires_approval=True,
)
```

---

## Phase 6 Completion Checklist

- [x] `quotes` table created with all fields
- [x] `quote_items` table created
- [x] `orders` table created
- [x] `order_items` table created
- [x] Alembic migration applied
- [x] Quote number generator: Q-YYYY-NNNN
- [x] Order number generator: ORD-YYYY-NNNN
- [x] Quote CRUD: create with items, list, get, update
- [x] Quote pricing: subtotal, tax, delivery, discount, total calculated correctly
- [x] Add/remove quote items → totals recalculated
- [x] Quote status flow: DRAFT → PENDING_APPROVAL → SENT → VIEWED → ACCEPTED/REJECTED/EXPIRED
- [x] Quote email: HTML + text rendered with items, totals, terms
- [x] Quote sent via EmailService through Mailpit
- [x] Quote acceptance triggers order creation (transactional)
- [x] Order created from quote with all items copied
- [x] Order status transitions validated
- [x] Revenue statistics API: total, count, average, by month
- [x] Lead pipeline_status updated: QUOTE_SENT on send, WON on accept
- [x] Lead activities logged on quote/order events
- [x] Audit logs created on quote approve, send, accept, reject
- [x] Celery Beat: quote expiration check runs daily
- [x] AI create_quote tool registered and connected
- [x] All queries scoped to organization_id
- [x] `git commit -m "Phase 6: Quotes, orders, revenue pipeline"`

---

## Transition to Phase 7

Once all boxes are checked, proceed to [07-calling.md](./07-calling.md).

Phase 7 will add Twilio phone calling and WebRTC browser-to-browser calling with WebSocket signaling.
