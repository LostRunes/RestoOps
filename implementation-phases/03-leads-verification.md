# Phase 3 — Leads, Email Verification Engine & Scoring

> **Goal:** Build the full lead management system (CRUD, CSV import, pipeline), the custom email verification engine (look into C:\RestoOps\bounce-blitz and C:\RestoOps\bounce-blitz\BounceBlitz_Complete_Documentation.md an already self built tool for this purpose), lead scoring, verification jobs via Celery with real-time progress tracking, and the suppression list. This is one of the most technically impressive parts of the project.

> **Depends on:** Phase 2 (Auth/RBAC/Multi-tenancy)

---

## Step 3.1 — Database Models

### 3.1.1 — Lead Model

**File:** `apps/api/app/models/lead.py`

```text
Table: leads
─────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
restaurant_id     UUID, FK → restaurants.id, NULLABLE

company_name      VARCHAR(255)
contact_name      VARCHAR(255)

email             VARCHAR(255)
phone             VARCHAR(50)

address           TEXT
industry          VARCHAR(100)
company_size      VARCHAR(50)

source            VARCHAR(50)    # CSV, MANUAL, PUBLIC, API

score             INTEGER, default 0
priority          VARCHAR(20)    # HOT, HIGH, MEDIUM, LOW

pipeline_status   VARCHAR(30)    # NEW, VERIFIED, CONTACTED, INTERESTED, QUALIFIED, QUOTE_SENT, NEGOTIATING, WON, LOST

created_at        TIMESTAMP WITH TZ
updated_at        TIMESTAMP WITH TZ
```

**Indexes:**
- `organization_id`
- `email`
- `pipeline_status`
- Composite: `(organization_id, pipeline_status)`

### 3.1.2 — Lead Contact (Additional Contacts)

**File:** `apps/api/app/models/lead_contact.py`

```text
Table: lead_contacts
─────────────────────
id         UUID, PK
lead_id    UUID, FK → leads.id, NOT NULL
name       VARCHAR(255)
email      VARCHAR(255)
phone      VARCHAR(50)
role       VARCHAR(100)
is_primary BOOLEAN, default false
```

### 3.1.3 — Lead Verification Model

**File:** `apps/api/app/models/lead_verification.py`

```text
Table: lead_verifications
──────────────────────────
id             UUID, PK
lead_id        UUID, FK → leads.id, NULLABLE
organization_id UUID, FK → organizations.id, NOT NULL

email          VARCHAR(255), NOT NULL
status         VARCHAR(20)   # VALID, INVALID, RISKY, UNKNOWN

syntax_valid   BOOLEAN
domain_valid   BOOLEAN
mx_valid       BOOLEAN
disposable     BOOLEAN
role_based     BOOLEAN
catch_all      BOOLEAN

smtp_code      INTEGER, NULLABLE
smtp_message   TEXT, NULLABLE

mx_host        VARCHAR(255), NULLABLE

latency_ms     INTEGER, NULLABLE
attempts       INTEGER, default 1

checked_at     TIMESTAMP WITH TZ
```

### 3.1.4 — Lead Activity Model

**File:** `apps/api/app/models/lead_activity.py`

```text
Table: lead_activities
───────────────────────
id          UUID, PK
lead_id     UUID, FK → leads.id, NOT NULL
user_id     UUID, FK → users.id, NULLABLE

activity_type   VARCHAR(50)   # EMAIL_SENT, EMAIL_RECEIVED, CALL_MADE, QUOTE_SENT, STATUS_CHANGED, NOTE_ADDED, VERIFIED
description     TEXT
metadata        JSONB, NULLABLE

created_at      TIMESTAMP WITH TZ
```

### 3.1.5 — Suppression List Model

**File:** `apps/api/app/models/suppression.py`

```text
Table: suppression_list
────────────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL

email             VARCHAR(255), NULLABLE
phone             VARCHAR(50), NULLABLE

reason            VARCHAR(50)    # UNSUBSCRIBED, BOUNCED, DO_NOT_CONTACT, MANUAL_BLOCK
source            VARCHAR(50)    # SYSTEM, MANUAL, AI

created_at        TIMESTAMP WITH TZ
```

- Unique constraint on `(organization_id, email)` where email is not null
- Index on `organization_id`

### 3.1.6 — Jobs Model

**File:** `apps/api/app/models/job.py`

