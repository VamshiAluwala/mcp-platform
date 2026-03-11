# 🚀 MCP Platform — Local Development Setup

Your complete MCP hosting platform with OAuth identity tracking.
**100% Free. Runs entirely on your local machine.**

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│  Developer uploads MCP code                      │
│           ↓                                      │
│  Platform deploys → generates URL               │
│           ↓                                      │
│  User connects URL in Claude Code               │
│           ↓                                      │
│  YOUR OAuth (Keycloak) verifies identity        │
│           ↓                                      │
│  Every tool call tracked → audit log            │
└─────────────────────────────────────────────────┘
```

---

## 📦 What's Running

| Service | URL | Purpose |
|---|---|---|
| **Backend API** | http://localhost:8000 | FastAPI — core platform |
| **API Docs** | http://localhost:8000/docs | Auto-generated Swagger UI |
| **Frontend** | http://localhost:3000 | Next.js dashboard |
| **Keycloak** | http://localhost:8080 | Identity & OAuth (free Cognito) |
| **MinIO** | http://localhost:9001 | File storage dashboard (free S3) |
| **PostgreSQL** | localhost:5433 | Main database |
| **Redis** | localhost:6379 | Sessions & cache |

---

## 🚀 Start Everything (One Command)



```bash
# 1. Make sure Docker Desktop is running
# 2. Clone this repo
# 3. Run:


docker-compose up -d


# Check everything is running:
docker-compose ps
```

---

## 🔐 Setup Keycloak (One Time — 10 Minutes)

1. Open http://localhost:8080
2. Login: **admin / admin123**
3. Create a new Realm: `mcp-platform`
4. Create a Client:
   - Client ID: `mcp-backend`
   - Client Protocol: `openid-connect`
   - Access Type: `confidential`
5. Create a test user:
   - Username: `testuser`
   - Email: `test@example.com`
   - Password: `test123`
6. Add custom attribute `tenant_id` to user

---

## 📡 API Quick Reference

### Deploy an MCP Server
```bash
curl -X POST http://localhost:8000/api/mcp/deploy \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "invoice-processor",
    "description": "AI Invoice Processing MCP",
    "server_code": "# your MCP code here"
  }'

# Returns:
# {
#   "endpoint_url": "http://localhost:8000/mcp/abc123/invoice-processor",
#   "instructions": "Add this URL to Claude Code..."
# }
```

### List Your MCP Servers
```bash
curl http://localhost:8000/api/mcp/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Start a Session
```bash
curl -X POST http://localhost:8000/api/sessions/start \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"mcp_server_id": "your-server-id"}'
```

### View Audit Logs
```bash
curl http://localhost:8000/api/audit/ \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Check Your Identity
```bash
curl http://localhost:8000/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## 📁 Project Structure

```
mcp-platform/
├── docker-compose.yml          ← Start everything here
├── backend/
│   ├── app/
│   │   ├── main.py             ← FastAPI entry point
│   │   ├── auth/
│   │   │   └── middleware.py   ← JWT per-call identity
│   │   ├── mcp/
│   │   │   ├── host.py         ← Deploy MCP servers
│   │   │   └── session.py      ← Multi-session manager
│   │   ├── api/
│   │   │   ├── deploy.py       ← Deploy endpoints
│   │   │   ├── sessions.py     ← Session endpoints
│   │   │   └── audit.py        ← Audit log endpoints
│   │   ├── models/
│   │   │   └── database.py     ← DB models
│   │   └── core/
│   │       └── config.py       ← Settings
│   └── requirements.txt
├── frontend/                   ← Next.js dashboard (add later)
├── mcps/
│   └── invoice-mcp/
│       └── server.py           ← Sample vertical MCP
└── infrastructure/
    └── init-db.sh              ← DB initialization
```

---

## 🔄 Local → AWS Migration (When Ready)

| Now (Free Local) | Later (AWS) | Change Needed |
|---|---|---|
| Keycloak | AWS Cognito | Swap env vars only |
| PostgreSQL Docker | AWS RDS | Zero change |
| Redis Docker | AWS ElastiCache | Zero change |
| MinIO | AWS S3 | Zero change (same boto3) |
| Docker Compose | AWS ECS Fargate | Terraform scripts |

---

## 🧪 Test the Full Flow

```bash
# 1. Start everything
docker-compose up -d

# 2. Get a JWT token from Keycloak
curl -X POST http://localhost:8080/realms/mcp-platform/protocol/openid-connect/token \
  -d "client_id=mcp-backend&username=testuser&password=test123&grant_type=password"

# 3. Use the token to deploy an MCP
TOKEN="your-token-here"
curl -X POST http://localhost:8000/api/mcp/deploy \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "test-mcp", "description": "Test", "server_code": "# MCP code"}'

# 4. See your identity tracked
curl http://localhost:8000/me -H "Authorization: Bearer $TOKEN"

# 5. Open API docs
open http://localhost:8000/docs
```

---

## 💡 Next Steps

1. ✅ Get this running locally
2. ✅ Deploy the sample invoice MCP
3. ✅ Connect the endpoint URL to Claude Code
4. 🔜 Build the Next.js dashboard
5. 🔜 Add your first real vertical MCP
6. 🔜 Deploy to AWS when ready
