# Phase 9 — Next.js Frontend Dashboard

> **Goal:** Build the complete Next.js frontend with all pages, components, real-time WebSocket integration, and the WebRTC call interface. The dashboard should be production-quality, responsive, and visually impressive — not a basic CRUD UI.
should be primarly dark themed, easy on the eye shades, still look good and visually pleasing and ravering, no neon stuff at all, need comfortable thing.

> **Depends on:** Phase 8 (Notifications, Events, Real-time)

---

## Step 9.1 — Initialize Next.js Project

**Commands:**
```bash
cd apps/web
npx -y create-next-app@latest ./ --typescript --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm
```

**Then install additional dependencies:**
```bash
npm install @tanstack/react-query @tanstack/react-query-devtools
npm install recharts
npm install lucide-react
npm install class-variance-authority clsx tailwind-merge
npm install date-fns
npm install zod
npm install react-hook-form @hookform/resolvers
npm install sonner           # Toast notifications
npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-tabs @radix-ui/react-select @radix-ui/react-checkbox @radix-ui/react-label @radix-ui/react-avatar @radix-ui/react-badge @radix-ui/react-separator @radix-ui/react-tooltip @radix-ui/react-popover @radix-ui/react-scroll-area @radix-ui/react-switch @radix-ui/react-slot
npm install tailwindcss-animate
npm install --save-dev prettier eslint-config-prettier
```

**Then:** Initialize shadcn/ui
```bash
npx shadcn@latest init
```

Add core components:
```bash
npx shadcn@latest add button card input label table badge dialog dropdown-menu tabs select checkbox avatar separator tooltip popover scroll-area switch sheet skeleton alert-dialog command
```

---

## Step 9.2 — Project Structure

```text
apps/web/src/
├── app/
│   ├── layout.tsx              # Root layout (sidebar, providers)
│   ├── page.tsx                # Redirect to /dashboard
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/
│   │   ├── layout.tsx          # Dashboard layout (sidebar + topbar)
│   │   ├── dashboard/page.tsx  # Overview
│   │   ├── leads/
│   │   │   ├── page.tsx        # Lead list
│   │   │   └── [id]/page.tsx   # Lead detail
│   │   ├── campaigns/
│   │   │   ├── page.tsx        # Campaign list
│   │   │   └── [id]/page.tsx   # Campaign detail
│   │   ├── conversations/
│   │   │   ├── page.tsx        # Conversation list (inbox style)
│   │   │   └── [id]/page.tsx   # Conversation thread
│   │   ├── calls/page.tsx
│   │   ├── quotes/
│   │   │   ├── page.tsx
│   │   │   └── [id]/page.tsx   # Quote editor
│   │   ├── orders/page.tsx
│   │   ├── notifications/page.tsx
│   │   ├── ai/
│   │   │   └── activity/page.tsx
│   │   ├── jobs/page.tsx
│   │   ├── settings/page.tsx
│   │   └── users/page.tsx
│
├── components/
│   ├── ui/                     # shadcn components (auto-generated)
│   ├── layout/
│   │   ├── sidebar.tsx
│   │   ├── topbar.tsx
│   │   └── mobile-nav.tsx
│   ├── dashboard/
│   │   ├── stats-cards.tsx
│   │   ├── pipeline-chart.tsx
│   │   ├── revenue-chart.tsx
│   │   └── recent-activity.tsx
│   ├── leads/
│   │   ├── lead-table.tsx
│   │   ├── lead-filters.tsx
│   │   ├── lead-detail.tsx
│   │   ├── lead-import-dialog.tsx
│   │   ├── lead-score-badge.tsx
│   │   └── verification-status.tsx
│   ├── campaigns/
│   │   ├── campaign-builder.tsx
│   │   ├── campaign-step-editor.tsx
│   │   └── campaign-analytics.tsx
│   ├── conversations/
│   │   ├── conversation-list.tsx
│   │   ├── message-thread.tsx
│   │   ├── message-composer.tsx
│   │   └── ai-analysis-panel.tsx
│   ├── ai/
│   │   ├── ai-action-card.tsx
│   │   ├── pending-actions.tsx
│   │   └── ai-activity-feed.tsx
│   ├── quotes/
│   │   ├── quote-editor.tsx
│   │   ├── quote-item-table.tsx
│   │   └── quote-preview.tsx
│   ├── calls/
│   │   ├── call-dialog.tsx
│   │   ├── webrtc-call.tsx
│   │   └── call-history.tsx
│   ├── notifications/
│   │   ├── notification-bell.tsx
│   │   ├── notification-list.tsx
│   │   └── notification-toast.tsx
│   ├── jobs/
│   │   ├── job-progress.tsx
│   │   └── job-list.tsx
│   └── shared/
│       ├── data-table.tsx       # Reusable table with sorting/filtering
│       ├── page-header.tsx
│       ├── empty-state.tsx
│       ├── loading-skeleton.tsx
│       ├── confirm-dialog.tsx
│       └── pagination.tsx
│
├── hooks/
│   ├── use-auth.ts
│   ├── use-websocket.ts
│   ├── use-notifications.ts
│   ├── use-webrtc.ts
│   └── use-debounce.ts
│
├── lib/
│   ├── api-client.ts           # Axios/fetch wrapper with auth interceptor
│   ├── auth.ts                 # Token storage, refresh logic
│   ├── websocket.ts            # WebSocket connection manager
│   ├── utils.ts                # cn(), formatDate, formatCurrency, etc.
│   └── constants.ts            # Roles, statuses, etc.
│
├── types/
│   ├── api.ts                  # API response types
│   ├── lead.ts
│   ├── campaign.ts
│   ├── conversation.ts
│   ├── quote.ts
│   ├── order.ts
│   ├── call.ts
│   ├── notification.ts
│   ├── ai.ts
│   └── user.ts
│
└── providers/
    ├── query-provider.tsx      # TanStack Query provider
    ├── auth-provider.tsx       # Auth context
    ├── websocket-provider.tsx  # WebSocket context
    └── notification-provider.tsx
```

