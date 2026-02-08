"""
Overview: Application configuration loaded from environment variables with defaults.
Architecture: Core config module referenced by all components (Section 3.1)
Dependencies: pydantic-settings
Concepts: Configuration management, environment-based settings
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="NIMBUS_", env_file=".env", extra="ignore")

    # Application
    app_name: str = "Nimbus"
    app_version: str = "0.1.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://nimbus:nimbus_dev@localhost:5432/nimbus"

    # JWT
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    jwt_refresh_token_expire_days: int = 7

    # Session
    max_concurrent_sessions: int = 5

    # Temporal
    temporal_host: str = "localhost"
    temporal_port: int = 7233
    temporal_namespace: str = "nimbus"
    temporal_task_queue: str = "nimbus-workflows"

    # Tenant
    tenant_retention_days: int = 30

    # Impersonation
    impersonation_max_duration_minutes: int = 240

    # SSO
    oidc_callback_url: str = "http://localhost:8000/api/v1/auth/sso/oidc/callback"
    saml_acs_url: str = "http://localhost:8000/api/v1/auth/sso/saml/acs"
    saml_entity_id: str = "nimbus"

    # SMTP (email notifications)
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from_email: str = "noreply@nimbus.local"
    smtp_from_name: str = "Nimbus"
    smtp_use_tls: bool = True

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "nimbus"
    minio_secret_key: str = "nimbus_dev"
    minio_bucket: str = "nimbus"
    minio_use_ssl: bool = False

    @property
    def temporal_address(self) -> str:
        return f"{self.temporal_host}:{self.temporal_port}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
