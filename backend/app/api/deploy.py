"""
MCP DEPLOY API

POST /api/mcp/deploy     — Upload MCP code → get a URL
GET  /api/mcp/           — List all deployed MCPs for tenant
GET  /api/mcp/{id}       — Get MCP server details
DELETE /api/mcp/{id}     — Stop and remove an MCP server
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.database import get_db, MCPServer
from app.auth.middleware import get_current_user
from app.auth.service import build_remote_mcp_client_config
from app.mcp.host import mcp_host
import uuid
import re

router = APIRouter(prefix="/api/mcp", tags=["MCP Management"])


class DeployRequest(BaseModel):
    name: str
    description: str = ""
    server_code: str       # MCP Python code as string


class AccessUpdateRequest(BaseModel):
    emails: list[str] = []


class MCPServerResponse(BaseModel):
    id: str
    name: str
    description: str
    endpoint_url: str
    status: str
    config: dict | None = None

    class Config:
        from_attributes = True


def _normalize_allowed_emails(emails: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for email in emails or []:
        cleaned = re.sub(r"\s+", "", (email or "").strip().lower())
        if cleaned and "@" in cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def _server_access_payload(server: MCPServer) -> dict:
    config = server.config or {}
    return {
        "server_id": server.id,
        "allowed_emails": config.get("allowed_user_emails", []),
        "owner_email": config.get("owner_email"),
    }


@router.post("/deploy")
async def deploy_mcp_server(
    request: DeployRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Deploy an MCP server.
    Returns a URL the user can plug into Claude Code.
    URL is OAuth-protected — only authenticated users can access it.
    """
    tenant_id = user.get("tenant_id") or user.get("user_id")

    # Deploy the MCP server
    result = await mcp_host.deploy(
        tenant_id=tenant_id,
        server_name=request.name,
        server_code=request.server_code,
    )

    # Save to database
    server = MCPServer(
        id=result["server_id"],
        tenant_id=tenant_id,
        name=request.name,
        description=request.description,
        endpoint_url=result["endpoint_url"],
        storage_path=result["storage_path"],
        status=result["status"],
    )
    db.add(server)
    await db.commit()

    return {
        "message": "MCP server deployed successfully",
        "server_id": result["server_id"],
        "endpoint_url": result["endpoint_url"],
        "client_config": build_remote_mcp_client_config(request.name, result["endpoint_url"]),
        "instructions": (
            f"Add this URL to Claude Code: {result['endpoint_url']}\n"
            f"Use your platform OAuth credentials to authenticate."
        ),
    }


@router.get("/", response_model=list[MCPServerResponse])
async def list_mcp_servers(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all MCP servers for the current tenant"""
    tenant_id = user.get("tenant_id") or user.get("user_id")
    query = select(MCPServer)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == tenant_id)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{server_id}")
async def get_mcp_server(
    server_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific MCP server"""
    tenant_id = user.get("tenant_id") or user.get("user_id")
    query = select(MCPServer).where(MCPServer.id == server_id)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == tenant_id)
    result = await db.execute(query)
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server


@router.delete("/{server_id}")
async def stop_mcp_server(
    server_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stop and remove an MCP server"""
    tenant_id = user.get("tenant_id") or user.get("user_id")
    query = select(MCPServer).where(MCPServer.id == server_id)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == tenant_id)
    result = await db.execute(query)
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="Not found")

    await mcp_host.stop(server_id)
    server.status = "stopped"
    await db.commit()
    return {"message": "MCP server stopped"}


@router.get("/{server_id}/access")
async def get_mcp_server_access(
    server_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MCPServer).where(MCPServer.id == server_id)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == (user.get("tenant_id") or user.get("user_id")))
    result = await db.execute(query)
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return _server_access_payload(server)


@router.post("/{server_id}/access")
async def update_mcp_server_access(
    server_id: str,
    request: AccessUpdateRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MCPServer).where(MCPServer.id == server_id)
    if "admin" not in user.get("roles", []):
        query = query.where(MCPServer.tenant_id == (user.get("tenant_id") or user.get("user_id")))
    result = await db.execute(query)
    server = result.scalar_one_or_none()
    if not server:
        raise HTTPException(status_code=404, detail="MCP server not found")

    config = server.config or {}
    config["allowed_user_emails"] = _normalize_allowed_emails(request.emails)
    if user.get("email") and not config.get("owner_email"):
        config["owner_email"] = user["email"].strip().lower()
    server.config = config

    return {
        "message": "Server access updated",
        **_server_access_payload(server),
        "client_config": build_remote_mcp_client_config(server.name, server.endpoint_url or ""),
    }
