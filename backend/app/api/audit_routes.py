from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.audit import get_audit_logs
from app.auth.middleware import get_current_user
from app.models.database import get_db


router = APIRouter(prefix="/api/audit", tags=["Audit Logs"])


@router.get("/")
async def list_audit_logs(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Query(default=None),
    mcp_server_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
):
    tenant_filter = None if "admin" in user.get("roles", []) else user["tenant_id"]
    logs = await get_audit_logs(
        db=db,
        tenant_id=tenant_filter,
        user_id=user_id,
        mcp_server_id=mcp_server_id,
        limit=limit,
    )
    return {
        "count": len(logs),
        "items": [
            {
                "id": log.id,
                "session_id": log.session_id,
                "mcp_server_id": log.mcp_server_id,
                "tenant_id": log.tenant_id,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "tool_name": log.tool_name,
                "tool_input": log.tool_input,
                "tool_output": log.tool_output,
                "status": log.status,
                "duration_ms": log.duration_ms,
                "called_at": log.called_at.isoformat() if log.called_at else None,
            }
            for log in logs
        ],
    }