---

## Step 9.3 — API Client

**File:** `apps/web/src/lib/api-client.ts`

```typescript
/**
 * Centralized API client:
 * - Base URL from env (NEXT_PUBLIC_API_URL)
 * - Automatic Bearer token injection
 * - Automatic token refresh on 401
 * - Request/response interceptors
 * - Structured error handling
 */

class APIClient {
    private baseURL: string;
    
    async request<T>(method: string, path: string, data?: any, config?: any): Promise<T>;
    
    // Convenience methods
    async get<T>(path: string, params?: any): Promise<T>;
    async post<T>(path: string, data?: any): Promise<T>;
    async patch<T>(path: string, data?: any): Promise<T>;
    async delete(path: string): Promise<void>;
    async upload<T>(path: string, formData: FormData): Promise<T>;
}
```

---

## Step 9.4 — Authentication

### Login Page: `apps/web/src/app/(auth)/login/page.tsx`

- Email + password form
- Loading state
- Error display
- Redirect to /dashboard on success
- Link to register

### Register Page: `apps/web/src/app/(auth)/register/page.tsx`

- Name, email, password, organization name
- Loading state
- Redirect to /dashboard on success

### Auth Provider: `apps/web/src/providers/auth-provider.tsx`

```typescript
/**
 * - Stores tokens in localStorage (access + refresh)
 * - Provides: user, login(), register(), logout(), isAuthenticated
 * - Auto-refreshes expired access token using refresh token
 * - Redirects to /login if fully logged out
 */
```

### Auth Hook: `apps/web/src/hooks/use-auth.ts`

```typescript
function useAuth() {
    // Returns { user, login, register, logout, isAuthenticated, isLoading }
}
```

---

## Step 9.5 — Dashboard Layout

### Sidebar: `components/layout/sidebar.tsx`

