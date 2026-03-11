"""
MCP SESSION MANAGER

Handles multi-session tracking per user.
Each user can have multiple parallel MCP sessions.
Each session is isolated — no cross-session data leakage.
"""

import json
import uuid
from datetime import datetime
import redis.asyncio as aioredis
from app.core.config import settings


class SessionManager:
    def __init__(self):
        self.redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    def _session_key(self, tenant_id: str, session_id: str) -> str:
        return f"mcp:session:{tenant_id}:{session_id}"

    def _user_sessions_key(self, tenant_id: str, user_id: str) -> str:
        return f"mcp:user_sessions:{tenant_id}:{user_id}"

    async def create_session(
        self,
        user_id: str,
        user_email: str,
        tenant_id: str,
        mcp_server_id: str,
        roles: list,
        session_id: str | None = None,
    ) -> dict:
        """
        Create a new isolated session for a user connecting to an MCP server.
        Each session gets its own Redis key — fully isolated.
        """
        session_id = session_id or str(uuid.uuid4())
        session = {
            "id": session_id,
            "user_id": user_id,
            "user_email": user_email,
            "tenant_id": tenant_id,
            "mcp_server_id": mcp_server_id,
            "roles": json.dumps(roles),
            "status": "active",
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "call_count": "0",
        }

        # Store session in Redis (expires in 8 hours)
        await self.redis.hset(self._session_key(tenant_id, session_id), mapping=session)
        await self.redis.expire(self._session_key(tenant_id, session_id), 28800)

        # Track all sessions for this user
        await self.redis.sadd(self._user_sessions_key(tenant_id, user_id), session_id)

        return session

    async def get_session(self, tenant_id: str, session_id: str) -> dict | None:
        """Get session data by ID"""
        data = await self.redis.hgetall(self._session_key(tenant_id, session_id))
        return data if data else None

    async def update_activity(self, tenant_id: str, session_id: str):
        """Update last activity timestamp + increment call count"""
        await self.redis.hset(
            self._session_key(tenant_id, session_id),
            mapping={
                "last_activity": datetime.utcnow().isoformat(),
            }
        )
        await self.redis.hincrby(self._session_key(tenant_id, session_id), "call_count", 1)

    async def get_user_sessions(self, tenant_id: str, user_id: str) -> list[dict]:
        """Get all active sessions for a user"""
        session_ids = await self.redis.smembers(self._user_sessions_key(tenant_id, user_id))
        sessions = []
        for sid in session_ids:
            session = await self.get_session(tenant_id, sid)
            if session:
                sessions.append(session)
        return sessions

    async def close_session(self, tenant_id: str, session_id: str, user_id: str):
        """Close a session and remove from user's active sessions"""
        await self.redis.hset(
            self._session_key(tenant_id, session_id),
            "status", "closed"
        )
        await self.redis.srem(self._user_sessions_key(tenant_id, user_id), session_id)

    async def validate_session_ownership(
        self, session_id: str, user_id: str, tenant_id: str
    ) -> bool:
        """
        Critical security check:
        Ensure user can only access THEIR OWN sessions.
        Prevents cross-tenant / cross-user session hijacking.
        """
        session = await self.get_session(tenant_id, session_id)
        if not session:
            return False
        return (
            session.get("user_id") == user_id
            and session.get("tenant_id") == tenant_id
        )


# Singleton instance
session_manager = SessionManager()
