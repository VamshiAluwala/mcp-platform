from datetime import datetime
import re
import uuid

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.sql_factory import engine, get_db


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", (value or "").strip().lower()).strip("-")
    return cleaned or f"tenant-{uuid.uuid4().hex[:8]}"


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PlatformUser(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True)  # Keycloak subject
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    roles: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String, default="keycloak")
    provider_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class GitHubConnection(Base):
    __tablename__ = "github_connections"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    provider_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    github_username: Mapped[str | None] = mapped_column(String, nullable=True)
    connection_name: Mapped[str | None] = mapped_column(String, nullable=True)
    account_url: Mapped[str | None] = mapped_column(String, nullable=True)
    token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    deployed_by_user_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )


class MCPSession(Base):
    __tablename__ = "mcp_sessions"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    mcp_server_id: Mapped[str] = mapped_column(String, ForeignKey("mcp_servers.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    user_email: Mapped[str | None] = mapped_column(String, nullable=True)
    user_roles: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String, default="active")
    call_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_activity: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    session_id: Mapped[str | None] = mapped_column(String, ForeignKey("mcp_sessions.id"), nullable=True)
    mcp_server_id: Mapped[str] = mapped_column(String, ForeignKey("mcp_servers.id"), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenants.id"), nullable=False)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    user_email: Mapped[str | None] = mapped_column(String, nullable=True)
    tool_name: Mapped[str] = mapped_column(String, nullable=False)
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str | None] = mapped_column(String, nullable=True)
    called_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    duration_ms: Mapped[str | None] = mapped_column(String, nullable=True)


async def ensure_tenant(
    db: AsyncSession,
    tenant_id: str,
    tenant_name: str | None = None,
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant:
        return tenant

    tenant = Tenant(
        id=tenant_id,
        name=tenant_name or f"Tenant {tenant_id[:8]}",
        slug=_slugify(tenant_name or tenant_id),
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def upsert_platform_user(
    db: AsyncSession,
    *,
    user_id: str,
    tenant_id: str,
    email: str | None,
    name: str | None,
    roles: list | None = None,
    provider: str = "keycloak",
    provider_user_id: str | None = None,
) -> PlatformUser:
    await ensure_tenant(db, tenant_id, tenant_name=tenant_id)

    user = await db.get(PlatformUser, user_id)
    if user:
        user.tenant_id = tenant_id
        user.email = email
        user.name = name
        user.roles = roles or []
        user.provider = provider
        user.provider_user_id = provider_user_id or user_id
        user.last_login_at = datetime.utcnow()
        user.updated_at = datetime.utcnow()
        return user

    user = PlatformUser(
        id=user_id,
        tenant_id=tenant_id,
        email=email,
        name=name,
        roles=roles or [],
        provider=provider,
        provider_user_id=provider_user_id or user_id,
        is_active=True,
        last_login_at=datetime.utcnow(),
    )
    db.add(user)
    await db.flush()
    return user


async def create_tables():
    """Create schema and apply light non-destructive compat alterations."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        # Compatibility for existing local DBs created with earlier schema.
        await conn.execute(
            text("ALTER TABLE mcp_sessions ADD COLUMN IF NOT EXISTS call_count INTEGER DEFAULT 0")
        )
        await conn.execute(
            text("ALTER TABLE mcp_servers ADD COLUMN IF NOT EXISTS deployed_by_user_id VARCHAR")
        )
        await conn.execute(
            text("ALTER TABLE users ADD COLUMN IF NOT EXISTS roles JSON DEFAULT '[]'")
        )
        await conn.execute(
            text("ALTER TABLE github_connections DROP CONSTRAINT IF EXISTS github_connections_user_id_key")
        )
        await conn.execute(
            text("ALTER TABLE github_connections ADD COLUMN IF NOT EXISTS provider_user_id VARCHAR")
        )
        await conn.execute(
            text("ALTER TABLE github_connections ADD COLUMN IF NOT EXISTS connection_name VARCHAR")
        )
        await conn.execute(
            text("ALTER TABLE github_connections ADD COLUMN IF NOT EXISTS account_url VARCHAR")
        )
        await conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS ix_github_connections_user_provider "
                "ON github_connections (user_id, provider_user_id)"
            )
        )


__all__ = [
    "AuditLog",
    "Base",
    "GitHubConnection",
    "MCPServer",
    "MCPSession",
    "PlatformUser",
    "Tenant",
    "create_tables",
    "ensure_tenant",
    "get_db",
    "upsert_platform_user",
]
