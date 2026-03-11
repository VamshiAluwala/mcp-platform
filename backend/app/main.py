"""
MCP PLATFORM — Main Entry Point

FastAPI application with:
- JWT identity enforcement on every request
- MCP server deployment
- Multi-session management
- Full audit logging
"""

from datetime import datetime
import re
from urllib.parse import quote

from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import log_tool_call
from app.api.auth import router as auth_router
from app.api.audit_routes import router as audit_router
from app.api.deploy import router as deploy_router
from app.api.github_integration import router as github_router
from app.api.sessions import router as sessions_router
from app.api.admin import router as admin_router
from app.auth.middleware import get_current_user, get_request_access_token, resolve_user_from_token
from app.core.config import settings
from app.mcp.session import session_manager
from app.models.database import MCPSession, MCPServer, create_tables, get_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables"""
    await create_tables()
    print("✅ Database tables created")
    print("✅ MCP Platform started")
    yield
    print("MCP Platform shutting down...")


app = FastAPI(
    title="MCP Platform",
    description="Host any MCP server with identity tracking & OAuth",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend to talk to backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routes ──────────────────────────────────────────────────────
app.include_router(deploy_router)
app.include_router(sessions_router)
app.include_router(github_router)
app.include_router(auth_router)
app.include_router(audit_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {
        "name": "MCP Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    """Test endpoint — returns your identity from the JWT token"""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "tenant_id": user.get("tenant_id"),
        "roles": user.get("roles"),
    }


def _normalize_server_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized


async def _extract_tool_input(request: Request) -> dict:
    if request.method != "POST":
        return {}

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return {}

    try:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def _allowed_server_emails(server: MCPServer) -> list[str]:
    config = server.config or {}
    allowed = config.get("allowed_user_emails", [])
    if not isinstance(allowed, list):
        return []
    normalized: list[str] = []
    for email in allowed:
        cleaned = (email or "").strip().lower()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    owner_email = (config.get("owner_email") or "").strip().lower()
    if owner_email and owner_email not in normalized:
        normalized.append(owner_email)
    return normalized


@app.api_route("/mcp/{tenant_slug}/{server_name}", methods=["GET", "POST"])
async def mcp_endpoint(
    tenant_slug: str,
    server_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    MCP Server Endpoint.
    This is the URL users plug into Claude Code.
    Identity verified on EVERY request — not just first connection.
    """
    def login_redirect_response() -> RedirectResponse:
        next_url = quote(str(request.url), safe="")
        login_url = f"{settings.FRONTEND_URL}/login?provider=google_direct&next={next_url}"
        return RedirectResponse(login_url, status_code=307)

    token = get_request_access_token(request)
    if not token:
        if request.method == "GET":
            return login_redirect_response()
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        user = await resolve_user_from_token(token=token, db=db)
    except HTTPException:
        if request.method == "GET":
            return login_redirect_response()
        raise

    result = await db.execute(select(MCPServer))
    servers = result.scalars().all()
    matching_server = next(
        (
            server
            for server in servers
            if server.tenant_id[:8] == tenant_slug
            and _normalize_server_name(server.name) == _normalize_server_name(server_name)
        ),
        None,
    )
    if not matching_server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    allowed_emails = _allowed_server_emails(matching_server)
    requester_email = (user.get("email") or "").strip().lower()
    is_owner = matching_server.tenant_id == (user.get("tenant_id") or user["user_id"])
    is_admin = "admin" in user.get("roles", [])
    is_allowed = requester_email and requester_email in allowed_emails
    if not (is_owner or is_admin or is_allowed):
        raise HTTPException(status_code=403, detail="You do not have access to this MCP server")

    server_tenant_id = matching_server.tenant_id

    session_id = request.headers.get("x-session-id")
    session = await db.get(MCPSession, session_id) if session_id else None
    if session and (
        session.tenant_id != server_tenant_id
        or session.user_id != user["user_id"]
        or session.mcp_server_id != matching_server.id
    ):
        session = None

    if not session:
        session = MCPSession(
            mcp_server_id=matching_server.id,
            tenant_id=server_tenant_id,
            user_id=user["user_id"],
            user_email=user.get("email"),
            user_roles=user.get("roles", []),
            status="active",
            started_at=datetime.utcnow(),
            last_activity=datetime.utcnow(),
        )
        db.add(session)
        await db.flush()
        try:
            await session_manager.create_session(
                session_id=session.id,
                user_id=user["user_id"],
                user_email=user.get("email") or "",
                tenant_id=server_tenant_id,
                mcp_server_id=matching_server.id,
                roles=user.get("roles", []),
            )
        except Exception:
            pass
    else:
        try:
            await session_manager.update_activity(server_tenant_id, session.id)
        except Exception:
            pass

    started = datetime.utcnow()
    tool_input = await _extract_tool_input(request)
    tool_name = (
        tool_input.get("tool_name")
        or tool_input.get("tool")
        or tool_input.get("method")
        or "mcp_call"
    )

    session.status = "active"
    session.call_count = (session.call_count or 0) + 1
    session.last_activity = datetime.utcnow()

    response_payload = {
        "message": f"MCP server '{server_name}' for tenant '{tenant_slug}'",
        "authenticated_user": user["email"],
        "tenant_id": server_tenant_id,
        "server_id": matching_server.id,
        "session_id": session.id,
    }

    duration_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
    await log_tool_call(
        db=db,
        session_id=session.id,
        mcp_server_id=matching_server.id,
        tenant_id=server_tenant_id,
        user_id=user["user_id"],
        user_email=user.get("email") or "",
        tool_name=tool_name,
        tool_input=tool_input or {"method": request.method, "path": request.url.path},
        tool_output=response_payload,
        status="success",
        duration_ms=duration_ms,
    )

    return response_payload
