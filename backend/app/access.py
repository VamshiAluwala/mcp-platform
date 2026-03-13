from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import AccessGroup, AccessGroupMember, MCPServer


def normalize_email_list(emails: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for email in emails or []:
        cleaned = re.sub(r"\s+", "", (email or "").strip().lower())
        if cleaned and "@" in cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


def normalize_group_ids(group_ids: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for group_id in group_ids or []:
        cleaned = (group_id or "").strip()
        if cleaned and cleaned not in normalized:
            normalized.append(cleaned)
    return normalized


async def resolve_groups(
    db: AsyncSession,
    *,
    tenant_id: str,
    group_ids: list[str] | None,
) -> list[AccessGroup]:
    normalized = normalize_group_ids(group_ids)
    if not normalized:
        return []

    result = await db.execute(
        select(AccessGroup).where(
            AccessGroup.tenant_id == tenant_id,
            AccessGroup.id.in_(normalized),
        )
    )
    return list(result.scalars().all())


async def validate_group_ids(
    db: AsyncSession,
    *,
    tenant_id: str,
    group_ids: list[str] | None,
) -> list[str]:
    normalized = normalize_group_ids(group_ids)
    groups = await resolve_groups(db, tenant_id=tenant_id, group_ids=normalized)
    resolved_ids = [group.id for group in groups]
    missing = [group_id for group_id in normalized if group_id not in resolved_ids]
    if missing:
        raise ValueError(f"Unknown access group ids: {', '.join(missing)}")
    return resolved_ids


async def load_group_map(
    db: AsyncSession,
    *,
    tenant_id: str,
    group_ids: list[str] | None,
) -> list[dict]:
    groups = await resolve_groups(db, tenant_id=tenant_id, group_ids=group_ids)
    if not groups:
        return []

    counts_result = await db.execute(
        select(AccessGroupMember.group_id, AccessGroupMember.email).where(
            AccessGroupMember.group_id.in_([group.id for group in groups])
        )
    )
    members_by_group: dict[str, list[str]] = {}
    for group_id, email in counts_result.all():
        members_by_group.setdefault(group_id, []).append(email)

    return [
        {
            "id": group.id,
            "name": group.name,
            "description": group.description,
            "source": group.source,
            "member_count": len(members_by_group.get(group.id, [])),
            "members": sorted(members_by_group.get(group.id, [])),
        }
        for group in groups
    ]


async def email_allowed_via_groups(
    db: AsyncSession,
    *,
    group_ids: list[str] | None,
    email: str | None,
) -> bool:
    normalized_email = (email or "").strip().lower()
    normalized_groups = normalize_group_ids(group_ids)
    if not normalized_email or not normalized_groups:
        return False

    result = await db.execute(
        select(AccessGroupMember.id).where(
            AccessGroupMember.group_id.in_(normalized_groups),
            AccessGroupMember.email == normalized_email,
        )
    )
    return result.scalar_one_or_none() is not None


async def build_server_access_payload(
    db: AsyncSession,
    server: MCPServer,
) -> dict:
    config = server.config or {}
    group_ids = config.get("allowed_group_ids", [])
    return {
        "server_id": server.id,
        "allowed_emails": normalize_email_list(config.get("allowed_user_emails", [])),
        "allowed_group_ids": normalize_group_ids(group_ids),
        "allowed_groups": await load_group_map(
            db,
            tenant_id=server.tenant_id,
            group_ids=group_ids,
        ),
        "owner_email": config.get("owner_email"),
    }