```text
Table: jobs
───────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL

type              VARCHAR(50)   # VERIFICATION, CSV_IMPORT, CAMPAIGN_EXECUTION, etc.
status            VARCHAR(20)   # PENDING, RUNNING, COMPLETED, FAILED, CANCELLED

total_items       INTEGER, default 0
processed_items   INTEGER, default 0
failed_items      INTEGER, default 0

result            JSONB, NULLABLE
error             TEXT, NULLABLE

started_at        TIMESTAMP WITH TZ, NULLABLE
completed_at      TIMESTAMP WITH TZ, NULLABLE
created_at        TIMESTAMP WITH TZ
```

### 3.1.7 — Job Events Model

**File:** `apps/api/app/models/job_event.py`

```text
Table: job_events
──────────────────
id          UUID, PK
job_id      UUID, FK → jobs.id, NOT NULL

event_type  VARCHAR(50)   # STARTED, PROGRESS, COMPLETED, FAILED, CANCELLED, ITEM_PROCESSED
payload     JSONB, NULLABLE

created_at  TIMESTAMP WITH TZ
```

### 3.1.8 — Migration

```bash
alembic revision --autogenerate -m "add leads verification and jobs tables"
alembic upgrade head
```

---

## Step 3.2 — Email Verification Engine

This is a standalone, reusable subsystem. Build it as a self-contained module.

**Directory:** `apps/api/app/services/verification/`

```text
verification/
├── __init__.py
├── engine.py          # Main orchestrator
├── syntax.py          # Syntax validation
├── dns_checker.py     # DNS/MX lookup
├── disposable.py      # Disposable domain detection
├── role_based.py      # Role-based address detection
├── smtp_prober.py     # SMTP connection & probe
├── classifier.py      # Final classification logic
├── cache.py           # Domain-level MX caching
└── data/
    ├── disposable_domains.txt    # ~3000+ disposable domains
    └── role_addresses.txt        # info@, admin@, support@, etc.
```

### 3.2.1 — Syntax Validator

**File:** `verification/syntax.py`

```python
def validate_syntax(email: str) -> tuple[bool, str]:
    """
    Returns (is_valid, normalized_email).
    
    Checks:
    - Has exactly one @
    - Local part: 1-64 chars, allowed chars (a-z, 0-9, ._%+-)
    - Domain part: has at least one dot, valid TLD, 2-255 chars
    - No consecutive dots
    - Doesn't start/end with dot
    - Lowercase normalization
    - Strip whitespace
    """
```

### 3.2.2 — DNS/MX Checker

**File:** `verification/dns_checker.py`

```python
import dns.resolver

async def check_domain(domain: str) -> dict:
    """
    Returns:
    {
        "domain_exists": bool,
        "mx_records": [{"host": str, "priority": int}, ...],
        "mx_valid": bool,
        "error": str | None,    # NXDOMAIN, SERVFAIL, TIMEOUT, etc.
    }
    
    Steps:
    1. Try MX lookup
    2. If MX fails, try A record as fallback
    3. Sort MX by priority (lowest first)
    4. Handle NXDOMAIN, SERVFAIL, Timeout distinctly
    """
```

### 3.2.3 — Disposable Domain Detector

**File:** `verification/disposable.py`

```python
class DisposableDomainChecker:
    def __init__(self):
        """Load disposable_domains.txt into a set (O(1) lookup)."""
    
    def is_disposable(self, domain: str) -> bool:
        """Check if domain is in the disposable set."""
```

**File:** `verification/data/disposable_domains.txt`

Include a comprehensive list (guerrillamail.com, mailinator.com, tempmail.com, etc.). At least 1000+ domains.

### 3.2.4 — Role-Based Address Detector

**File:** `verification/role_based.py`

```python
ROLE_PREFIXES = {
    "info", "admin", "support", "sales", "help",
    "contact", "webmaster", "postmaster", "abuse",
    "noreply", "no-reply", "billing", "marketing",
    "team", "office", "hello", "enquiry", "feedback",
}

def is_role_based(email: str) -> bool:
    """Check if the local part matches a role-based prefix."""
```

### 3.2.5 — SMTP Prober

**File:** `verification/smtp_prober.py`

This is the most technically complex part.

