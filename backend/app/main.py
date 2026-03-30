"""
MCP PLATFORM — Main Entry Point

FastAPI application with:
- JWT identity enforcement on every request
- MCP server deployment
- Multi-session management
- Full audit logging
"""

from datetime import datetime
import base64
import hashlib
import json
import re
from urllib.parse import quote
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, Response
from contextlib import asynccontextmanager
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import email_allowed_via_groups, normalize_group_ids
from app.api.audit import log_tool_call
from app.api.auth import router as auth_router
from app.api.access_groups import router as access_groups_router
from app.api.audit_routes import router as audit_router
from app.api.deploy import router as deploy_router
from app.api.github_integration import router as github_router
from app.api.sessions import router as sessions_router
from app.api.admin import router as admin_router
from app.auth.middleware import get_current_user, get_request_access_token, resolve_user_from_token
from app.auth.service import (
    build_google_login_url,
    exchange_google_code,
    exchange_google_refresh_token,
    exchange_mcp_tokens,
    extract_google_identity,
    fetch_google_userinfo,
    gateway_oauth_metadata,
    protected_resource_metadata,
)
from app.core.config import settings
from app.mcp.host import mcp_host
from app.mcp.session import session_manager
from app.models.database import MCPSession, MCPServer, create_tables, get_db, upsert_platform_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create DB tables"""
    await create_tables()
    print("✅ Database tables created")
    if settings.is_gateway_url_localhost:
        print("⚠️  GATEWAY_PUBLIC_URL is set to a localhost address.")
        print("   MCP URLs will be auto-resolved from request Host headers.")
        print("   For production, set GATEWAY_PUBLIC_URL to your public domain.")
    else:
        print(f"✅ GATEWAY_PUBLIC_URL: {settings.GATEWAY_PUBLIC_URL}")
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
app.include_router(access_groups_router)


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


async def _extract_tool_input(request: Request, body: bytes | None = None) -> dict:
    if request.method not in {"POST", "PUT", "PATCH"}:
        return {}

    content_type = request.headers.get("content-type", "")
    if "application/json" not in content_type:
        return {}

    try:
        payload = request.scope.get("_cached_json_payload")
        if payload is None:
            raw_body = body if body is not None else await request.body()
            if not raw_body:
                return {}
            payload = httpx.Response(200, content=raw_body).json()
            request.scope["_cached_json_payload"] = payload
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


def _login_redirect_response(request: Request) -> RedirectResponse:
    next_url = quote(str(request.url), safe="")
    login_url = f"{settings.FRONTEND_URL}/login?provider=google_direct&next={next_url}"
    return RedirectResponse(login_url, status_code=307)


def _is_browser_request(request: Request) -> bool:
    accept = request.headers.get("accept", "").lower()
    user_agent = request.headers.get("user-agent", "").lower()
    return request.method == "GET" and "text/html" in accept and "mozilla" in user_agent


def _mcp_resource_metadata_url(server_id: str, request: Request | None = None) -> str:
    host = request.headers.get("host") if request else None
    scheme = request.url.scheme if request else None
    base = settings.resolve_gateway_url(request_host=host, scheme=scheme)
    return f"{base}/.well-known/oauth-protected-resource/mcp/{server_id}"


def _mcp_access_mode(server: MCPServer) -> str:
    config = server.config or {}
    mode = str(config.get("mcp_access_mode") or "").strip().lower()
    if mode in {"public", "unauthenticated", "noauth", "none"}:
        return "public"
    if mode in {"platform_auth", "oauth", "protected"}:
        return "platform_auth"
    if config.get("source_type") == "github":
        return "public"
    return "platform_auth"


def _unauthorized_mcp_response(request: Request, server_id: str) -> Response:
    if _is_browser_request(request):
        return _login_redirect_response(request)

    host = request.headers.get("host")
    scheme = request.url.scheme
    base = settings.resolve_gateway_url(request_host=host, scheme=scheme)
    resource_url = f"{base}/mcp/{server_id}"
    headers = {
        "WWW-Authenticate": (
            'Bearer realm="mcp", '
            f'resource="{resource_url}", '
            f'authorization_uri="{base}/authorize", '
            f'resource_metadata="{_mcp_resource_metadata_url(server_id, request)}"'
        )
    }
    return JSONResponse(
        status_code=401,
        content={"detail": "Not authenticated"},
        headers=headers,
    )


def _proxy_response_headers(upstream_headers: httpx.Headers) -> dict[str, str]:
    excluded = {
        "connection",
        "content-length",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
    }
    return {
        key: value
        for key, value in upstream_headers.items()
        if key.lower() not in excluded
    }


def _legacy_runtime_fallback_url(config: dict | None) -> str | None:
    runtime = (config or {}).get("runtime", {})
    if runtime.get("kind") != "docker":
        return None
    if runtime.get("path"):
        return None
    internal_url = runtime.get("internal_url")
    if not internal_url:
        return None
    return f"{internal_url.rstrip('/')}/mcp"


def _encode_google_bridge_state(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")


def _decode_google_bridge_state(raw_state: str | None) -> dict:
    if not raw_state:
        raise HTTPException(status_code=400, detail="Missing OAuth state")
    try:
        return json.loads(base64.b64decode(raw_state).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth state") from exc


def _oauth_txn_key(txn_id: str) -> str:
    return f"mcp:oauth:txn:{txn_id}"


def _oauth_code_key(code: str) -> str:
    return f"mcp:oauth:code:{code}"


def _verify_pkce(
    *,
    code_verifier: str | None,
    code_challenge: str | None,
    code_challenge_method: str | None,
) -> bool:
    if not code_challenge:
        return True
    if not code_verifier:
        return False

    method = (code_challenge_method or "plain").upper()
    if method == "S256":
        digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        computed = base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")
    else:
        computed = code_verifier
    return computed == code_challenge


async def _resolve_server_by_legacy_slug(
    db: AsyncSession,
    *,
    tenant_slug: str,
    server_name: str,
) -> MCPServer | None:
    result = await db.execute(select(MCPServer))
    servers = result.scalars().all()
    return next(
        (
            server
            for server in servers
            if server.tenant_id[:8] == tenant_slug
            and _normalize_server_name(server.name) == _normalize_server_name(server_name)
        ),
        None,
    )


async def _handle_mcp_request(
    *,
    server: MCPServer,
    request: Request,
    db: AsyncSession,
):
    server_tenant_id = server.tenant_id
    access_mode = _mcp_access_mode(server)
    user = None
    session = None
    session_id = None

    if access_mode != "public":
        token = get_request_access_token(request)
        if not token:
            return _unauthorized_mcp_response(request, server.id)

        try:
            user = await resolve_user_from_token(token=token, db=db)
        except HTTPException:
            return _unauthorized_mcp_response(request, server.id)

        allowed_emails = _allowed_server_emails(server)
        allowed_group_ids = normalize_group_ids((server.config or {}).get("allowed_group_ids", []))
        requester_email = (user.get("email") or "").strip().lower()
        is_owner = server.tenant_id == (user.get("tenant_id") or user["user_id"])
        is_admin = "admin" in user.get("roles", [])
        is_allowed = requester_email and requester_email in allowed_emails
        if not is_allowed:
            is_allowed = await email_allowed_via_groups(
                db,
                group_ids=allowed_group_ids,
                email=requester_email,
            )
        if not (is_owner or is_admin or is_allowed):
            await log_tool_call(
                db=db,
                session_id=None,
                mcp_server_id=server.id,
                tenant_id=server.tenant_id,
                user_id=user["user_id"],
                user_email=user.get("email") or "",
                tool_name="access_check",
                tool_input={"method": request.method, "path": request.url.path},
                tool_output={"detail": "Access denied"},
                status="denied",
                duration_ms=0,
            )
            raise HTTPException(status_code=403, detail="You do not have access to this MCP server")

        session_id = request.headers.get("x-session-id")
        session = await db.get(MCPSession, session_id) if session_id else None
        if session and (
            session.tenant_id != server_tenant_id
            or session.user_id != user["user_id"]
            or session.mcp_server_id != server.id
        ):
            session = None

        if not session:
            session = MCPSession(
                mcp_server_id=server.id,
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
                    mcp_server_id=server.id,
                    roles=user.get("roles", []),
                )
            except Exception:
                pass
        else:
            try:
                await session_manager.update_activity(server_tenant_id, session.id)
            except Exception:
                pass

        # Release the DB connection before waiting on the upstream MCP runtime.
        # Without this, concurrent MCP calls can exhaust the async pool and break
        # unrelated login/OAuth requests.
        await db.commit()

    upstream_url = mcp_host.upstream_url(server.config or {})
    if not upstream_url:
        raise HTTPException(status_code=503, detail="MCP runtime target is not configured")

    body = await request.body()
    started = datetime.utcnow()
    tool_input = await _extract_tool_input(request, body)
    tool_name = (
        tool_input.get("tool_name")
        or tool_input.get("tool")
        or tool_input.get("method")
        or "mcp_call"
    )

    forward_headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"authorization", "cookie", "host", "content-length"}
    }
    forward_headers.update(mcp_host.upstream_headers(server.config or {}))
    if session is not None:
        forward_headers["x-mcp-session-id"] = session.id
    if user is not None:
        forward_headers["x-mcp-user-id"] = user["user_id"]
    if user and user.get("email"):
        forward_headers["x-mcp-user-email"] = user["email"]
    forward_headers["x-mcp-tenant-id"] = server_tenant_id
    if access_mode == "public":
        forward_headers["x-mcp-access-mode"] = "public"

    if request.url.query:
        upstream_url = f"{upstream_url}?{request.url.query}"

    try:
        async with httpx.AsyncClient(timeout=mcp_host.upstream_timeout(server.config or {})) as client:
            upstream = await client.request(
                request.method,
                upstream_url,
                headers=forward_headers,
                content=body or None,
                follow_redirects=False,
            )
            if upstream.status_code == 404:
                fallback_url = _legacy_runtime_fallback_url(server.config or {})
                if fallback_url and fallback_url != upstream_url:
                    if request.url.query:
                        fallback_url = f"{fallback_url}?{request.url.query}"
                    upstream = await client.request(
                        request.method,
                        fallback_url,
                        headers=forward_headers,
                        content=body or None,
                        follow_redirects=False,
                    )
    except Exception as exc:
        duration_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
        if session is not None and user is not None:
            await log_tool_call(
                db=db,
                session_id=session.id,
                mcp_server_id=server.id,
                tenant_id=server_tenant_id,
                user_id=user["user_id"],
                user_email=user.get("email") or "",
                tool_name=tool_name,
                tool_input=tool_input or {"method": request.method, "path": request.url.path},
                tool_output={"detail": str(exc)},
                status="upstream_error",
                duration_ms=duration_ms,
            )
        raise HTTPException(status_code=502, detail=f"Failed to reach MCP runtime: {exc}") from exc

    try:
        response_output = upstream.json()
    except Exception:
        preview = upstream.text[:400] if upstream.text else ""
        response_output = {
            "status_code": upstream.status_code,
            "content_type": upstream.headers.get("content-type"),
            "body_preview": preview,
        }

    duration_ms = int((datetime.utcnow() - started).total_seconds() * 1000)
    if session is not None and user is not None:
        session.status = "active"
        session.call_count = (session.call_count or 0) + 1
        session.last_activity = datetime.utcnow()
        await log_tool_call(
            db=db,
            session_id=session.id,
            mcp_server_id=server.id,
            tenant_id=server_tenant_id,
            user_id=user["user_id"],
            user_email=user.get("email") or "",
            tool_name=tool_name,
            tool_input=tool_input or {"method": request.method, "path": request.url.path},
            tool_output=response_output,
            status="success" if upstream.status_code < 400 else "error",
            duration_ms=duration_ms,
        )

    return Response(
        content=upstream.content,
        status_code=upstream.status_code,
        headers=_proxy_response_headers(upstream.headers),
        media_type=upstream.headers.get("content-type"),
    )


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    return gateway_oauth_metadata()


@app.get("/.well-known/oauth-authorization-server/{resource_path:path}")
async def oauth_authorization_server_metadata_for_path(resource_path: str):
    return gateway_oauth_metadata()


@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    return gateway_oauth_metadata()


@app.get("/.well-known/openid-configuration/{resource_path:path}")
async def openid_configuration_for_path(resource_path: str):
    return gateway_oauth_metadata()


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_root(request: Request):
    base = settings.resolve_gateway_url(
        request_host=request.headers.get("host"),
        scheme=request.url.scheme,
    )
    return protected_resource_metadata(base)


@app.get("/.well-known/oauth-protected-resource/{resource_path:path}")
async def oauth_protected_resource_for_path(
    resource_path: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    # If the path refers to a specific MCP server, check if it's public.
    # Public MCP servers should NOT advertise OAuth so clients connect directly.
    import re as _re
    match = _re.match(r"^mcp/([^/]+)$", resource_path.strip("/"))
    if match:
        server_id = match.group(1)
        server = await db.get(MCPServer, server_id)
        if server and _mcp_access_mode(server) == "public":
            raise HTTPException(
                status_code=404,
                detail="This MCP server does not require authentication",
            )

    base = settings.resolve_gateway_url(
        request_host=request.headers.get("host"),
        scheme=request.url.scheme,
    )
    resource_url = f"{base}/{resource_path.lstrip('/')}"
    return protected_resource_metadata(resource_url)


@app.get("/authorize")
async def gateway_authorize(request: Request):
    query = request.query_params
    redirect_uri = query.get("redirect_uri")
    if not redirect_uri:
        raise HTTPException(status_code=400, detail="redirect_uri is required")

    txn_id = str(uuid4())
    await session_manager.redis.set(
        _oauth_txn_key(txn_id),
        json.dumps(
            {
                "redirect_uri": redirect_uri,
                "state": query.get("state") or "",
                "scope": query.get("scope") or "openid profile email",
                "code_challenge": query.get("code_challenge") or "",
                "code_challenge_method": query.get("code_challenge_method") or "S256",
            }
        ),
        ex=600,
    )

    redirect_url = build_google_login_url(
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
        state=_encode_google_bridge_state(
            {
                "provider": "google_direct",
                "flow": "mcp_client",
                "txn_id": txn_id,
            }
        ),
    )
    return RedirectResponse(redirect_url, status_code=307)


@app.post("/token")
async def gateway_token(request: Request):
    form = await request.form()
    grant_type = str(form.get("grant_type") or "")

    code = str(form.get("code") or "") or None
    redirect_uri = str(form.get("redirect_uri") or "") or None
    refresh_token = str(form.get("refresh_token") or "") or None
    code_verifier = str(form.get("code_verifier") or "") or None

    if grant_type == "authorization_code" and code:
        code_payload_raw = await session_manager.redis.get(_oauth_code_key(code))
        if code_payload_raw:
            await session_manager.redis.delete(_oauth_code_key(code))
            try:
                code_payload = json.loads(code_payload_raw)
            except json.JSONDecodeError as exc:
                raise HTTPException(status_code=400, detail="Invalid authorization code payload") from exc

            if redirect_uri != code_payload.get("redirect_uri"):
                raise HTTPException(status_code=400, detail="redirect_uri mismatch")
            if not _verify_pkce(
                code_verifier=code_verifier,
                code_challenge=code_payload.get("code_challenge"),
                code_challenge_method=code_payload.get("code_challenge_method"),
            ):
                raise HTTPException(status_code=400, detail="Invalid code_verifier")
            return code_payload["token_payload"]

    if grant_type == "refresh_token" and refresh_token:
        try:
            return await exchange_google_refresh_token(refresh_token)
        except httpx.HTTPStatusError as exc:
            detail = exc.response.text
            try:
                detail = exc.response.json()
            except Exception:
                pass
            raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc

    try:
        payload = await exchange_mcp_tokens(
            grant_type=grant_type,
            code=code,
            redirect_uri=redirect_uri,
            refresh_token=refresh_token,
            code_verifier=code_verifier,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json()
        except Exception:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc

    return payload


@app.post("/oauth/google/complete")
async def complete_google_client_oauth(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON body") from exc

    code = payload.get("code")
    raw_state = payload.get("state")
    redirect_uri = payload.get("redirect_uri") or settings.GOOGLE_REDIRECT_URI
    if not code:
        raise HTTPException(status_code=400, detail="code is required")

    state = _decode_google_bridge_state(raw_state)
    if state.get("flow") != "mcp_client" or not state.get("txn_id"):
        raise HTTPException(status_code=400, detail="Invalid MCP OAuth state")

    txn_raw = await session_manager.redis.get(_oauth_txn_key(state["txn_id"]))
    if not txn_raw:
        raise HTTPException(status_code=400, detail="OAuth transaction expired")
    await session_manager.redis.delete(_oauth_txn_key(state["txn_id"]))

    try:
        txn = json.loads(txn_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid OAuth transaction") from exc

    try:
        token_payload = await exchange_google_code(code=code, redirect_uri=redirect_uri)
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        try:
            detail = exc.response.json()
        except Exception:
            pass
        raise HTTPException(status_code=exc.response.status_code, detail=detail) from exc

    access_token = token_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token returned by Google")

    try:
        userinfo = await fetch_google_userinfo(access_token)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Google user info: {exc}") from exc

    identity = extract_google_identity(userinfo)
    if not identity.get("user_id"):
        raise HTTPException(status_code=400, detail="Google token missing subject claim")

    await upsert_platform_user(
        db,
        user_id=identity["user_id"],
        tenant_id=identity["tenant_id"],
        email=identity.get("email"),
        name=identity.get("name"),
        roles=[],
        provider="google",
        provider_user_id=identity["user_id"],
    )

    issued_code = str(uuid4())
    await session_manager.redis.set(
        _oauth_code_key(issued_code),
        json.dumps(
            {
                "redirect_uri": txn["redirect_uri"],
                "code_challenge": txn.get("code_challenge"),
                "code_challenge_method": txn.get("code_challenge_method"),
                "token_payload": {
                    "access_token": token_payload.get("access_token"),
                    "refresh_token": token_payload.get("refresh_token"),
                    "id_token": token_payload.get("id_token"),
                    "token_type": token_payload.get("token_type", "Bearer"),
                    "expires_in": token_payload.get("expires_in"),
                    "scope": token_payload.get("scope"),
                },
            }
        ),
        ex=600,
    )

    redirect_target = f"{txn['redirect_uri']}?code={quote(issued_code, safe='')}"
    if txn.get("state") is not None:
        redirect_target += f"&state={quote(txn.get('state') or '', safe='')}"
    return {"redirect_to": redirect_target}


@app.post("/register")
async def gateway_register(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    redirect_uris = body.get("redirect_uris") or []
    if not isinstance(redirect_uris, list):
        redirect_uris = []

    metadata = gateway_oauth_metadata()
    return JSONResponse(
        status_code=201,
        headers={
            "Cache-Control": "no-store",
            "Pragma": "no-cache",
        },
        content={
            "client_id": settings.KEYCLOAK_MCP_CLIENT_ID,
            "client_name": body.get("client_name") or "MCP Client",
            "redirect_uris": redirect_uris,
            "grant_types": metadata["grant_types_supported"],
            "response_types": metadata["response_types_supported"],
            "token_endpoint_auth_method": "none",
            "scope": "openid profile email",
            "client_id_issued_at": int(datetime.utcnow().timestamp()),
            "client_secret_expires_at": 0,
        },
    )


@app.api_route("/mcp/{server_id}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def mcp_endpoint(
    server_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(MCPServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return await _handle_mcp_request(server=server, request=request, db=db)


@app.api_route("/mcp/{tenant_slug}/{server_name}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
async def legacy_mcp_endpoint(
    tenant_slug: str,
    server_name: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    server = await _resolve_server_by_legacy_slug(
        db,
        tenant_slug=tenant_slug,
        server_name=server_name,
    )
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    target = mcp_host.build_gateway_url(
        server.id,
        request_host=request.headers.get("host"),
        scheme=request.url.scheme,
    )
    if request.url.query:
        target = f"{target}?{request.url.query}"
    return RedirectResponse(target, status_code=307)
