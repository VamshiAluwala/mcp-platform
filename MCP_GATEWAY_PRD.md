# MCP Gateway — Product Requirements Document (PRD)

> **Product Name:** MCP Gateway  
> **Type:** SaaS / Self-Hosted Platform  
> **Version:** v1.0 — Local-First, Cloud-Ready  
> **Author:** Vamshi  
> **Status:** Draft

---

## 1. Problem Statement

When deploying custom MCP (Model Context Protocol) servers today, there is no centralized layer for:

- **Identity** — knowing *who* is connecting to an MCP
- **Authorization** — controlling *whether* they should have access
- **Observability** — tracking *what* they are doing and when

Every MCP deployment is a raw endpoint with no access control, no audit trail, and no user management. This creates security gaps, compliance risk, and operational blind spots — especially as the number of MCPs grows across teams or organizations.

---

## 2. Product Vision

**MCP Gateway** is a platform that sits in front of your MCP servers and acts as a unified identity, authorization, and observability layer. It allows platform owners (admins) to deploy, manage, and monitor MCP servers — while enforcing authenticated, authorized access for every client that connects.

Think of it as: **an API Gateway, purpose-built for MCP servers.**

---

## 3. Target Users

| User Role | Description |
|-----------|-------------|
| **Platform Admin** | The person who owns and manages the Gateway. Deploys MCPs, manages user access, views logs. (You) |
| **MCP Consumer** | A developer or AI agent that connects to an MCP endpoint via the Gateway. Must be authenticated. |
| **Enterprise Org Admin** | (Future) A tenant admin who manages access for their Google Workspace org. |

---

## 4. Core Use Cases

### UC-1: Admin Login
- Admin logs into MCP Gateway using **Google OAuth**
- For enterprise scenarios, admin can connect a **Google Workspace tenant** to pull all member emails automatically
- **Keycloak** (running locally) acts as the identity broker for backend authorization decisions

### UC-2: GitHub Integration & MCP Discovery
- Admin connects their GitHub account from the dashboard
- Gateway lists all repositories
- Admin selects a repo and specifies the **main entry file** (e.g., `server.py`)
- Gateway prepares the MCP for deployment

### UC-3: MCP Deployment
- Admin deploys the selected MCP (from GitHub or external JSON config)
- Gateway spins up the MCP in a **Docker container**
- A **unique, routed URL** is issued for that MCP instance (e.g., `https://gateway.local/mcp/{id}`)

### UC-4: External / Public MCP Import
- Admin can also add an external/public MCP server via **JSON config**
- Gateway wraps it with its auth + tracking layer
- Same unique URL + access control applies

### UC-5: Authenticated MCP Access (Client Flow)
- A client (e.g., Claude Code, agent, developer tool) hits the Gateway URL
- Gateway redirects to **OAuth login** (Google or Keycloak)
- After successful auth, Gateway checks if the user is authorized for that specific MCP
- If authorized → request is proxied to the MCP; session is logged
- If not authorized → request is rejected with a clear error

### UC-6: Access Management
- Admin grants/revokes access to specific MCPs for specific users or groups
- For enterprise tenants: admin can bulk-import users from Google Workspace

### UC-7: Observability & Logs
- Admin sees a live/historical log of: who accessed which MCP, when, and with what outcome
- Metrics: total requests, active users, error rates per MCP

---

## 5. Authentication & Authorization Architecture

### 5.1 Authentication Providers

| Provider | Use Case | Environment |
|----------|----------|-------------|
| **Google OAuth 2.0** | Admin login + MCP consumer login | All environments |
| **Google Workspace (tenant)** | Enterprise — pull org member emails, enforce domain-level access | Cloud / Enterprise |
| **Keycloak** | Identity broker, token issuance, session management, local dev auth | Local (runs in Docker) |

### 5.2 Auth Flow (High Level)

```
Client → Gateway URL
          ↓
    Is user authenticated?
    NO  → Redirect to Keycloak (which federates to Google OAuth)
    YES → Is user authorized for this MCP?
          NO  → 403 Forbidden
          YES → Proxy request to MCP container → Log session
```

### 5.3 Token Strategy
- **Google OAuth** issues ID tokens (JWT) for identity
- **Keycloak** issues access tokens scoped to specific MCPs
- Gateway validates tokens on every request (stateless validation where possible)

### 5.4 Enterprise Tenant Integration
- Admin connects a **Google Workspace** account (via OAuth with admin scopes)
- Gateway pulls the directory (user emails) from **Google Directory API**
- These users are auto-provisioned in Keycloak as a group
- Admin can then assign this group to one or more MCPs

---

## 6. Key Features Summary

| Feature | Priority | Notes |
|---------|----------|-------|
| Google OAuth login (Admin) | P0 | Core auth |
| Keycloak integration (local) | P0 | Identity broker |
| GitHub connect + repo listing | P0 | MCP discovery |
| MCP deployment via Docker | P0 | Core deployment |
| Unique routed URL per MCP | P0 | Access entry point |
| Auth-gated MCP access | P0 | Core security |
| Access logs & audit trail | P0 | Observability |
| External MCP import (JSON) | P1 | Flexibility |
| Google Workspace tenant import | P1 | Enterprise |
| User/group access management | P1 | Admin control |
| Multi-cloud deployment (AWS/GCP) | P2 | Phase 2 |
| Multi-tenant SaaS mode | P2 | Phase 3 |

---

## 7. Non-Functional Requirements

- **Deployment:** Docker Compose (local), container-based (cloud)
- **Cost:** Free-tier / open-source stack only (v1.0)
- **Availability:** Local-first; cloud-ready architecture from day one
- **Security:** All MCP endpoints are private by default; no unauthenticated access
- **Scalability:** Stateless gateway layer; horizontal scaling ready for cloud phase
- **Portability:** No cloud-vendor lock-in in v1.0

---

## 8. Out of Scope (v1.0)

- Billing / usage-based metering
- Multi-tenant admin panels (each admin manages their own instance)
- MCP version management / rollback
- Custom domain support
- CI/CD pipeline integration

---

## 9. Success Metrics

- Admin can deploy an MCP and get a working auth-gated URL in < 5 minutes
- Zero unauthenticated requests reach any deployed MCP
- All access events are logged with user identity + timestamp
- Admin can revoke a user's access and it takes effect immediately

---

*End of PRD*