```python
import asyncio
import aiosmtplib

class SMTPProber:
    def __init__(self, timeout: int = 10, max_retries: int = 2):
        self.timeout = timeout
        self.max_retries = max_retries
    
    async def probe(self, email: str, mx_hosts: list[dict]) -> dict:
        """
        For each MX host (in priority order):
            1. Connect to port 25 (with timeout)
            2. EHLO restoops.local
            3. MAIL FROM:<verify@restoops.local>
            4. RCPT TO:<email>
            5. Read response code
            6. QUIT
            7. Properly close connection
        
        Returns:
        {
            "smtp_success": bool,
            "smtp_code": int | None,         # 250, 550, 451, etc.
            "smtp_message": str | None,
            "mx_host_used": str | None,
            "is_catch_all": bool | None,
            "latency_ms": int,
            "attempts": int,
            "error": str | None,             # TIMEOUT, REFUSED, BLOCKED, etc.
        }
        
        Error handling:
        - Connection refused → try next MX
        - Timeout → try next MX (with backoff)
        - 4xx → RISKY (greylisting possible)
        - 5xx → INVALID
        - 2xx → VALID
        - All MX failed → UNKNOWN
        """
    
    async def detect_catch_all(self, mx_host: str) -> bool | None:
        """
        Send RCPT TO with a random non-existent address.
        If the server accepts it → catch-all domain.
        
        Random address: <uuid>@<domain>
        """
```

**IMPORTANT SMTP Caveats to handle:**
- Greylisting (4xx on first attempt, success on retry after delay)
- Catch-all servers (accept everything)
- Rate limiting by target server
- Connection timeouts
- TLS issues
- Server blocking verification probes
- Properly closing connections (QUIT + socket close)

### 3.2.6 — Domain Cache

**File:** `verification/cache.py`

```python
import redis.asyncio as redis

class DomainCache:
    def __init__(self, redis_url: str, ttl: int = 3600):
        """
        Cache domain-level MX lookup results.
        Key: f"mx:{domain}"
        TTL: 1 hour default
        
        This prevents repeated DNS lookups for the same domain
        when verifying thousands of addresses from the same provider.
        """
    
    async def get_mx(self, domain: str) -> dict | None: ...
    async def set_mx(self, domain: str, data: dict) -> None: ...
```

### 3.2.7 — Final Classifier

**File:** `verification/classifier.py`

```python
def classify(
    syntax_valid: bool,
    domain_exists: bool,
    mx_valid: bool,
    is_disposable: bool,
    is_role_based: bool,
    smtp_result: dict | None,
    is_catch_all: bool | None,
) -> str:
    """
    Returns one of: VALID, INVALID, RISKY, UNKNOWN
    
    Logic:
    - syntax invalid → INVALID
    - domain doesn't exist → INVALID
    - no MX records → INVALID
    - disposable → INVALID
    - SMTP 5xx → INVALID
    - SMTP 2xx, not catch-all → VALID
    - SMTP 2xx, catch-all → RISKY
    - SMTP 4xx (greylist) → RISKY
    - role-based + valid → RISKY (not invalid, but flagged)
    - SMTP timeout/all failures → UNKNOWN
    - No SMTP attempted (quick mode) + MX valid → RISKY
    """
```

### 3.2.8 — Main Verification Engine

**File:** `verification/engine.py`

```python
class VerificationEngine:
    def __init__(self, domain_cache: DomainCache, smtp_prober: SMTPProber):
        ...
    
    async def verify_quick(self, email: str) -> VerificationResult:
        """
        Quick mode — no SMTP:
        1. Syntax check
        2. DNS/MX lookup (with cache)
        3. Disposable check
        4. Role-based check
        5. Classify
        """
    
    async def verify_power(self, email: str) -> VerificationResult:
        """
        Power mode — full check:
        1. Everything in quick
        2. SMTP probe (multiple MX fallback)
        3. Catch-all detection
        4. Retry handling
        5. Classify
        """
```

`VerificationResult` is a Pydantic model matching the `lead_verifications` table schema.

---

## Step 3.3 — Lead Scoring

**File:** `apps/api/app/services/scoring.py`

```python
class LeadScoringService:
    def score(self, lead: Lead, verification: LeadVerification | None = None) -> tuple[int, str]:
        """
        Returns (score: 0-100, priority: HOT/HIGH/MEDIUM/LOW).
        
        Scoring rules:
        - Valid email:           +15
        - Valid phone:           +10
        - Company name present:  +10
        - Contact name present:  +5
        - Relevant industry:     +20
        - Company size known:    +10
        - Good source (manual):  +10
        - Address present:       +5
        - Has website:           +5
        - Has interaction:       +5
        - Not disposable:        +5
        
        Priority mapping:
        80-100 → HOT
        60-79  → HIGH
        40-59  → MEDIUM
        0-39   → LOW
        """
```

---

## Step 3.4 — Repositories

### `apps/api/app/repositories/lead_repo.py`

