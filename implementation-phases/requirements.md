# Manual Requirements — What You Need to Install

> These are tools/software that **you** must install manually. The agent cannot install these for you. Complete these before starting Phase 1.

---

## ✅ Required Before Phase 1

### 1. Docker Desktop
- **What:** Runs PostgreSQL, Redis, Mailpit, Ollama, Prometheus, Grafana as containers
- **Install:** https://www.docker.com/products/docker-desktop/
- **Verify:** `docker --version` and `docker-compose --version`
- **Note:** On Windows, ensure WSL 2 backend is enabled

### 2. Python ≥ 3.11
- **What:** Backend language
- **Install:** https://www.python.org/downloads/
- **Verify:** `python --version` → 3.11+
- **Note:** Ensure `pip` is available. Add to PATH during installation.

### 3. Node.js ≥ 18
- **What:** Frontend runtime
- **Install:** https://nodejs.org/en/download/
- **Verify:** `node --version` → 18+ and `npm --version`

### 4. Git
- **What:** Version control
- **Install:** https://git-scm.com/downloads
- **Verify:** `git --version`

---

## ✅ Required Before Phase 7 (Calling)

### 5. Twilio Account (Free Trial)
- **What:** Phone call API (trial gives ~$15 credit)
- **Sign up:** https://www.twilio.com/try-twilio
- **Get:**
  - Account SID
  - Auth Token
  - Phone Number (claim a free trial number)
- **Put in `.env`:**
  ```
  TWILIO_ACCOUNT_SID=AC...
  TWILIO_AUTH_TOKEN=...
  TWILIO_PHONE_NUMBER=+1...
  ```
- **Trial limitations:**
  - Can only call verified numbers
  - Calls prefixed with "This is a trial account..." message
  - These are fine for demo purposes

### 6. ngrok (For Twilio Webhooks in Dev)
- **What:** Exposes your localhost to the internet so Twilio can send webhooks back
- **Install:** https://ngrok.com/download
- **Usage:** `ngrok http 8000` → gives a public URL
- **Set Twilio webhook URLs** to the ngrok URL
- **Alternative:** Twilio CLI has `twilio phone-numbers:update` for webhook setup

---

## ✅ Required Before Phase 9 (Frontend)

### 7. Ollama Model Download
- **What:** The local LLM model that powers the AI agent
- **After Docker Compose is running:**
  ```bash
  docker exec -it <ollama-container-name> ollama pull llama3.2
  ```
  Or if Ollama is running natively:
  ```bash
  ollama pull llama3.2
  ```
- **Verify:** `curl http://localhost:11434/api/tags` → shows llama3.2
- **Note:** llama3.2 is ~2GB. Smaller models like `phi3:mini` work too if RAM is limited.

---

## ✅ Required Before Phase 10 (Testing)

### 8. Playwright Browsers
- **What:** Headless browsers for E2E testing
- **Install (after npm install):**
  ```bash
  cd apps/web
  npx playwright install
  ```

---

## 📋 Optional / Nice-to-Have

### PostgreSQL Client (psql)
- **What:** CLI to query the database directly
- **Install:** Comes with PostgreSQL, or install separately
- **Usage:** `psql -h localhost -U restoops -d restoops`

### Redis CLI
- **What:** CLI to inspect Redis
- **Install:** Comes with Redis, or use `redis-tools` package
- **Usage:** `redis-cli ping` → PONG

### Make (for Makefile)
- **What:** Task runner
- **Windows:** Install via Chocolatey: `choco install make`
- **Or:** Just run the commands from the Makefile manually

### Postman or httpie
- **What:** API testing tool
- **Install:** https://www.postman.com/downloads/ or `pip install httpie`
- **Usage:** Test API endpoints manually

---

## ⚙️ MCP Connections

No MCP server connections are needed for this project. Everything runs locally:

| Service | How it's accessed |
|---------|------------------|
| PostgreSQL | Direct TCP connection (asyncpg), runs in Docker |
| Redis | Direct TCP connection (redis-py), runs in Docker |
| Mailpit | SMTP on port 1025 + HTTP API on port 8025, runs in Docker |
| Ollama | HTTP API on port 11434, runs in Docker |
| Twilio | REST API via `twilio` Python SDK (internet required) |
| Prometheus | HTTP on port 9090, runs in Docker |
| Grafana | HTTP on port 3001, runs in Docker |

---

## 💰 Cost Summary

| Service | Cost |
|---------|------|
| PostgreSQL | FREE (Docker) |
| Redis | FREE (Docker) |
| Mailpit | FREE (Docker) |
| Ollama | FREE (Docker) |
| Prometheus | FREE (Docker) |
| Grafana | FREE (Docker) |
| Twilio | FREE trial (~$15 credit, enough for demos) |
| ngrok | FREE tier (sufficient for dev) |
| **Total** | **$0** for development |

---

## 🖥️ System Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| RAM | 8 GB | 16 GB (Ollama needs ~4GB for llama3.2) |
| Disk | 10 GB | 20 GB (Docker images + Ollama model) |
| CPU | 4 cores | 8 cores (for concurrent workers) |
| GPU | None | Any NVIDIA GPU (speeds up Ollama, not required) |

---

## Pre-Flight Checklist

Run these commands to verify everything is ready:

```bash
# Docker
docker --version
docker-compose --version

# Python  
python --version
pip --version

# Node
node --version
npm --version

# Git
git --version

# Start infrastructure
cd c:\RestoOps
docker-compose up -d

# Verify services
curl http://localhost:8025          # Mailpit UI
curl http://localhost:11434/api/tags # Ollama
curl http://localhost:9090          # Prometheus
curl http://localhost:3001          # Grafana
```

If all return valid responses, you're ready to begin Phase 1.
