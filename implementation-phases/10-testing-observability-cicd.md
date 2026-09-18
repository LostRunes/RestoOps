# Phase 10 — Testing, Observability, CI/CD & Documentation

> **Goal:** Add comprehensive testing (unit, integration, E2E with Playwright), finalize Prometheus metrics and Grafana dashboards, set up GitHub Actions CI/CD, and complete all project documentation including README, Architecture Decision Records, and API docs. This is the polish phase that makes the project portfolio-grade.

> **Depends on:** Phase 9 (Frontend)

---

## Step 10.1 — Unit Tests (Backend)

**Directory:** `apps/api/tests/unit/`

### 10.1.1 — Email Verification Tests

**File:** `tests/unit/test_syntax_validator.py`

```python
"""
Test cases:
- Valid emails: john@example.com, user.name+tag@domain.co, a@b.cd
- Invalid: no @, double @@, no domain, no TLD, empty local, too long
- Normalization: whitespace stripped, lowercase
- Edge cases: dots at start/end, consecutive dots
"""
```

**File:** `tests/unit/test_dns_checker.py`

```python
"""
Test cases (mock dns.resolver):
- Valid domain with MX records
- Domain with A record only (fallback)
- NXDOMAIN
- SERVFAIL
- Timeout
- Multiple MX records sorted by priority
"""
```

**File:** `tests/unit/test_disposable.py`

```python
"""
Test cases:
- Known disposable domains: guerrillamail.com, mailinator.com
- Known valid domains: gmail.com, outlook.com, company.com
- Edge cases: subdomains of disposable domains
"""
```

**File:** `tests/unit/test_role_based.py`

```python
"""
Test cases:
- Role-based: info@, admin@, support@, noreply@
- Not role-based: john@, sarah.smith@, john.doe@
"""
```

**File:** `tests/unit/test_smtp_prober.py`

```python
"""
Test cases (mock SMTP):
- SMTP 250 → VALID
- SMTP 550 → INVALID
- SMTP 451 → RISKY (greylist)
- Connection refused → try next MX
- Timeout → try next MX
- All MX failed → UNKNOWN
"""
```

**File:** `tests/unit/test_classifier.py`

```python
"""
Test the final classification logic:
- All valid → VALID
- Syntax invalid → INVALID
- No MX → INVALID
- Disposable → INVALID
- SMTP 550 → INVALID
- Catch-all + SMTP 250 → RISKY
- Role-based + valid → RISKY
- SMTP timeout → UNKNOWN
"""
```

### 10.1.2 — Lead Scoring Tests

**File:** `tests/unit/test_lead_scoring.py`

```python
"""
Test cases:
- Lead with all fields → max score
- Lead with only email → low score
- Verified email adds points
- Invalid email doesn't add points
- Score → priority mapping: 85=HOT, 65=HIGH, 45=MEDIUM, 20=LOW
"""
```

### 10.1.3 — Auth Tests

**File:** `tests/unit/test_password_hashing.py`

```python
"""
- Hash password → verify succeeds
- Verify wrong password → fails
- Hash is different each time (salt)
"""
```

**File:** `tests/unit/test_jwt.py`

```python
"""
- Create access token → decode → correct payload
- Expired token → raises error
- Invalid token → raises error
- Refresh token → different secret/expiry
"""
```

### 10.1.4 — Permission Tests

**File:** `tests/unit/test_permissions.py`

```python
"""
- OWNER can access everything
- ADMIN can manage users
- AGENT cannot manage users
- VIEWER has read-only access
- require_roles() dependency works correctly
"""
```

### 10.1.5 — Quote Calculation Tests

**File:** `tests/unit/test_quote_calculations.py`

```python
"""
- Subtotal = sum of item totals
- Tax = subtotal × tax_rate
- Total = subtotal + tax + delivery - discount
- Item total = quantity × unit_price
- Zero items → zero total
- Discount cannot exceed subtotal + tax + delivery
"""
```

---

## Step 10.2 — Integration Tests (Backend)

**Directory:** `apps/api/tests/integration/`

**Setup:** `tests/conftest.py`