```text
Navigation items:
- Dashboard (icon: LayoutDashboard)
- Leads (icon: Users)
- Campaigns (icon: Megaphone)
- Conversations (icon: MessageSquare)
- Calls (icon: Phone)
- Quotes (icon: FileText)
- Orders (icon: ShoppingBag)
- AI Activity (icon: Brain)
- Jobs (icon: Activity)
- Notifications (icon: Bell) with unread badge
- Settings (icon: Settings)
- Users (icon: UserCog)

Collapsible on mobile
Organization name + user info at bottom
Logout button
```

### Topbar: `components/layout/topbar.tsx`

```text
- Page title (dynamic)
- Search bar
- Notification bell with unread count (real-time)
- User avatar dropdown
```

---

## Step 9.6 — Dashboard Overview Page

**Page:** `apps/web/src/app/(dashboard)/dashboard/page.tsx`

**Components:**

### Stats Cards (4-6 cards in a grid)
```text
- Total Leads (with trend indicator)
- Hot Leads
- Active Campaigns
- Open Quotes
- Accepted Quotes / Revenue
- Pending AI Actions
```

### Charts (using Recharts)
```text
- Lead Pipeline (bar chart — leads per status)
- Campaign Performance (line chart — emails sent, replies over time)
- Revenue (area chart — monthly revenue)
- Verification Results (donut/pie chart — VALID, INVALID, RISKY, UNKNOWN)
- Quote Conversion (funnel — sent → viewed → accepted)
```

### Recent Activity Feed
```text
- Scrollable list of recent events (lead created, email sent, quote accepted, etc.)
- Clickable to navigate to the relevant entity
```

---

## Step 9.7 — Leads Page

### Lead List: `apps/web/src/app/(dashboard)/leads/page.tsx`

```text
Features:
- Data table with columns: Company, Contact, Email, Verification, Score, Priority, Status, Last Activity
- Filters: status, priority, verified, search
- Sorting: score, created_at, updated_at
- Pagination
- Bulk actions: Verify, Score, Delete
- "Import CSV" button → opens dialog
- "Add Lead" button → opens form
```

### Lead Import Dialog: `components/leads/lead-import-dialog.tsx`

```text
- File upload (CSV only)
- Restaurant selector
- Preview first 5 rows
- "Import" button
- Shows job progress after import starts
```

### Lead Detail: `apps/web/src/app/(dashboard)/leads/[id]/page.tsx`

```text
Layout: Two columns
Left:
- Lead info card (company, contact, email, phone, address, industry)
- Score & Priority badge
- Pipeline status selector
- Verification details (expandable)

Right:
- Activity timeline (chronological: emails, calls, status changes, notes)
- Conversations list
- Quotes list
- Actions: Verify, Score, Call, Email, Create Quote
```

### Score Badge: `components/leads/lead-score-badge.tsx`

```text
Visual: Colored badge
- HOT (80-100): Red/orange pulsing
- HIGH (60-79): Orange
- MEDIUM (40-59): Yellow
- LOW (0-39): Gray
```

---

## Step 9.8 — Campaigns Page

### Campaign List: `apps/web/src/app/(dashboard)/campaigns/page.tsx`

```text
- Cards or table: Name, Status, Leads count, Progress, Started, Actions
- "New Campaign" button
```

### Campaign Builder: `apps/web/src/app/(dashboard)/campaigns/[id]/page.tsx`

```text
Tabs:
1. Setup: Name, description, target filters (multi-select for status, priority)
2. Steps: Draggable/addable steps
   - Each step: step number, type (EMAIL), delay days, subject template, body template
   - Template variable picker: {{contact_name}}, {{company_name}}, etc.
3. Leads: List of targeted leads with their campaign status
4. Analytics: Bar chart of lead statuses, email performance

Actions: Start, Pause, Cancel (based on campaign status)
```

---

## Step 9.9 — Conversations Page (Inbox)

### Conversation List: `apps/web/src/app/(dashboard)/conversations/page.tsx`

