from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # App
    APP_NAME: str = "MCP Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres123@localhost:5432/appdb"

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
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/auth/callback"

    # GitHub OAuth2
    GITHUB_OAUTH_CLIENT_ID: str = ""
    GITHUB_OAUTH_CLIENT_SECRET: str = ""
    GITHUB_OAUTH_REDIRECT_URI: str = "http://localhost:3000/auth/github/callback"

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    FRONTEND_OAUTH_CALLBACK_URL: str = "http://localhost:3000/auth/callback"
    ADMIN_EMAILS: str = "sales@agentorix.in"

    # Encryption (used for GitHub token-at-rest)
    GITHUB_TOKEN_ENCRYPTION_SECRET: str = "change-this-local-dev-secret"

    # MinIO (Free S3 locally — swap to AWS S3 later)
    MINIO_URL: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin123"
    MINIO_BUCKET: str = "mcp-files"

    class Config:
        env_file = ".env"


settings = Settings()
