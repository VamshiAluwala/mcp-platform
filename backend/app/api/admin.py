from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException

from app.auth.middleware import get_current_user
from app.models.database import AuditLog, MCPSession, MCPServer, PlatformUser, get_db


router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _require_admin(user: dict) -> None:
    if "admin" not in user.get("roles", []):
        raise HTTPException(status_code=403, detail="Admin access required")


@router.get("/users")
async def list_platform_users(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    _require_admin(user)

    users_result = await db.execute(
        select(PlatformUser).order_by(
            PlatformUser.last_login_at.desc().nullslast(),
            PlatformUser.created_at.desc(),
        )
    )
    users = list(users_result.scalars().all())

    session_counts_result = await db.execute(
        select(
            MCPSession.user_id,
            func.count(MCPSession.id),
            func.coalesce(func.sum(MCPSession.call_count), 0),
        ).group_by(MCPSession.user_id)
    )
    session_counts = {
        row[0]: {"sessions": int(row[1] or 0), "calls": int(row[2] or 0)}
        for row in session_counts_result.all()
    }

    active_sessions_result = await db.execute(
        select(MCPSession.user_id, func.count(MCPSession.id))
        .where(MCPSession.status == "active")
        .group_by(MCPSession.user_id)
    )
    active_sessions = {row[0]: int(row[1] or 0) for row in active_sessions_result.all()}

    server_counts_result = await db.execute(
        select(MCPServer.deployed_by_user_id, func.count(MCPServer.id))
        .where(MCPServer.deployed_by_user_id.is_not(None))
        .group_by(MCPServer.deployed_by_user_id)
    )
    deployed_servers = {row[0]: int(row[1] or 0) for row in server_counts_result.all()}

    last_activity_result = await db.execute(
        select(AuditLog.user_id, func.max(AuditLog.called_at)).group_by(AuditLog.user_id)
    )
    last_activity = {row[0]: row[1] for row in last_activity_result.all()}

    return {
        "count": len(users),
        "users": [
            {
                "id": item.id,
                "tenant_id": item.tenant_id,
                "email": item.email,
                "name": item.name,
                "roles": item.roles or [],
                "provider": item.provider,
                "is_active": item.is_active,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                "last_login_at": item.last_login_at.isoformat() if item.last_login_at else None,
                "active_sessions": active_sessions.get(item.id, 0),
                "total_sessions": session_counts.get(item.id, {}).get("sessions", 0),
                "total_calls": session_counts.get(item.id, {}).get("calls", 0),
                "deployed_servers": deployed_servers.get(item.id, 0),
                "last_activity_at": (
                    last_activity[item.id].isoformat()
                    if item.id in last_activity and last_activity[item.id]
                    else None
                ),
            }
            for item in users
        ],
    }
