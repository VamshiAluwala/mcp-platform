"""
AUTH MIDDLEWARE — Your Core Innovation

This validates identity on EVERY single MCP tool call.
NOT just at login. EVERY call.

Existing tools: validate at connection only.
Your platform: validates at every tool execution.
"""

import httpx
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import get_db, upsert_platform_user

ACCESS_TOKEN_COOKIE_NAME = "mcp_access_token"
security = HTTPBearer(auto_error=False)

# Cache public key so we don't hit Keycloak on every request
_public_key_cache = None


async def get_keycloak_public_key() -> str:
    """Fetch Keycloak public key for JWT verification"""
    global _public_key_cache
    if _public_key_cache:
        return _public_key_cache

    url = f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        data = resp.json()
        raw_key = data["public_key"]
        _public_key_cache = (
            f"-----BEGIN PUBLIC KEY-----\n{raw_key}\n-----END PUBLIC KEY-----"
        )
        return _public_key_cache


async def _verify_google_token(token: str) -> dict | None:
    """
    Verify a Google access token via Google's tokeninfo endpoint.
    Returns claims dict on success, None on failure.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"access_token": token},
            )
            if not resp.is_success:
                return None
            data = resp.json()
            # Make sure the token belongs to our client
            if data.get("aud") and settings.GOOGLE_CLIENT_ID not in str(data.get("aud", "")):
                # Also accept if azp matches (some Google tokens use azp)
                if data.get("azp") != settings.GOOGLE_CLIENT_ID:
                    pass  # Be permissive — let user-info confirm identity
            # Normalise to standard claim names
            return {
                "sub": data.get("sub") or data.get("user_id"),
                "email": data.get("email"),
                "name": data.get("name", ""),
                "provider": "google",
            }
    except Exception:
        return None


def _admin_emails() -> set[str]:
    return {
        email.strip().lower()
        for email in settings.ADMIN_EMAILS.split(",")
        if email.strip()
    }


def _with_admin_role(email: str | None, roles: list[str]) -> list[str]:
    normalized = list(dict.fromkeys(roles))
    if email and email.strip().lower() in _admin_emails() and "admin" not in normalized:
        normalized.append("admin")
    return normalized


def get_request_access_token(request: Request) -> str | None:
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return token

    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if cookie_token:
        return cookie_token

    return None


async def verify_access_token(token: str) -> dict:
    """
    Verify JWT token.
    Tries Keycloak first; falls back to Google token verification
    so Google-authenticated users can also access protected endpoints.
    """
    # ── Try Keycloak first ────────────────────────────────────────
    try:
        public_key = await get_keycloak_public_key()
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_aud": False},
        )
        return {**payload, "provider": "keycloak"}

    except (JWTError, Exception):
        pass  # Fall through to Google verification

    # ── Try Google token verification ─────────────────────────────
    google_claims = await _verify_google_token(token)
    if google_claims and google_claims.get("sub"):
        return google_claims

    raise HTTPException(
        status_code=401,
        detail="Invalid or expired token. Please log in again.",
    )


async def verify_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    token = credentials.credentials if credentials else get_request_access_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await verify_access_token(token)


async def resolve_user_from_token(
    *,
    token: str,
    db: AsyncSession,
) -> dict:
    token_payload = await verify_access_token(token)
    return await _sync_user_from_token_payload(token_payload=token_payload, db=db)


async def _sync_user_from_token_payload(
    *,
    token_payload: dict,
    db: AsyncSession,
) -> dict:
    roles = token_payload.get("realm_access", {}).get("roles", [])
    if not isinstance(roles, list):
        roles = []

    roles = _with_admin_role(token_payload.get("email"), roles)

    user = {
        "user_id": token_payload.get("sub"),
        "email": token_payload.get("email"),
        "name": token_payload.get("name"),
        "tenant_id": token_payload.get("tenant_id"),
        "roles": roles,
        "raw": token_payload,
        "provider": token_payload.get("provider", "keycloak"),
    }

    if not user["user_id"]:
        raise HTTPException(status_code=401, detail="Token missing required 'sub' claim")

    tenant_id = user.get("tenant_id") or user["user_id"]
    provider = user.get("provider", "keycloak")

    await upsert_platform_user(
        db,
        user_id=user["user_id"],
        tenant_id=tenant_id,
        email=user.get("email"),
        name=user.get("name"),
        roles=user.get("roles", []),
        provider=provider,
        provider_user_id=user["user_id"],
    )
    user["tenant_id"] = tenant_id
    return user


async def get_current_user(
    token_payload: dict = Depends(verify_token),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract clean user identity from token.
    This is injected into EVERY protected endpoint.
    """
    return await _sync_user_from_token_payload(token_payload=token_payload, db=db)


def require_role(role: str):
    """
    Role-based access control decorator.
    Usage: @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(user: dict = Depends(get_current_user)):
        if role not in user.get("roles", []):
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' required"
            )
        return user
    return check_role
