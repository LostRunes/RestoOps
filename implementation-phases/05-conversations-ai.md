# Phase 5 — Conversations, AI Agent & Human-in-the-Loop

> **Goal:** Build the AI agent layer using Ollama. The agent analyzes conversations, classifies intent, suggests actions via structured outputs, calls controlled tools, and requires human approval before executing. This implements the core philosophy: **AI suggests → human decides → system executes.**

> **Depends on:** Phase 4 (Campaigns, Email, Conversations)

---

## Step 5.1 — Database Models

### 5.1.1 — AI Runs Model

**File:** `apps/api/app/models/ai_run.py`

```text
Table: ai_runs
───────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL

agent             VARCHAR(50)    # CONVERSATION_ANALYZER, QUOTE_GENERATOR, LEAD_SCORER, etc.
model             VARCHAR(100)   # llama3.2, mistral, etc.

conversation_id   UUID, FK → conversations.id, NULLABLE
lead_id           UUID, FK → leads.id, NULLABLE

input             TEXT           # The prompt/context sent to LLM
output            TEXT           # The raw LLM response

structured_output JSONB, NULLABLE  # Parsed structured output

latency_ms        INTEGER
tokens_used       INTEGER, NULLABLE

status            VARCHAR(20)    # COMPLETED, FAILED, TIMEOUT
error             TEXT, NULLABLE

created_at        TIMESTAMP WITH TZ
```

### 5.1.2 — AI Actions Model

**File:** `apps/api/app/models/ai_action.py`

```text
Table: ai_actions
──────────────────
id              UUID, PK
ai_run_id       UUID, FK → ai_runs.id, NOT NULL
organization_id UUID, FK → organizations.id, NOT NULL

tool            VARCHAR(100)    # create_quote, send_email, update_lead, schedule_followup, etc.
arguments       JSONB           # Tool arguments as JSON
result          JSONB, NULLABLE # Execution result

status          VARCHAR(20)     # PROPOSED, APPROVED, REJECTED, EXECUTED, FAILED

approved_by     UUID, FK → users.id, NULLABLE
approved_at     TIMESTAMP WITH TZ, NULLABLE
executed_at     TIMESTAMP WITH TZ, NULLABLE

rejection_reason TEXT, NULLABLE

created_at      TIMESTAMP WITH TZ
```

### 5.1.3 — Migration

```bash
alembic revision --autogenerate -m "add ai_runs and ai_actions tables"
alembic upgrade head
```

---

## Step 5.2 — Ollama Integration

**File:** `apps/api/app/integrations/ollama/__init__.py`
**File:** `apps/api/app/integrations/ollama/client.py`

```python
import httpx
from app.core.config import settings

class OllamaClient:
    def __init__(self, base_url: str = None, model: str = None):
        self.base_url = base_url or settings.OLLAMA_URL
        self.model = model or settings.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(self, prompt: str, system: str = None, 
                       format: str = "json") -> dict:
        """
        POST {base_url}/api/generate
        
        Body:
        {
            "model": self.model,
            "prompt": prompt,
            "system": system,
            "format": format,
            "stream": false,
            "options": {
                "temperature": 0.3,
                "num_predict": 2048
            }
        }
        
        Returns:
        {
            "response": str,
            "total_duration": int (nanoseconds),
            "eval_count": int (tokens),
        }
        
        Error handling:
        - Connection refused → raise with clear message
        - Timeout → raise with latency info
        - Invalid JSON in response → parse error
        """
    
    async def chat(self, messages: list[dict], system: str = None,
                   format: str = "json") -> dict:
        """
        POST {base_url}/api/chat
        
        For multi-turn conversation analysis.
        Messages format: [{"role": "user", "content": "..."}, ...]
        """
    
    async def health_check(self) -> bool:
        """GET {base_url}/api/tags → returns True if Ollama is running."""
```

---

## Step 5.3 — AI Agent Architecture

**Directory:** `apps/api/app/agents/`

```text
agents/
├── __init__.py
├── base.py              # Base agent class
├── conversation_agent.py # Conversation analyzer
├── tools.py             # Tool definitions & registry
├── prompts.py           # System prompts & templates
└── schemas.py           # Structured output schemas
```

### 5.3.1 — Base Agent

**File:** `apps/api/app/agents/base.py`

