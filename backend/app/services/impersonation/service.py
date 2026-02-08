"""
Overview: Impersonation service — manages standard and override impersonation lifecycle.
Architecture: Service layer for impersonation operations (Section 5)
Dependencies: sqlalchemy, temporalio, app.models, app.services.auth, app.services.permission
Concepts: Standard impersonation (JWT swap), override (password change), approval workflow
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.impersonation import ImpersonationMode, ImpersonationSession, ImpersonationStatus
from app.models.user import User
from app.models.user_role import UserRole
from app.models.user_tenant import UserTenant
from app.services.auth.jwt import create_access_token
from app.services.auth.password import hash_password, verify_password
from app.services.impersonation.config import ImpersonationConfigService

logger = logging.getLogger(__name__)
settings = get_settings()


class ImpersonationError(Exception):
    def __init__(self, message: str, code: str = "IMPERSONATION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ImpersonationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_impersonation(
        self,
        requester_id: str,
        target_user_id: str,
        tenant_id: str,
        mode: str,
        reason: str,
        password: str,
    ) -> ImpersonationSession:
        """Create an impersonation request and start Temporal workflow."""
        # Validate requester
        requester = await self._get_user(requester_id)
        if not requester:
            raise ImpersonationError("Requester not found", "USER_NOT_FOUND")

        # Re-authenticate requester
        if not requester.password_hash or not verify_password(password, requester.password_hash):
            raise ImpersonationError("Invalid password", "INVALID_CREDENTIALS")

        # Block nested impersonation (requester must not already be impersonating)
        active = await self.db.execute(
            select(ImpersonationSession).where(
                ImpersonationSession.requester_id == requester_id,
                ImpersonationSession.status == ImpersonationStatus.ACTIVE,
            )
        )
        if active.scalar_one_or_none():
            raise ImpersonationError(
                "Cannot impersonate while already impersonating",
                "NESTED_IMPERSONATION",
            )

        # Validate target user exists and is in the target tenant
        target = await self._get_user(target_user_id)
        if not target:
            raise ImpersonationError("Target user not found", "USER_NOT_FOUND")

        target_membership = await self.db.execute(
            select(UserTenant).where(
                UserTenant.user_id == target_user_id,
                UserTenant.tenant_id == tenant_id,
            )
        )
        if not target_membership.scalar_one_or_none():
            raise ImpersonationError(
                "Target user is not a member of this tenant",
                "TARGET_NOT_IN_TENANT",
            )

        # Check permission directly in target tenant (no hierarchy inheritance)
        imp_mode = ImpersonationMode(mode)
        perm_key = (
            "impersonation:session:create"
            if imp_mode == ImpersonationMode.STANDARD
            else "impersonation:override:create"
        )
        await self._check_direct_permission(requester_id, perm_key, tenant_id)

        # Block concurrent override on same target
        if imp_mode == ImpersonationMode.OVERRIDE:
            existing_override = await self.db.execute(
                select(ImpersonationSession).where(
                    ImpersonationSession.target_user_id == target_user_id,
                    ImpersonationSession.mode == ImpersonationMode.OVERRIDE,
                    ImpersonationSession.status.in_([
                        ImpersonationStatus.PENDING_APPROVAL,
                        ImpersonationStatus.APPROVED,
                        ImpersonationStatus.ACTIVE,
                    ]),
                )
            )
            if existing_override.scalar_one_or_none():
                raise ImpersonationError(
                    "An active override session already exists for this user",
                    "CONCURRENT_OVERRIDE",
                )

        # Create session
        session = ImpersonationSession(
            tenant_id=tenant_id,
            requester_id=requester_id,
            target_user_id=target_user_id,
            mode=imp_mode,
            status=ImpersonationStatus.PENDING_APPROVAL,
            reason=reason,
        )
        self.db.add(session)
        await self.db.flush()

        return session

    async def process_approval(
        self,
        session_id: str,
        approver_id: str,
        decision: str,
        reason: str | None = None,
    ) -> ImpersonationSession:
        """Record approval decision on a pending session."""
        session = await self._get_session(session_id)
        if not session:
            raise ImpersonationError("Session not found", "SESSION_NOT_FOUND")
        if session.status != ImpersonationStatus.PENDING_APPROVAL:
            raise ImpersonationError(
                "Session is not pending approval",
                "INVALID_SESSION_STATE",
            )

        session.approver_id = approver_id
        session.approval_decision_at = datetime.now(UTC)

        if decision == "approve":
            session.status = ImpersonationStatus.APPROVED
        else:
            session.status = ImpersonationStatus.REJECTED
            session.rejection_reason = reason

        await self.db.flush()
        return session

    async def start_standard_session(
        self, session_id: str, duration_minutes: int
    ) -> dict:
        """Activate standard impersonation — create JWT with impersonating claim."""
        session = await self._get_session(session_id)
        if not session:
            raise ImpersonationError("Session not found", "SESSION_NOT_FOUND")

        target = await self._get_user(str(session.target_user_id))
        if not target:
            raise ImpersonationError("Target user not found", "USER_NOT_FOUND")

        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=duration_minutes)

        # Create impersonation token
        impersonating_claim = {
            "original_user": str(session.requester_id),
            "original_tenant": str(session.tenant_id),
            "session_id": str(session.id),
            "started_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        token, jti, _ = create_access_token(
            user_id=str(target.id),
            provider_id=str(target.provider_id),
            tenant_ids=[str(session.tenant_id)],
            current_tenant_id=str(session.tenant_id),
            impersonating=impersonating_claim,
            expires_at=expires_at,
        )

        session.status = ImpersonationStatus.ACTIVE
        session.started_at = now
        session.expires_at = expires_at
        session.token_jti = jti
        await self.db.flush()

        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": duration_minutes * 60,
            "session_id": str(session.id),
        }

    async def start_override_session(
        self, session_id: str, new_password: str, duration_minutes: int
    ) -> None:
        """Activate override — save original state, deactivate target, change password."""
        session = await self._get_session(session_id)
        if not session:
            raise ImpersonationError("Session not found", "SESSION_NOT_FOUND")

        target = await self._get_user(str(session.target_user_id))
        if not target:
            raise ImpersonationError("Target user not found", "USER_NOT_FOUND")

        now = datetime.now(UTC)

        # Save original state for restoration
        session.original_password_hash = target.password_hash
        session.original_is_active = target.is_active

        # Deactivate target and set new password
        target.password_hash = hash_password(new_password)
        target.is_active = False

        session.status = ImpersonationStatus.ACTIVE
        session.started_at = now
        session.expires_at = now + timedelta(minutes=duration_minutes)
        await self.db.flush()

    async def end_session(self, session_id: str, reason: str = "manual") -> None:
        """End an active impersonation session."""
        session = await self._get_session(session_id)
        if not session:
            raise ImpersonationError("Session not found", "SESSION_NOT_FOUND")
        if session.status != ImpersonationStatus.ACTIVE:
            return  # Already ended

        session.status = ImpersonationStatus.ENDED
        session.ended_at = datetime.now(UTC)
        session.end_reason = reason

        if session.mode == ImpersonationMode.STANDARD:
            # Revoke impersonation token
            if session.token_jti:
                from app.models.session import Session as AuthSession

                result = await self.db.execute(
                    select(AuthSession).where(AuthSession.token_jti == session.token_jti)
                )
                auth_session = result.scalar_one_or_none()
                if auth_session and auth_session.is_active:
                    auth_session.revoked_at = datetime.now(UTC)

        elif session.mode == ImpersonationMode.OVERRIDE:
            # Restore target user's original state
            target = await self._get_user(str(session.target_user_id))
            if target:
                if session.original_password_hash is not None:
                    target.password_hash = session.original_password_hash
                if session.original_is_active is not None:
                    target.is_active = session.original_is_active

        await self.db.flush()

    async def expire_session(self, session_id: str) -> None:
        """Mark a pending-approval session as expired (approval timeout)."""
        session = await self._get_session(session_id)
        if not session:
            return
        if session.status in (
            ImpersonationStatus.PENDING_APPROVAL,
            ImpersonationStatus.APPROVED,
        ):
            session.status = ImpersonationStatus.EXPIRED
            session.ended_at = datetime.now(UTC)
            session.end_reason = "approval_timeout"
            await self.db.flush()

    async def extend_session(self, session_id: str, minutes: int) -> None:
        """Extend an active session's expiry, capped at max duration."""
        session = await self._get_session(session_id)
        if not session:
            raise ImpersonationError("Session not found", "SESSION_NOT_FOUND")
        if session.status != ImpersonationStatus.ACTIVE:
            raise ImpersonationError("Session is not active", "INVALID_SESSION_STATE")

        config_service = ImpersonationConfigService(self.db)
        config = await config_service.get_config(str(session.tenant_id))
        max_minutes = config["max_duration_minutes"]

        if session.started_at:
            max_expires = session.started_at + timedelta(minutes=max_minutes)
            new_expires = session.expires_at + timedelta(minutes=minutes)
            session.expires_at = min(new_expires, max_expires)
            await self.db.flush()

    async def get_session(self, session_id: str) -> ImpersonationSession | None:
        """Get a single impersonation session."""
        return await self._get_session(session_id)

    async def get_sessions(
        self, tenant_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[ImpersonationSession], int]:
        """List impersonation sessions for a tenant."""
        from sqlalchemy import func

        count_result = await self.db.execute(
            select(func.count()).select_from(ImpersonationSession).where(
                ImpersonationSession.tenant_id == tenant_id
            )
        )
        total = count_result.scalar() or 0

        result = await self.db.execute(
            select(ImpersonationSession)
            .where(ImpersonationSession.tenant_id == tenant_id)
            .order_by(ImpersonationSession.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        sessions = list(result.scalars().all())
        return sessions, total

    # ── Private helpers ───────────────────────────────────────────

    async def _get_user(self, user_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _get_session(self, session_id: str) -> ImpersonationSession | None:
        result = await self.db.execute(
            select(ImpersonationSession).where(ImpersonationSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def _check_direct_permission(
        self, user_id: str, permission_key: str, tenant_id: str
    ) -> None:
        """Check permission directly in target tenant (no hierarchy walk)."""
        from app.models.permission import Permission
        from app.models.role_permission import RolePermission

        parts = permission_key.split(":")
        domain, resource, action = parts[0], parts[1], parts[2]

        result = await self.db.execute(
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(
                UserRole.user_id == user_id,
                UserRole.tenant_id == tenant_id,
                Permission.domain == domain,
                Permission.resource == resource,
                Permission.action == action,
                # Check expiry
                (
                    (UserRole.expires_at.is_(None))
                    | (UserRole.expires_at > datetime.now(UTC))
                ),
            )
            .limit(1)
        )
        if not result.scalar_one_or_none():
            raise ImpersonationError(
                f"Permission '{permission_key}' not granted in this tenant",
                "PERMISSION_DENIED",
            )
