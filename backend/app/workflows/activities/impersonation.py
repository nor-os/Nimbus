"""
Overview: Temporal activities for impersonation workflow lifecycle.
Architecture: Impersonation workflow activities (Section 9)
Dependencies: temporalio, app.services.impersonation, app.services.audit, app.services.audit.taxonomy
Concepts: Temporal activities, impersonation lifecycle, audit logging, event taxonomy
"""

import logging
import secrets
import string
from dataclasses import dataclass

from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ActivateInput:
    session_id: str
    mode: str
    duration_minutes: int


@dataclass
class ActivateResult:
    success: bool
    access_token: str | None = None
    expires_in: int | None = None
    error: str | None = None


@dataclass
class EndInput:
    session_id: str
    reason: str


@dataclass
class AuditInput:
    session_id: str
    action: str
    details: dict | None = None


@dataclass
class NotifyInput:
    session_id: str
    approver_ids: list[str] | None = None


@activity.defn
async def activate_impersonation_session(input: ActivateInput) -> ActivateResult:
    """Activate a standard or override impersonation session."""
    from app.db.session import async_session_factory
    from app.services.impersonation.service import ImpersonationService

    try:
        async with async_session_factory() as db:
            service = ImpersonationService(db)
            if input.mode == "STANDARD":
                result = await service.start_standard_session(
                    input.session_id, input.duration_minutes
                )
                await db.commit()
                return ActivateResult(
                    success=True,
                    access_token=result["access_token"],
                    expires_in=result["expires_in"],
                )
            else:
                # Override mode: generate temporary password
                temp_password = _generate_temp_password()
                await service.start_override_session(
                    input.session_id, temp_password, input.duration_minutes
                )
                await db.commit()
                logger.info(
                    "Override session %s activated — temporary password set",
                    input.session_id,
                )
                return ActivateResult(success=True)
    except Exception as e:
        logger.exception("Failed to activate impersonation session %s", input.session_id)
        return ActivateResult(success=False, error=str(e))


@activity.defn
async def end_impersonation_session(input: EndInput) -> bool:
    """End an active impersonation session (revoke token or restore user)."""
    from app.db.session import async_session_factory
    from app.services.impersonation.service import ImpersonationService

    try:
        async with async_session_factory() as db:
            service = ImpersonationService(db)
            await service.end_session(input.session_id, input.reason)
            await db.commit()
            return True
    except Exception:
        logger.exception("Failed to end impersonation session %s", input.session_id)
        return False


@activity.defn
async def notify_approver(input: NotifyInput) -> bool:
    """Placeholder: notify approvers about a pending impersonation request.

    Phase 9 will replace this with real notification delivery.
    """
    logger.info(
        "Impersonation approval requested for session %s — approvers: %s",
        input.session_id,
        input.approver_ids or "tenant_admins",
    )
    return True


_IMPERSONATION_ACTION_TO_EVENT_TYPE: dict[str, str] = {
    "start": "security.impersonate.start",
    "end": "security.impersonate.end",
    "reject": "security.impersonate.reject",
    "expire": "security.impersonate.expire",
    "activate": "security.impersonate.start",
    "override_start": "security.override",
    "override_end": "security.impersonate.end",
}


@activity.defn
async def record_impersonation_audit(input: AuditInput) -> bool:
    """Write an audit log entry for an impersonation lifecycle event."""
    from app.db.session import async_session_factory
    from app.models.audit import AuditPriority
    from app.models.impersonation import ImpersonationMode, ImpersonationSession
    from app.services.audit.service import AuditService

    try:
        async with async_session_factory() as db:
            from sqlalchemy import select

            result = await db.execute(
                select(ImpersonationSession).where(
                    ImpersonationSession.id == input.session_id
                )
            )
            session = result.scalar_one_or_none()
            if not session:
                return False

            # Derive event_type from action string and impersonation mode
            action_key = input.action.lower()
            if session.mode == ImpersonationMode.OVERRIDE and action_key == "start":
                action_key = "override_start"
            elif session.mode == ImpersonationMode.OVERRIDE and action_key == "end":
                action_key = "override_end"
            event_type = _IMPERSONATION_ACTION_TO_EVENT_TYPE.get(
                action_key, "security.impersonate.start"
            )

            priority = AuditPriority.WARN
            if event_type == "security.override":
                priority = AuditPriority.CRITICAL

            audit = AuditService(db)
            await audit.log(
                tenant_id=str(session.tenant_id),
                event_type=event_type,
                actor_type="USER",
                actor_id=str(session.requester_id),
                impersonator_id=str(session.requester_id),
                resource_type="security:impersonation",
                resource_id=str(session.id),
                resource_name=input.action,
                new_values=input.details,
                priority=priority,
                metadata={
                    "impersonation_mode": session.mode.value,
                    "target_user_id": str(session.target_user_id),
                },
            )
            await db.commit()
            return True
    except Exception:
        logger.exception("Failed to record impersonation audit for %s", input.session_id)
        return False


@activity.defn
async def expire_impersonation_session(input_session_id: str) -> bool:
    """Mark a session as expired (approval timeout)."""
    from app.db.session import async_session_factory
    from app.services.impersonation.service import ImpersonationService

    try:
        async with async_session_factory() as db:
            service = ImpersonationService(db)
            await service.expire_session(input_session_id)
            await db.commit()
            return True
    except Exception:
        logger.exception("Failed to expire impersonation session %s", input_session_id)
        return False


@activity.defn
async def reject_impersonation_session(input_session_id: str) -> bool:
    """Mark a session as rejected."""
    from app.db.session import async_session_factory
    from app.models.impersonation import ImpersonationSession, ImpersonationStatus

    try:
        async with async_session_factory() as db:
            from sqlalchemy import select

            result = await db.execute(
                select(ImpersonationSession).where(
                    ImpersonationSession.id == input_session_id
                )
            )
            session = result.scalar_one_or_none()
            if session and session.status == ImpersonationStatus.PENDING_APPROVAL:
                session.status = ImpersonationStatus.REJECTED
                session.rejection_reason = "Approval timeout"
                await db.commit()
            return True
    except Exception:
        logger.exception("Failed to reject impersonation session %s", input_session_id)
        return False


def _generate_temp_password(length: int = 24) -> str:
    """Generate a cryptographically secure temporary password."""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return "".join(secrets.choice(alphabet) for _ in range(length))