```python
class BaseAgent:
    def __init__(self, ollama_client: OllamaClient, name: str):
        self.ollama = ollama_client
        self.name = name
    
    async def run(self, context: dict) -> AgentResult:
        """
        1. Build prompt from context
        2. Call Ollama
        3. Parse structured response
        4. Identify proposed actions
        5. Return AgentResult
        """
    
    def build_prompt(self, context: dict) -> str:
        """Override in subclasses."""
        raise NotImplementedError
    
    def parse_response(self, raw_response: str) -> dict:
        """Parse JSON from LLM response. Handle malformed JSON gracefully."""
```

### 5.3.2 — Agent Result Schema

**File:** `apps/api/app/agents/schemas.py`

```python
from pydantic import BaseModel

class ConversationAnalysis(BaseModel):
    intent: str           # NEEDS_QUOTE, INTERESTED, NOT_INTERESTED, QUESTION, COMPLAINT, SCHEDULING, GENERAL
    sentiment: str        # POSITIVE, NEUTRAL, NEGATIVE
    urgency: str          # HIGH, MEDIUM, LOW
    
    guest_count: int | None = None
    event_date: str | None = None
    event_type: str | None = None
    budget_mentioned: str | None = None
    dietary_requirements: list[str] | None = None
    
    key_points: list[str]
    
    suggested_lead_status: str | None = None    # INTERESTED, QUALIFIED, etc.
    
    suggested_actions: list[SuggestedAction]

class SuggestedAction(BaseModel):
    tool: str             # create_quote, send_email, update_lead, schedule_followup, create_task
    description: str      # Human-readable description
    arguments: dict       # Tool-specific arguments
    confidence: float     # 0.0 to 1.0
    requires_approval: bool = True
```

### 5.3.3 — System Prompts

**File:** `apps/api/app/agents/prompts.py`

```python
CONVERSATION_ANALYZER_SYSTEM = """
You are an AI assistant for a catering business. You analyze customer conversations 
and suggest actions for the restaurant staff.

You must respond in valid JSON format matching this schema:
{
    "intent": "NEEDS_QUOTE | INTERESTED | NOT_INTERESTED | QUESTION | COMPLAINT | SCHEDULING | GENERAL",
    "sentiment": "POSITIVE | NEUTRAL | NEGATIVE",
    "urgency": "HIGH | MEDIUM | LOW",
    "guest_count": null or integer,
    "event_date": null or "YYYY-MM-DD" or descriptive string,
    "event_type": null or string,
    "budget_mentioned": null or string,
    "dietary_requirements": null or list of strings,
    "key_points": ["point 1", "point 2"],
    "suggested_lead_status": null or "INTERESTED | QUALIFIED | WON | LOST",
    "suggested_actions": [
        {
            "tool": "create_quote | send_email | update_lead | schedule_followup | create_task",
            "description": "human readable description",
            "arguments": {},
            "confidence": 0.0-1.0,
            "requires_approval": true
        }
    ]
}

Rules:
- Always suggest actions that help close the deal
- If guest count and date are mentioned, suggest creating a quote
- If the customer says "don't contact me", suggest adding to suppression list
- Never make up data — only extract what's in the conversation
- Be conservative with confidence scores
- All actions with side effects require approval
"""

QUOTE_SUGGESTION_CONTEXT = """
Given the following conversation and lead information, suggest a catering quote.
Include estimated items, quantities, and pricing based on typical catering rates.
"""
```

### 5.3.4 — Conversation Agent

**File:** `apps/api/app/agents/conversation_agent.py`

```python
class ConversationAgent(BaseAgent):
    def __init__(self, ollama_client: OllamaClient):
        super().__init__(ollama_client, "CONVERSATION_ANALYZER")
    
    async def analyze(self, conversation: Conversation, messages: list[Message], 
                      lead: Lead) -> ConversationAnalysis:
        """
        1. Build context:
            - Lead info (company, contact, industry, score)
            - Conversation channel
            - Full message history (formatted as thread)
        2. Build prompt with system prompt + context
        3. Call Ollama (format=json)
        4. Parse response into ConversationAnalysis
        5. Log AI run (input, output, latency, tokens)
        6. Create AI action records for each suggested_action (status=PROPOSED)
        7. Return analysis
        """
    
    def build_prompt(self, context: dict) -> str:
        """
        Format:
        ---
        Lead: {company_name} ({industry})
        Contact: {contact_name}
        Score: {score}/100 ({priority})
        
        Conversation:
        [OUTBOUND] {date}: {body}
        [INBOUND] {date}: {body}
        ---
        Analyze this conversation and suggest actions.
        """
```

