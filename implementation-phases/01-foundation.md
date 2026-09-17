# Phase 1 — Project Foundation & Infrastructure

> **Goal:** Set up the monorepo structure, Docker Compose with all infrastructure services, the FastAPI skeleton, database connection, Alembic migrations framework, Celery worker skeleton, and the `.env` configuration system. After this phase, `docker-compose up` boots a working (empty) stack.

---

## Pre-Requisites (Human)

- [ ] Docker Desktop installed & running
- [ ] Node.js ≥ 18 installed
- [ ] Python ≥ 3.11 installed
- [ ] Git initialized (`git init` in `c:\RestoOps`)

---

## Step 1.1 — Initialize Git & `.gitignore`

**What:** Create `.gitignore` at project root.

**File:** `c:\RestoOps\.gitignore`

**Contents must ignore:**
```text
# Python
__pycache__/
*.pyc
*.pyo
.venv/
venv/
*.egg-info/
dist/
build/

# Node
node_modules/
.next/
out/

# Environment
.env
.env.local
.env.*.local

# IDE
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml

# Test
.coverage
htmlcov/
.pytest_cache/

# Misc
*.log
```

**Verification:** File exists, `git status` doesn't show noise.

---

## Step 1.2 — Create Directory Skeleton

**What:** Create every directory the project needs. No code yet — just empty structure.

**Directories to create:**
```text
apps/api/app/
apps/api/app/api/
apps/api/app/models/
apps/api/app/schemas/
apps/api/app/repositories/
apps/api/app/services/
apps/api/app/workers/
apps/api/app/agents/
apps/api/app/integrations/email/
apps/api/app/integrations/twilio/
apps/api/app/integrations/ollama/
apps/api/app/core/
apps/api/app/db/
apps/api/tests/
apps/web/
migrations/
infrastructure/docker/
infrastructure/monitoring/prometheus/
infrastructure/monitoring/grafana/
docs/decisions/
scripts/
```

**Each `__init__.py`:** Every Python package directory (`app/`, `api/`, `models/`, etc.) gets an empty `__init__.py`.

**Verification:** `tree apps/api` shows the full structure.

---

## Step 1.3 — `.env.example` & `.env`

**File:** `c:\RestoOps\.env.example`

**Contents:**
```env
# Database
DATABASE_URL=postgresql+asyncpg://restoops:restoops@localhost:5432/restoops
DATABASE_URL_SYNC=postgresql://restoops:restoops@localhost:5432/restoops

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET=change-me-to-a-random-secret-key
JWT_REFRESH_SECRET=change-me-to-another-random-secret-key
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# Ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2

# SMTP (Mailpit)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_FROM=noreply@restoops.local

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

# App URLs
WEB_APP_URL=http://localhost:3000
API_URL=http://localhost:8000

# Celery
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Environment
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
```

**Then:** Copy `.env.example` → `.env` and fill in real values.

**Verification:** `.env` exists, is in `.gitignore`.

---

## Step 1.4 — Docker Compose

**File:** `c:\RestoOps\docker-compose.yml`

**Services to define:**

### 1. `postgres`
- Image: `postgres:16-alpine`
- Port: `5432:5432`
- Env: `POSTGRES_USER=restoops`, `POSTGRES_PASSWORD=restoops`, `POSTGRES_DB=restoops`
- Volume: `postgres_data:/var/lib/postgresql/data`
- Healthcheck: `pg_isready -U restoops`

### 2. `redis`
- Image: `redis:7-alpine`
- Port: `6379:6379`
- Volume: `redis_data:/data`
- Healthcheck: `redis-cli ping`

### 3. `mailpit`
- Image: `axllent/mailpit:latest`
- Ports: `1025:1025` (SMTP), `8025:8025` (Web UI)
- No volumes needed

### 4. `ollama`
- Image: `ollama/ollama:latest`
- Port: `11434:11434`
- Volume: `ollama_data:/root/.ollama`
- GPU passthrough if available (deploy → resources → reservations → devices → capabilities: [gpu])

### 5. `prometheus`
- Image: `prom/prometheus:latest`
- Port: `9090:9090`
- Volume bind-mount: `./infrastructure/monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml`

### 6. `grafana`
- Image: `grafana/grafana:latest`
- Port: `3001:3000`
- Env: `GF_SECURITY_ADMIN_PASSWORD=admin`
- Volume: `grafana_data:/var/lib/grafana`

**Named volumes:**
```yaml
volumes:
  postgres_data:
  redis_data:
  ollama_data:
  grafana_data:
```

**Network:** Default bridge is fine for dev.

**Verification:** `docker-compose up -d` → all 6 services healthy. Visit:
- PostgreSQL: `psql -h localhost -U restoops -d restoops`
- Redis: `redis-cli ping` → `PONG`
- Mailpit UI: `http://localhost:8025`
- Ollama: `curl http://localhost:11434/api/tags`
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3001` (admin/admin)

---

## Step 1.5 — Prometheus Configuration

**File:** `c:\RestoOps\infrastructure\monitoring\prometheus\prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'fastapi'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
```

---

## Step 1.6 — Backend Python Project Setup

**File:** `c:\RestoOps\apps\api\pyproject.toml`

**Key dependencies:**
```toml
[project]
name = "restoops-api"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "psycopg2-binary>=2.9.9",
    "alembic>=1.13.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-jose[cryptography]>=3.3.0",
    "argon2-cffi>=23.1.0",
    "celery[redis]>=5.3.0",
    "redis>=5.0.0",
    "httpx>=0.27.0",
    "python-multipart>=0.0.9",
    "structlog>=24.1.0",
    "prometheus-fastapi-instrumentator>=7.0.0",
    "aiosmtplib>=3.0.0",
    "aioimaplib>=1.0.1",
    "dnspython>=2.6.0",
    "python-dotenv>=1.0.0",
    "twilio>=9.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "httpx>=0.27.0",
    "ruff>=0.3.0",
    "mypy>=1.8.0",
]
```

**Setup command:**
```bash
cd apps/api
python -m venv .venv
.venv\Scripts\activate    # Windows
pip install -e ".[dev]"
```

---

## Step 1.7 — Core Configuration Module

**File:** `c:\RestoOps\apps\api\app\core\config.py`

**What:** Pydantic `BaseSettings` class that reads from `.env`.

**Class: `Settings`**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # Redis
    REDIS_URL: str

    # JWT
    JWT_SECRET: str
    JWT_REFRESH_SECRET: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"

    # SMTP
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_FROM: str = "noreply@restoops.local"

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    # App URLs
    WEB_APP_URL: str = "http://localhost:3000"
    API_URL: str = "http://localhost:8000"

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Environment
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = "../../.env"
        case_sensitive = True

settings = Settings()
```

