# Catering Revenue Agent

## Complete Implementation End Goal & Technical Specification

> **Goal:** Build an almost-production-grade portfolio implementation of an AI-powered catering/revenue operations platform for restaurants, demonstrating the backend, systems, AI-agent, communication, email-verification, authentication, database, queueing, and real-time engineering skills required for a platform like Kutlerri.
>
> **Important:** This is a serious portfolio/prototype system, not a production SaaS. We will build production-style architecture and engineering practices without introducing unnecessary enterprise infrastructure.

---

# 1. What We Are Building

A restaurant operator gets a complete revenue/catering operations dashboard.

The system allows restaurant staff to:

1. Create/manage a restaurant organization.
2. Invite multiple admins/users.
3. Assign roles and permissions.
4. Import or discover potential catering leads.
5. Verify lead emails using our **own email-verification engine**.
6. Score and prioritize leads.
7. Create outreach campaigns.
8. Send emails through a local/dev email infrastructure.
9. Receive and parse replies.
10. Automatically associate replies with conversations.
11. Use a local AI agent to understand conversations.
12. Have the AI suggest actions.
13. Require human approval for important actions.
14. Generate catering quotes.
15. Send quotes.
16. Track quote status.
17. Convert accepted quotes into orders.
18. Schedule follow-ups.
19. Send notifications.
20. Make phone calls through Twilio.
21. Support browser-to-browser WebRTC calls.
22. Receive Twilio webhooks.
23. Maintain a complete activity/audit history.
24. Run long-running work through background queues.
25. Monitor system health and job performance.

The core philosophy is:

**AI suggests → human decides → system executes.**

---

# 2. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │      Next.js Web     │
                         │      Dashboard       │
                         └──────────┬───────────┘
                                    │
                              HTTPS / WS
                                    │
                         ┌──────────▼───────────┐
                         │      FastAPI API     │
                         │ Authentication/RBAC  │
                         │ REST + WebSockets    │
                         │ Webhooks             │
                         └───────┬─────┬────────┘
                                 │     │
                    ┌────────────┘     └───────────────┐
                    │                                  │
             ┌──────▼──────┐                    ┌──────▼──────┐
             │ PostgreSQL  │                    │    Redis    │
             │   Database  │                    │ Cache/Queue │
             └─────────────┘                    └──────┬──────┘
                                                       │
                                              ┌────────▼────────┐
                                              │ Celery Workers  │
                                              │ Background Jobs  │
                                              └──────┬──────────┘
                                                     │
          ┌──────────────────────┬───────────────────┼──────────────────┐
          │                      │                   │                  │
   ┌──────▼──────┐       ┌──────▼──────┐     ┌──────▼──────┐    ┌──────▼──────┐
   │   Email     │       │  Verifier   │     │   Ollama    │    │   Twilio    │
   │  Mailpit    │       │ Our Engine  │     │ Local LLM    │    │ Voice/SMS   │
   └─────────────┘       └─────────────┘     └─────────────┘    └─────────────┘
                                                                    │
                                                             Phone Network
                                                                    │
                                                               Customer Phone


                     WebRTC
       Admin Browser ◄──────────────► Customer Browser
                         │
                     WebSocket
                      Signaling
                         │
                     FastAPI
```

---

# 3. Technology Stack

## Frontend

### Next.js

* React
* TypeScript
* App Router

### UI

* Tailwind CSS
* shadcn/ui

### Data/API

* TanStack Query

### Charts

* Recharts

### Real-time

* WebSocket client

### Browser calling

* Native WebRTC APIs

---

# 4. Backend

## Python

Primary backend language.

We will deliberately use Python heavily because the project needs:

* FastAPI
* async programming
* background workers
* networking
* DNS
* SMTP
* AI
* data processing
* APIs
* WebSockets

---

## FastAPI

Primary backend framework.

Responsibilities:

* REST API
* authentication
* authorization
* request validation
* WebSocket signaling
* webhook endpoints
* dependency injection
* API documentation

We will NOT build the main backend in Django.

Django concepts should still be understood, but FastAPI is the primary implementation.

---

## Pydantic

Used for:

* API request models
* response models
* configuration
* validation
* AI structured outputs

---

## SQLAlchemy 2.0

Used for database access.

Use:

* async SQLAlchemy where appropriate
* typed models
* repositories/services
* transactions
* relationship management

---

## Alembic

Database migrations.

Never manually modify production-style schema without migrations.

---

# 5. Database

## PostgreSQL

Primary relational database.

Why:

* relational business data
* transactions
* constraints
* relationships
* indexing
* JSONB where useful
* excellent fit for multi-tenant SaaS
* demonstrates SQL skills

---

# 6. Redis

Redis is used for:

* Celery broker
* background jobs
* temporary state
* caching
* rate limiting
* short-lived locks
* possibly WebSocket-related ephemeral state

Redis is NOT our primary database.

---

# 7. Background Processing

## Celery

Long-running tasks must not block FastAPI requests.

Examples:

```text
CSV verification
Email sending
Email ingestion
Lead scoring
Campaign execution
Follow-up scheduling
AI processing
Quote generation
Notification generation
Analytics calculations
```

Architecture:

```text
FastAPI
   ↓
Create Job
   ↓
Redis
   ↓
Celery Worker
   ↓
Execute
   ↓
