# RestoOps — Catering Revenue Agent

RestoOps is an AI-powered catering and revenue operations platform for restaurants.

## Project Structure

```
RestoOps/
├── apps/
│   ├── api/             # FastAPI Backend Service (Python)
│   └── web/             # Next.js Dashboard Frontend (TypeScript)
├── infrastructure/
│   └── monitoring/      # Prometheus & Grafana configurations
├── implementation-phases/# Implementation plans (00 to 10)
├── docker-compose.yml   # Dev environment infrastructure services
└── Makefile             # Developer workflow commands
```

## Local Development Setup

### 1. Requirements
- Docker Desktop
- Python 3.11+
- Node.js 18+

### 2. Infrastructure
Start all core backing services (PostgreSQL, Redis, Mailpit, Ollama, Prometheus, Grafana):
```bash
docker compose up -d
```

### 3. Backend Setup
```bash
cd apps/api
pip install -e .
uvicorn app.main:app --reload
```

- API Base URL: `http://localhost:8000`
- API Health Check: `http://localhost:8000/health`
- Swagger Docs: `http://localhost:8000/docs`
- Mailpit UI: `http://localhost:8025`
- Prometheus UI: `http://localhost:9090`
- Grafana UI: `http://localhost:3000` (admin/admin)
