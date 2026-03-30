from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MCP Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/appdb"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Keycloak (Free Auth — swap to AWS Cognito later)
    KEYCLOAK_URL: str = "http://localhost:8080"
    KEYCLOAK_PUBLIC_URL: str = "http://localhost:8080"
    KEYCLOAK_REALM: str = "mcp-platform"
    KEYCLOAK_CLIENT_ID: str = "mcp-backend"
    KEYCLOAK_CLIENT_SECRET: Optional[str] = None
    KEYCLOAK_FRONTEND_CLIENT_ID: str = "mcp-frontend"
    KEYCLOAK_FRONTEND_CLIENT_SECRET: Optional[str] = None
    KEYCLOAK_MCP_CLIENT_ID: str = "mcp-clients"
    KEYCLOAK_GOOGLE_IDP_HINT: str = "google"

    # Google OAuth2 (Direct — not via Keycloak)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/google/callback"

    # GitHub OAuth2
    GITHUB_OAUTH_CLIENT_ID: str = ""
    GITHUB_OAUTH_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    FRONTEND_OAUTH_CALLBACK_URL: str = "http://localhost:3000/auth/callback"
    GATEWAY_PUBLIC_URL: str = "http://localhost:8000"
    ADMIN_EMAILS: str = "sales@agentorix.in"
    ALLOW_DIRECT_GOOGLE_TOKENS: bool = True

    # Runtime
    DOCKER_NETWORK: str = "mcp-platform-network"
    MCP_DEFAULT_RUNTIME_PORT: int = 8000

    # Encryption (used for GitHub token-at-rest)
    GITHUB_TOKEN_ENCRYPTION_SECRET: str = "change-this-local-dev-secret"

    # MinIO (Free S3 locally — swap to AWS S3 later)
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "mcp-files"

    @property
    def is_gateway_url_localhost(self) -> bool:
        """Check if GATEWAY_PUBLIC_URL is still set to a localhost default."""
        url = self.GATEWAY_PUBLIC_URL.lower()
        return "localhost" in url or "127.0.0.1" in url or "0.0.0.0" in url

    def resolve_gateway_url(self, request_host: str | None = None, scheme: str | None = None) -> str:
        """Return the effective public gateway URL.

        If GATEWAY_PUBLIC_URL has been explicitly set to a non-localhost value,
        return it as-is. Otherwise, if a request Host header is available,
        construct the URL from that header so deployed MCPs get a reachable URL.
        """
        if not self.is_gateway_url_localhost:
            return self.GATEWAY_PUBLIC_URL.rstrip("/")

        if request_host:
            effective_scheme = scheme or "https"
            return f"{effective_scheme}://{request_host}"

        return self.GATEWAY_PUBLIC_URL.rstrip("/")

    class Config:
        env_file = ".env"


settings = Settings()