PostgreSQL
```

---

# 8. Scheduling

## Celery Beat

Used for scheduled work.

Examples:

```text
Follow-up due
Campaign step due
Quote expiration
Daily analytics
Periodic cleanup
Retry processing
```

Do NOT do:

```python
time.sleep(...)
```

inside API handlers or long-running worker logic when scheduling future work.

---

# 9. Authentication

We will build authentication ourselves.

## Stack

* Password hashing: Argon2
* JWT access tokens
* Refresh tokens
* FastAPI dependencies
* PostgreSQL sessions/token metadata where appropriate

Flow:

```text
Login
  ↓
Verify password
  ↓
Generate access token
  ↓
Generate refresh token
  ↓
Frontend stores/authenticates
  ↓
API validates JWT
```

---

# 10. Authorization / RBAC

Roles:

```text
OWNER
ADMIN
MANAGER
AGENT
VIEWER
```

Example:

### OWNER

Everything.

### ADMIN

Users, campaigns, leads, quotes, settings.

### MANAGER

Operations, campaigns, quotes, conversations.

### AGENT

Leads, conversations, follow-ups.

### VIEWER

Read-only access.

Authorization must happen on the backend.

Never trust the frontend to enforce permissions.

---

# 11. Multi-Tenant Architecture

The platform supports multiple organizations.

Every important business record belongs to an organization.

Example:

```text
Organization
   │
   ├── Users
   ├── Restaurants
   ├── Leads
   ├── Campaigns
   ├── Conversations
   ├── Quotes
   ├── Orders
   └── Notifications
```

Most relevant tables contain:

```text
organization_id
```

Many operational tables additionally contain:

```text
restaurant_id
```

Every backend query must be scoped to the authenticated user's organization.

Example:

```text
User A
  ↓
Organization A
  ↓
Only Organization A's leads

User B
  ↓
Organization B
  ↓
Only Organization B's leads
```

This is one of the most important backend design requirements.

---

# 12. Database Schema

Core tables:

```text
organizations

users
roles
user_roles

restaurants

leads
lead_contacts
lead_verifications
lead_activities

campaigns
campaign_leads
campaign_steps

conversations
messages

calls
call_events

quotes
quote_items

orders
order_items

notifications

jobs
job_events

ai_runs
ai_actions

suppression_list

audit_logs
```

---

# 13. Organization

```text
organizations
--------------
id
name
slug
created_at
updated_at
```

---

# 14. Users

```text
users
-----
id
organization_id
email
password_hash
name
is_active
created_at
updated_at
```

Role assignment is separate.

---

# 15. Restaurants

```text
restaurants
-----------
id
organization_id
name
address
phone
email
website
timezone
created_at
updated_at
```

An organization can eventually operate multiple restaurants.

---

# 16. Leads

```text
leads
-----
id
organization_id
restaurant_id

company_name
contact_name

email
phone

address
industry
company_size

source

score
priority

pipeline_status

created_at
updated_at
```

Pipeline:

```text
NEW
 ↓
VERIFIED
 ↓
CONTACTED
 ↓
INTERESTED
 ↓
QUALIFIED
 ↓
QUOTE_SENT
 ↓
NEGOTIATING
 ↓
WON / LOST
```

---

# 17. Lead Verification

```text
lead_verifications
------------------
id
lead_id

email
status

syntax_valid
domain_valid
mx_valid
disposable
role_based
catch_all

smtp_code
smtp_message

mx_host

latency_ms

checked_at
```

Statuses:

```text
VALID
INVALID
RISKY
UNKNOWN
```

---

# 18. Our Own Email Verification Engine

This replaces Reoon/NeverBounce for the core project.

We are building our own verification subsystem.

Architecture:

```text
Email
 ↓
Normalize
 ↓
Syntax
 ↓
Domain
 ↓
DNS
 ↓
MX
 ↓
Disposable
 ↓
Role-based
 ↓
Catch-all
 ↓
SMTP
 ↓
Classification
```

---

# 19. Quick Verification Mode

Quick mode performs inexpensive checks:

```text
Syntax
DNS
MX
Disposable domain
Role-based address
```

Example:

```text
john@example.com

✓ Syntax
✓ Domain exists
✓ MX exists
✓ Not disposable
✓ Not role-based

→ likely valid
```

---

# 20. Power Verification Mode

Power mode performs deeper checks:

```text
Everything in Quick
+
Multiple MX servers
+
SMTP connection
+
MAIL FROM
+
RCPT TO
+
Catch-all detection
+
Retries
+
Greylisting handling
+
Timeout handling
```

---

# 21. Important SMTP Caveat

SMTP verification is NOT a guaranteed truth mechanism.

Some servers:

* block probes
* accept all addresses
* rate-limit
* greylist
* hide mailbox existence
* return misleading responses

Therefore:

```text
VALID
INVALID
RISKY
UNKNOWN
```

is more realistic than pretending every email can be perfectly classified.

---

# 22. Verification Engine Improvements

The prototype verifier will be upgraded to support:

### DNS

* multiple MX records
* MX priority
* NXDOMAIN distinction
* SERVFAIL distinction
* timeout distinction

### SMTP

* connection timeout
* command timeout
* retry/backoff
* multiple MX fallback
* controlled concurrency
* connection cleanup

### Caching

Cache domain-level MX information.

Example:

```text
gmail.com
 ↓
MX records cached
 ↓
Thousands of Gmail addresses
 ↓
No repeated DNS lookup
```

### Rate limiting

Avoid hammering the same mail server.

### Result metadata

Store:

```text
reason
smtp_code
mx_host
latency
attempts
checked_at
```

---

# 23. Verification Jobs

A CSV upload should NOT be processed directly inside FastAPI.

Flow:

```text
Upload CSV
 ↓
Create verification job
 ↓
Store job
 ↓
Queue Celery task
 ↓
Worker processes emails
 ↓