```python
"""
Fixtures:
- test_db: Creates test PostgreSQL database, runs migrations, tears down after
- test_redis: Connects to test Redis, flushes after each test
- test_client: httpx.AsyncClient with base URL
- authenticated_client: Client with valid JWT token
- test_org: Pre-created organization
- test_user: Pre-created user with OWNER role
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

### 10.2.1 — Auth Flow Tests

**File:** `tests/integration/test_auth_flow.py`

```python
"""
Test complete auth flow:
1. Register → returns tokens
2. Login with created credentials → returns tokens
3. GET /auth/me → returns user info
4. Refresh token → returns new tokens
5. Invalid login → 401
6. Duplicate email → 409
7. Rate limited after 10 attempts → 429
"""
```

### 10.2.2 — Lead CRUD Tests

**File:** `tests/integration/test_leads.py`

```python
"""
1. Create lead → 201
2. List leads → includes created lead
3. Get lead → returns full details
4. Update lead → 200
5. Delete lead → 204
6. Multi-tenancy: User A cannot see User B's leads
7. CSV import → creates job, leads created
"""
```

### 10.2.3 — Campaign Flow Tests

**File:** `tests/integration/test_campaigns.py`

```python
"""
1. Create campaign with steps
2. Start campaign → leads assigned
3. Pause campaign → status updated
4. Cancel campaign → status updated
5. Campaign analytics → correct counts
"""
```

### 10.2.4 — Quote → Order Flow Tests

**File:** `tests/integration/test_quote_order_flow.py`

```python
"""
Full pipeline test:
1. Create lead
2. Create quote with items
3. Verify totals calculated correctly
4. Send quote → status = SENT
5. Accept quote → order created, lead status = WON
6. Verify order has all items
7. Verify revenue stats updated
"""
```

### 10.2.5 — AI Action Tests

**File:** `tests/integration/test_ai_actions.py`

```python
"""
1. Create conversation with messages
2. Trigger AI analysis (mock Ollama response)
3. Verify AI run record created
4. Verify AI action created as PROPOSED
5. Approve action → EXECUTED
6. Reject action → REJECTED
7. Edit and approve → modified arguments used
"""
```

### 10.2.6 — Multi-Tenancy Tests

**File:** `tests/integration/test_multi_tenancy.py`

```python
"""
CRITICAL tests:
1. Create two organizations
2. Create leads in each
3. User from Org A CANNOT see Org B's leads
4. User from Org A CANNOT modify Org B's leads
5. Queries always filter by organization_id
6. This applies to ALL entities: leads, campaigns, quotes, orders, conversations
"""
```

---

## Step 10.3 — E2E Tests (Playwright)

**Directory:** `apps/web/tests/e2e/`

**Setup:**
```bash
cd apps/web
npm install --save-dev @playwright/test
npx playwright install
```

**File:** `apps/web/playwright.config.ts`

```typescript
export default defineConfig({
    testDir: './tests/e2e',
    baseURL: 'http://localhost:3000',
    webServer: [
        { command: 'npm run dev', url: 'http://localhost:3000', reuseExistingServer: true },
    ],
});
```

### 10.3.1 — Auth E2E

**File:** `tests/e2e/auth.spec.ts`

```typescript
/**
 * - Visit /login → form visible
 * - Fill invalid credentials → error shown
 * - Fill valid credentials → redirected to /dashboard
 * - Register new account → redirected to /dashboard
 * - Logout → redirected to /login
 */
```

### 10.3.2 — Lead Management E2E

**File:** `tests/e2e/leads.spec.ts`

```typescript
/**
 * - Navigate to /leads → table visible
 * - Click "Add Lead" → form appears
 * - Fill form, submit → lead in table
 * - Click lead → detail page
 * - Upload CSV → import dialog, job starts
 * - View verification progress
 */
```

### 10.3.3 — Campaign E2E

**File:** `tests/e2e/campaigns.spec.ts`

```typescript
/**
 * - Create campaign with 2 steps
 * - Start campaign
 * - View campaign analytics
 */
```

### 10.3.4 — Conversation & AI E2E

**File:** `tests/e2e/conversations.spec.ts`

```typescript
/**
 * - Navigate to conversations
 * - Select conversation
 * - View AI analysis panel
 * - Approve AI action → success toast
 */
```

### 10.3.5 — Quote E2E

**File:** `tests/e2e/quotes.spec.ts`

```typescript
/**
 * - Create quote with items
 * - Edit item quantities
 * - Verify total updates
 * - Send quote
 */
```

---

## Step 10.4 — Prometheus Metrics

### FastAPI Metrics (already instrumented in Phase 1)

Verify these are exposed at `GET /metrics`:

```text
# Request metrics (auto from prometheus-fastapi-instrumentator)
http_requests_total
http_request_duration_seconds

# Custom metrics to add:
```

**File:** `apps/api/app/core/metrics.py`

```python
from prometheus_client import Counter, Histogram, Gauge

