# ─────────────────────────────────────────────────────────────────
# MCP Platform — Local Development Makefile
# Run WITHOUT Docker. Just needs Postgres + Redis (see `make setup`)
# ─────────────────────────────────────────────────────────────────

.PHONY: setup backend frontend dev stop logs help keycloak-fix-http keycloak-mcp-client

# ── Colours ──────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RESET  := \033[0m

# ════════════════════════════════════════════════════════════════
# SETUP — one-time: install system services + Python venv
# ════════════════════════════════════════════════════════════════
setup:
	@echo "$(GREEN)▶ Installing system services via Homebrew…$(RESET)"
	brew install postgresql@16 redis git || true
	brew services start postgresql@16 || true
	brew services start redis || true
	@echo "$(YELLOW)▶ Creating PostgreSQL database 'appdb'…$(RESET)"
	createdb appdb 2>/dev/null || echo "  (database already exists, skipping)"
	@echo "$(GREEN)▶ Setting up Python virtual environment…$(RESET)"
	cd backend && python3 -m venv .venv && \
	  .venv/bin/pip install --upgrade pip && \
	  .venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)▶ Installing frontend dependencies…$(RESET)"
	cd frontend && npm install
	@echo ""
	@echo "$(GREEN)✅  Setup complete! Run 'make dev' to start everything.$(RESET)"

# ════════════════════════════════════════════════════════════════
# DEV — start backend + frontend in parallel (foreground)
# ════════════════════════════════════════════════════════════════
dev:
	@echo "$(GREEN)▶ Starting backend (port 8000) and frontend (port 3000)…$(RESET)"
	@trap 'kill 0' INT; \
	  (cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload 2>&1 | sed 's/^/[backend] /') & \
	  (cd frontend && npm run dev 2>&1 | sed 's/^/[frontend] /') & \
	  wait

# ════════════════════════════════════════════════════════════════
# Individual service targets
# ════════════════════════════════════════════════════════════════
backend:
	@echo "$(GREEN)▶ Starting backend only (port 8000)…$(RESET)"
	cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

frontend:
	@echo "$(GREEN)▶ Starting frontend only (port 3000)…$(RESET)"
	cd frontend && npm run dev

# ════════════════════════════════════════════════════════════════
# SERVICES — start/stop only Postgres + Redis
# ════════════════════════════════════════════════════════════════
services-start:
	@brew services start postgresql@16
	@brew services start redis
	@echo "$(GREEN)✅  Postgres + Redis running$(RESET)"

services-stop:
	@brew services stop postgresql@16
	@brew services stop redis
	@echo "$(YELLOW)✅  Postgres + Redis stopped$(RESET)"

services-status:
	@brew services list | grep -E "postgresql|redis"

keycloak-fix-http:
	@echo "$(GREEN)▶ Allowing HTTP login for local Keycloak realms…$(RESET)"
	docker compose exec -T keycloak sh -lc '/opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin123 >/dev/null && /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=NONE >/dev/null && /opt/keycloak/bin/kcadm.sh get realms/mcp-platform >/dev/null 2>&1 && /opt/keycloak/bin/kcadm.sh update realms/mcp-platform -s sslRequired=NONE >/dev/null || true'
	@echo "$(GREEN)✅  Keycloak realms updated for local HTTP$(RESET)"

keycloak-mcp-client:
	@echo "$(GREEN)▶ Creating/updating Keycloak public client for MCP apps…$(RESET)"
	docker compose cp scripts/bootstrap_keycloak_mcp.sh keycloak:/tmp/bootstrap_keycloak_mcp.sh >/dev/null
	docker compose exec -T keycloak sh /tmp/bootstrap_keycloak_mcp.sh >/dev/null
	@echo "$(GREEN)✅  Keycloak client 'mcp-clients' is ready$(RESET)"

# ════════════════════════════════════════════════════════════════
# HELP
# ════════════════════════════════════════════════════════════════
help:
	@echo ""
	@echo "  $(GREEN)make setup$(RESET)           One-time: brew install + venv + npm install"
	@echo "  $(GREEN)make dev$(RESET)             Start backend + frontend together"
	@echo "  $(GREEN)make backend$(RESET)         Start backend only"
	@echo "  $(GREEN)make frontend$(RESET)        Start frontend only"
	@echo "  $(GREEN)make services-start$(RESET)  Start Postgres + Redis"
	@echo "  $(GREEN)make services-stop$(RESET)   Stop Postgres + Redis"
	@echo "  $(GREEN)make services-status$(RESET) Check service status"
	@echo "  $(GREEN)make keycloak-fix-http$(RESET) Re-enable HTTP login for local Keycloak"
	@echo "  $(GREEN)make keycloak-mcp-client$(RESET) Create/update loopback OAuth client for Claude/MCP apps"
	@echo ""
