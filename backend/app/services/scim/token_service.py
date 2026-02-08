"""
Overview: SCIM bearer token management service.
Architecture: Token creation, validation, and revocation for SCIM API (Section 5.1)
Dependencies: sqlalchemy, app.models.scim_token
Concepts: SCIM authentication, bearer tokens, token lifecycle
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.scim_token import SCIMToken


class SCIMTokenError(Exception):
    def __init__(self, message: str, code: str = "SCIM_TOKEN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SCIMTokenService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_token(
        self,
        tenant_id: str,
        created_by: str,
        description: str | None = None,
        expires_in_days: int | None = None,
    ) -> tuple[SCIMToken, str]:
        """Create a new SCIM token. Returns (token_record, raw_token)."""
        raw_token = secrets.token_urlsafe(48)
        token_hash = self._hash_token(raw_token)

        expires_at = None
        if expires_in_days:
            expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

        scim_token = SCIMToken(
            tenant_id=tenant_id,
            token_hash=token_hash,
            description=description,
            expires_at=expires_at,
            created_by=created_by,
        )
        self.db.add(scim_token)
        await self.db.flush()

        return scim_token, raw_token

    async def validate_token(self, raw_token: str) -> SCIMToken | None:
        """Validate a SCIM bearer token and return the token record."""
        token_hash = self._hash_token(raw_token)

        result = await self.db.execute(
            select(SCIMToken).where(
                SCIMToken.token_hash == token_hash,
                SCIMToken.is_active.is_(True),
            )
        )
        token = result.scalar_one_or_none()

        if not token:
            return None

        if token.expires_at and token.expires_at < datetime.now(UTC):
            return None

        return token

    async def list_tokens(self, tenant_id: str) -> list[SCIMToken]:
        """List all SCIM tokens for a tenant."""
        result = await self.db.execute(
            select(SCIMToken)
            .where(SCIMToken.tenant_id == tenant_id)
            .order_by(SCIMToken.created_at.desc())
        )
        return list(result.scalars().all())

    async def revoke_token(self, token_id: str, tenant_id: str) -> None:
        """Revoke a SCIM token."""
        result = await self.db.execute(
            select(SCIMToken).where(
                SCIMToken.id == token_id,
                SCIMToken.tenant_id == tenant_id,
            )
        )
        token = result.scalar_one_or_none()
        if not token:
            raise SCIMTokenError("Token not found", "TOKEN_NOT_FOUND")

        token.is_active = False
        await self.db.flush()

    @staticmethod
    def _hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode()).hexdigest()
