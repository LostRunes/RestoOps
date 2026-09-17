# Catering Revenue Agent — Implementation Master Plan

## Overview

This document is the master index for all implementation phases. The project is decomposed into **10 phases**, each with its own detailed `.md` file in this folder. Phases are ordered by dependency — each phase builds on the previous one.

> **Rule:** No files from any phase are ever deleted. Each phase adds to the codebase incrementally.

---

## Phase Map

| Phase | File | Title | Depends On | Estimated Effort |
|-------|------|-------|------------|------------------|
| 1 | [01-foundation.md](./01-foundation.md) | Project Foundation & Infrastructure | — | 2-3 days |
| 2 | [02-auth-rbac-multitenancy.md](./02-auth-rbac-multitenancy.md) | Auth, RBAC & Multi-Tenancy | Phase 1 | 2-3 days |
| 3 | [03-leads-verification.md](./03-leads-verification.md) | Leads, Email Verification Engine & Scoring | Phase 2 | 3-4 days |
| 4 | [04-campaigns-email.md](./04-campaigns-email.md) | Campaigns, Email Sending & Ingestion | Phase 3 | 2-3 days |
| 5 | [05-conversations-ai.md](./05-conversations-ai.md) | Conversations, AI Agent & Human-in-the-Loop | Phase 4 | 3-4 days |
| 6 | [06-quotes-orders.md](./06-quotes-orders.md) | Quotes, Orders & Revenue Pipeline | Phase 5 | 2 days |
| 7 | [07-calling.md](./07-calling.md) | Calling — Twilio & WebRTC | Phase 6 | 2-3 days |
| 8 | [08-notifications-events.md](./08-notifications-events.md) | Notifications, Events & Real-Time | Phase 7 | 2 days |
| 9 | [09-frontend.md](./09-frontend.md) | Next.js Frontend Dashboard | Phase 8 | 4-5 days |
| 10 | [10-testing-observability-cicd.md](./10-testing-observability-cicd.md) | Testing, Observability, CI/CD & Documentation | Phase 9 | 2-3 days |

---

## Repository Structure (Target)

```text
c:\RestoOps\
├── apps/
│   ├── api/                     # FastAPI backend
│   │   ├── app/
│   │   │   ├── main.py
│   │   │   ├── api/             # Route handlers
│   │   │   ├── models/          # SQLAlchemy models
│   │   │   ├── schemas/         # Pydantic schemas
│   │   │   ├── repositories/    # Data access layer
│   │   │   ├── services/        # Business logic
│   │   │   ├── workers/         # Celery tasks
│   │   │   ├── agents/          # AI agent logic
│   │   │   ├── integrations/    # External providers
│   │   │   │   ├── email/
│   │   │   │   ├── twilio/
│   │   │   │   └── ollama/
│   │   │   ├── core/            # Auth, config, deps, events
│   │   │   └── db/              # DB session, base
│   │   ├── tests/
│   │   ├── pyproject.toml
│   │   └── alembic/
│   │       └── versions/
│   │
│   └── web/                     # Next.js frontend
│       ├── app/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       └── types/
│
├── migrations/                  # Alembic config
├── infrastructure/
│   ├── docker/
│   └── monitoring/
│       ├── prometheus/
│       └── grafana/
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── decisions/
├── scripts/
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
├── .gitignore
├── final_goal.md
└── implementation-phases/       # This folder
```

---

## Transition Rules

1. **Before starting Phase N+1**, verify Phase N's checklist is fully green.
2. **No file is ever deleted** — only added or modified.
3. **Database changes** always go through Alembic migrations.
4. **Each phase creates its own Alembic migration** for any schema additions.
5. **Docker Compose** is updated incrementally — new services added per phase.
6. **Tests** for each phase's components are written during that phase, not deferred.

---

## Technology Stack Reference

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js (React, TypeScript, App Router) |
| UI Kit | Tailwind CSS + shadcn/ui |
| Data Fetching | TanStack Query |
| Charts | Recharts |
| Backend | Python, FastAPI |
| Validation | Pydantic |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Database | PostgreSQL |
| Cache/Broker | Redis |
| Background Jobs | Celery + Celery Beat |
| AI | Ollama (local LLM) |
| Email (Dev) | Mailpit |
| Phone Calls | Twilio (trial) |
| Browser Calls | WebRTC (native APIs) |
| Monitoring | Prometheus + Grafana |
| Testing | pytest, httpx, Playwright |
| CI/CD | GitHub Actions |
| Containerization | Docker + Docker Compose |

---

## Manual Requirements (For the Human)

See: [requirements.md](./requirements.md) for everything you need to install manually before/during the build.
