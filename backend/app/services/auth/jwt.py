"""
Overview: JWT token creation and validation for access and refresh tokens.
Architecture: Token management layer (Section 5.1)
Dependencies: python-jose, app.core.config
Concepts: JWT, access tokens, refresh tokens, token expiry, tenant context
"""

import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def create_access_token(
    user_id: str,
    provider_id: str,
    jti: str | None = None,
    tenant_ids: list[str] | None = None,
    current_tenant_id: str | None = None,
    impersonating: dict | None = None,
    expires_at: datetime | None = None,
) -> tuple[str, str, datetime]:
    """Create a JWT access token. Returns (token, jti, expires_at)."""
    jti = jti or str(uuid.uuid4())
    if expires_at is None:
        expires_at = datetime.now(UTC) + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": user_id,
        "provider_id": provider_id,
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "type": "access",
    }

    if tenant_ids is not None:
        payload["tenant_ids"] = tenant_ids
    if current_tenant_id is not None:
        payload["current_tenant_id"] = current_tenant_id
    if impersonating is not None:
        payload["impersonating"] = impersonating

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, jti, expires_at


def create_refresh_token(user_id: str, jti: str) -> tuple[str, datetime]:
    """Create a JWT refresh token tied to an access token's jti. Returns (token, expires_at)."""
    expires_at = datetime.now(UTC) + timedelta(days=settings.jwt_refresh_token_expire_days)

    payload = {
        "sub": user_id,
        "jti": jti,
        "exp": expires_at,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token. Raises JWTError on failure."""
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        raise


def hash_refresh_token(refresh_token: str) -> str:
    """Hash a refresh token for storage (we never store raw refresh tokens)."""
    return hashlib.sha256(refresh_token.encode()).hexdigest()
