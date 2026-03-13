from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.access import normalize_email_list
from app.auth.middleware import get_current_user
from app.models.database import AccessGroup, AccessGroupMember, get_db


router = APIRouter(prefix="/api/access-groups", tags=["Access Groups"])


class AccessGroupRequest(BaseModel):
    name: str
    description: str = ""
    members: list[str] = []


def _tenant_id_for(user: dict) -> str:
    return user.get("tenant_id") or user.get("user_id")


async def _load_group_for_user(
    db: AsyncSession,
    *,
    group_id: str,
    user: dict,
) -> AccessGroup:
    query = select(AccessGroup).where(AccessGroup.id == group_id)
    if "admin" not in user.get("roles", []):
        query = query.where(AccessGroup.tenant_id == _tenant_id_for(user))
    result = await db.execute(query)
    group = result.scalar_one_or_none()
    if not group:
        raise HTTPException(status_code=404, detail="Access group not found")
    return group


async def _serialize_group(db: AsyncSession, group: AccessGroup) -> dict:
    members_result = await db.execute(
        select(AccessGroupMember.email)
        .where(AccessGroupMember.group_id == group.id)
        .order_by(AccessGroupMember.email.asc())
    )
    members = [row[0] for row in members_result.all()]
    return {
        "id": group.id,
        "tenant_id": group.tenant_id,
        "name": group.name,
        "description": group.description,
        "source": group.source,
        "member_count": len(members),
        "members": members,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
    }


async def _replace_members(
    db: AsyncSession,
    *,
    group_id: str,
    members: list[str],
) -> None:
    await db.execute(delete(AccessGroupMember).where(AccessGroupMember.group_id == group_id))
    for email in normalize_email_list(members):
        db.add(AccessGroupMember(group_id=group_id, email=email))


@router.get("/")
async def list_access_groups(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = select(AccessGroup).order_by(AccessGroup.created_at.desc())
    if "admin" not in user.get("roles", []):
        query = query.where(AccessGroup.tenant_id == _tenant_id_for(user))

    result = await db.execute(query)
    groups = list(result.scalars().all())
    return {
        "count": len(groups),
        "groups": [await _serialize_group(db, group) for group in groups],
    }


@router.post("/")
async def create_access_group(
    request: AccessGroupRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    tenant_id = _tenant_id_for(user)
    group = AccessGroup(
        tenant_id=tenant_id,
        created_by_user_id=user["user_id"],
        name=request.name.strip(),
        description=request.description.strip(),
        source="manual",
    )
    db.add(group)
    await db.flush()
    await _replace_members(db, group_id=group.id, members=request.members)
    return await _serialize_group(db, group)


@router.put("/{group_id}")
async def update_access_group(
    group_id: str,
    request: AccessGroupRequest,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await _load_group_for_user(db, group_id=group_id, user=user)
    group.name = request.name.strip()
    group.description = request.description.strip()
    await _replace_members(db, group_id=group.id, members=request.members)
    return await _serialize_group(db, group)


@router.delete("/{group_id}")
async def delete_access_group(
    group_id: str,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = await _load_group_for_user(db, group_id=group_id, user=user)
    await db.execute(delete(AccessGroupMember).where(AccessGroupMember.group_id == group.id))
    await db.delete(group)
    return {"message": "Access group deleted", "group_id": group_id}
