"""
AUDIT ENGINE

Every single MCP tool call is logged here.
- WHO called (user_id, email, tenant)
- WHAT tool (tool_name, inputs, outputs)
- WHEN (timestamp, duration)
- RESULT (success, error, denied)

This is your compliance + observability engine.
Required for SOC2, GDPR, enterprise sales.
"""

from datetime import datetime
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.models.database import AuditLog


async def log_tool_call(
    db: AsyncSession,
    session_id: str,
    mcp_server_id: str,
    tenant_id: str,
    user_id: str,
    user_email: str,
    tool_name: str,
    tool_input: dict,
    tool_output: dict,
    status: str,
    duration_ms: int,
):
    """
    Write an immutable audit log entry for every MCP tool call.
    Called BEFORE returning response to user — always logged.
    """
    log = AuditLog(
        id=str(uuid.uuid4()),
        session_id=session_id,
        mcp_server_id=mcp_server_id,
        tenant_id=tenant_id,
        user_id=user_id,
        user_email=user_email,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        status=status,
        duration_ms=str(duration_ms),
        called_at=datetime.utcnow(),
    )
    db.add(log)
    await db.flush()
    return log


async def get_audit_logs(
    db: AsyncSession,
    tenant_id: str | None,
    user_id: str = None,
    mcp_server_id: str = None,
    limit: int = 100,
) -> list[AuditLog]:
    """
    Fetch audit logs for a tenant.
    Can filter by user or specific MCP server.
    """
    query = select(AuditLog).order_by(desc(AuditLog.called_at)).limit(limit)

    if tenant_id:
        query = query.where(AuditLog.tenant_id == tenant_id)

    if user_id:
        query = query.where(AuditLog.user_id == user_id)

    if mcp_server_id:
        query = query.where(AuditLog.mcp_server_id == mcp_server_id)

    result = await db.execute(query)
    return result.scalars().all()
