"""
GitHub OAuth import + deploy endpoints.

Flow:
1) User starts GitHub OAuth from the dashboard.
2) Backend exchanges the code and stores an encrypted access token.
3) User can keep multiple GitHub connections.
4) Each deploy uses a selected GitHub connection.
5) Deploy returns only the hosted MCP URL.
"""

from datetime import datetime
from pathlib import Path
import json
import secrets
import subprocess
import uuid
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import normalize_email_list, validate_group_ids
from app.auth.middleware import get_current_user
from app.auth.service import build_remote_mcp_client_config, decrypt_github_token, encrypt_github_token
from app.core.config import settings
from app.mcp.host import mcp_host
from app.mcp.session import session_manager
from app.models.database import GitHubConnection, MCPServer, get_db


router = APIRouter(prefix="/api/github", tags=["GitHub Integration"])

MCP_SERVERS_DIR = Path("/tmp/mcp-github-servers")
MCP_SERVERS_DIR.mkdir(exist_ok=True)

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_API_URL = "https://api.github.com"


class DeployFromGitHubRequest(BaseModel):
    connection_id: str
    repo_full_name: str
    entry_file: str
    server_name: str
    description: str = ""
    allowed_emails: list[str] = []
    allowed_group_ids: list[str] = []
    runtime_port: int = settings.MCP_DEFAULT_RUNTIME_PORT
    runtime_env: dict[str, str] = {}


class GitHubOAuthCallbackRequest(BaseModel):
    code: str
    state: str


def _append_log(server_id: str, msg: str):
    mcp_host.append_log(server_id, msg)


def _github_oauth_state_key(state: str) -> str:
    return f"mcp:github_oauth_state:{state}"


async def _new_github_oauth_state(user: dict) -> str:
    state = secrets.token_urlsafe(24)
    payload = {
        "user_id": user["user_id"],
        "tenant_id": user["tenant_id"],
        "created_at": datetime.utcnow().isoformat(),
    }
    await session_manager.redis.set(
        _github_oauth_state_key(state),
        json.dumps(payload),
        ex=1800,
    )
    return state


async def _consume_github_oauth_state(state: str) -> dict:
    key = _github_oauth_state_key(state)
    payload_raw = await session_manager.redis.get(key)
    if not payload_raw:
        raise HTTPException(status_code=400, detail="Expired GitHub OAuth state")
    await session_manager.redis.delete(key)
    try:
        return json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid GitHub OAuth state") from exc


def _github_oauth_redirect_uri() -> str:
    return settings.GITHUB_OAUTH_REDIRECT_URI


def _github_oauth_configured() -> bool:
    return bool(settings.GITHUB_OAUTH_CLIENT_ID and settings.GITHUB_OAUTH_CLIENT_SECRET)


def _build_github_oauth_url(state: str) -> str:
    query = urlencode(
        {
            "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
            "redirect_uri": _github_oauth_redirect_uri(),
            "scope": "repo read:user user:email",
            "state": state,
        }
    )
    return f"{GITHUB_AUTHORIZE_URL}?{query}"


async def _exchange_github_code(code: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
                "code": code,
                "redirect_uri": _github_oauth_redirect_uri(),
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        if payload.get("error"):
            raise HTTPException(status_code=400, detail=payload.get("error_description") or payload["error"])
        return payload


async def _github_get(token: str, path: str, *, params: dict | None = None) -> dict | list:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{GITHUB_API_URL}{path}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            params=params,
        )
        if resp.status_code >= 400:
            detail = None
            try:
                payload = resp.json()
                detail = payload.get("message") or payload.get("error")
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=400, detail=f"GitHub request failed for {path}: {detail}")
        return resp.json()


async def _active_connections(db: AsyncSession, user: dict) -> list[GitHubConnection]:
    result = await db.execute(
        select(GitHubConnection)
        .where(
            GitHubConnection.user_id == user["user_id"],
            GitHubConnection.tenant_id == user["tenant_id"],
            GitHubConnection.is_active.is_(True),
        )
        .order_by(GitHubConnection.updated_at.desc())
    )
    return list(result.scalars().all())


async def _resolve_connection(
    db: AsyncSession,
    user: dict,
    connection_id: str | None,
) -> GitHubConnection:
    if connection_id:
        connection = await db.get(GitHubConnection, connection_id)
        if (
            not connection
            or connection.user_id != user["user_id"]
            or connection.tenant_id != user["tenant_id"]
            or not connection.is_active
        ):
            raise HTTPException(status_code=404, detail="GitHub connection not found")
        return connection

    connections = await _active_connections(db, user)
    if not connections:
        raise HTTPException(status_code=400, detail="No active GitHub connections found")
    return connections[0]