# Verification
verification_duration = Histogram(
    "verification_duration_seconds",
    "Time to verify a single email",
    ["mode"],  # quick, power
)
verification_results = Counter(
    "verification_results_total",
    "Verification results by status",
    ["status"],  # VALID, INVALID, RISKY, UNKNOWN
)

# Jobs
active_jobs = Gauge(
    "active_jobs",
    "Number of currently running jobs",
    ["type"],
)
job_duration = Histogram(
    "job_duration_seconds",
    "Job execution duration",
    ["type"],
)

# Email
emails_sent_total = Counter("emails_sent_total", "Total emails sent")
emails_failed_total = Counter("emails_failed_total", "Total email send failures")

# Calls
calls_started_total = Counter("calls_started_total", "Total calls started", ["provider"])
calls_failed_total = Counter("calls_failed_total", "Total call failures", ["provider"])

# AI
ai_latency = Histogram("ai_latency_seconds", "AI inference latency")
ai_errors_total = Counter("ai_errors_total", "AI processing errors")
ai_actions_total = Counter("ai_actions_total", "AI actions by status", ["status"])

# Queue
celery_queue_depth = Gauge("celery_queue_depth", "Celery queue depth", ["queue"])
```

Instrument these throughout the codebase (verification engine, email service, call service, AI service).

---

## Step 10.5 — Grafana Dashboards

### Provisioning

**File:** `infrastructure/monitoring/grafana/provisioning/datasources/prometheus.yml`

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
```

### Dashboard JSON

**File:** `infrastructure/monitoring/grafana/dashboards/restoops.json`

Create a Grafana dashboard with panels:

```text
Row 1: API Health
- Request rate (http_requests_total)
- Error rate (http_requests_total{status=~"5.."})
- P95 latency (http_request_duration_seconds)

Row 2: Email Verification
- Verification rate (verification_results_total)
- Verification duration (verification_duration_seconds)
- Results breakdown (pie: VALID/INVALID/RISKY/UNKNOWN)

Row 3: Jobs & Workers
- Active jobs (active_jobs)
- Job duration (job_duration_seconds)
- Queue depth (celery_queue_depth)

Row 4: AI
- AI latency (ai_latency_seconds)
- AI errors (ai_errors_total)
- Actions breakdown (ai_actions_total by status)

Row 5: Communication
- Emails sent/failed
- Calls started/failed
```

---

## Step 10.6 — CI/CD with GitHub Actions

**File:** `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install ruff mypy
      - run: cd apps/api && ruff check .
      - run: cd apps/api && mypy app/

  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
          POSTGRES_DB: test
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
      redis:
        image: redis:7-alpine
        ports: ['6379:6379']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: cd apps/api && pip install -e ".[dev]"
      - run: cd apps/api && pytest --cov=app tests/
        env:
          DATABASE_URL: postgresql+asyncpg://test:test@localhost:5432/test
          DATABASE_URL_SYNC: postgresql://test:test@localhost:5432/test
          REDIS_URL: redis://localhost:6379/0
          JWT_SECRET: test-secret
          JWT_REFRESH_SECRET: test-refresh-secret

  frontend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: cd apps/web && npm ci
      - run: cd apps/web && npm run lint
      - run: cd apps/web && npx tsc --noEmit

  frontend-build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '18'
      - run: cd apps/web && npm ci
      - run: cd apps/web && npm run build
```

---

## Step 10.7 — Documentation

### README.md (Final Version)

**File:** `c:\RestoOps\README.md`

```markdown
Sections:
1. Project Title + Badge (CI status)
2. What This Is (1 paragraph)
3. Architecture Diagram (text)
4. Tech Stack (table)
5. Features List
6. Getting Started
   - Prerequisites
   - Clone
   - Environment Setup (.env)
   - Docker Compose
   - Database Migrations
   - Running the API
   - Running Workers
   - Running the Frontend
   - Pulling Ollama Model
7. Demo Walkthrough
   - Register + Login
   - Create Restaurant
   - Import Leads (CSV)
   - Run Verification
   - Create Campaign
   - Receive Reply
   - AI Analysis
   - Approve Quote
   - Accept Order
8. API Documentation (link to /docs)
9. Testing
10. Architecture Decisions (link to docs/decisions/)
11. Contributing
12. License
```

### Architecture Doc

**File:** `docs/architecture.md`

```text
- System overview diagram
- Component descriptions
- Data flow diagrams (email, verification, AI, calling)
- Database schema overview
- Event flow
- Worker architecture
```

### API Documentation

**File:** `docs/api.md`