Update progress
 ↓
Store results
 ↓
Job completed
```

Job states:

```text
PENDING
RUNNING
COMPLETED
FAILED
CANCELLED
```

---

# 24. Lead Scoring

Initially deterministic.

Example:

```text
Distance              +20
Company size          +20
Relevant industry     +20
Valid email           +15
Valid phone           +10
Good source           +10
Existing interaction  +5
```

Maximum:

```text
100
```

Priority:

```text
80–100 → HOT
60–79  → HIGH
40–59  → MEDIUM
0–39   → LOW
```

Later the scoring system can incorporate AI.

---

# 25. Lead Sources

Do NOT depend on paid lead APIs.

Initial sources:

```text
CSV
Manual entry
Public/free data
Free APIs where available
```

Architecture should use an abstraction:

```python
class LeadSource:
    ...
```

Potential implementations:

```text
CSVLeadSource
ManualLeadSource
PublicLeadSource
```

This makes adding another source later easy.

---

# 26. Campaign System

A campaign contains:

```text
Campaign
 ├── Target leads
 ├── Email template
 ├── Campaign steps
 └── Schedule
```

Example:

```text
Day 0
Initial email

Day 3
Follow-up

Day 7
Second follow-up

Day 14
Final follow-up
```

---

# 27. Campaign Execution

```text
Campaign
 ↓
Find eligible leads
 ↓
Check suppression list
 ↓
Check verification status
 ↓
Queue email
 ↓
Worker sends
 ↓
Record message
 ↓
Schedule next step
```

Never send to a suppressed address.

---

# 28. Suppression List

```text
suppression_list
----------------
id
organization_id

email
phone

reason
source

created_at
```

Reasons:

```text
UNSUBSCRIBED
BOUNCED
DO_NOT_CONTACT
MANUAL_BLOCK
```

If someone says:

> Don't contact me again.

The system should:

```text
Create suppression record
+
Stop future campaign steps
+
Record audit event
```

---

# 29. Email Infrastructure

For development we use:

## Mailpit

Local SMTP server + email UI.

Architecture:

```text
Application
    ↓
SMTP
    ↓
Mailpit
    ↓
Browser inbox
```

This gives us a completely free development email environment.

---

# 30. Email Sending

Create an abstraction:

```python
class EmailService:
    send(...)
```

Implementation:

```text
MailpitEmailProvider
```

Later:

```text
SMTPProvider
ExternalProvider
```

The application should not directly depend on Mailpit.

---

# 31. Email Reading

We need to demonstrate email ingestion.

Flow:

```text
Mailbox
 ↓
IMAP / Mailpit
 ↓
Email reader
 ↓
Parse headers
 ↓
Find conversation
 ↓
Create message
 ↓
Queue AI processing
```

Important headers:

```text
Message-ID
In-Reply-To
References
From
To
Subject
Date
```

---

# 32. Conversation Matching

Incoming reply:

```text
Customer replies
 ↓
Message-ID / In-Reply-To / References
 ↓
Find existing conversation
 ↓
Attach message
 ↓
Update lead
```

If no match exists:

```text
Create new conversation
```

---

# 33. Conversations

```text
conversations
-------------
id
organization_id
restaurant_id
lead_id
channel

status

created_at
updated_at
```

Channels:

```text
EMAIL
SMS
VOICE
WEBRTC
```

---

# 34. Messages

```text
messages
--------
id
conversation_id

direction
sender
recipient

subject
body

message_id
in_reply_to

status

created_at
```

Directions:

```text
INBOUND
OUTBOUND
```

---

# 35. AI Layer

Use:

## Ollama

Local LLM.

No paid OpenAI/Anthropic/Gemini API is required.

Architecture:

```text
Conversation
 ↓
FastAPI / Worker
 ↓
Ollama
 ↓
Structured output
 ↓
AI decision layer
 ↓
Human approval
 ↓
Tool execution
```

---

# 36. AI Agent

The AI should NOT have unrestricted access to the database.

Instead it receives controlled tools.

Example:

```text
search_leads()
get_lead()
update_lead()

get_conversation()

create_quote()

send_email()

schedule_followup()

create_task()
```

---

# 37. AI Example

Customer:

> We're interested in catering lunch for around 120 people next Friday.

AI:

```text
Intent:
NEEDS_QUOTE

Guest count:
120

Event date:
Next Friday

Lead status:
INTERESTED

Suggested action:
CREATE_QUOTE
```

The AI then suggests:

```text
Create a catering quote for 120 guests.
```

Human:

```text
APPROVE
```

Only then does the system execute the action.

---

# 38. AI Runs

```text
ai_runs
-------
id
organization_id

agent
model

input
output

latency_ms
tokens

created_at
```

This gives us traceability.

---

# 39. AI Actions

```text
ai_actions
----------
id
ai_run_id

tool
arguments
result

status

approved_by
approved_at

created_at
```

Statuses:

```text
PROPOSED
APPROVED
REJECTED
EXECUTED
FAILED
```

---

# 40. Human-in-the-Loop UI

Example:

```text
┌───────────────────────────────────────┐
│ AI Recommendation                    │
│                                       │
│ Lead is interested in catering.       │
│ 120 guests detected.                  │
│                                       │
│ Suggested action: Create Quote        │
│                                       │
│ [ Approve ] [ Edit ] [ Reject ]       │
└───────────────────────────────────────┘
```

This is an important part of the system.

---

# 41. Quote System

```text
quotes
------
id
organization_id
restaurant_id
lead_id

event_date
guest_count

subtotal
tax
delivery_fee
total

status

expires_at