```python
class LeadRepository:
    async def create(self, org_id: UUID, **data) -> Lead: ...
    async def get_by_id(self, lead_id: UUID, org_id: UUID) -> Lead | None: ...
    async def list(self, org_id: UUID, filters: dict | None = None, 
                   page: int = 1, page_size: int = 50) -> tuple[list[Lead], int]: ...
    async def update(self, lead_id: UUID, org_id: UUID, **data) -> Lead: ...
    async def delete(self, lead_id: UUID, org_id: UUID) -> None: ...
    async def bulk_create(self, org_id: UUID, leads: list[dict]) -> list[Lead]: ...
    async def get_by_email(self, email: str, org_id: UUID) -> Lead | None: ...
```

### `apps/api/app/repositories/verification_repo.py`

```python
class VerificationRepository:
    async def create(self, **data) -> LeadVerification: ...
    async def get_by_email(self, email: str, org_id: UUID) -> LeadVerification | None: ...
    async def get_by_lead(self, lead_id: UUID) -> LeadVerification | None: ...
    async def list_by_job(self, job_id: UUID) -> list[LeadVerification]: ...
```

### `apps/api/app/repositories/job_repo.py`

```python
class JobRepository:
    async def create(self, org_id: UUID, job_type: str, total_items: int) -> Job: ...
    async def get_by_id(self, job_id: UUID, org_id: UUID) -> Job | None: ...
    async def update_progress(self, job_id: UUID, processed: int, failed: int) -> None: ...
    async def set_status(self, job_id: UUID, status: str, error: str | None = None) -> None: ...
    async def list_by_org(self, org_id: UUID) -> list[Job]: ...
    async def add_event(self, job_id: UUID, event_type: str, payload: dict | None) -> None: ...
```

### `apps/api/app/repositories/suppression_repo.py`

```python
class SuppressionRepository:
    async def add(self, org_id: UUID, email: str, reason: str, source: str) -> None: ...
    async def is_suppressed(self, org_id: UUID, email: str) -> bool: ...
    async def list(self, org_id: UUID) -> list: ...
    async def remove(self, suppression_id: UUID, org_id: UUID) -> None: ...
```

---

## Step 3.5 — Services

### `apps/api/app/services/lead_service.py`

```python
class LeadService:
    async def create_lead(self, org_id, **data) -> Lead: ...
    async def import_csv(self, org_id, restaurant_id, file) -> Job:
        """
        1. Parse CSV (validate columns: company_name, contact_name, email, phone, etc.)
        2. Create Job record (type=CSV_IMPORT, status=PENDING)
        3. Queue Celery task
        4. Return Job
        """
    async def verify_lead(self, lead_id, org_id, mode="quick") -> LeadVerification: ...
    async def score_lead(self, lead_id, org_id) -> Lead: ...
    async def bulk_verify(self, org_id, lead_ids, mode) -> Job: ...
```

### `apps/api/app/services/verification_service.py`

```python
class VerificationService:
    async def verify_single(self, email: str, org_id: UUID, lead_id: UUID | None, mode: str) -> LeadVerification:
        """Run verification engine, store result, return."""
    
    async def create_bulk_job(self, org_id: UUID, emails: list[str], mode: str) -> Job:
        """Create job, queue Celery task, return job."""
```

---

## Step 3.6 — Celery Workers

### `apps/api/app/workers/verification_worker.py`

```python
from app.workers.celery_app import celery_app

@celery_app.task(bind=True, max_retries=3)
def process_verification_job(self, job_id: str, org_id: str, emails: list[str], mode: str):
    """
    1. Update job status → RUNNING
    2. For each email:
        a. Run verification engine (quick or power)
        b. Store result in lead_verifications
        c. Update job progress (processed_items += 1)
        d. Publish progress to Redis (for WebSocket)
        e. If lead exists, update lead's pipeline_status if applicable
    3. On completion → status = COMPLETED
    4. On failure → status = FAILED, store error
    5. Concurrency: Use asyncio.Semaphore(20) to limit concurrent SMTP probes
    """
```

### `apps/api/app/workers/csv_import_worker.py`

```python
@celery_app.task(bind=True)
def process_csv_import(self, job_id: str, org_id: str, restaurant_id: str, file_path: str):
    """
    1. Read CSV from stored path
    2. Validate rows
    3. For each valid row:
        a. Create lead (skip duplicates by email+org)
        b. Update progress
    4. Store summary in job result
    """
```

---

## Step 3.7 — Lead Source Abstraction

**File:** `apps/api/app/services/lead_sources.py`

