from datetime import datetime
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.mcp.session import session_manager
from app.models.database import MCPSession, MCPServer, get_db


router = APIRouter(prefix="/api/sessions", tags=["Sessions"])


class StartSessionRequest(BaseModel):
    mcp_server_id: str


@router.post("/start")
async def start_session(
    request: StartSessionRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    server = await db.get(MCPServer, request.mcp_server_id)
    if not server or server.tenant_id != user["tenant_id"]:
        raise HTTPException(status_code=404, detail="MCP server not found")

    session = MCPSession(
        id=str(uuid.uuid4()),
        mcp_server_id=request.mcp_server_id,
        tenant_id=user["tenant_id"],
        user_id=user["user_id"],
        user_email=user.get("email"),
        user_roles=user.get("roles", []),
        status="active",
        started_at=datetime.utcnow(),
        last_activity=datetime.utcnow(),
    )
    db.add(session)
    await db.flush()

    redis_synced = True
    try:
        await session_manager.create_session(
            session_id=session.id,
            user_id=user["user_id"],
            user_email=user.get("email") or "",
            tenant_id=user["tenant_id"],
            mcp_server_id=request.mcp_server_id,
            roles=user.get("roles", []),
        )
    except Exception:
        redis_synced = False

    return {
        "session_id": session.id,
        "message": "Session started",
        "mcp_server_id": request.mcp_server_id,
        "redis_synced": redis_synced,
    }


@router.get("/")
async def list_my_sessions(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(MCPSession).order_by(MCPSession.started_at.desc())
    if "admin" in user.get("roles", []):
        result = await db.execute(query)
    else:
        result = await db.execute(
            query.where(
                MCPSession.tenant_id == user["tenant_id"],
                MCPSession.user_id == user["user_id"],
            )
        )
    sessions = result.scalars().all()
    return {
        "sessions": [
            {
                "id": s.id,
                "mcp_server_id": s.mcp_server_id,
                "user_email": s.user_email,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "last_activity": s.last_activity.isoformat() if s.last_activity else None,
                "call_count": s.call_count,
            }
            for s in sessions
        ],
        "count": len(sessions),
    }


@router.get("/{session_id}")
async def get_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(MCPSession, session_id)
    if (
        not session
        or (
            "admin" not in user.get("roles", [])
            and (
                session.tenant_id != user["tenant_id"]
                or session.user_id != user["user_id"]
            )
        )
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    return {
        "id": session.id,
        "mcp_server_id": session.mcp_server_id,
        "tenant_id": session.tenant_id,
        "user_id": session.user_id,
        "user_email": session.user_email,
        "user_roles": session.user_roles,
        "status": session.status,
        "call_count": session.call_count,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "last_activity": session.last_activity.isoformat() if session.last_activity else None,
    }


@router.post("/{session_id}/close")
async def close_session(
    session_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = await db.get(MCPSession, session_id)
    if (
        not session
        or (
            "admin" not in user.get("roles", [])
            and (
                session.tenant_id != user["tenant_id"]
                or session.user_id != user["user_id"]
            )
        )
    ):
        raise HTTPException(status_code=403, detail="Access denied")

    session.status = "closed"
    session.last_activity = datetime.utcnow()

    redis_synced = True
    try:
        await session_manager.close_session(
            tenant_id=session.tenant_id,
            session_id=session_id,
            user_id=session.user_id,
        )
    except Exception:
        redis_synced = False

    return {"message": "Session closed", "redis_synced": redis_synced}
