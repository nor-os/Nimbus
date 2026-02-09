"""
Overview: Temporal activities for the ApprovalChainWorkflow — notifications, audit, resolution.
Architecture: Approval workflow activities (Section 9)
Dependencies: temporalio, app.services.approval, app.services.notification, app.services.audit
Concepts: Temporal activities, approval notifications, audit logging, request resolution
"""

import logging
from dataclasses import dataclass, field

from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ApprovalNotifyInput:
    request_id: str
    approver_ids: list[str]
    title: str
    description: str
    tenant_id: str


@dataclass
class ApprovalAuditInput:
    request_id: str
    tenant_id: str
    actor_id: str
    action: str  # requested, approved, rejected, delegated, expired, cancelled
    details: dict | None = None


@dataclass
class ResolveInput:
    request_id: str
    tenant_id: str
    status: str  # APPROVED, REJECTED, EXPIRED
    requester_id: str = ""
    title: str = ""


@dataclass
class ExpireInput:
    request_id: str
    tenant_id: str


@dataclass
class CreateApprovalRequestInput:
    tenant_id: str
    requester_id: str
    operation_type: str
    title: str
    description: str | None = None
    context: dict | None = None
    parent_workflow_id: str | None = None


@dataclass
class CreateApprovalRequestResult:
    request_id: str
    approver_ids: list[str] = field(default_factory=list)
    chain_mode: str = "SEQUENTIAL"
    quorum_required: int = 1
    timeout_minutes: int = 1440
    escalation_user_ids: list[str] = field(default_factory=list)


_APPROVAL_ACTION_TO_EVENT_TYPE: dict[str, str] = {
    "requested": "approval.requested",
    "approved": "approval.approved",
    "rejected": "approval.rejected",
    "delegated": "approval.delegated",
    "expired": "approval.expired",
    "cancelled": "approval.cancelled",
}


@activity.defn
async def send_approval_notification(input: ApprovalNotifyInput) -> bool:
    """Send approval notifications to all approvers via NotificationService."""
    from app.db.session import async_session_factory
    from app.models.notification import NotificationCategory
    from app.services.notification.service import NotificationService

    try:
        async with async_session_factory() as db:
            service = NotificationService(db)
            await service.send(
                tenant_id=input.tenant_id,
                user_ids=input.approver_ids,
                category=NotificationCategory.APPROVAL,
                event_type="approval.requested",
                title=input.title,
                body=input.description or "An approval request requires your attention.",
                related_resource_type="approval_request",
                related_resource_id=input.request_id,
            )
            await db.commit()
        return True
    except Exception:
        logger.exception(
            "Failed to send approval notifications for request %s", input.request_id
        )
        return False


@activity.defn
async def record_approval_audit(input: ApprovalAuditInput) -> bool:
    """Write an audit log entry for an approval lifecycle event."""
    from app.db.session import async_session_factory
    from app.models.audit import AuditPriority
    from app.services.audit.service import AuditService

    try:
        async with async_session_factory() as db:
            event_type = _APPROVAL_ACTION_TO_EVENT_TYPE.get(
                input.action, "approval.requested"
            )
            priority = AuditPriority.INFO
            if input.action in ("rejected", "expired"):
                priority = AuditPriority.WARN

            audit = AuditService(db)
            await audit.log(
                tenant_id=input.tenant_id,
                event_type=event_type,
                actor_type="USER",
                actor_id=input.actor_id,
                resource_type="approval:request",
                resource_id=input.request_id,
                resource_name=input.action,
                new_values=input.details,
                priority=priority,
            )
            await db.commit()
        return True
    except Exception:
        logger.exception(
            "Failed to record approval audit for request %s", input.request_id
        )
        return False


@activity.defn
async def resolve_approval_request(input: ResolveInput) -> bool:
    """Update ApprovalRequest to final status and notify requester."""
    from app.db.session import async_session_factory
    from app.models.notification import NotificationCategory
    from app.services.approval.service import ApprovalService
    from app.services.notification.service import NotificationService

    try:
        async with async_session_factory() as db:
            approval_service = ApprovalService(db)
            await approval_service.resolve_request(
                input.tenant_id, input.request_id, input.status
            )

            # Notify requester of the result
            if input.requester_id:
                notification_service = NotificationService(db)
                status_label = input.status.lower()
                await notification_service.send_to_user(
                    tenant_id=input.tenant_id,
                    user_id=input.requester_id,
                    category=NotificationCategory.APPROVAL,
                    event_type=f"approval.{status_label}",
                    title=f"Approval {status_label}: {input.title}",
                    body=f"Your approval request has been {status_label}.",
                    related_resource_type="approval_request",
                    related_resource_id=input.request_id,
                )

            await db.commit()
        return True
    except Exception:
        logger.exception(
            "Failed to resolve approval request %s", input.request_id
        )
        return False


@activity.defn
async def expire_approval_steps(input: ExpireInput) -> bool:
    """Mark remaining PENDING steps as EXPIRED."""
    from app.db.session import async_session_factory
    from app.services.approval.service import ApprovalService

    try:
        async with async_session_factory() as db:
            service = ApprovalService(db)
            await service.expire_pending_steps(input.tenant_id, input.request_id)
            await db.commit()
        return True
    except Exception:
        logger.exception(
            "Failed to expire steps for request %s", input.request_id
        )
        return False


@activity.defn
async def create_approval_request_activity(
    input: CreateApprovalRequestInput,
) -> CreateApprovalRequestResult:
    """Create an approval request + steps via ApprovalService. Returns request metadata."""
    from app.db.session import async_session_factory
    from app.services.approval.service import ApprovalService

    async with async_session_factory() as db:
        service = ApprovalService(db)
        request = await service.create_request(
            tenant_id=input.tenant_id,
            requester_id=input.requester_id,
            operation_type=input.operation_type,
            title=input.title,
            description=input.description,
            context=input.context,
            parent_workflow_id=input.parent_workflow_id,
        )

        # Get policy for timeout/escalation info
        policy = await service.get_policy(input.tenant_id, input.operation_type)
        escalation_ids: list[str] = []
        timeout_minutes = 1440
        if policy:
            escalation_ids = [str(uid) for uid in (policy.escalation_user_ids or [])]
            timeout_minutes = policy.timeout_minutes

        approver_ids = [str(s.approver_id) for s in request.steps]

        await db.commit()

        return CreateApprovalRequestResult(
            request_id=str(request.id),
            approver_ids=approver_ids,
            chain_mode=request.chain_mode,
            quorum_required=request.quorum_required,
            timeout_minutes=timeout_minutes,
            escalation_user_ids=escalation_ids,
        )
