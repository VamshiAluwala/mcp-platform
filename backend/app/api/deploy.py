"""
MCP deploy and import APIs.

- Deploy inline Python MCP code into a Docker container.
- Import external/public MCP endpoints via JSON config.
- Manage per-server access policies and logs.
"""

from __future__ import annotations

from pathlib import Path
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import (
    build_server_access_payload,
    email_allowed_via_groups,
    normalize_email_list,
    normalize_group_ids,
    validate_group_ids,
)
from app.auth.middleware import get_current_user
from app.auth.service import build_remote_mcp_client_config
from app.core.config import settings
from app.mcp.host import mcp_host
from app.models.database import MCPServer, get_db


router = APIRouter(prefix="/api/mcp", tags=["MCP Management"])


class DeployRequest(BaseModel):
    name: str
    description: str = ""
    server_code: str
    entry_file: str = "server.py"
    requirements_txt: str | None = None
    runtime_port: int = Field(default=settings.MCP_DEFAULT_RUNTIME_PORT, ge=1, le=65535)
    allowed_emails: list[str] = []
    allowed_group_ids: list[str] = []
    runtime_env: dict[str, str] = {}


class ExternalImportRequest(BaseModel):
    name: str
    description: str = ""
    json_config: dict
    allowed_emails: list[str] = []
    allowed_group_ids: list[str] = []


class AccessUpdateRequest(BaseModel):
    emails: list[str] = []
    group_ids: list[str] = []


class MCPServerResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    endpoint_url: str | None = None
    status: str
    config: dict | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _tenant_id_for(user: dict) -> str:
    return user.get("tenant_id") or user.get("user_id")


def _server_query_for_user(user: dict):
    query = select(MCPServer)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == _tenant_id_for(user))
    return query


def _server_allowed_emails(server: MCPServer) -> list[str]:
    config = server.config or {}
    allowed = normalize_email_list(config.get("allowed_user_emails", []))
    owner_email = (config.get("owner_email") or "").strip().lower()
    if owner_email and owner_email not in allowed:
        allowed.append(owner_email)
    return allowed


async def _user_can_view_server(
    db: AsyncSession,
    *,
    server: MCPServer,
    user: dict,
) -> bool:
    if "admin" in user.get("roles", []):
        return True

    if server.tenant_id == _tenant_id_for(user):
        return True

    email = (user.get("email") or "").strip().lower()
    if email and email in _server_allowed_emails(server):
        return True

    return await email_allowed_via_groups(
        db,
        group_ids=normalize_group_ids((server.config or {}).get("allowed_group_ids", [])),
        email=email,
    )


async def _load_server_for_user(
    db: AsyncSession,
    *,
    server_id: str,
    user: dict,
) -> MCPServer:
    query = _server_query_for_user(user).where(MCPServer.id == server_id)
    result = await db.execute(query)
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


async def _load_viewable_server_for_user(
    db: AsyncSession,
    *,
    server_id: str,
    user: dict,
) -> MCPServer:
    server = await db.get(MCPServer, server_id)
    if not server or not await _user_can_view_server(db, server=server, user=user):
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


def _external_target_from_json(config: dict) -> tuple[str, dict, int]:
    upstream_url = (
        config.get("upstream_url")
        or config.get("serverUrl")
        or config.get("url")
    )
    if not upstream_url and isinstance(config.get("mcpServers"), dict):
        first_server = next(iter(config["mcpServers"].values()), {})
        if isinstance(first_server, dict):
            upstream_url = first_server.get("serverUrl") or first_server.get("url")

    if not upstream_url or not isinstance(upstream_url, str):
        raise HTTPException(
            status_code=400,
            detail="JSON config must include upstream_url or mcpServers.*.serverUrl",
        )

    headers = config.get("headers") or {}
    if not isinstance(headers, dict):
        raise HTTPException(status_code=400, detail="json_config.headers must be an object")

    timeout_seconds = config.get("timeout_seconds") or 30
    try:
        timeout_seconds = int(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="timeout_seconds must be an integer") from exc

    return upstream_url, headers, timeout_seconds