created_at
updated_at
```

Quote items:

```text
quote_items
-----------
id
quote_id

name
description
quantity
unit_price
total
```

Statuses:

```text
DRAFT
PENDING_APPROVAL
SENT
VIEWED
ACCEPTED
REJECTED
EXPIRED
```

---

# 42. Order System

Accepted quote:

```text
QUOTE
 ↓
ACCEPTED
 ↓
ORDER CREATED
```

Orders:

```text
orders
------
id
organization_id
restaurant_id
lead_id
quote_id

status
event_date
guest_count

total

created_at
updated_at
```

---

# 43. Calling Architecture

We implement TWO communication approaches.

## A. Twilio

For actual phone numbers.

## B. WebRTC

For browser-to-browser communication.

Both sit behind:

```python
CallService
```

---

# 44. Call Service

Conceptually:

```python
class CallService:
    start_call(...)
    end_call(...)
    get_call_status(...)
```

Providers:

```text
TwilioProvider
WebRTCProvider
```

The rest of the application doesn't care which provider is being used.

---

# 45. Twilio Architecture

```text
Admin Browser
      ↓
FastAPI
      ↓
Twilio
      ↓
Telephone Network
      ↓
Customer's Phone
```

The customer does NOT need the application.

This is the solution when we need to call a normal phone number.

For development, we can use Twilio's trial allowance rather than paying for calls.

The trial has restrictions, so this is for demonstrations/testing rather than unlimited usage.

---

# 46. WebRTC Architecture

```text
Admin Browser
      │
      │ SDP / ICE
      ▼
FastAPI WebSocket
      │
      │ Signaling
      ▼
Customer Browser
```

The actual audio is carried by the WebRTC peer connection.

The backend primarily handles:

```text
Signaling
Authentication
Call state
```

---

# 47. WebRTC Signaling

Flow:

```text
Browser A
   ↓
Create SDP Offer
   ↓
FastAPI WebSocket
   ↓
Browser B
   ↓
Create SDP Answer
   ↓
FastAPI
   ↓
Browser A
```

Then:

```text
ICE candidates
      ↓
Exchange
      ↓
Connection established
```

---

# 48. STUN / TURN

STUN:

```text
Helps browser discover network information.
```

TURN:

```text
Relays traffic when direct peer-to-peer connection fails.
```

For initial development:

```text
localhost
+
same-network testing
+
public STUN server
```

Later:

```text
Own TURN server
```

We do NOT need to build a telecom system from scratch.

---

# 49. Call Database

```text
calls
-----
id
organization_id
restaurant_id
lead_id
conversation_id

provider

from_number
to_number

status

started_at
answered_at
ended_at

duration_seconds

recording_url
created_at
```

Call events:

```text
call_events
-----------
id
call_id

event_type
payload

created_at
```

---

# 50. Twilio Webhooks

Twilio will send events back to our backend.

Example:

```text
Twilio
  ↓
POST /webhooks/twilio/voice
  ↓
FastAPI
  ↓
Verify webhook signature
  ↓
Update call
  ↓
Create event
  ↓
Queue notification
```

We should never blindly trust webhook requests.

---

# 51. Notifications

Unified notification model:

```text
notifications
-------------
id
organization_id
user_id

type
title
body

entity_type
entity_id

read_at
created_at
```

Examples:

```text
LEAD_REPLIED
QUOTE_REQUESTED
QUOTE_ACCEPTED
CALL_COMPLETED
HIGH_VALUE_LEAD
CAMPAIGN_COMPLETED
FOLLOWUP_DUE
```

---

# 52. Real-Time Notifications

Flow:

```text
Event
 ↓
Redis Queue
 ↓
Notification Worker
 ↓
PostgreSQL
 ↓
WebSocket
 ↓
Next.js
 ↓
Notification appears
```

Example:

```text
Customer replies
      ↓
Email ingestion
      ↓
Conversation updated
      ↓
Event emitted
      ↓
Notification worker
      ↓
WebSocket
      ↓
🔔 New lead reply
```

---

# 53. Event-Driven Architecture

Important events:

```text
LEAD_CREATED
LEAD_VERIFIED
LEAD_REPLIED

CAMPAIGN_STARTED
CAMPAIGN_COMPLETED

QUOTE_CREATED
QUOTE_SENT
QUOTE_ACCEPTED
QUOTE_REJECTED

ORDER_CREATED

CALL_STARTED
CALL_ANSWERED
CALL_ENDED

FOLLOWUP_DUE

AI_ACTION_PROPOSED
AI_ACTION_APPROVED
AI_ACTION_REJECTED
```

Events allow different parts of the system to react independently.

---

# 54. Queue Design

Example:

```text
EMAIL_RECEIVED
      ↓
Redis
      ↓
Conversation Worker
      ↓
AI Worker
      ↓
Event
      ↓
Notification Worker
```

Another example:

```text
CSV_UPLOAD
     ↓
Verification Queue
     ↓
Verifier Worker
     ↓
Database
     ↓
VERIFICATION_COMPLETED
```

---

# 55. Reliability

Jobs need:

```text
Retries
Timeouts
Failure states
Idempotency
Logging
Job IDs
Progress tracking
```

Example:

```text
PENDING
   ↓
RUNNING
   ↓
FAILED
   ↓
RETRY
   ↓
RUNNING
   ↓
COMPLETED
```

---

# 56. Idempotency

If the same event arrives twice:

```text
Do NOT execute the action twice.
```

Example:

```text
Twilio webhook arrives
Twilio webhook retries
```

We use event IDs / unique constraints / idempotency keys to prevent duplicate processing.

---

# 57. Audit Logging

Important actions are logged.

```text
audit_logs
----------
id
organization_id
user_id