async def _require_github_token(
    db: AsyncSession,
    user: dict,
    connection_id: str | None,
) -> tuple[GitHubConnection, str]:
    connection = await _resolve_connection(db, user, connection_id)
    try:
        token = decrypt_github_token(connection.token_encrypted)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Failed to decrypt stored GitHub token") from exc
    return connection, token


@router.get("/oauth/url")
async def github_oauth_url(user: dict = Depends(get_current_user)):
    if not _github_oauth_configured():
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")

    state = await _new_github_oauth_state(user)
    return {
        "login_url": _build_github_oauth_url(state),
        "redirect_uri": _github_oauth_redirect_uri(),
    }


@router.post("/oauth/callback")
async def github_oauth_callback(
    request: GitHubOAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    if not _github_oauth_configured():
        raise HTTPException(status_code=400, detail="GitHub OAuth is not configured")

    state_payload = await _consume_github_oauth_state(request.state)
    token_payload = await _exchange_github_code(request.code)
    access_token = token_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub did not return an access token")

    github_user = await _github_get(access_token, "/user")
    provider_user_id = str(github_user.get("id") or "")
    if not provider_user_id:
        raise HTTPException(status_code=400, detail="GitHub user id missing from OAuth response")

    result = await db.execute(
        select(GitHubConnection).where(
            GitHubConnection.user_id == state_payload["user_id"],
            GitHubConnection.tenant_id == state_payload["tenant_id"],
            GitHubConnection.provider_user_id == provider_user_id,
        )
    )
    existing = result.scalar_one_or_none()
    encrypted = encrypt_github_token(access_token)

    if existing:
        existing.github_username = github_user.get("login")
        existing.connection_name = github_user.get("login")
        existing.account_url = github_user.get("html_url")
        existing.token_encrypted = encrypted
        existing.is_active = True
        existing.updated_at = datetime.utcnow()
        connection = existing
    else:
        connection = GitHubConnection(
            user_id=state_payload["user_id"],
            tenant_id=state_payload["tenant_id"],
            provider_user_id=provider_user_id,
            github_username=github_user.get("login"),
            connection_name=github_user.get("login"),
            account_url=github_user.get("html_url"),
            token_encrypted=encrypted,
            is_active=True,
        )
        db.add(connection)
        await db.flush()

    return {
        "connection_id": connection.id,
        "github_username": connection.github_username,
        "account_url": connection.account_url,
    }


@router.get("/connections")
async def list_connections(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connections = await _active_connections(db, user)
    return {
        "connections": [
            {
                "id": connection.id,
                "github_username": connection.github_username,
                "connection_name": connection.connection_name or connection.github_username,
                "account_url": connection.account_url,
                "created_at": connection.created_at.isoformat() if connection.created_at else None,
                "updated_at": connection.updated_at.isoformat() if connection.updated_at else None,
            }
            for connection in connections
        ]
    }


@router.post("/disconnect/{connection_id}")
async def disconnect_github(
    connection_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connection = await _resolve_connection(db, user, connection_id)
    connection.is_active = False
    connection.updated_at = datetime.utcnow()
    return {"message": "GitHub disconnected", "connection_id": connection_id}


@router.get("/repos")
async def list_repos(
    connection_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connection, token = await _require_github_token(db, user, connection_id)
    repos = await _github_get(
        token,
        "/user/repos",
        params={"sort": "updated", "per_page": 100, "type": "all"},
    )

    filtered = [
        {
            "id": repo["id"],
            "full_name": repo["full_name"],
            "name": repo["name"],
            "description": repo.get("description", ""),
            "language": repo.get("language"),
            "updated_at": repo.get("updated_at"),
            "private": repo.get("private", False),
            "url": repo.get("html_url"),
            "connection_id": connection.id,
        }
        for repo in repos
        if repo.get("language") in ("Python", None)
    ]
    return {"repos": filtered, "connection_id": connection.id}


@router.get("/repos/{owner}/{repo}/files")
async def list_python_files(
    owner: str,
    repo: str,
    connection_id: str | None = Query(default=None),
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connection, token = await _require_github_token(db, user, connection_id)
    repo_payload = await _github_get(token, f"/repos/{owner}/{repo}")
    default_branch = repo_payload.get("default_branch") or "main"
    branch_payload = await _github_get(token, f"/repos/{owner}/{repo}/branches/{default_branch}")
    tree_sha = (
        branch_payload.get("commit", {})
        .get("commit", {})
        .get("tree", {})
        .get("sha")
    )
    if not tree_sha:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to resolve tree SHA for {owner}/{repo} branch {default_branch}",
        )
    payload = await _github_get(
        token,
        f"/repos/{owner}/{repo}/git/trees/{tree_sha}",
        params={"recursive": "1"},
    )

    tree = payload.get("tree", [])
    py_files = [
        item["path"]
        for item in tree
        if item.get("type") == "blob" and item.get("path", "").endswith(".py")
    ]
    suggestions = [f for f in py_files if any(word in f.lower() for word in ("main", "server", "app"))]

    return {
        "connection_id": connection.id,
        "python_files": py_files,
        "suggested_entry_points": suggestions,
    }


@router.post("/deploy")
async def deploy_from_github(
    request: DeployFromGitHubRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    connection, token = await _require_github_token(db, user, request.connection_id)

    server_id = str(uuid.uuid4())
    tenant_id = user["tenant_id"]
    server_dir = MCP_SERVERS_DIR / server_id
    server_dir.mkdir(exist_ok=True)

    try:
        _append_log(server_id, f"Cloning repo: {request.repo_full_name}")
        repo_url = f"https://oauth2:{token}@github.com/{request.repo_full_name}.git"
        clone_result = subprocess.run(
            ["git", "clone", repo_url, str(server_dir)],
            capture_output=True,
            text=True,
            timeout=90,
        )
        if clone_result.returncode != 0:
            _append_log(server_id, f"Clone failed: {clone_result.stderr.strip()}")
            raise HTTPException(status_code=400, detail="Failed to clone repository")
        _append_log(server_id, "Repo cloned successfully")

        entry_path = server_dir / request.entry_file
        if not entry_path.exists():
            _append_log(server_id, f"Entry file not found: {request.entry_file}")
            raise HTTPException(status_code=400, detail="Selected entry file not found in repository")
        _append_log(server_id, f"Entry file found: {request.entry_file}")

        try:
            allowed_group_ids = await validate_group_ids(
                db,
                tenant_id=tenant_id,
                group_ids=request.allowed_group_ids,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        runtime = await mcp_host.deploy_python_workspace(
            server_id=server_id,
            workspace_dir=server_dir,
            entry_file=request.entry_file,
            runtime_port=request.runtime_port,
            runtime_env=request.runtime_env,
        )

        endpoint_url = mcp_host.build_gateway_url(server_id)
        _append_log(server_id, f"Endpoint URL: {endpoint_url}")
        client_config = build_remote_mcp_client_config(request.server_name, endpoint_url)

        db.add(
            MCPServer(
                id=server_id,
                tenant_id=tenant_id,
                deployed_by_user_id=user["user_id"],
                name=request.server_name,
                description=request.description or f"Deployed from {request.repo_full_name}",
                endpoint_url=endpoint_url,
                storage_path=str(entry_path),
                status="running",
                config={
                    "source_type": "github",
                    "github_repo": request.repo_full_name,
                    "github_connection_id": connection.id,
                    "github_username": connection.github_username,
                    "entry_file": request.entry_file,
                    "runtime_port": request.runtime_port,
                    "owner_email": (user.get("email") or "").strip().lower() or None,
                    "allowed_user_emails": normalize_email_list(request.allowed_emails),
                    "allowed_group_ids": allowed_group_ids,
                    "runtime_env_keys": sorted(request.runtime_env.keys()),
                    "mcp_access_mode": "public",
                    "runtime": runtime,
                    "client_config": client_config,
                },
            )
        )

        return {
            "server_id": server_id,
            "status": "running",
            "endpoint_url": endpoint_url,
            "client_config": client_config,
            "allowed_emails": normalize_email_list(request.allowed_emails),
            "allowed_group_ids": allowed_group_ids,
            "message": f"'{request.server_name}' is live",
        }
    except HTTPException:
        raise
    except Exception as exc:
        _append_log(server_id, f"Deployment failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Deployment failed: {exc}") from exc


@router.get("/logs/{server_id}")
async def get_logs(
    server_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(MCPServer, server_id)
    if not server or (
        "admin" not in user.get("roles", [])
        and server.tenant_id != user["tenant_id"]
    ):
        raise HTTPException(status_code=404, detail="Server not found")

    status = await mcp_host.get_status(server.config or {})
    server.status = status
    logs = await mcp_host.get_logs(server_id, server.config or {})

    return {
        "server_id": server_id,
        "status": status,
        "logs": logs,
        "log_count": len(logs),
    }


@router.post("/stop/{server_id}")
async def stop_server(
    server_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(MCPServer, server_id)
    if not server or (
        "admin" not in user.get("roles", [])
        and server.tenant_id != user["tenant_id"]
    ):
        raise HTTPException(status_code=404, detail="Server not found")

    await mcp_host.stop(server.config or {})
    _append_log(server_id, "Server stopped by user")
    server.status = "stopped"
    server.updated_at = datetime.utcnow()
    return {"message": "Server stopped", "server_id": server_id}