async def _validate_access_groups(
    db: AsyncSession,
    *,
    tenant_id: str,
    group_ids: list[str],
) -> list[str]:
    try:
        return await validate_group_ids(db, tenant_id=tenant_id, group_ids=group_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _base_server_config(
    *,
    source_type: str,
    owner_email: str | None,
    allowed_emails: list[str],
    allowed_group_ids: list[str],
    runtime: dict,
    client_config: dict,
    extra: dict | None = None,
) -> dict:
    config = {
        "source_type": source_type,
        "owner_email": owner_email,
        "allowed_user_emails": allowed_emails,
        "allowed_group_ids": allowed_group_ids,
        "runtime": runtime,
        "client_config": client_config,
    }
    if extra:
        config.update(extra)
    return config


def _canonical_endpoint_url(server: MCPServer, *, request_host: str | None = None, scheme: str | None = None) -> str:
    return mcp_host.build_gateway_url(server.id, request_host=request_host, scheme=scheme)


def _ensure_server_gateway_config(server: MCPServer, *, request_host: str | None = None, scheme: str | None = None) -> None:
    canonical_url = _canonical_endpoint_url(server, request_host=request_host, scheme=scheme)
    if server.endpoint_url != canonical_url:
        server.endpoint_url = canonical_url

    config = server.config or {}
    config["client_config"] = build_remote_mcp_client_config(server.name, canonical_url)
    server.config = config


@router.post("/deploy")
async def deploy_mcp_server(
    request: DeployRequest,
    raw_request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id_for(user)
    server_id = str(uuid.uuid4())
    owner_email = (user.get("email") or "").strip().lower() or None
    allowed_emails = normalize_email_list(request.allowed_emails)
    allowed_group_ids = await _validate_access_groups(
        db,
        tenant_id=tenant_id,
        group_ids=request.allowed_group_ids,
    )

    workspace_dir = await mcp_host.provision_inline_code(
        server_id=server_id,
        server_code=request.server_code,
        entry_file=request.entry_file,
        requirements_txt=request.requirements_txt,
    )
    runtime = await mcp_host.deploy_python_workspace(
        server_id=server_id,
        workspace_dir=workspace_dir,
        entry_file=request.entry_file,
        runtime_port=request.runtime_port,
        runtime_env=request.runtime_env,
    )

    req_host = raw_request.headers.get("host")
    req_scheme = raw_request.url.scheme
    endpoint_url = mcp_host.build_gateway_url(server_id, request_host=req_host, scheme=req_scheme)
    client_config = build_remote_mcp_client_config(request.name, endpoint_url)
    server = MCPServer(
        id=server_id,
        tenant_id=tenant_id,
        deployed_by_user_id=user["user_id"],
        name=request.name,
        description=request.description,
        endpoint_url=endpoint_url,
        storage_path=str(Path(workspace_dir) / request.entry_file),
        status="running",
        config=_base_server_config(
            source_type="manual_code",
            owner_email=owner_email,
            allowed_emails=allowed_emails,
            allowed_group_ids=allowed_group_ids,
            runtime=runtime,
            client_config=client_config,
            extra={
                "entry_file": request.entry_file,
                "runtime_port": request.runtime_port,
                "runtime_env_keys": sorted(request.runtime_env.keys()),
            },
        ),
    )
    db.add(server)
    await db.flush()

    return {
        "message": "MCP server deployed successfully",
        "server_id": server_id,
        "endpoint_url": endpoint_url,
        "client_config": client_config,
        "allowed_emails": allowed_emails,
        "allowed_group_ids": allowed_group_ids,
    }


@router.post("/import")
async def import_external_mcp(
    request: ExternalImportRequest,
    raw_request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id_for(user)
    server_id = str(uuid.uuid4())
    owner_email = (user.get("email") or "").strip().lower() or None
    allowed_emails = normalize_email_list(request.allowed_emails)
    allowed_group_ids = await _validate_access_groups(
        db,
        tenant_id=tenant_id,
        group_ids=request.allowed_group_ids,
    )

    upstream_url, headers, timeout_seconds = _external_target_from_json(request.json_config)
    runtime = await mcp_host.register_external_target(
        server_id=server_id,
        upstream_url=upstream_url,
        headers=headers,
        timeout_seconds=timeout_seconds,
    )
    req_host = raw_request.headers.get("host")
    req_scheme = raw_request.url.scheme
    endpoint_url = mcp_host.build_gateway_url(server_id, request_host=req_host, scheme=req_scheme)
    client_config = build_remote_mcp_client_config(request.name, endpoint_url)

    db.add(
        MCPServer(
            id=server_id,
            tenant_id=tenant_id,
            deployed_by_user_id=user["user_id"],
            name=request.name,
            description=request.description or f"External MCP imported from {upstream_url}",
            endpoint_url=endpoint_url,
            storage_path=upstream_url,
            status="running",
            config=_base_server_config(
                source_type="external",
                owner_email=owner_email,
                allowed_emails=allowed_emails,
                allowed_group_ids=allowed_group_ids,
                runtime=runtime,
                client_config=client_config,
                extra={
                    "import_config": request.json_config,
                },
            ),
        )
    )

    return {
        "message": "External MCP imported successfully",
        "server_id": server_id,
        "endpoint_url": endpoint_url,
        "client_config": client_config,
        "allowed_emails": allowed_emails,
        "allowed_group_ids": allowed_group_ids,
        "upstream_url": upstream_url,
    }


@router.get("/", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = request.headers.get("host")
    req_scheme = request.url.scheme
    result = await db.execute(select(MCPServer).order_by(MCPServer.created_at.desc()))
    all_servers = list(result.scalars().all())
    servers: list[MCPServer] = []
    for server in all_servers:
        if await _user_can_view_server(db, server=server, user=user):
            servers.append(server)

    payload: list[MCPServerResponse] = []
    for server in servers:
        _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
        server.status = await mcp_host.get_status(server.config or {})
        payload.append(
            MCPServerResponse(
                id=server.id,
                name=server.name,
                description=server.description,
                endpoint_url=server.endpoint_url,
                status=server.status,
                config=server.config or {},
                created_at=server.created_at.isoformat() if server.created_at else None,
                updated_at=server.updated_at.isoformat() if server.updated_at else None,
            )
        )
    return payload


@router.get("/{server_id}")
async def get_mcp_server(
    server_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = request.headers.get("host")
    req_scheme = request.url.scheme
    server = await _load_viewable_server_for_user(db, server_id=server_id, user=user)
    _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
    server.status = await mcp_host.get_status(server.config or {})
    return {
        "id": server.id,
        "name": server.name,
        "description": server.description,
        "endpoint_url": server.endpoint_url,
        "status": server.status,
        "config": server.config or {},
        "created_at": server.created_at.isoformat() if server.created_at else None,
        "updated_at": server.updated_at.isoformat() if server.updated_at else None,
    }


@router.delete("/{server_id}")
async def stop_mcp_server(
    server_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = request.headers.get("host")
    req_scheme = request.url.scheme
    server = await _load_server_for_user(db, server_id=server_id, user=user)
    _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
    await mcp_host.stop(server.config or {})
    server.status = "stopped"
    return {"message": "MCP server stopped", "server_id": server_id}


@router.get("/{server_id}/logs")
async def get_mcp_server_logs(
    server_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = request.headers.get("host")
    req_scheme = request.url.scheme
    server = await _load_viewable_server_for_user(db, server_id=server_id, user=user)
    _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
    status = await mcp_host.get_status(server.config or {})
    server.status = status
    logs = await mcp_host.get_logs(server_id, server.config or {})
    return {
        "server_id": server_id,
        "status": status,
        "logs": logs,
        "log_count": len(logs),
    }


@router.get("/{server_id}/access")
async def get_mcp_server_access(
    server_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = request.headers.get("host")
    req_scheme = request.url.scheme
    server = await _load_viewable_server_for_user(db, server_id=server_id, user=user)
    _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
    return await build_server_access_payload(db, server)


@router.post("/{server_id}/access")
async def update_mcp_server_access(
    server_id: str,
    request: AccessUpdateRequest,
    raw_request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    req_host = raw_request.headers.get("host")
    req_scheme = raw_request.url.scheme
    server = await _load_server_for_user(db, server_id=server_id, user=user)
    _ensure_server_gateway_config(server, request_host=req_host, scheme=req_scheme)
    allowed_group_ids = await _validate_access_groups(
        db,
        tenant_id=server.tenant_id,
        group_ids=request.group_ids,
    )

    config = server.config or {}
    config["allowed_user_emails"] = normalize_email_list(request.emails)
    config["allowed_group_ids"] = allowed_group_ids
    if user.get("email") and not config.get("owner_email"):
        config["owner_email"] = user["email"].strip().lower()
    config["client_config"] = build_remote_mcp_client_config(server.name, server.endpoint_url or _canonical_endpoint_url(server, request_host=req_host, scheme=req_scheme))
    server.config = config

    return {
        "message": "Server access updated",
        **await build_server_access_payload(db, server),
        "client_config": config["client_config"],
    }