action
entity_type
entity_id

old_value
new_value

created_at
```

Examples:

```text
USER_CREATED
LEAD_UPDATED
QUOTE_APPROVED
AI_ACTION_APPROVED
CAMPAIGN_STARTED
CALL_STARTED
```

---

# 58. API Structure

```text
/api/v1/auth
/api/v1/users
/api/v1/organizations
/api/v1/restaurants

/api/v1/leads
/api/v1/verifications

/api/v1/campaigns

/api/v1/conversations
/api/v1/messages

/api/v1/calls

/api/v1/quotes
/api/v1/orders

/api/v1/notifications

/api/v1/jobs

/api/v1/ai

/api/v1/webhooks
```

---

# 59. Authentication API

```text
POST /auth/register
POST /auth/login
POST /auth/refresh
POST /auth/logout
GET  /auth/me
```

---

# 60. Lead API

```text
POST   /leads
GET    /leads
GET    /leads/{id}
PATCH  /leads/{id}
DELETE /leads/{id}

POST /leads/import
POST /leads/{id}/verify
POST /leads/{id}/score
```

---

# 61. Campaign API

```text
POST   /campaigns
GET    /campaigns
GET    /campaigns/{id}
PATCH  /campaigns/{id}

POST /campaigns/{id}/start
POST /campaigns/{id}/pause
POST /campaigns/{id}/cancel
```

---

# 62. Conversation API

```text
GET /conversations
GET /conversations/{id}
GET /conversations/{id}/messages

POST /conversations/{id}/messages
```

---

# 63. Quote API

```text
POST /quotes
GET /quotes
GET /quotes/{id}
PATCH /quotes/{id}

POST /quotes/{id}/send
POST /quotes/{id}/approve
POST /quotes/{id}/reject
```

---

# 64. Call API

```text
POST /calls
GET  /calls
GET  /calls/{id}

POST /calls/{id}/end
GET  /calls/{id}/status
```

---

# 65. WebSocket API

Example:

```text
/ws/notifications
/ws/calls/{call_id}
/ws/webrtc/{room_id}
```

Used for:

* notifications
* live call state
* WebRTC signaling
* real-time job progress

---

# 66. Webhooks

```text
POST /webhooks/twilio/voice
POST /webhooks/twilio/status

POST /webhooks/email/inbound
```

All external webhooks should have validation/signature checks where supported.

---

# 67. Frontend Dashboard

Main pages:

```text
/login

/dashboard

/leads
/leads/{id}

/campaigns
/campaigns/{id}

/conversations
/conversations/{id}

/calls

/quotes
/quotes/{id}

/orders

/notifications

/settings
/users

/ai/activity
/jobs
```

---

# 68. Dashboard Overview

Display:

```text
Total leads
Verified leads
Hot leads
Active campaigns
Replies
Quotes
Accepted quotes
Revenue
Open conversations
Pending AI actions
```

Charts:

```text
Lead pipeline
Campaign performance
Verification results
Quote conversion
Revenue
```

---

# 69. Lead UI

Table:

```text
Company
Contact
Email
Verification
Score
Priority
Status
Last Activity
```

Filters:

```text
Verified
Invalid
Hot
Interested
Quoted
Won
Lost
```

---

# 70. Conversation UI

Similar to an inbox.

```text
Conversation list
        │
        ├── Customer A
        ├── Customer B
        └── Customer C

Selected conversation
        │
        ├── Message history
        ├── Lead information
        ├── AI analysis
        └── Suggested actions
```

---

# 71. AI Action UI

```text
Customer wants quote.

AI detected:
• 120 guests
• Event next Friday
• Catering intent: HIGH

Suggested:
Create quote

[Approve]
[Edit]
[Reject]
```

---

# 72. Campaign UI

Campaign builder:

```text
Campaign Name

Target:
[Verified leads]
[Hot leads]

Step 1
Email
Day 0

Step 2
Email
Day 3

Step 3
Email
Day 7
```

---

# 73. Quote UI

Quote editor:

```text
Customer
Event date
Guest count

Items
--------------------
Lunch package
120 × ₹X

Delivery
₹X

Tax
₹X

Total
₹X

[Save]
[Send]
```

---

# 74. Real-Time Job Progress

For verification:

```text
Verification Job

████████████████░░░░ 80%

8,000 / 10,000

Valid:     5,421
Invalid:   1,213
Risky:       812
Unknown:     554
```

This uses:

```text
Celery
+
Redis
+
WebSocket
```

---

# 75. Security

Implement:

### Password security

Argon2.

### JWT

Short-lived access tokens.

### Refresh tokens

Controlled rotation/revocation.

### RBAC

Backend enforced.

### Input validation

Pydantic.

### SQL safety

SQLAlchemy parameterization.

### CORS

Explicit origins.

### Rate limiting

Authentication, verification, webhooks, sensitive endpoints.

### Secrets

Environment variables.

### Webhooks

Signature verification.

### Audit logs

Important state changes.

---

# 76. Email Security

Do not blindly trust inbound email content.

Handle:

```text
HTML
Plain text
Attachments
Malformed headers
Large messages
Encoding
```

Sanitize HTML before displaying it in the frontend.

---

# 77. AI Security

The AI must NOT:

```text
Execute arbitrary SQL
Execute arbitrary shell commands
Access arbitrary filesystem paths
Send arbitrary messages without authorization
Modify users/permissions freely
```

Instead:

```text
LLM
 ↓
Controlled tool
 ↓