```python
from abc import ABC, abstractmethod

class LeadSource(ABC):
    @abstractmethod
    async def import_leads(self, org_id: UUID, **kwargs) -> list[dict]:
        """Return list of lead dicts."""

class CSVLeadSource(LeadSource):
    async def import_leads(self, org_id, file_path, **kwargs) -> list[dict]: ...

class ManualLeadSource(LeadSource):
    async def import_leads(self, org_id, data, **kwargs) -> list[dict]: ...
```

---

## Step 3.8 — API Routes

### `apps/api/app/api/leads.py`

```text
POST   /api/v1/leads                → Create lead
GET    /api/v1/leads                → List leads (with filters, pagination)
GET    /api/v1/leads/{id}           → Get lead (with verification, activities)
PATCH  /api/v1/leads/{id}           → Update lead
DELETE /api/v1/leads/{id}           → Delete lead (ADMIN+ only)

POST   /api/v1/leads/import         → Upload CSV → returns Job
POST   /api/v1/leads/{id}/verify    → Verify single lead (mode=quick|power)
POST   /api/v1/leads/{id}/score     → Recalculate lead score

GET    /api/v1/leads/{id}/activities → Get lead activity history
```

### `apps/api/app/api/verifications.py`

```text
POST /api/v1/verifications/single      → Verify single email (standalone)
POST /api/v1/verifications/bulk        → Bulk verify (CSV upload → Job)
GET  /api/v1/verifications/job/{id}    → Get job status + progress
GET  /api/v1/verifications/results/{job_id} → Get verification results for a job
```

### `apps/api/app/api/jobs.py`

```text
GET  /api/v1/jobs            → List all jobs for org
GET  /api/v1/jobs/{id}       → Get job details + progress
POST /api/v1/jobs/{id}/cancel → Cancel a running job
```

---

## Step 3.9 — Pydantic Schemas

**File:** `apps/api/app/schemas/lead.py`

```python
# LeadCreate, LeadUpdate, LeadResponse, LeadListResponse (with pagination)
# LeadImportResponse (job_id)
# LeadFilter (status, priority, verified, search)
```

**File:** `apps/api/app/schemas/verification.py`

```python
# VerificationRequest: email, mode (quick|power)
# VerificationBulkRequest: file upload
# VerificationResponse: all fields from lead_verifications
# VerificationJobResponse: job progress
```

**File:** `apps/api/app/schemas/job.py`

```python
# JobResponse: id, type, status, total, processed, failed, result, error, timestamps
# JobEventResponse
```

---

## Step 3.10 — Register Routers

Add to `main.py`:
```python
from app.api import leads, verifications, jobs
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(verifications.router, prefix="/api/v1/verifications", tags=["verifications"])
app.include_router(jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
```

---

## Phase 3 Completion Checklist

- [ ] `leads` table with all fields and indexes
- [ ] `lead_contacts` table
- [ ] `lead_verifications` table
- [ ] `lead_activities` table
- [ ] `suppression_list` table
- [ ] `jobs` + `job_events` tables
- [ ] Alembic migration applied
- [ ] Verification engine: syntax validator works
- [ ] Verification engine: DNS/MX checker works
- [ ] Verification engine: disposable domain detection works (1000+ domains loaded)
- [ ] Verification engine: role-based detection works
- [ ] Verification engine: SMTP prober connects, sends RCPT TO, reads response
- [ ] Verification engine: catch-all detection works
- [ ] Verification engine: domain MX cache works (Redis)
- [ ] Verification engine: classifier produces VALID/INVALID/RISKY/UNKNOWN correctly
- [ ] Quick mode: runs syntax + DNS + disposable + role checks
- [ ] Power mode: runs everything including SMTP
- [ ] Lead scoring: 0-100 score, HOT/HIGH/MEDIUM/LOW priority
- [ ] Lead CRUD API works (create, list, get, update, delete)
- [ ] CSV import: parses file, creates leads, returns Job
- [ ] Single verify API: returns VerificationResult
- [ ] Bulk verify API: creates Job, queues Celery task
- [ ] Celery verification worker: processes emails, updates progress
- [ ] Job progress tracking: processed/total updated in DB
- [ ] Suppression list: add, check, remove
- [ ] Lead activities logged on key events
- [ ] All queries scoped to organization_id
- [ ] `git commit -m "Phase 3: Leads, verification engine, scoring"`

---

## Transition to Phase 4

Once all boxes are checked, proceed to [04-campaigns-email.md](./04-campaigns-email.md).

Phase 4 will build the campaign system, email templates, multi-step campaign execution via Celery, email sending through Mailpit, and email ingestion (reading incoming replies).
