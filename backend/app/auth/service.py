import hashlib
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet
from jose import jwt

from app.core.config import settings


# ─── Keycloak helpers ────────────────────────────────────────────────────────

def _realm_base_internal() -> str:
    return f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}"


def _realm_base_public() -> str:
    return f"{settings.KEYCLOAK_PUBLIC_URL}/realms/{settings.KEYCLOAK_REALM}"


def _token_endpoint_internal() -> str:
    return f"{_realm_base_internal()}/protocol/openid-connect/token"


def _userinfo_endpoint_internal() -> str:
    return f"{_realm_base_internal()}/protocol/openid-connect/userinfo"


def _authorization_endpoint_public() -> str:
    return f"{_realm_base_public()}/protocol/openid-connect/auth"


def _authorization_endpoint_public_with_google_hint() -> str:
    return f"{_authorization_endpoint_public()}?kc_idp_hint={settings.KEYCLOAK_GOOGLE_IDP_HINT}"


def _gateway_base_public() -> str:
    return settings.GATEWAY_PUBLIC_URL.rstrip("/")


def gateway_authorization_endpoint() -> str:
    return f"{_gateway_base_public()}/authorize"


def gateway_token_endpoint() -> str:
    return f"{_gateway_base_public()}/token"


def gateway_registration_endpoint() -> str:
    return f"{_gateway_base_public()}/register"


def build_login_url(
    *,
    redirect_uri: str | None = None,
    state: str | None = None,
    provider: str = "keycloak",
) -> str:
    """Build the OAuth2 authorization URL for the given provider."""
    if provider == "google_direct":
        return build_google_login_url(redirect_uri=redirect_uri, state=state)

    query: dict[str, str] = {
        "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
        "response_type": "code",
        "scope": "openid profile email",
        "redirect_uri": redirect_uri or settings.FRONTEND_OAUTH_CALLBACK_URL,
    }
    if state:
        query["state"] = state
    if provider == "google":
        query["kc_idp_hint"] = settings.KEYCLOAK_GOOGLE_IDP_HINT

    return f"{_authorization_endpoint_public()}?{urlencode(query)}"


async def exchange_code_for_tokens(
    *,
    code: str,
    redirect_uri: str | None = None,
) -> dict:
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": settings.KEYCLOAK_FRONTEND_CLIENT_ID,
        "code": code,
        "redirect_uri": redirect_uri or settings.FRONTEND_OAUTH_CALLBACK_URL,
    }

    if settings.KEYCLOAK_FRONTEND_CLIENT_SECRET:
        payload["client_secret"] = settings.KEYCLOAK_FRONTEND_CLIENT_SECRET

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _token_endpoint_internal(),
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_userinfo(access_token: str) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            _userinfo_endpoint_internal(),
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ─── Direct Google OAuth2 helpers ────────────────────────────────────────────

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v3/userinfo"


def build_google_login_url(
    *,
    redirect_uri: str | None = None,
    state: str | None = None,
) -> str:
    """Build a direct Google OAuth2 authorization URL."""
    query: dict[str, str] = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
        "access_type": "offline",
        "prompt": "select_account",
    }
    if state:
        query["state"] = state
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(query)}"