Permission check
 ↓
Validation
 ↓
Human approval if required
 ↓
Execution
```

---

# 78. Observability

Use:

## Prometheus

Metrics:

```text
verification_duration
verification_success_total
verification_failure_total

queue_depth
job_duration
job_failure_total

emails_sent
emails_failed

calls_started
calls_failed

ai_latency
ai_errors

api_latency
api_errors
```

## Grafana

Dashboard for system health.

---

# 79. Logging

Use structured logging.

Example:

```json
{
  "event": "verification_completed",
  "job_id": "...",
  "email": "...",
  "status": "VALID",
  "latency_ms": 412
}
```

Avoid logging sensitive credentials or unnecessary personal information.

---

# 80. Testing

## Unit tests

Test:

```text
Email syntax
DNS
MX
SMTP classification
Disposable domains
Catch-all detection

Lead scoring
Quote calculation

Permissions
JWT
```

---

# 81. Integration Tests

Use:

```text
pytest
httpx
test PostgreSQL
test Redis
```

Test complete API flows.

Example:

```text
Register
 ↓
Login
 ↓
Create restaurant
 ↓
Create lead
 ↓
Verify lead
 ↓
Create campaign
 ↓
Create quote
```

---

# 82. E2E Tests

Use:

## Playwright

Test:

```text
Login
Create lead
Upload CSV
View verification progress
Create campaign
Read conversation
Approve AI action
Create quote
```

---

# 83. CI/CD

GitHub Actions.

Pipeline:

```text
Push
 ↓
Lint
 ↓
Type checks
 ↓
Unit tests
 ↓
Integration tests
 ↓
Build
```

---

# 84. Code Quality

Backend:

```text
ruff
pytest
mypy
```

Frontend:

```text
ESLint
Prettier
TypeScript
```

Use:

* type hints
* clear interfaces
* service/repository separation
* dependency injection
* meaningful errors
* consistent naming

---

# 85. Repository Structure

```text
catering-revenue-agent/
│
├── apps/
│   │
│   ├── api/
│   │   ├── app/
│   │   │   │
│   │   │   ├── main.py
│   │   │   │
│   │   │   ├── api/
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── organizations.py
│   │   │   │   ├── restaurants.py
│   │   │   │   ├── leads.py
│   │   │   │   ├── verifications.py
│   │   │   │   ├── campaigns.py
│   │   │   │   ├── conversations.py
│   │   │   │   ├── calls.py
│   │   │   │   ├── quotes.py
│   │   │   │   ├── orders.py
│   │   │   │   ├── notifications.py
│   │   │   │   ├── jobs.py
│   │   │   │   └── webhooks.py
│   │   │   │
│   │   │   ├── models/
│   │   │   ├── schemas/
│   │   │   ├── repositories/
│   │   │   ├── services/
│   │   │   ├── workers/
│   │   │   ├── agents/
│   │   │   ├── integrations/
│   │   │   │   ├── email/
│   │   │   │   ├── twilio/
│   │   │   │   └── ollama/
│   │   │   │
│   │   │   ├── core/
│   │   │   └── db/
│   │   │
│   │   └── tests/
│   │
│   └── web/
│       ├── app/
│       ├── components/
│       ├── hooks/
│       ├── lib/
│       └── types/
│
├── migrations/
│
├── infrastructure/
│   ├── docker/
│   └── monitoring/
│
├── docs/
│   ├── architecture.md
│   ├── api.md
│   └── decisions/
│
├── scripts/
│
├── docker-compose.yml
├── .env.example
├── Makefile
├── README.md
└── .gitignore
```

---

# 86. Docker Compose

Initial services:

```text
frontend
api
worker
scheduler
postgres
redis
ollama
mailpit
prometheus
grafana
```

Potential later addition:

```text
coturn
```

for TURN.

---

# 87. Development Environment

Everything possible should run locally.

```text
Docker Compose
      ↓
PostgreSQL
Redis
Mailpit
Ollama
Prometheus
Grafana
```

The application can therefore be demonstrated without paying for infrastructure.

---

# 88. Free vs External Services

## Completely local/free

```text
FastAPI
PostgreSQL
Redis
Celery
Next.js
Ollama
Mailpit
WebRTC
Prometheus
Grafana
Playwright
Docker
```

---

# 89. Twilio

Use only where actual telephone-network calling is required.

Development strategy:

```text
Twilio Trial
    ↓
Small number of real calls
    ↓
Demonstrate phone integration
```

Then continue development using:

```text
WebRTC
+
mock/local call provider
```

to avoid unnecessary charges.

---

# 90. What We Explicitly Do NOT Use

## ❌ Reoon API

We build our own verifier.

## ❌ NeverBounce API

Same reason.

## ❌ Paid LLM APIs

Use Ollama.

## ❌ Paid email APIs

Use Mailpit/local SMTP for development.

## ❌ Paid lead databases

Use CSV/manual/free/public sources.

## ❌ Supabase Auth

Build authentication ourselves to demonstrate backend capability.

## ❌ Firebase

Not needed for notifications.

## ❌ Kafka

Redis + Celery is sufficient.

## ❌ Kubernetes

Massive overkill for this project.

## ❌ Microservices

One modular FastAPI backend is better.

## ❌ MongoDB

PostgreSQL is a better fit.

## ❌ GraphQL

REST is enough.

## ❌ Building telecom infrastructure

Use Twilio for actual phone-network calls.

---

# 91. Why We Don't Use Microservices

We want to demonstrate architecture without creating unnecessary complexity.

Instead:

```text
One FastAPI application
+
Clear modules
+
Services
+
Repositories
+
Workers
+
Integrations
```

Internally modular.

Externally simple.

If this ever became a real company, individual components could later be extracted.

---

# 92. Architecture Principles

### Separation of concerns

```text
API
 ↓