---

## Step 1.8 — Database Session Setup

**File:** `c:\RestoOps\apps\api\app\db\session.py`

**What:** Async SQLAlchemy engine + session factory.

```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

**File:** `c:\RestoOps\apps\api\app\db\base.py`

```python
from sqlalchemy.orm import DeclarativeBase
import uuid
from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

class UUIDMixin:
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
```

---

## Step 1.9 — Alembic Setup

**Commands:**
```bash
cd apps/api
alembic init alembic
```

**Modify:** `c:\RestoOps\apps\api\alembic\env.py`
- Import `Base` from `app.db.base`
- Set `target_metadata = Base.metadata`
- Use sync `DATABASE_URL_SYNC` for migrations

**Modify:** `c:\RestoOps\apps\api\alembic.ini`
- Set `sqlalchemy.url` to use env var

**Verification:** `alembic revision --autogenerate -m "init"` runs without error (even if empty).

---

## Step 1.10 — Celery Application

**File:** `c:\RestoOps\apps\api\app\workers\celery_app.py`

```python
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "restoops",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.autodiscover_tasks(["app.workers"])
```

---

## Step 1.11 — Structured Logging

**File:** `c:\RestoOps\apps\api\app\core\logging.py`

**What:** Configure `structlog` for JSON-based structured logging.

```python
import structlog
import logging
from app.core.config import settings

def setup_logging():
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT != "development"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.LOG_LEVEL, logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
```

---

## Step 1.12 — FastAPI Application Shell

**File:** `c:\RestoOps\apps\api\app\main.py`

**What:** Minimal FastAPI app with:
- CORS middleware (explicit origins: `http://localhost:3000`)
- Prometheus instrumentator
- Lifespan handler (startup/shutdown)
- Health check endpoint: `GET /health` → `{"status": "ok"}`
- Root endpoint: `GET /` → `{"name": "RestoOps API", "version": "0.1.0"}`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from contextlib import asynccontextmanager
from app.core.logging import setup_logging
from app.core.config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Startup
    yield
    # Shutdown

app = FastAPI(
    title="RestoOps API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.WEB_APP_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/")
async def root():
    return {"name": "RestoOps API", "version": "0.1.0"}
```

**Run:** `uvicorn app.main:app --reload --port 8000` from `apps/api/`

---

## Step 1.13 — Makefile

**File:** `c:\RestoOps\Makefile`

```makefile
.PHONY: up down api worker beat test lint

up:
	docker-compose up -d

down:
	docker-compose down

api:
	cd apps/api && uvicorn app.main:app --reload --port 8000

worker:
	cd apps/api && celery -A app.workers.celery_app worker --loglevel=info

beat:
	cd apps/api && celery -A app.workers.celery_app beat --loglevel=info

migrate:
	cd apps/api && alembic upgrade head

migration:
	cd apps/api && alembic revision --autogenerate -m "$(msg)"

test:
	cd apps/api && pytest

lint:
	cd apps/api && ruff check .
```

---

## Step 1.14 — README (Initial)

**File:** `c:\RestoOps\README.md`

**Contents:** Project title, brief description, "Getting Started" with Docker Compose instructions, link to `final_goal.md`.

---

## Phase 1 Completion Checklist

- [ ] `.gitignore` created
- [ ] Full directory skeleton in place with `__init__.py` files
- [ ] `.env.example` created, `.env` copied and filled
- [ ] `docker-compose.yml` with postgres, redis, mailpit, ollama, prometheus, grafana
- [ ] `docker-compose up -d` → all services healthy
- [ ] Prometheus config file in `infrastructure/monitoring/prometheus/`
- [ ] `pyproject.toml` with all dependencies listed
- [ ] Python venv created, dependencies installed
- [ ] `core/config.py` — Settings class loads from `.env`
- [ ] `db/session.py` — Async engine + session factory
- [ ] `db/base.py` — Base, TimestampMixin, UUIDMixin
- [ ] Alembic initialized, can generate empty migration
- [ ] `workers/celery_app.py` — Celery configured
- [ ] `core/logging.py` — Structured logging configured
- [ ] `main.py` — FastAPI app boots, `/health` returns OK, `/metrics` exposed
- [ ] Makefile works: `make up`, `make api`, `make worker`
- [ ] README.md with basic setup instructions
- [ ] `git add . && git commit -m "Phase 1: Foundation"` succeeds

---

## Transition to Phase 2

Once all boxes are checked, proceed to [02-auth-rbac-multitenancy.md](./02-auth-rbac-multitenancy.md).

Phase 2 will build on this foundation by adding the `organizations`, `users`, `roles`, and `user_roles` database models, JWT authentication, RBAC middleware, and the auth/user/org API endpoints.