```text
Layout: Two-panel inbox
Left panel:
- List of conversations (scrollable)
- Each item: Lead name, last message preview, timestamp, channel badge, unread indicator
- Filter by: channel, status
- Search

Right panel (selected conversation):
- Message thread (WhatsApp/email style)
- Message composer at bottom
- Lead info sidebar (collapsible)
- AI analysis panel (if analysis exists)
```

### AI Analysis Panel: `components/conversations/ai-analysis-panel.tsx`

```text
Displays:
- Intent badge (NEEDS_QUOTE, INTERESTED, etc.)
- Sentiment (color-coded)
- Urgency level
- Extracted data (guest count, event date, event type)
- Key points list
- Suggested actions with Approve/Edit/Reject buttons

This is the HUMAN-IN-THE-LOOP UI.
```

---

## Step 9.10 — AI Activity Page

**Page:** `apps/web/src/app/(dashboard)/ai/activity/page.tsx`

```text
- Timeline/feed of AI runs
- Each run shows: agent, model, conversation link, latency, tokens
- Expandable: shows input/output
- Actions list: tool, status (badge), description
- Filter: by status (PROPOSED, APPROVED, REJECTED, EXECUTED, FAILED)
```

### Pending Actions Widget

```text
- Prominent display of all PROPOSED actions
- Approve/Edit/Reject buttons
- Count in sidebar badge
```

---

## Step 9.11 — Quotes Page

### Quote List: `apps/web/src/app/(dashboard)/quotes/page.tsx`

```text
Table: Quote#, Customer, Event Date, Guests, Total, Status, Actions
Filters: status
```

### Quote Editor: `apps/web/src/app/(dashboard)/quotes/[id]/page.tsx`

```text
- Quote header: number, status badge, lead info
- Event info: date, guest count, type
- Items table (editable):
  - Name, Description, Category, Qty, Unit Price, Total
  - Add/Remove rows
  - Auto-calculated totals
- Pricing summary: Subtotal, Tax, Delivery Fee, Discount, TOTAL
- Notes & Terms (editable text areas)
- Action buttons: Save, Submit for Approval, Send to Customer
- Status flow visualization (stepper: DRAFT → SENT → ACCEPTED)
```

---

## Step 9.12 — Calls Page

**Page:** `apps/web/src/app/(dashboard)/calls/page.tsx`

```text
- Call history table: Lead, Provider, Direction, Status, Duration, Date
- "New Call" button
```

### Call Dialog: `components/calls/call-dialog.tsx`

```text
When initiating a call:
1. Select provider: [📱 Phone Call] [🖥️ Browser Call]
2. Phone call: enter/confirm phone number → Twilio
3. Browser call: generates room link, shows WebRTC interface

WebRTC UI:
- Full-screen overlay or dialog
- Audio visualization (volume indicator)
- Mute/unmute button
- End call button
- Call duration timer
- Lead info display
```

### WebRTC Hook: `hooks/use-webrtc.ts`

```typescript
function useWebRTC(roomId: string) {
    // - Connect WebSocket to /ws/webrtc/{roomId}
    // - getUserMedia() for microphone
    // - Create RTCPeerConnection with STUN servers
    // - Handle offer/answer/ICE candidate exchange
    // - Track connection state
    // - Returns: { startCall, endCall, isMuted, toggleMute, callState, duration }
}
```

---

## Step 9.13 — WebSocket Integration

### WebSocket Hook: `hooks/use-websocket.ts`

```typescript
function useWebSocket() {
    // - Connect to /ws/notifications on mount
    // - Auto-reconnect with exponential backoff
    // - Handle message types: notification, job_progress, unread_count
    // - Returns: { isConnected, lastMessage }
}
```

### Notification Provider: `providers/notification-provider.tsx`

```typescript
/**
 * - Listens for WebSocket notification messages
 * - Shows toast (sonner) for new notifications
 * - Updates unread count in sidebar badge
 * - Provides: notifications, unreadCount, markRead, markAllRead
 */
```

---

## Step 9.14 — Jobs Page

**Page:** `apps/web/src/app/(dashboard)/jobs/page.tsx`

