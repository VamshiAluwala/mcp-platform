from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.middleware import get_current_user
from app.auth.service import (
    build_login_url,
    decode_unverified_claims,
    exchange_code_for_tokens,
    exchange_google_code,
    extract_identity,
    extract_google_identity,
    fetch_userinfo,
    fetch_google_userinfo,
    oauth_metadata,
)
from app.models.database import get_db, upsert_platform_user


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class OAuthCallbackRequest(BaseModel):
    code: str
    redirect_uri: str | None = None
    provider: str = "keycloak"   # "keycloak" | "google" | "google_direct"


@router.get("/login-url")
async def get_login_url(
    provider: str = Query(
        default="keycloak",
        pattern="^(keycloak|google|google_direct)$",
    ),
    redirect_uri: str | None = None,
    state: str | None = None,
):
    # Embed provider in state so callback knows which flow to use
    effective_state = state or provider
    return {
        "provider": provider,
        "login_url": build_login_url(
            redirect_uri=redirect_uri,
            state=effective_state,
            provider=provider,
        ),
        "oauth": oauth_metadata(google_hint=(provider == "google")),
    }


@router.get("/oauth-metadata")
async def get_oauth_metadata():
    return oauth_metadata()


@router.post("/callback")
async def oauth_callback(
    request: OAuthCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    # ── Direct Google OAuth2 path ──────────────────────────────────────────
    if request.provider == "google_direct":
        try:
            token_payload = await exchange_google_code(
                code=request.code,
                redirect_uri=request.redirect_uri,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Google code exchange failed: {exc}",
            ) from exc

        access_token = token_payload.get("access_token")
        if not access_token:
            raise HTTPException(
                status_code=400,
                detail="No access token returned by Google",
            )

        try:
            userinfo = await fetch_google_userinfo(access_token)
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch Google user info: {exc}",
            ) from exc

        identity = extract_google_identity(userinfo)
        if not identity.get("user_id"):
            raise HTTPException(status_code=400, detail="Google token missing subject claim")

        await upsert_platform_user(
            db,
            user_id=identity["user_id"],
            tenant_id=identity["tenant_id"],
            email=identity.get("email"),
            name=identity.get("name"),
            roles=[],
            provider="google",
            provider_user_id=identity["user_id"],
        )

        return {
            "access_token": token_payload.get("access_token"),
            "refresh_token": token_payload.get("refresh_token"),
            "id_token": token_payload.get("id_token"),
            "token_type": token_payload.get("token_type", "Bearer"),
            "expires_in": token_payload.get("expires_in"),
            "scope": token_payload.get("scope"),
            "user": identity,
            "oauth": None,
        }

    # ── Keycloak (default) path ────────────────────────────────────────────
    try:
        token_payload = await exchange_code_for_tokens(
            code=request.code,
            redirect_uri=request.redirect_uri,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth code exchange failed: {exc}",
        ) from exc

    access_token = token_payload.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token returned by OAuth provider")

    claims = decode_unverified_claims(access_token)
    try:
        userinfo = await fetch_userinfo(access_token)
    except Exception:
        userinfo = {}
    claims.update({k: v for k, v in userinfo.items() if k not in claims or not claims.get(k)})

    identity = extract_identity(claims)
    if not identity.get("user_id"):
        raise HTTPException(status_code=400, detail="OAuth token missing subject claim")

    await upsert_platform_user(
        db,
        user_id=identity["user_id"],
        tenant_id=identity.get("tenant_id") or identity["user_id"],
        email=identity.get("email"),
        name=identity.get("name"),
        roles=identity.get("roles", []),
        provider="keycloak",
        provider_user_id=identity["user_id"],
    )

    return {
        "access_token": token_payload.get("access_token"),
        "refresh_token": token_payload.get("refresh_token"),
        "id_token": token_payload.get("id_token"),
        "token_type": token_payload.get("token_type", "Bearer"),
        "expires_in": token_payload.get("expires_in"),
        "scope": token_payload.get("scope"),
        "user": identity,
        "oauth": oauth_metadata(),
    }


@router.get("/me")
async def who_am_i(user: dict = Depends(get_current_user)):
    return {
        "user_id": user.get("user_id"),
        "email": user.get("email"),
        "name": user.get("name"),
        "tenant_id": user.get("tenant_id"),
        "roles": user.get("roles", []),
    }