---

## Step 5.4 — Tool Registry

**File:** `apps/api/app/agents/tools.py`

```python
from typing import Callable

class ToolRegistry:
    """Registry of tools the AI can suggest calling."""
    
    _tools: dict[str, dict] = {}
    
    @classmethod
    def register(cls, name: str, description: str, handler: Callable, 
                 requires_approval: bool = True):
        cls._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
            "requires_approval": requires_approval,
        }
    
    @classmethod
    def get_tool(cls, name: str) -> dict | None:
        return cls._tools.get(name)
    
    @classmethod
    def execute(cls, name: str, **kwargs) -> dict:
        tool = cls._tools.get(name)
        if not tool:
            raise ValueError(f"Unknown tool: {name}")
        return tool["handler"](**kwargs)

# Register tools:
# - create_quote: Creates a draft quote
# - send_email: Sends an email to a lead
# - update_lead: Updates lead status/fields
# - schedule_followup: Creates a follow-up task
# - create_task: Creates a manual task for staff
# - add_suppression: Adds email to suppression list
```

---

## Step 5.5 — Human-in-the-Loop Service

**File:** `apps/api/app/services/ai_service.py`

```python
class AIService:
    def __init__(self, ollama: OllamaClient, ai_run_repo, ai_action_repo):
        ...
    
    async def analyze_conversation(self, conversation_id: UUID, org_id: UUID) -> ConversationAnalysis:
        """
        1. Fetch conversation + messages + lead
        2. Run ConversationAgent.analyze()
        3. Store AI run record
        4. For each suggested action:
            a. Create ai_actions record (status=PROPOSED)
            b. Queue notification for user (Phase 8)
        5. Return analysis
        """
    
    async def approve_action(self, action_id: UUID, user_id: UUID, org_id: UUID) -> dict:
        """
        1. Fetch AI action
        2. Validate status == PROPOSED
        3. Execute the tool via ToolRegistry
        4. Update action: status=EXECUTED, approved_by, approved_at, result
        5. Create audit log
        6. Return execution result
        """
    
    async def reject_action(self, action_id: UUID, user_id: UUID, org_id: UUID, reason: str) -> None:
        """
        1. Fetch AI action
        2. Validate status == PROPOSED
        3. Update: status=REJECTED, rejection_reason
        4. Create audit log
        """
    
    async def edit_and_approve(self, action_id: UUID, user_id: UUID, org_id: UUID,
                                new_arguments: dict) -> dict:
        """
        1. Fetch AI action
        2. Update arguments with user edits
        3. Execute with edited arguments
        4. Update status → EXECUTED
        """
    
    async def list_pending_actions(self, org_id: UUID) -> list[AIAction]:
        """List all PROPOSED actions for the org."""
    
    async def get_ai_activity(self, org_id: UUID, page: int = 1) -> list[AIRun]:
        """Paginated list of all AI runs with actions."""
```

---

## Step 5.6 — Repositories

### `apps/api/app/repositories/ai_run_repo.py`

```python
class AIRunRepository:
    async def create(self, org_id, agent, model, input_text, output_text, 
                     structured_output, latency_ms, tokens, status, 
                     conversation_id=None, lead_id=None) -> AIRun: ...
    async def get_by_id(self, run_id, org_id) -> AIRun | None: ...
    async def list_by_org(self, org_id, page=1, page_size=20) -> list[AIRun]: ...
```

### `apps/api/app/repositories/ai_action_repo.py`

```python
class AIActionRepository:
    async def create(self, ai_run_id, org_id, tool, arguments, status="PROPOSED") -> AIAction: ...
    async def get_by_id(self, action_id, org_id) -> AIAction | None: ...
    async def update(self, action_id, **data) -> AIAction: ...
    async def list_pending(self, org_id) -> list[AIAction]: ...
    async def list_by_run(self, ai_run_id) -> list[AIAction]: ...
```

---

## Step 5.7 — Celery Worker for AI Processing

**File:** `apps/api/app/workers/ai_worker.py`

```python
@celery_app.task(bind=True, max_retries=2)
def process_conversation_ai(self, conversation_id: str, org_id: str):
    """
    Called when a new inbound message is received.
    
    1. Run AIService.analyze_conversation()
    2. If analysis suggests high-confidence actions:
        a. Create notification for user
        b. Publish via WebSocket (Phase 8)
    3. Handle Ollama errors gracefully:
        - Connection refused: retry after 30s
        - Timeout: retry after 60s
        - Invalid response: log and store error
    """
```

