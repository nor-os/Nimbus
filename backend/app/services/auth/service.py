"""
Overview: Authentication service handling login, token management, sessions, and tenant switching.
Architecture: Service layer for auth operations (Section 3.1, 5.1)
Dependencies: sqlalchemy, app.models, app.services.auth.jwt, app.services.auth.password
Concepts: Authentication, session management, concurrent session limits, tenant context
"""

from datetime import UTC, datetime

from jose import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.session import Session
from app.models.user import User
from app.models.user_tenant import UserTenant
from app.services.auth.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_refresh_token,
)
from app.services.auth.password import verify_password

settings = get_settings()


class AuthError(Exception):
    def __init__(self, message: str, code: str = "AUTH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def login(
        self,
        email: str,
        password: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict:
        """Authenticate a user and create a new session with tokens."""
        user = await self._get_user_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password", "INVALID_CREDENTIALS")

        if not user.is_active:
            raise AuthError("Account is disabled", "ACCOUNT_DISABLED")

        if user.is_deleted:
            raise AuthError("Invalid email or password", "INVALID_CREDENTIALS")

        await self._enforce_session_limit(user.id)

        return await self._create_session(user, ip_address, user_agent)

    async def refresh(self, refresh_token: str) -> dict:
        """Issue new tokens using a valid refresh token."""
        try:
            payload = decode_token(refresh_token)
        except JWTError:
            raise AuthError("Invalid refresh token", "INVALID_TOKEN")

        if payload.get("type") != "refresh":
            raise AuthError("Invalid token type", "INVALID_TOKEN")

        # Impersonation tokens cannot be refreshed
        if payload.get("impersonating"):
            raise AuthError("Impersonation tokens cannot be refreshed", "IMPERSONATION_NO_REFRESH")

        jti = payload.get("jti")
        session = await self._get_session_by_jti(jti)
        if not session or not session.is_active:
            raise AuthError("Session not found or revoked", "SESSION_REVOKED")

        # Verify the refresh token hash matches
        if session.refresh_token_hash != hash_refresh_token(refresh_token):
            raise AuthError("Invalid refresh token", "INVALID_TOKEN")

        user = await self._get_user_by_id(payload["sub"])
        if not user or not user.is_active or user.is_deleted:
            raise AuthError("User not found or disabled", "USER_INVALID")

        # Revoke old session, create new one
        session.revoked_at = datetime.now(UTC)
        return await self._create_session(user, session.ip_address, session.user_agent)

    async def logout(self, jti: str) -> None:
        """Revoke the session associated with the given JTI."""
        session = await self._get_session_by_jti(jti)
        if session and session.is_active:
            session.revoked_at = datetime.now(UTC)

    async def revoke_session(self, session_id: str, user_id: str) -> None:
        """Revoke a specific session belonging to the user."""
        result = await self.db.execute(
            select(Session).where(Session.id == session_id, Session.user_id == user_id)
        )
        session = result.scalar_one_or_none()
        if session and session.is_active:
            session.revoked_at = datetime.now(UTC)

    async def get_active_sessions(self, user_id: str) -> list[Session]:
        """Get all active sessions for a user."""
        result = await self.db.execute(
            select(Session)
            .where(
                Session.user_id == user_id,
                Session.revoked_at.is_(None),
                Session.expires_at > datetime.now(UTC),
            )
            .order_by(Session.created_at.desc())
        )
        return list(result.scalars().all())

    async def validate_token(self, token: str) -> dict:
        """Validate an access token and return its payload (including impersonating claim)."""
        try:
            payload = decode_token(token)
        except JWTError:
            raise AuthError("Invalid or expired token", "INVALID_TOKEN")

        if payload.get("type") != "access":
            raise AuthError("Invalid token type", "INVALID_TOKEN")

        # Impersonation tokens don't have a session row — validate via ImpersonationSession
        if payload.get("impersonating"):
            from app.models.impersonation import ImpersonationSession, ImpersonationStatus

            imp = payload["impersonating"]
            session_id = imp.get("session_id")
            if session_id:
                result = await self.db.execute(
                    select(ImpersonationSession).where(
                        ImpersonationSession.id == session_id
                    )
                )
                imp_session = result.scalar_one_or_none()
                if not imp_session or imp_session.status != ImpersonationStatus.ACTIVE:
                    raise AuthError("Impersonation session ended", "SESSION_REVOKED")
            return payload

        session = await self._get_session_by_jti(payload["jti"])
        if not session or not session.is_active:
            raise AuthError("Session revoked", "SESSION_REVOKED")

        return payload

    async def switch_tenant(self, user: User, tenant_id: str) -> dict:
        """Switch the user's active tenant. Returns new tokens with updated context."""
        tenant_ids = await self._get_user_tenant_ids(str(user.id))
        if tenant_id not in tenant_ids:
            raise AuthError("User does not have access to this tenant", "TENANT_ACCESS_DENIED")

        return await self._create_session(
            user, ip_address=None, user_agent=None, current_tenant_id=tenant_id
        )

    async def get_user_tenants(self, user_id: str) -> list[UserTenant]:
        """Get all tenant associations for a user."""
        result = await self.db.execute(
            select(UserTenant).where(UserTenant.user_id == user_id)
        )
        return list(result.scalars().all())

    # ── Private helpers ───────────────────────────────────────────

    async def _get_user_by_email(self, email: str) -> User | None:
        from sqlalchemy import func

        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def _get_user_by_id(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _get_session_by_jti(self, jti: str) -> Session | None:
        result = await self.db.execute(select(Session).where(Session.token_jti == jti))
        return result.scalar_one_or_none()

    async def _enforce_session_limit(self, user_id) -> None:
        """Revoke oldest sessions if user exceeds concurrent session limit."""
        active_sessions = await self.get_active_sessions(str(user_id))
        max_sessions = settings.max_concurrent_sessions

        if len(active_sessions) >= max_sessions:
            # Revoke oldest sessions to make room
            sessions_to_revoke = active_sessions[max_sessions - 1 :]
            for session in sessions_to_revoke:
                session.revoked_at = datetime.now(UTC)

    async def _get_user_tenant_ids(self, user_id: str) -> list[str]:
        """Get all tenant IDs a user has access to (explicit assignments + descendant tenants)."""
        from sqlalchemy import text

        result = await self.db.execute(
            text("""
                WITH RECURSIVE accessible AS (
                    SELECT t.id
                    FROM tenants t
                    JOIN user_tenants ut ON t.id = ut.tenant_id
                    WHERE ut.user_id = :user_id AND t.deleted_at IS NULL
                    UNION
                    SELECT t.id
                    FROM tenants t
                    JOIN accessible a ON t.parent_id = a.id
                    WHERE t.deleted_at IS NULL
                )
                SELECT id FROM accessible
            """),
            {"user_id": user_id},
        )
        return [str(row[0]) for row in result.all()]

    async def _get_default_tenant_id(self, user_id: str) -> str | None:
        """Get the user's default tenant ID."""
        result = await self.db.execute(
            select(UserTenant.tenant_id).where(
                UserTenant.user_id == user_id,
                UserTenant.is_default.is_(True),
            )
        )
        row = result.first()
        if row:
            return str(row[0])

        # Fall back to first tenant
        result = await self.db.execute(
            select(UserTenant.tenant_id)
            .where(UserTenant.user_id == user_id)
            .limit(1)
        )
        row = result.first()
        return str(row[0]) if row else None

    async def _create_session(
        self,
        user: User,
        ip_address: str | None,
        user_agent: str | None,
        current_tenant_id: str | None = None,
    ) -> dict:
        """Create tokens and a session record."""
        # Load tenant information
        tenant_ids = await self._get_user_tenant_ids(str(user.id))
        if not current_tenant_id and tenant_ids:
            current_tenant_id = await self._get_default_tenant_id(str(user.id))

        access_token, jti, expires_at = create_access_token(
            user_id=str(user.id),
            provider_id=str(user.provider_id),
            tenant_ids=tenant_ids,
            current_tenant_id=current_tenant_id,
        )
        refresh_token, refresh_expires_at = create_refresh_token(
            user_id=str(user.id),
            jti=jti,
        )

        session = Session(
            user_id=user.id,
            token_jti=jti,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(session)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "current_tenant_id": current_tenant_id,
        }
