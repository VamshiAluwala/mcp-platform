# ─────────────────────────────────────────────────────────────────
# MCP Platform — Local Development Makefile
# Run frontend/backend locally, but keep infra services in Docker.
# ─────────────────────────────────────────────────────────────────

.PHONY: setup local backend frontend dev stop logs help keycloak-fix-http keycloak-mcp-client

# ── Colours ──────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
RED    := \033[0;31m
RESET  := \033[0m

# Prefer a supported Python for local backend deps.
PYTHON_BIN := $(shell if command -v python3.12 >/dev/null 2>&1; then echo python3.12; \
               elif command -v python3.13 >/dev/null 2>&1; then echo python3.13; \
               else echo python3; fi)

# ════════════════════════════════════════════════════════════════
# SETUP — one-time: Python venv + npm install
# ════════════════════════════════════════════════════════════════
setup:
	@echo "$(GREEN)▶ Using Python interpreter: $$($(PYTHON_BIN) --version)$(RESET)"
	@if [ "$$($(PYTHON_BIN) -c 'import sys; print(sys.version_info[:2] >= (3, 14))')" = "True" ]; then \
	  echo "$(RED)✗ Python 3.14+ is not supported by this backend yet. Install python3.12 or python3.13 and rerun make setup.$(RESET)"; \
	  exit 1; \
	fi
	@echo "$(GREEN)▶ Setting up Python virtual environment…$(RESET)"
	rm -rf backend/.venv
	cd backend && $(PYTHON_BIN) -m venv .venv && \
	  .venv/bin/pip install --upgrade pip && \
	  .venv/bin/pip install -r requirements.txt
	@echo "$(GREEN)▶ Installing frontend dependencies…$(RESET)"
	cd frontend && npm install
	@echo ""
	@echo "$(GREEN)✅  Setup complete! Run 'make local' to start everything.$(RESET)"

# ════════════════════════════════════════════════════════════════
# DEV — start backend + frontend in parallel (foreground)
# ════════════════════════════════════════════════════════════════
local:
	@echo "$(GREEN)▶ Starting Docker infra (Postgres + Redis + Keycloak + MinIO), then backend + frontend locally…$(RESET)"
	@$(MAKE) services-start
	@$(MAKE) dev

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
# SERVICES — Docker infra only
# ════════════════════════════════════════════════════════════════
services-start:
	@echo "$(GREEN)▶ Starting Docker infra services…$(RESET)"
	@docker compose stop backend frontend >/dev/null 2>&1 || true
	@docker compose up -d postgres redis keycloak minio
	@echo "$(GREEN)✅  Docker infra running: postgres(5433), redis(6379), keycloak(8080), minio(9001/9002)$(RESET)"

services-stop:
	@docker compose stop postgres redis keycloak minio backend frontend >/dev/null 2>&1 || true
	@echo "$(YELLOW)✅  Docker infra stopped$(RESET)"

services-status:
	@docker compose ps postgres redis keycloak minio backend frontend

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
	@echo "  $(GREEN)make setup$(RESET)           One-time: backend venv + frontend npm install"
	@echo "  $(GREEN)make local$(RESET)           Start Docker infra + backend + frontend locally"
	@echo "  $(GREEN)make dev$(RESET)             Start backend + frontend together"
	@echo "  $(GREEN)$(PYTHON_BIN)$(RESET)               Preferred local backend interpreter"
	@echo "  $(GREEN)make backend$(RESET)         Start backend only"
	@echo "  $(GREEN)make frontend$(RESET)        Start frontend only"
	@echo "  $(GREEN)make services-start$(RESET)  Start Docker infra services"
	@echo "  $(GREEN)make services-stop$(RESET)   Stop Docker infra services"
	@echo "  $(GREEN)make services-status$(RESET) Check Docker infra status"
	@echo "  $(GREEN)make keycloak-fix-http$(RESET) Re-enable HTTP login for local Keycloak"
	@echo "  $(GREEN)make keycloak-mcp-client$(RESET) Create/update loopback OAuth client for Claude/MCP apps"
	@echo ""