Service
 ↓
Repository
 ↓
Database
```

Integrations are separate.

```text
Service
 ↓
Provider Interface
 ↓
Twilio / Mailpit / Ollama / etc.
```

---

# 93. Provider Pattern

Email:

```text
EmailService
 ├── MailpitProvider
 └── SMTPProvider
```

Calling:

```text
CallService
 ├── TwilioProvider
 └── WebRTCProvider
```

AI:

```text
AIService
 └── OllamaProvider
```

This lets us replace infrastructure without rewriting business logic.

---

# 94. Core Business Flow

The final demonstration should be able to show:

```text
Restaurant created
       ↓
Lead imported
       ↓
Email verified
       ↓
Lead scored
       ↓
Campaign started
       ↓
Email sent
       ↓
Customer replies
       ↓
Reply ingested
       ↓
Conversation created
       ↓
AI analyzes reply
       ↓
AI suggests quote
       ↓
Human approves
       ↓
Quote generated
       ↓
Quote sent
       ↓
Customer accepts
       ↓
Order created
       ↓
Restaurant notified
```

This is the **main end-to-end demo**.

---

# 95. Calling Demo

Separate demo:

```text
Lead
 ↓
Call button
 ↓
Choose:

[ Phone Call ]
[ Browser Call ]
```

Phone:

```text
Browser
 ↓
FastAPI
 ↓
Twilio
 ↓
Customer phone
```

Browser:

```text
Admin browser
 ↕
WebRTC
 ↕
Customer browser
```

---

# 96. Email Verification Demo

Separate demo:

```text
CSV
 ↓
Upload
 ↓
10,000 emails
 ↓
Queue
 ↓
Workers
 ↓
DNS/MX
 ↓
SMTP
 ↓
Results
```

Dashboard:

```text
Valid
Invalid
Risky
Unknown
Catch-all
Disposable
Role-based
```

This is one of the strongest technical demonstrations in the entire project.

---

# 97. Queue Demo

Show:

```text
10,000-email verification job
```

Then:

```text
API
 ↓
Redis
 ↓
20 workers
 ↓
Progress
 ↓
Database
```

The frontend updates live.

This demonstrates:

* concurrency
* queues
* workers
* Redis
* database persistence
* WebSockets
* job state

---

# 98. System Design Concepts Demonstrated

This single project covers:

```text
REST APIs
Authentication
Authorization
RBAC
Multi-tenancy
PostgreSQL
Indexes
Transactions
Caching
Redis
Queues
Workers
Scheduling
WebSockets
Webhooks
SMTP
DNS
MX records
IMAP
Email parsing
SMTP probing
Concurrency
Async programming
WebRTC
STUN
TURN
Twilio
AI agents
Tool calling
Human approval
Event-driven architecture
Observability
Testing
Docker
CI/CD
```

---

# 99. Data Structures / Algorithms Knowledge Applied

We should also deliberately use and understand:

### Big-O

```text
O(1)
O(log n)
O(n)
O(n log n)
O(n²)
```

### Hash tables

Used conceptually for:

```text
caches
lookups
deduplication
```

### Queues

Directly used in:

```text
background jobs
event processing
```

### Trees

Understand:

```text
BST
AVL
Red-Black Tree
B-Tree
```

### B-Tree

Especially relevant because PostgreSQL indexes commonly use B-tree structures.

### Sorting/searching

Used throughout lead management and data processing.

---

# 100. Database Indexing

Important indexes:

```text
users.email
leads.organization_id
leads.email
leads.pipeline_status

messages.conversation_id
messages.message_id

notifications.user_id
notifications.read_at

jobs.status
jobs.created_at

calls.lead_id
quotes.lead_id
orders.lead_id
```

Composite indexes where query patterns justify them.

---

# 101. Transactions

Use database transactions for operations such as:

```text
Approve quote
 ↓
Create order
 ↓
Update quote
 ↓
Create audit event
```

These should not leave the database half-updated.

---

# 102. Caching

Potential caches:

```text
MX records
Lead score calculations
Frequently accessed configuration
Short-lived notification state
```

Do NOT blindly cache everything.

---

# 103. Rate Limiting

Apply rate limits to:

```text
Login
Registration
Email verification
Webhook endpoints
AI endpoints
Call initiation
```

Especially important for the email verifier so external mail servers aren't abused.

---

# 104. Error Handling

Standard API errors.

Example:

```json
{
  "error": {
    "code": "LEAD_NOT_FOUND",
    "message": "Lead does not exist."
  }
}
```

Do not leak:

```text
stack traces
database internals
credentials
private system information
```

---

# 105. Configuration

`.env.example`

```text
DATABASE_URL=
REDIS_URL=

JWT_SECRET=
JWT_REFRESH_SECRET=

OLLAMA_URL=

SMTP_HOST=
SMTP_PORT=

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=

