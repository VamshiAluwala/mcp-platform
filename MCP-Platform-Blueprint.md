# MCP Cloud Platform — End-to-End Solution Blueprint

> **Vision:** A hosted platform where any developer or enterprise can upload their MCP server code (via GitHub), get a secure OAuth-protected URL, and plug it directly into Claude Code — with full user identity tracking, session management, and audit logging. Built vertically for Finance, HR, Legal, Procurement, and more.

---

## Table of Contents

1. [What Problem This Solves](#1-what-problem-this-solves)
2. [Who This Is For](#2-who-this-is-for)
3. [The Core Idea — In Plain English](#3-the-core-idea--in-plain-english)
4. [How It Works — Full User Journey](#4-how-it-works--full-user-journey)
5. [Platform Architecture — High Level](#5-platform-architecture--high-level)
6. [Tech Stack — Every Layer Explained](#6-tech-stack--every-layer-explained)
7. [Identity & Authentication — The Core Innovation](#7-identity--authentication--the-core-innovation)
8. [GitHub Integration Flow](#8-github-integration-flow)
9. [MCP Hosting Engine](#9-mcp-hosting-engine)
10. [Session Management](#10-session-management)
11. [Audit & Observability](#11-audit--observability)
12. [Vertical Products — AI Solutions Per Sector](#12-vertical-products--ai-solutions-per-sector)
13. [Dashboard & UI](#13-dashboard--ui)
14. [Database Design](#14-database-design)
15. [Security Model](#15-security-model)
16. [Local Development Setup — Zero Cost](#16-local-development-setup--zero-cost)
17. [AWS Migration Plan — When Ready](#17-aws-migration-plan--when-ready)
18. [Build Phases — Week by Week](#18-build-phases--week-by-week)
19. [Competitive Landscape](#19-competitive-landscape)
20. [Business Model & Pricing](#20-business-model--pricing)
21. [Open Questions & Decisions Needed](#21-open-questions--decisions-needed)

---

## 1. What Problem This Solves

### The Developer Pain
- Developers build MCP servers but have **no easy way to host them** in production
- Every MCP deployment requires **custom authentication** built from scratch
- There is **no standard way to track who called which tool** — identity is lost the moment an AI agent makes the call
- Teams deploying multiple MCP servers have **no central dashboard** to see what is running, who is using it, and what actions were taken

### The Enterprise Pain
- Enterprises want AI agents but are blocked by **security and compliance requirements**
- They need to know: *which user triggered this action, at what time, with what data*
- Existing MCP hosting tools are built for **developers only** — not for CFOs, HR Directors, or Legal teams
- Mid-market companies ($5M–$200M revenue) cannot afford enterprise tools like Kong ($50k+) or Azure APIM

### The Identity Gap (Your Specific Problem)
- JWT tokens work at the **connection level** — user logs in, session opens
- But once the session is open, **every tool call looks the same** — no identity attached per call
- This means: if 10 users share one MCP server, you cannot tell who did what
- **Your platform solves this** by validating identity on every single tool call, not just at login

---

## 2. Who This Is For

### Primary Users
| User Type | Pain Point | What They Get |
|---|---|---|
| **Developers / Consultants** | Build MCP servers but struggle to host + secure them | One-click deploy from GitHub → hosted URL |
| **IT Teams** | Need to manage multiple AI tools with audit trails | Central dashboard + per-call logging |
| **Enterprise Security** | Cannot allow AI agents without identity tracking | Per-user, per-call JWT enforcement |

### Target Verticals (Paying Customers)
| Vertical | Example Buyer | Problem You Solve |
|---|---|---|
| Finance | CFO / Finance Director | Invoice processing, anomaly detection, month-end close |
| Legal | General Counsel / Legal Ops | Contract analysis, renewal tracking, clause extraction |
| HR | HR Director / People Ops | Onboarding automation, policy Q&A, performance reviews |
| Procurement | CPO / Procurement Manager | Supplier risk, RFP generation, spend classification |
| Engineering / IT | CTO / VP Engineering | Code review, incident analysis, sprint intelligence |

---

## 3. The Core Idea — In Plain English

Think of your platform as **"Vercel for MCP Servers"** — but with identity built in.

Just like Vercel lets you push code to GitHub and get a live URL for a web app, your platform lets you push an MCP server to GitHub and get a live, OAuth-protected URL that Claude Code can talk to.

The difference from every competitor: **you track identity at the tool-call level, not just the session level.**

```
Existing platforms:   User logs in → session opens → all tools accessible → no per-call tracking
Your platform:        User logs in → session opens → EVERY tool call validates identity → full audit trail
```

---

## 4. How It Works — Full User Journey

### Journey A — The Developer (MCP Creator)

```
Step 1: Sign up for MCP Cloud Platform
         → Create account → tenant created automatically

Step 2: Connect GitHub
         → Enter GitHub Personal Access Token
         → Platform fetches all your repositories

Step 3: Select Repository
         → Dropdown shows all Python repos from your GitHub
         → Select the repo containing your MCP server code

Step 4: Pick Entry File
         → Platform scans repo for all .py files
         → Shows suggested entry points (main.py, server.py, app.py)
         → You select which file starts your MCP

Step 5: Deploy
         → Platform clones the repo
         → Installs requirements.txt automatically
         → Starts your MCP server
         → Generates a unique hosted URL

Step 6: Get Your URL
         → MCP URL:   https://mcp.yourplatform.com/{tenant}/{server-name}
         → OAuth URL: https://auth.yourplatform.com/realms/{tenant}/...
         → Claude Code config JSON auto-generated — paste and go

Step 7: Share with Users
         → Users add the MCP URL to Claude Code
         → They are prompted to login via YOUR OAuth
         → Every call they make is tracked with their identity
```

### Journey B — The End User (Business User)

```
Step 1: Open Claude Code
Step 2: Add MCP server URL (given to them by the developer/admin)
Step 3: Prompted to log in via the platform's OAuth page
Step 4: Enter credentials → authenticated → session started
Step 5: Use Claude Code normally
         → Claude calls MCP tools transparently
         → Every tool call: identity verified → action logged → result returned
Step 6: Admin can see: who used what, when, what data was accessed
```

---

## 5. Platform Architecture — High Level

```
┌──────────────────────────────────────────────────────────────────┐
│                        DEVELOPER / TENANT                         │
│          Connects GitHub → Selects Repo → Picks main.py          │
└──────────────────────────────┬───────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                    MCP CLOUD PLATFORM                             │
│                                                                   │
│  ┌─────────────────┐    ┌──────────────────┐                     │
│  │  GitHub Engine  │    │   MCP Host Engine │                     │
│  │  Clone → Install│───▶│   Run → URL gen  │                     │
│  │  requirements   │    │   Docker / ECS   │                     │
│  └─────────────────┘    └──────────────────┘                     │
│                                   │                               │
│  ┌─────────────────┐    ┌─────────▼────────┐                     │
│  │  Identity Layer  │    │  Session Manager │                     │
│  │  Keycloak/Cognito│◀───│  Redis-backed    │                     │
│  │  Per-call JWT   │    │  Multi-session   │                     │
│  └────────┬────────┘    └──────────────────┘                     │
│           │                                                        │
│  ┌────────▼────────┐    ┌──────────────────┐                     │
│  │  Audit Engine   │    │   Dashboard UI   │                     │
│  │  PostgreSQL     │    │   Next.js        │                     │
│  │  Immutable logs │    │   Logs, Sessions │                     │
│  └─────────────────┘    └──────────────────┘                     │
└──────────────────────────────┬───────────────────────────────────┘
                               ↓
┌──────────────────────────────────────────────────────────────────┐
│                     END USER (Claude Code)                         │
│         Adds MCP URL → Logs in via OAuth → Uses tools             │
│         Every call: Identity verified → Logged → Executed         │
└──────────────────────────────────────────────────────────────────┘
```

---

## 6. Tech Stack — Every Layer Explained

### Backend — Python + FastAPI
- **Why Python:** AI-first ecosystem — LangChain, MCP SDK, ML libraries all Python-native
- **Why FastAPI:** Async support, auto-generates API docs, fastest Python framework
- **Key libraries:** `mcp`, `python-jose` (JWT), `sqlalchemy`, `asyncpg`, `redis`, `httpx`, `boto3`

### Frontend — Next.js + TypeScript
- **Why Next.js:** Server-side rendering, fast dashboards, built-in API routes
- **Why TypeScript:** Type safety, scales well as the team grows
- **UI components:** Tailwind CSS, shadcn/ui for enterprise-grade components
- **Charts:** Recharts for usage analytics and audit log visualizations

### Identity & Auth — Keycloak (local) → AWS Cognito (production)
- **Keycloak locally:** Free, open-source, full OAuth 2.1 + OIDC support, Docker-ready
- **AWS Cognito later:** Swap env vars only — zero code change needed
- **Token type:** Short-lived JWT tokens (15 min expiry) with per-user claims
- **Custom claims:** `tenant_id`, `user_id`, `roles` injected into every token

### Database — PostgreSQL + pgvector + Redis
- **PostgreSQL:** Primary database — all tenants, servers, sessions, audit logs
- **pgvector:** Vector search extension — for RAG pipelines in vertical MCPs
- **Redis:** Session cache, Celery task queue, rate limiting per user

### File Storage — MinIO (local) → AWS S3 (production)
- **MinIO locally:** Exact same API as AWS S3, runs in Docker, zero cost
- **AWS S3 later:** Change one env var — same boto3 code works
- **Use case:** Store uploaded MCP code files, processed documents, audit log exports

### Infrastructure — Docker → AWS ECS Fargate
- **Docker Compose locally:** One command starts everything — zero setup friction
- **AWS ECS Fargate:** Containerized deployment — no server management, auto-scales
- **Terraform:** Infrastructure as code — reproducible environments, easy rollback

### CI/CD — GitHub Actions
- Push to `main` → automated tests → build Docker image → deploy to ECS
- Environment-specific configs for local / staging / production

---

## 7. Identity & Authentication — The Core Innovation

### The Problem With Current MCP Auth
Most MCP platforms validate identity **once** — at connection time. After that, the session token is reused for every tool call. This means:
- Tool call 1: "Who is this?" → validated
- Tool call 47: "Who is this?" → **assumed same person, never re-checked**
- Result: No per-action audit trail, no fine-grained access control

### Your Solution — Per-Call Identity Enforcement
Every single MCP tool call goes through this flow:

```
Claude Code sends tool call request
         ↓
Your middleware intercepts BEFORE forwarding to MCP
         ↓
Extract JWT from Authorization header
         ↓
Validate JWT signature with Keycloak public key
         ↓
Check: Is token expired? → If yes: reject, force re-login
         ↓
Extract: user_id, email, tenant_id, roles from token
         ↓
Check: Is this user allowed to call THIS specific tool?
         ↓
Inject identity into request context
         ↓
Forward to MCP server (MCP server receives enriched context)
         ↓
Write audit log: user → tool → input → output → duration
         ↓
Return response to Claude Code
```

### Token Design
Each JWT token carries:
```
{
  "sub": "user-uuid",              // Keycloak user ID
  "email": "user@company.com",
  "tenant_id": "acme-corp",        // Custom claim — which org
  "roles": ["mcp-user", "admin"],  // Access control
  "iat": 1700000000,               // Issued at
  "exp": 1700000900,               // Expires in 15 minutes
  "mcp_servers": ["invoice-mcp"]   // Which MCPs this user can access
}
```

### Multi-Tenant Isolation
- Every tenant gets their own **Keycloak realm** (like a separate universe)
- Tokens from Tenant A **cannot** be used to access Tenant B's MCP servers
- Database rows use **row-level security** — queries automatically filtered by `tenant_id`
- Redis session keys namespaced by tenant: `mcp:session:{tenant_id}:{session_id}`

---

## 8. GitHub Integration Flow

### Step-by-Step Technical Flow

```
1. User provides GitHub Personal Access Token (PAT)
         ↓
2. Platform calls GitHub API: GET /user
   → Verifies token is valid
   → Retrieves: username, avatar, repo count
         ↓
3. User selects a repository from dropdown
   Platform calls: GET /user/repos?sort=updated&per_page=100
   → Returns all repos (filtered to Python repos)
         ↓
4. User selects entry file
   Platform calls: GET /repos/{owner}/{repo}/git/trees/HEAD?recursive=1
   → Returns all files in repo
   → Platform filters .py files
   → Suggests files named main.py / server.py / app.py
         ↓
5. User clicks Deploy
   Platform performs:
   a. git clone https://{token}@github.com/{owner}/{repo}.git
   b. Check for requirements.txt → pip install -r requirements.txt
   c. Validate entry file exists in cloned directory
   d. Start process: python {entry_file}
   e. Record PID → attach stdout/stderr pipe for live logs
   f. Generate unique URL: /mcp/{tenant_slug}/{server_name}
   g. Save to database: MCPServer record created
         ↓
6. Platform returns:
   → MCP endpoint URL
   → OAuth login URL
   → Claude Code JSON config (ready to paste)
   → Live log stream URL
```

### GitHub Token Security
- Tokens are stored encrypted in the database (AES-256)
- Tokens are never logged or exposed in API responses after the first call
- Token is used only during clone operation — not stored in the running container
- Support for GitHub Apps (OAuth App flow) as a future upgrade for better security

---

## 9. MCP Hosting Engine

### What It Does
Takes any Python MCP server code and makes it accessible as a remote HTTPS endpoint, ready for Claude Code to connect to.

### Local Mode (Current)
- Clones repo into `/tmp/mcp-servers/{server_id}/`
- Installs dependencies via pip
- Runs `python {entry_file}` as a subprocess
- Captures stdout/stderr for live log streaming
- Maps the running process to a FastAPI route: `GET /mcp/{tenant}/{name}`

### Production Mode (AWS)
- Each MCP server runs in its own Docker container
- Container is deployed to AWS ECS Fargate (serverless containers)
- Each container gets its own subdomain via AWS Route53
- Auto-scaling: container scales to zero when no users connected, scales up on demand
- Health checks every 30 seconds — auto-restart on failure

### URL Structure
```
Local:       http://localhost:8000/mcp/{tenant_slug}/{server_name}
Production:  https://{server_name}.{tenant_slug}.mcp.yourplatform.com
```

### MCP Transport Support
- **STDIO transport:** Standard input/output — most common MCP type
- **SSE transport:** Server-Sent Events — for streaming responses
- **HTTP transport:** Direct HTTP — for stateless tool calls

---

## 10. Session Management

### Why Sessions Matter
A session is one user's connection to one MCP server. Managing sessions properly enables:
- Knowing exactly who is connected right now
- Detecting abandoned sessions and cleaning them up
- Preventing one user's context from leaking into another's
- Counting usage per user per server for billing

### Session Lifecycle
```
User connects Claude Code to MCP URL
         ↓
OAuth login flow → JWT issued
         ↓
Session created in Redis:
  {
    session_id: uuid,
    user_id: string,
    user_email: string,
    tenant_id: string,
    mcp_server_id: string,
    started_at: timestamp,
    last_activity: timestamp,
    call_count: number,
    status: "active"
  }
         ↓
Every tool call → session.last_activity updated
         ↓
Session expires after 8 hours of inactivity (Redis TTL)
         ↓
User can also manually close session
```

### Multi-Session Support
- One user can have sessions open to **multiple MCP servers simultaneously**
- Example: Alice has Invoice MCP + Contract MCP both open in Claude Code
- Each session is stored separately in Redis with a unique session ID
- Alice's Invoice session cannot see or affect her Contract session
- Admin dashboard shows all active sessions per user, per tenant

---

## 11. Audit & Observability

### What Is Logged
Every single MCP tool call creates an immutable audit record:

| Field | Description | Example |
|---|---|---|
| `session_id` | Which session made this call | `sess-abc123` |
| `user_id` | Keycloak user UUID | `usr-xyz789` |
| `user_email` | Human-readable identity | `alice@acme.com` |
| `tenant_id` | Which organisation | `acme-corp` |
| `mcp_server_id` | Which MCP was called | `invoice-processor` |
| `tool_name` | Which tool inside the MCP | `extract_invoice_data` |
| `tool_input` | What parameters were sent | `{invoice_text: "..."}` |
| `tool_output` | What was returned | `{amount: 1500, vendor: "..."}` |
| `status` | Result | `success` / `error` / `denied` |
| `duration_ms` | How long it took | `342ms` |
| `called_at` | Exact timestamp (UTC) | `2026-03-10T14:32:01Z` |

### Compliance Use Cases
- **SOC 2:** Full audit trail of every data access event — who, what, when
- **GDPR:** Can prove exactly what data was accessed and by whom
- **HIPAA (healthcare):** Patient data access logged per user per action
- **Finance:** Every financial tool call traceable to a specific employee

### Dashboard Views
- **Real-time feed:** Tool calls appearing as they happen
- **By user:** Everything Alice did across all MCP servers
- **By server:** All activity on the Invoice MCP this week
- **By tenant:** Organisation-wide activity summary
- **Anomaly alerts:** User calling a tool 500+ times in one hour → alert

---

## 12. Vertical Products — AI Solutions Per Sector

These are the ready-to-deploy MCP servers you will build and offer as products on your platform. Each one targets a specific business pain point.

### 12.1 Finance — Invoice Intelligence MCP
**Problem:** Accounts payable teams manually match invoices to POs across ERP systems. Takes 7–14 days. High error rate.

**Tools exposed:**
- `extract_invoice_data` — Parse invoice PDF → structured fields (vendor, amount, line items, due date)
- `match_to_purchase_order` — Find matching PO in ERP → flag discrepancies
- `flag_duplicate_invoice` — Detect if same invoice submitted twice
- `route_for_approval` — Send to correct approver based on amount thresholds
- `post_to_erp` — Auto-post approved invoices to accounting system

**Outcome:** Invoice processing from 10 days → same day. 90% reduction in manual work.

---

### 12.2 Legal — Contract Lifecycle MCP
**Problem:** Contracts managed in email folders. Renewals missed. Risky clauses unread. No version control.

**Tools exposed:**
- `extract_contract_clauses` — Pull key clauses, dates, parties, obligations
- `flag_risky_clauses` — Identify non-standard, risky, or missing clauses
- `track_renewal_dates` — Alert 90/60/30 days before expiry
- `compare_to_template` — Show how this contract deviates from standard template
- `generate_redline` — Suggest edits to bring contract to standard

**Outcome:** Never miss a renewal. Legal review time cut by 70%.

---

### 12.3 HR — Onboarding Orchestrator MCP
**Problem:** New hire onboarding involves 40+ manual tasks across IT, HR, Finance, Legal — mostly done via email chains.

**Tools exposed:**
- `create_onboarding_checklist` — Generate role-specific onboarding plan
- `provision_tools` — Trigger IT tool access requests automatically
- `send_welcome_sequence` — Automated welcome emails and document requests
- `track_completion` — Show manager what is done vs pending
- `collect_documents` — Request and track ID, tax forms, contracts

**Outcome:** Onboarding from 2 weeks → 1 day. Zero tasks fall through cracks.

---

### 12.4 Procurement — Supplier Intelligence MCP
**Problem:** Supplier health checked once a year. RFPs take 3–5 days to write. Spend data uncategorised.

**Tools exposed:**
- `monitor_supplier_risk` — Continuous news, financial, ESG monitoring per supplier
- `generate_rfp` — Create full RFP document from 5-minute intake form
- `classify_spend` — Normalise and categorise all spend data from any ERP
- `identify_consolidation` — Find duplicate vendors → recommend consolidation
- `score_suppliers` — Rank suppliers by quality, risk, price, delivery performance

**Outcome:** Supply chain disruptions caught 30 days earlier. RFP time from 5 days → 2 hours.

---

### 12.5 Engineering — SDLC Intelligence MCP
**Problem:** Senior engineers waste 40% of time on code reviews. Tech debt invisible. Post-mortems skipped.

**Tools exposed:**
- `review_pull_request` — AI code review with quality score and suggestions
- `map_tech_debt` — Scan codebase → categorise and prioritise debt
- `generate_sprint_report` — Pull Jira data → write executive-ready summary
- `write_post_mortem` — Pull incident logs → generate full post-mortem with root cause
- `predict_delivery_risk` — Flag sprints likely to miss deadlines based on velocity trends

**Outcome:** Senior engineer review time cut in half. Post-mortems done in 10 minutes not 4 hours.

---

## 13. Dashboard & UI

### Pages in the Platform Dashboard

#### Overview / Dashboard
- Stats row: Total servers deployed, Active sessions right now, Total tool calls logged, Unique users tracked
- Recent deployed servers with status badges
- Recent audit events feed (live updating)
- Quick action button: Deploy New MCP

#### GitHub Import (Deploy)
- 4-step guided wizard:
  - Step 1: Connect GitHub (token → validated → stored)
  - Step 2: Select Repository (dropdown from all your GitHub repos)
  - Step 3: Pick Entry File (all .py files shown, auto-suggests main.py)
  - Step 4: Configure & Deploy (name, description, click deploy)
- Live terminal showing deployment logs in real time
- Result panel: MCP URL + OAuth URL + Claude Code config JSON (copy buttons)

#### MCP Servers
- Card grid of all deployed servers
- Each card shows: name, GitHub repo, entry file, status (LIVE/STOPPED), endpoint URL
- Actions per card: Copy URL, View Logs, Stop server
- One-click redeploy on code push (future feature)

#### Sessions
- Table of all active user sessions
- Columns: Session ID, User email, MCP Server, Started, Call count, Status
- Filter by user or by MCP server

#### Audit Logs
- Full table: Time, User, Tenant, Tool Called, MCP Server, Duration, Status
- Filter by user, by server, by date range
- Export to CSV for compliance reporting

#### Settings / OAuth Config
- Keycloak connection details
- Quick links: Keycloak admin, Swagger API docs, MinIO dashboard
- AWS migration checklist (shows current local vs future AWS mapping)

---

## 14. Database Design

### Tables

#### `tenants`
Represents each company/organisation using the platform.
- `id`, `name`, `slug`, `is_active`, `created_at`

#### `users`
Platform users (synced from Keycloak).
- `id`, `tenant_id`, `email`, `name`, `roles`, `keycloak_id`, `created_at`

#### `mcp_servers`
Every deployed MCP server.
- `id`, `tenant_id`, `name`, `description`, `endpoint_url`, `storage_path`, `status`, `config` (JSON — stores github_repo, entry_file, pid), `created_at`, `updated_at`

#### `mcp_sessions`
Every user session connected to an MCP server.
- `id`, `mcp_server_id`, `tenant_id`, `user_id`, `user_email`, `user_roles`, `status`, `started_at`, `last_activity`

#### `audit_logs`
Immutable record of every MCP tool call.
- `id`, `session_id`, `mcp_server_id`, `tenant_id`, `user_id`, `user_email`, `tool_name`, `tool_input` (JSON), `tool_output` (JSON), `status`, `duration_ms`, `called_at`

### Key Design Decisions
- All tables include `tenant_id` — row-level security filters by this on every query
- `audit_logs` is insert-only — never updated or deleted (immutability for compliance)
- `config` column in `mcp_servers` is flexible JSON — stores different fields per server type
- Sessions stored in both Redis (live state) and PostgreSQL (history + analytics)

---

## 15. Security Model

### Principle 1 — Least Privilege
- Each user token lists exactly which MCP servers they can access (`mcp_servers` claim)
- Within an MCP server, roles control which tools are accessible (`roles` claim)
- Admin role required for: stopping servers, viewing all users' audit logs, changing config

### Principle 2 — Short-Lived Tokens
- JWT tokens expire after 15 minutes
- Refresh tokens valid for 8 hours (one working day)
- No long-lived API keys — all access goes through OAuth flow
- Token rotation on every refresh — old tokens invalidated immediately

### Principle 3 — Tenant Isolation
- Tenant A's tokens cannot authenticate with Tenant B's Keycloak realm
- Database queries always include `WHERE tenant_id = ?` — enforced at ORM level
- Redis keys namespaced by tenant — `mcp:{tenant_id}:session:{id}`
- MCP server endpoints include tenant slug — wrong tenant = 404, not 403 (prevents enumeration)

### Principle 4 — Immutable Audit Trail
- Audit logs are written before the response is returned — they cannot be skipped
- Audit table has no UPDATE or DELETE permissions in production
- Logs are replicated to S3/MinIO every hour as cold storage backup
- Tamper detection: each log entry includes a hash of the previous entry (chain integrity)

### Principle 5 — Secrets Management
- GitHub tokens: encrypted at rest using AES-256 before storing in database
- JWT signing keys: stored in AWS Secrets Manager (or HashiCorp Vault locally)
- Database credentials: never in code — always environment variables
- No secrets in Git — `.env` files are gitignored, secrets injected at runtime

---

## 16. Local Development Setup — Zero Cost

### What Runs Locally (All Free)

| Service | Tool | Port | Purpose |
|---|---|---|---|
| Identity Server | Keycloak | 8080 | OAuth 2.1 + JWT + User management |
| Backend API | FastAPI (Python) | 8000 | Core platform logic |
| Frontend | Next.js | 3000 | Dashboard UI |
| Database | PostgreSQL | 5432 | All persistent data |
| Cache / Sessions | Redis | 6379 | Sessions, task queue |
| File Storage | MinIO | 9000/9001 | Documents, code files (S3 compatible) |
| Containers | Docker Desktop | — | Runs everything |

### Start Command
```
docker-compose up -d
```
That single command starts all 6 services. Total monthly cost: $0.

### First-Time Setup Checklist
- Install Docker Desktop (free)
- Run `docker-compose up -d`
- Open Keycloak at localhost:8080 (admin / admin123)
- Create realm: `mcp-platform`
- Create client: `mcp-backend` (confidential, openid-connect)
- Create test user with email and password
- Add custom attribute `tenant_id` to user
- Open dashboard at localhost:3000 or open `dashboard.html` directly in browser
- Test API connection from Settings page

---

## 17. AWS Migration Plan — When Ready

### Migration is Zero Code Change — Only Config Change

| Local (Free) | AWS (Paid) | How to Migrate |
|---|---|---|
| Keycloak in Docker | AWS Cognito | Change `KEYCLOAK_URL` env var to Cognito endpoint |
| PostgreSQL in Docker | AWS RDS (PostgreSQL) | Change `DATABASE_URL` env var |
| Redis in Docker | AWS ElastiCache (Redis) | Change `REDIS_URL` env var |
| MinIO in Docker | AWS S3 | Change `MINIO_URL` to S3, same boto3 code |
| Docker Compose | AWS ECS Fargate | Write Terraform scripts (templates provided) |
| Local Nginx | AWS API Gateway | Add API Gateway in front of ECS |
| Manual deploy | GitHub Actions CI/CD | Already set up — just add AWS credentials |

### Estimated AWS Monthly Cost (at launch)
| Service | Spec | Monthly Cost |
|---|---|---|
| AWS RDS (PostgreSQL) | t3.medium, 20GB | ~$50 |
| AWS ECS Fargate | 2 tasks, 0.5 vCPU each | ~$40 |
| AWS ElastiCache (Redis) | t3.micro | ~$15 |
| AWS S3 | 10GB storage | ~$1 |
| AWS Cognito | Up to 50,000 users | Free |
| AWS CloudWatch | Basic logs | ~$10 |
| AWS API Gateway | 1M calls/month | ~$4 |
| **Total** | | **~$120/month** |

First paying customer at $299/month covers entire AWS infrastructure cost.

---

## 18. Build Phases — Week by Week

### Phase 1 — Foundation (Week 1–2)
- Docker Compose setup running all services
- FastAPI project structure (monorepo)
- PostgreSQL schema + Alembic migrations
- Keycloak running locally with test realm and user
- JWT middleware validating tokens on every request
- `/health` and `/me` endpoints working
- **Milestone:** Call `/me` with a Keycloak JWT → see your identity returned

### Phase 2 — MCP Core (Week 3–4)
- GitHub connect flow (token → validate → list repos)
- Repo file scanner (fetch tree → filter .py → suggest entry point)
- MCP deploy engine (clone → pip install → run subprocess → generate URL)
- Live log streaming from running MCP process
- Session creation in Redis on first tool call
- Per-call audit logging to PostgreSQL
- **Milestone:** Deploy the sample invoice MCP from GitHub → call a tool → see audit log

### Phase 3 — Dashboard (Week 5–6)
- Deploy page with 4-step GitHub wizard
- Servers page with card grid and status
- Sessions page with live table
- Audit logs page with full call history
- Settings page with OAuth config and quick links
- **Milestone:** Full end-to-end via UI — connect GitHub → deploy → see logs in dashboard

### Phase 4 — First Vertical Product (Week 7–10)
- Choose one vertical: Invoice Processing OR Contract Analysis
- Build complete MCP server for that vertical (5–8 tools)
- Connect to real document sources (PDF upload via MinIO)
- Add LangChain/LlamaIndex RAG pipeline for document processing
- Create landing page for the vertical product
- Stripe integration for $299/month subscription
- **Milestone:** First paying customer — real invoice or contract processed end to end

### Phase 5 — Multi-Tenant & Scale (Week 11–16)
- Tenant onboarding flow (signup → own Keycloak realm → isolated environment)
- Usage-based billing (track calls per tenant → Stripe metered billing)
- Second vertical MCP product
- AWS migration (move from local Docker to ECS)
- Custom domain support (customers bring their own domain)
- **Milestone:** 5 paying tenants on AWS with zero downtime

---

## 19. Competitive Landscape

### Direct Competitors (MCP Hosting)
| Competitor | Strength | Weakness | Your Advantage |
|---|---|---|---|
| MintMCP | One-click deploy, SOC2 | No per-call identity, no verticals | Per-call enforcement + vertical products |
| TrueFoundry | Sub-3ms latency, enterprise | Complex setup, no SMB option | Self-serve, no DevOps required |
| AWS Bedrock AgentCore | Deep AWS integration | AWS lock-in, enterprise pricing | Multi-cloud, cheaper, self-serve |
| Kong MCP Gateway | Mature gateway, RBAC | $50k+ enterprise, no GitHub import | Accessible to mid-market from day 1 |
| Cloudflare Workers | Edge performance | No identity layer, no dashboard | Full identity + audit dashboard |

### Your Unique Position
- Only platform combining: **GitHub import + per-call identity + vertical products + SMB pricing**
- Competitors are either infrastructure tools (for DevOps) or enterprise products ($50k+)
- You target the gap: **mid-market companies ($5M–$200M) who need enterprise capabilities at SMB prices**

---

## 20. Business Model & Pricing

### Pricing Tiers

#### Starter — Free
- 1 MCP server
- 1 user
- 1,000 tool calls per month
- Community support
- Ideal for: individual developers testing the platform

#### Developer — $49/month
- 5 MCP servers
- 10 users
- 50,000 tool calls per month
- GitHub import (unlimited repos)
- Audit logs (30-day retention)
- Email support
- Ideal for: small consultancies, freelance developers

#### Team — $299/month
- 20 MCP servers
- 50 users
- 500,000 tool calls per month
- Vertical MCP templates included
- Audit logs (1-year retention) + CSV export
- Priority support + onboarding call
- Ideal for: mid-market companies, IT departments

#### Enterprise — Custom pricing
- Unlimited MCP servers
- Unlimited users
- Unlimited tool calls
- Custom domain support
- SSO with company IdP (Okta, Azure AD, Google Workspace)
- SLA guarantee (99.9% uptime)
- Dedicated support engineer
- On-premise / private cloud deployment option
- Ideal for: 1,000+ employee companies with compliance requirements

### Revenue Projections (Conservative)
| Month | Customers | MRR |
|---|---|---|
| Month 3 | 5 Team | $1,495 |
| Month 6 | 20 Team + 2 Enterprise | $7,980 |
| Month 12 | 60 Team + 10 Enterprise | $27,940 |

---

## 21. Open Questions & Decisions Needed

These are the things you need to decide before or during building:

### Technical Decisions
- **MCP transport protocol:** Will you support only SSE or also HTTP streaming? (SSE is simpler to start)
- **Multi-process vs Docker per MCP:** Running each MCP as subprocess (simple) vs its own Docker container (isolated, safer) — Docker is better but harder to implement initially
- **Token expiry:** 15 minutes is secure but requires more frequent re-auth — consider 1 hour for better UX
- **Vector database:** Start with pgvector (inside existing PostgreSQL) or separate Qdrant/Weaviate? (pgvector is simpler to start)
- **GitHub Apps vs PAT:** Personal Access Tokens are simple but less secure — GitHub OAuth Apps are better for production

### Business Decisions
- **Which vertical first?** Invoice processing (Finance) is highest ROI and easiest to demo. Recommend starting here.
- **Freemium vs paid-only?** Freemium drives signups but can attract non-paying users who drain support — consider a 14-day free trial instead
- **Self-serve vs sales-led?** Start self-serve (no sales team needed) → add sales motion when you hit $10k MRR
- **Open source the platform?** Open-sourcing the infrastructure layer and charging for hosted service (like Supabase model) could drive developer adoption

### Go-To-Market Decisions
- **First channel:** Developer communities (Discord, Reddit, Hacker News) for platform; direct outreach to Finance/Legal departments for vertical products
- **Partnership opportunity:** MCP server marketplace — let other developers publish their MCPs to your platform and take a revenue share
- **Content strategy:** Write about MCP security and identity (the gap you solve) — position yourself as the expert before launching

---

*Document Version: 1.0 | Created: March 2026 | Status: Active Blueprint*

*This document covers the complete vision, architecture, technical design, and go-to-market strategy for the MCP Cloud Platform. Update this document as decisions are made and the product evolves.*