```text
- Link to FastAPI auto-generated docs (/docs, /redoc)
- Overview of all endpoints grouped by feature
- Authentication instructions
- Example requests/responses
```

### Architecture Decision Records

**File:** `docs/decisions/`

Create these ADRs:
```text
001-fastapi-over-django.md
002-postgresql-over-mongodb.md
003-celery-over-custom-workers.md
004-own-email-verifier.md
005-ollama-for-local-ai.md
006-twilio-and-webrtc.md
007-modular-monolith.md
008-argon2-for-passwords.md
009-jwt-not-sessions.md
010-event-driven-notifications.md
```

Each ADR follows:
```markdown
# ADR-NNN: Title

## Status: Accepted

## Context
Why this decision was needed.

## Decision
What we decided.

## Consequences
What are the trade-offs.
```

---

## Step 10.8 — Final Docker Compose Update

Update `docker-compose.yml` to include the application services:

```yaml
services:
  # ... existing services (postgres, redis, mailpit, ollama, prometheus, grafana) ...
  
  api:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./apps/api:/app

  worker:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      - api
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

  scheduler:
    build:
      context: ./apps/api
      dockerfile: Dockerfile
    env_file: .env
    depends_on:
      - api
    command: celery -A app.workers.celery_app beat --loglevel=info

  frontend:
    build:
      context: ./apps/web
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    depends_on:
      - api
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Dockerfiles

**File:** `apps/api/Dockerfile`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml .
RUN pip install -e .
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**File:** `apps/web/Dockerfile`

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json .
RUN npm ci
COPY . .
RUN npm run build
CMD ["npm", "start"]
```

---

## Phase 10 Completion Checklist

### Unit Tests
- [x] Syntax validator: 10+ test cases
- [x] DNS checker: mock tests for MX, A, NXDOMAIN, timeout
- [x] Disposable domain: known disposable + valid domains
- [x] Role-based: role prefixes + normal addresses
- [x] SMTP prober: mock 250, 550, 451, timeout, refused
- [x] Classifier: all classification combinations
- [x] Lead scoring: full score, minimal score, priority mapping
- [x] Password hashing: hash, verify, wrong password
- [x] JWT: create, decode, expired, invalid
- [x] Permissions: role checks for all 5 roles
- [x] Quote calculations: subtotal, tax, total, edge cases

### Integration Tests
- [x] Auth flow: register, login, refresh, me
- [x] Lead CRUD: create, list, get, update, delete
- [x] Multi-tenancy: org isolation verified
- [x] Campaign flow: create, start, pause, cancel
- [x] Quote → Order: full pipeline
- [x] AI actions: propose, approve, reject

### E2E Tests
- [x] Login/register
- [x] Lead management
- [x] CSV import
- [x] Campaign creation
- [x] Conversation + AI panel
- [x] Quote creation

### Observability
- [x] Custom Prometheus metrics defined
- [x] Metrics instrumented in verification, email, AI, calls
- [x] Grafana provisioning configured
- [x] Grafana dashboard created with all panels
- [x] Prometheus scraping FastAPI /metrics

### CI/CD
- [x] GitHub Actions workflow: lint, type check, unit tests, integration tests, build
- [x] CI uses service containers for Postgres + Redis
- [x] Frontend: lint + build in CI

### Documentation
- [x] README.md complete with all sections
- [x] docs/architecture.md with diagrams
- [x] docs/api.md with endpoint overview
- [x] 10 Architecture Decision Records created
- [x] .env.example up to date with all variables

### Docker
- [x] API Dockerfile works
- [x] Frontend Dockerfile works
- [x] docker-compose.yml includes all 10 services
- [x] `docker-compose up` boots the entire stack
- [x] Can complete full demo flow from Docker

### Final Verification
- [x] `git commit -m "Phase 10: Testing, observability, CI/CD, documentation"`
- [x] Full end-to-end demo works (spec section 94)
- [x] All checklist items from final_goal.md section 110 are green

---

## 🎉 PROJECT COMPLETE

The project is done when you can:

1. `docker-compose up`
2. Create an account
3. Create a restaurant
4. Import leads via CSV
5. Run email verification (see real-time progress)
6. Score leads
7. Create and start a campaign
8. See emails in Mailpit
9. Receive a reply
10. See AI analyze the conversation
11. Approve AI's quote suggestion
12. Send the quote
13. Accept the quote → order created
14. See revenue stats
15. Make a browser call (WebRTC)
16. See real-time notifications throughout
17. View the Grafana dashboard

**That is the project.**