async def exchange_google_code(
    *,
    code: str,
    redirect_uri: str | None = None,
) -> dict:
    """Exchange an authorization code for Google tokens."""
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "code": code,
        "redirect_uri": redirect_uri or settings.GOOGLE_REDIRECT_URI,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def exchange_google_refresh_token(refresh_token: str) -> dict:
    payload: dict[str, str] = {
        "grant_type": "refresh_token",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_google_userinfo(access_token: str) -> dict:
    """Fetch user profile from Google's userinfo endpoint."""
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            GOOGLE_USERINFO_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        resp.raise_for_status()
        return resp.json()


# ─── Shared token / identity helpers ─────────────────────────────────────────

def decode_unverified_claims(access_token: str) -> dict:
    try:
        return jwt.get_unverified_claims(access_token)
    except Exception:
        return {}


def extract_identity(claims: dict) -> dict:
    return {
        "user_id": claims.get("sub"),
        "email": claims.get("email"),
        "name": claims.get("name") or claims.get("preferred_username"),
        "tenant_id": claims.get("tenant_id") or claims.get("sub"),
        "roles": claims.get("realm_access", {}).get("roles", []),
    }


def extract_google_identity(userinfo: dict) -> dict:
    """Build a normalised identity dict from Google's userinfo response."""
    sub = userinfo.get("sub")
    return {
        "user_id": sub,
        "email": userinfo.get("email"),
        "name": userinfo.get("name"),
        "tenant_id": sub,
        "roles": [],
    }


def oauth_metadata(client_id: str | None = None, google_hint: bool = False) -> dict:
    realm_base = _realm_base_public()
    return {
        "authorization_endpoint": (
            _authorization_endpoint_public_with_google_hint()
            if google_hint
            else f"{realm_base}/protocol/openid-connect/auth"
        ),
        "token_endpoint": f"{realm_base}/protocol/openid-connect/token",
        "userinfo_endpoint": f"{realm_base}/protocol/openid-connect/userinfo",
        "issuer": realm_base,
        "client_id": client_id or settings.KEYCLOAK_FRONTEND_CLIENT_ID,
    }


def gateway_oauth_metadata() -> dict:
    return {
        "issuer": _gateway_base_public(),
        "authorization_endpoint": gateway_authorization_endpoint(),
        "token_endpoint": gateway_token_endpoint(),
        "registration_endpoint": gateway_registration_endpoint(),
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256", "plain"],
        "scopes_supported": ["openid", "profile", "email"],
        "client_id_metadata_document_supported": True,
    }


def protected_resource_metadata(resource_url: str) -> dict:
    return {
        "resource": resource_url,
        "authorization_servers": [_gateway_base_public()],
        "scopes_supported": ["openid", "profile", "email"],
        "bearer_methods_supported": ["header"],
    }


def build_mcp_authorize_redirect(
    *,
    redirect_uri: str,
    state: str | None = None,
    scope: str | None = None,
    code_challenge: str | None = None,
    code_challenge_method: str | None = None,
) -> str:
    query: dict[str, str] = {
        "client_id": settings.KEYCLOAK_MCP_CLIENT_ID,
        "response_type": "code",
        "scope": scope or "openid profile email",
        "redirect_uri": redirect_uri,
        "kc_idp_hint": settings.KEYCLOAK_GOOGLE_IDP_HINT,
    }
    if state:
        query["state"] = state
    if code_challenge:
        query["code_challenge"] = code_challenge
    if code_challenge_method:
        query["code_challenge_method"] = code_challenge_method
    return f"{_authorization_endpoint_public()}?{urlencode(query)}"


async def exchange_mcp_tokens(
    *,
    grant_type: str,
    code: str | None = None,
    redirect_uri: str | None = None,
    refresh_token: str | None = None,
    code_verifier: str | None = None,
) -> dict:
    payload: dict[str, str] = {
        "grant_type": grant_type,
        "client_id": settings.KEYCLOAK_MCP_CLIENT_ID,
    }

    if grant_type == "authorization_code":
        if not code:
            raise ValueError("code is required")
        if not redirect_uri:
            raise ValueError("redirect_uri is required")
        payload["code"] = code
        payload["redirect_uri"] = redirect_uri
        if code_verifier:
            payload["code_verifier"] = code_verifier
    elif grant_type == "refresh_token":
        if not refresh_token:
            raise ValueError("refresh_token is required")
        payload["refresh_token"] = refresh_token
    else:
        raise ValueError(f"Unsupported grant_type: {grant_type}")

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            _token_endpoint_internal(),
            data=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        return resp.json()


def base64_urlsafe(raw: bytes) -> bytes:
    import base64
    return base64.urlsafe_b64encode(raw)


def _fernet() -> Fernet:
    key = base64_urlsafe(hashlib.sha256(settings.GITHUB_TOKEN_ENCRYPTION_SECRET.encode("utf-8")).digest())
    return Fernet(key)


def encrypt_github_token(token: str) -> str:
    return _fernet().encrypt(token.encode("utf-8")).decode("utf-8")


def decrypt_github_token(token_encrypted: str) -> str:
    return _fernet().decrypt(token_encrypted.encode("utf-8")).decode("utf-8")


def build_claude_oauth_block(endpoint_url: str) -> dict:
    meta = gateway_oauth_metadata()
    return {
        "url": endpoint_url,
        "auth": {
            "type": "oauth2",
            "authorizationUrl": meta["authorization_endpoint"],
            "tokenUrl": meta["token_endpoint"],
            "clientId": settings.KEYCLOAK_MCP_CLIENT_ID,
            "scopes": ["openid", "profile", "email"],
        },
    }


def build_remote_mcp_client_config(server_name: str, endpoint_url: str) -> dict:
    return {
        "mcpServers": {
            server_name: {
                "serverUrl": endpoint_url,
            }
        }
    }