Update email ingestion (Phase 4) to queue this task after creating an inbound message:
```python
# In email_ingestion.py, after creating message:
process_conversation_ai.delay(str(conversation.id), str(org_id))
```

---

## Step 5.8 — API Routes

### `apps/api/app/api/ai.py`

```text
GET  /api/v1/ai/activity                    → List AI runs (paginated)
GET  /api/v1/ai/activity/{run_id}           → Get AI run with actions
GET  /api/v1/ai/actions/pending              → List all pending actions

POST /api/v1/ai/actions/{action_id}/approve  → Approve action
POST /api/v1/ai/actions/{action_id}/reject   → Reject action (with reason)
POST /api/v1/ai/actions/{action_id}/edit     → Edit arguments and approve

POST /api/v1/ai/analyze/{conversation_id}    → Manually trigger AI analysis on a conversation
```

### Pydantic Schemas

**File:** `apps/api/app/schemas/ai.py`

```python
# AIRunResponse: all fields + list of actions
# AIActionResponse: all fields
# AIActionApproveRequest: (empty or with modifications)
# AIActionRejectRequest: reason
# AIActionEditRequest: new_arguments: dict
# AIAnalysisResponse: ConversationAnalysis data
```

### Register Router

```python
from app.api import ai
app.include_router(ai.router, prefix="/api/v1/ai", tags=["ai"])
```

---

## Step 5.9 — Audit Logging Integration

**File:** `apps/api/app/models/audit_log.py`

```text
Table: audit_logs
──────────────────
id                UUID, PK
organization_id   UUID, FK → organizations.id, NOT NULL
user_id           UUID, FK → users.id, NULLABLE

action            VARCHAR(100)   # AI_ACTION_APPROVED, AI_ACTION_REJECTED, LEAD_UPDATED, etc.
entity_type       VARCHAR(50)    # ai_action, lead, quote, campaign, etc.
entity_id         UUID

old_value         JSONB, NULLABLE
new_value         JSONB, NULLABLE

ip_address        VARCHAR(45), NULLABLE
user_agent        TEXT, NULLABLE

created_at        TIMESTAMP WITH TZ
```

**File:** `apps/api/app/services/audit_service.py`

```python
class AuditService:
    async def log(self, org_id, user_id, action, entity_type, entity_id,
                  old_value=None, new_value=None, ip_address=None):
        """Create audit log entry."""
```

This service should be called from:
- AI action approval/rejection
- Lead status changes
- Quote creation/updates
- Campaign start/stop
- User creation
- Role changes

---

## Phase 5 Completion Checklist

- [ ] `ai_runs` table created
- [ ] `ai_actions` table created
- [ ] `audit_logs` table created
- [ ] Alembic migration applied
- [ ] Ollama client: can connect and generate responses
- [ ] Ollama client: handles connection errors, timeouts
- [ ] Conversation agent: builds proper context from messages + lead
- [ ] Conversation agent: sends prompt with system instructions
- [ ] Conversation agent: parses structured JSON response
- [ ] Conversation agent: extracts intent, sentiment, urgency, guest count, event date
- [ ] Conversation agent: suggests actions (create_quote, send_email, update_lead, etc.)
- [ ] AI run records stored with input, output, latency, tokens
- [ ] AI actions created as PROPOSED for each suggested action
- [ ] Tool registry: tools registered and callable
- [ ] Approve action: executes tool, updates status, creates audit log
- [ ] Reject action: updates status, stores reason, creates audit log
- [ ] Edit action: modifies arguments before execution
- [ ] Pending actions API: lists all PROPOSED actions
- [ ] AI activity API: paginated history of all AI runs
- [ ] Manual analysis trigger: POST /ai/analyze/{conversation_id}
- [ ] Celery worker: processes conversation AI after inbound message
- [ ] Celery worker: retries on Ollama errors
- [ ] Audit service: logs important state changes
- [ ] Email ingestion (Phase 4) updated to queue AI processing
- [ ] All queries scoped to organization_id
- [ ] `git commit -m "Phase 5: AI agent, human-in-the-loop, audit logs"`

---

## Transition to Phase 6

Once all boxes are checked, proceed to [06-quotes-orders.md](./06-quotes-orders.md).

Phase 6 will build the quote system (creation, line items, pricing, sending, acceptance) and the order system (quote→order conversion, status tracking, revenue).