WEB_APP_URL=
API_URL=
```

Secrets never committed.

---

# 106. Documentation

README should contain:

```text
What the project does
Architecture
Tech stack
Setup
Docker setup
Environment variables
Database migrations
Running workers
Running frontend
Running tests
API documentation
AI architecture
Email verification architecture
Calling architecture
```

---

# 107. Architecture Decision Records

Create:

```text
docs/decisions/
```

Examples:

```text
001-fastapi-over-django.md
002-postgresql-over-mongodb.md
003-celery-over-custom-workers.md
004-own-email-verifier.md
005-ollama-for-local-ai.md
006-twilio-and-webrtc.md
007-modular-monolith.md
```

This makes the project look significantly more mature.

---

# 108. Final System

At completion:

```text
                 CATERING REVENUE AGENT

                       ┌─────────┐
                       │  USER   │
                       └────┬────┘
                            │
                       Next.js
                            │
                       FastAPI API
                            │
       ┌────────────────────┼────────────────────┐
       │                    │                    │
 PostgreSQL               Redis             WebSocket
       │                    │                    │
       │                 Celery                 │
       │                    │                    │
       │          ┌─────────┼─────────┐          │
       │          │         │         │          │
       │       Email      Verify      AI       Calls
       │          │         │         │          │
       │       Mailpit    Own DNS   Ollama   Twilio/WebRTC
       │
       └─────────────────────────────────────────┐
                                                 │
                                         Business Logic
                                                 │
                                      Leads → Campaigns
                                                 ↓
                                      Conversations
                                                 ↓
                                           Quotes
                                                 ↓
                                            Orders
                                                 ↓
                                           Revenue
```

---

# 109. The Final Portfolio Story

When someone asks:

> "What did you build?"

The answer should be:

> **I built a modular, multi-tenant catering revenue operations platform with a FastAPI backend, PostgreSQL, Redis/Celery background processing, custom email verification using DNS/MX/SMTP analysis, local AI agents through Ollama, human-in-the-loop tool execution, campaign automation, conversation intelligence, quote/order workflows, real-time notifications, Twilio phone calling, WebRTC browser calling, webhook processing, RBAC, audit logging, observability, automated testing, and Dockerized infrastructure.**

And every part of that statement will actually exist in the codebase.

---

# 110. Definition of Done

The project is considered complete when we can demonstrate all of these:

## Core

* [ ] User registration
* [ ] Login/logout
* [ ] JWT authentication
* [ ] Refresh tokens
* [ ] RBAC
* [ ] Multi-tenant organizations
* [ ] Restaurant management

## Leads

* [ ] Lead CRUD
* [ ] CSV import
* [ ] Lead scoring
* [ ] Pipeline
* [ ] Activity history

## Email Verification

* [ ] Syntax validation
* [ ] DNS lookup
* [ ] MX lookup
* [ ] Disposable detection
* [ ] Role detection
* [ ] SMTP probe
* [ ] Catch-all detection
* [ ] Quick mode
* [ ] Power mode
* [ ] Retry handling
* [ ] Multiple MX
* [ ] Result persistence
* [ ] Bulk jobs
* [ ] Progress tracking
* [ ] Cancellation

## Campaigns

* [ ] Campaign creation
* [ ] Target selection
* [ ] Email templates
* [ ] Follow-up steps
* [ ] Scheduling
* [ ] Suppression checks
* [ ] Campaign analytics

## Email

* [ ] SMTP sending
* [ ] Mailpit
* [ ] Email ingestion
* [ ] IMAP/email parsing
* [ ] Conversation matching
* [ ] Message persistence

## AI

* [ ] Ollama
* [ ] Conversation classification
* [ ] Intent detection
* [ ] Structured output
* [ ] Tool calling
* [ ] AI action logs
* [ ] Human approval
* [ ] AI-generated quote suggestions

## Quotes

* [ ] Quote creation
* [ ] Quote items
* [ ] Pricing
* [ ] Approval
* [ ] Sending
* [ ] Acceptance
* [ ] Expiration

## Orders

* [ ] Order creation
* [ ] Quote → order conversion
* [ ] Order status
* [ ] Revenue tracking

## Calling

* [ ] Call abstraction
* [ ] Twilio provider
* [ ] Twilio webhooks
* [ ] Call state
* [ ] Browser WebRTC
* [ ] WebSocket signaling
* [ ] STUN
* [ ] TURN-ready architecture

## Notifications

* [ ] Notification persistence
* [ ] Read/unread
* [ ] WebSocket delivery
* [ ] Event-driven notifications

## Infrastructure

* [ ] Docker
* [ ] Docker Compose
* [ ] PostgreSQL
* [ ] Redis
* [ ] Celery
* [ ] Celery Beat
* [ ] Ollama
* [ ] Mailpit
* [ ] Prometheus
* [ ] Grafana

## Engineering

* [ ] Unit tests
* [ ] Integration tests
* [ ] Playwright E2E
* [ ] Logging
* [ ] Metrics
* [ ] Audit logs
* [ ] Rate limiting
* [ ] Webhook verification
* [ ] CI
* [ ] Documentation
* [ ] Architecture decisions

---

# 111. Final Philosophy

The project should be:

**Technically serious, architecturally clean, locally runnable, free to develop, and impressive enough to demonstrate that we understand the backend systems behind an AI-agent company.**

We are NOT trying to build:

```text
"another CRUD app"
```

We are building:

```text
A distributed-ish, event-driven, AI-assisted
revenue operations system
with real networking and communication infrastructure.
```

But we will keep it as a **modular monolith**, because that gives us the engineering depth without drowning the project in unnecessary infrastructure.

The implementation should always prioritize:

```text
Correctness
↓
Clear architecture
↓
Observability
↓
Security
↓
Testability
↓
Performance
↓
UI polish
```

---

# END STATE

The final repository should be something we can clone onto another machine, run with Docker Compose, create an account, create a restaurant, import leads, verify emails, run campaigns, receive conversations, invoke the AI agent, approve actions, generate quotes, create orders, receive notifications, and demonstrate both phone and browser calling.

That is the project we are building.