```text
- Table: Job Type, Status, Progress, Created, Completed
- Progress bar for running jobs (real-time via WebSocket)
- Expandable: results summary
- Cancel button for running jobs
```

### Job Progress Component: `components/jobs/job-progress.tsx`

```text
For verification jobs:
████████████████░░░░ 80%
8,000 / 10,000

Valid:     5,421
Invalid:   1,213
Risky:       812
Unknown:     554

Updates in real-time via WebSocket.
```

---

## Step 9.15 — Orders Page

**Page:** `apps/web/src/app/(dashboard)/orders/page.tsx`

```text
- Table: Order#, Customer, Event Date, Guests, Total, Status, Date
- Revenue summary card at top
- Status update dropdown
```

---

## Step 9.16 — Settings & Users Pages

### Settings: `apps/web/src/app/(dashboard)/settings/page.tsx`

```text
- Organization info (name, slug)
- Restaurant management (list, add, edit, delete)
- SMTP settings display
```

### Users: `apps/web/src/app/(dashboard)/users/page.tsx`

```text
- User list with roles
- Invite user form
- Edit role dropdown (OWNER/ADMIN only)
- Deactivate user
```

---

## Step 9.17 — Notifications Page

**Page:** `apps/web/src/app/(dashboard)/notifications/page.tsx`

```text
- Full notification list (paginated)
- Filter: unread only
- Mark all as read button
- Click notification → navigate to entity
```

---

## Step 9.18 — SEO & Meta

Every page should have:
- Proper `<title>` tag (via Next.js metadata)
- Single `<h1>` per page
- Semantic HTML (`<main>`, `<nav>`, `<section>`, `<article>`)
- Unique IDs on interactive elements

---

## Phase 9 Completion Checklist

- [ ] Next.js project initialized with TypeScript, Tailwind, shadcn
- [ ] All dependencies installed
- [ ] Project structure created
- [ ] API client with auth interceptor + auto refresh
- [ ] Auth provider + hook
- [ ] Login page functional
- [ ] Register page functional
- [ ] Protected routes redirect to login
- [ ] Dashboard layout: sidebar + topbar
- [ ] Sidebar: all navigation links, active state, collapse
- [ ] Topbar: search, notification bell, user menu
- [ ] Dashboard overview: stats cards, charts (Recharts)
- [ ] Lead list: table, filters, sorting, pagination
- [ ] Lead import: CSV upload, preview, job tracking
- [ ] Lead detail: info, score, verification, activity timeline
- [ ] Campaign list + campaign builder
- [ ] Campaign step editor with template variables
- [ ] Conversation inbox: two-panel layout
- [ ] Message thread: styled like email/chat
- [ ] Message composer: send manual replies
- [ ] AI analysis panel: intent, sentiment, actions (Approve/Edit/Reject)
- [ ] Quote list + quote editor
- [ ] Quote items table: add/remove/edit, auto-calculate totals
- [ ] Call dialog: phone vs browser selector
- [ ] WebRTC call interface: audio, mute, timer
- [ ] WebRTC hook: signaling, peer connection, ICE
- [ ] Notifications: bell badge, toast popups, full page
- [ ] WebSocket: auto-connect, reconnect, real-time notifications
- [ ] Job progress: real-time progress bar via WebSocket
- [ ] Orders page: list + status updates
- [ ] Users page: list, invite, role management
- [ ] Settings page: org info, restaurant management
- [ ] AI activity page: runs timeline, pending actions
- [ ] Responsive design: works on tablet/mobile
- [ ] Loading skeletons on data fetch
- [ ] Empty states for empty lists
- [ ] Error states for failed requests
- [ ] `git commit -m "Phase 9: Next.js frontend dashboard"`

---

## Transition to Phase 10

Once all boxes are checked, proceed to [10-testing-observability-cicd.md](./10-testing-observability-cicd.md).

Phase 10 adds comprehensive testing (unit, integration, E2E), Prometheus metrics, Grafana dashboards, CI/CD with GitHub Actions, and documentation (README, ADRs, API docs).
