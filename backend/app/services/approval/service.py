"""
Overview: Approval service — manages policies, requests, steps, decisions, and delegation.
Architecture: Service layer for approval workflow operations (Section 5)
Dependencies: sqlalchemy, app.models.approval_*, app.models.user, app.models.user_role
Concepts: Approval chains, sequential/parallel/quorum, delegation, policy snapshots
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.approval_policy import ApprovalChainMode, ApprovalPolicy
from app.models.approval_request import ApprovalRequest, ApprovalRequestStatus
from app.models.approval_step import ApprovalStep, ApprovalStepStatus
from app.models.user_role import UserRole

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    def __init__(self, message: str, code: str = "APPROVAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ApprovalService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Policy Management ─────────────────────────────────

    async def get_policy(
        self, tenant_id: str, operation_type: str
    ) -> ApprovalPolicy | None:
        """Get the active approval policy for a tenant + operation type."""
        result = await self.db.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.tenant_id == tenant_id,
                ApprovalPolicy.operation_type == operation_type,
                ApprovalPolicy.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_policies(self, tenant_id: str) -> list[ApprovalPolicy]:
        """List all active policies for a tenant."""
        result = await self.db.execute(
            select(ApprovalPolicy)
            .where(
                ApprovalPolicy.tenant_id == tenant_id,
                ApprovalPolicy.deleted_at.is_(None),
            )
            .order_by(ApprovalPolicy.operation_type)
        )
        return list(result.scalars().all())

    async def create_policy(
        self, tenant_id: str, data: dict
    ) -> ApprovalPolicy:
        """Create a new approval policy."""
        existing = await self.get_policy(tenant_id, data["operation_type"])
        if existing:
            raise ApprovalError(
                f"Policy for '{data['operation_type']}' already exists",
                "POLICY_EXISTS",
            )

        policy = ApprovalPolicy(
            tenant_id=tenant_id,
            operation_type=data["operation_type"],
            chain_mode=ApprovalChainMode(data.get("chain_mode", "SEQUENTIAL")),
            quorum_required=data.get("quorum_required", 1),
            timeout_minutes=data.get("timeout_minutes", 1440),
            escalation_user_ids=data.get("escalation_user_ids"),
            approver_role_names=data.get("approver_role_names"),
            approver_user_ids=data.get("approver_user_ids"),
            approver_group_ids=data.get("approver_group_ids"),
            is_active=data.get("is_active", True),
        )
        self.db.add(policy)
        await self.db.flush()
        return policy

    async def update_policy(
        self, tenant_id: str, policy_id: str, data: dict
    ) -> ApprovalPolicy | None:
        """Update an existing approval policy."""
        result = await self.db.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.id == policy_id,
                ApprovalPolicy.tenant_id == tenant_id,
                ApprovalPolicy.deleted_at.is_(None),
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return None

        for field in (
            "chain_mode", "quorum_required", "timeout_minutes",
            "escalation_user_ids", "approver_role_names", "approver_user_ids",
            "approver_group_ids", "is_active",
        ):
            if field in data and data[field] is not None:
                if field == "chain_mode":
                    setattr(policy, field, ApprovalChainMode(data[field]))
                else:
                    setattr(policy, field, data[field])

        await self.db.flush()
        return policy

    async def delete_policy(self, tenant_id: str, policy_id: str) -> bool:
        """Soft-delete an approval policy."""
        result = await self.db.execute(
            select(ApprovalPolicy).where(
                ApprovalPolicy.id == policy_id,
                ApprovalPolicy.tenant_id == tenant_id,
                ApprovalPolicy.deleted_at.is_(None),
            )
        )
        policy = result.scalar_one_or_none()
        if not policy:
            return False

        policy.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def resolve_approvers(
        self, tenant_id: str, policy: ApprovalPolicy
    ) -> list[str]:
        """Resolve list of approver user IDs from policy configuration.

        Priority:
        1. approver_user_ids — explicit user list
        2. approver_role_names + approver_group_ids — union of role members and group members
        3. Falls back to Tenant Admin role members.
        """
        user_id_set: set[str] = set()

        if policy.approver_user_ids:
            user_id_set.update(str(uid) for uid in policy.approver_user_ids)

        # Resolve from groups
        if policy.approver_group_ids:
            from app.models.user_group import UserGroup

            result = await self.db.execute(
                select(UserGroup.user_id)
                .where(
                    UserGroup.group_id.in_(
                        [str(gid) for gid in policy.approver_group_ids]
                    ),
                )
                .distinct()
            )
            user_id_set.update(str(row[0]) for row in result.all())

        # Resolve from roles
        if policy.approver_role_names:
            from app.models.role import Role

            result = await self.db.execute(
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRole.tenant_id == tenant_id,
                    Role.name.in_(policy.approver_role_names),
                    or_(
                        UserRole.expires_at.is_(None),
                        UserRole.expires_at > datetime.now(UTC),
                    ),
                )
                .distinct()
            )
            user_id_set.update(str(row[0]) for row in result.all())

        # If nothing configured, fall back to role-based resolution
        if not user_id_set and not policy.approver_user_ids and not policy.approver_group_ids:
            role_names = policy.approver_role_names or ["Tenant Admin"]
            from app.models.role import Role

            result = await self.db.execute(
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRole.tenant_id == tenant_id,
                    Role.name.in_(role_names),
                    or_(
                        UserRole.expires_at.is_(None),
                        UserRole.expires_at > datetime.now(UTC),
                    ),
                )
                .distinct()
            )
            user_id_set.update(str(row[0]) for row in result.all())

        if not user_id_set:
            # Final fallback: Tenant Admin
            from app.models.role import Role

            result = await self.db.execute(
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRole.tenant_id == tenant_id,
                    Role.name == "Tenant Admin",
                )
                .distinct()
            )
            user_id_set.update(str(row[0]) for row in result.all())

        return list(user_id_set)

    # ── Request Management ────────────────────────────────

    async def create_request(
        self,
        tenant_id: str,
        requester_id: str,
        operation_type: str,
        title: str,
        description: str | None,
        context: dict | None,
        parent_workflow_id: str | None = None,
    ) -> ApprovalRequest:
        """Create an approval request + steps based on the active policy.

        Returns the request with workflow_id unset — caller starts the workflow.
        """
        policy = await self.get_policy(tenant_id, operation_type)

        # Defaults if no policy
        chain_mode = ApprovalChainMode.SEQUENTIAL
        quorum_required = 1

        if policy and policy.is_active:
            chain_mode = policy.chain_mode
            quorum_required = policy.quorum_required

        request = ApprovalRequest(
            tenant_id=tenant_id,
            operation_type=operation_type,
            requester_id=requester_id,
            chain_mode=chain_mode.value,
            quorum_required=quorum_required,
            status=ApprovalRequestStatus.PENDING,
            title=title,
            description=description,
            context=context,
            parent_workflow_id=parent_workflow_id,
        )
        self.db.add(request)
        await self.db.flush()

        # Resolve approvers and create steps
        if policy and policy.is_active:
            approver_ids = await self.resolve_approvers(tenant_id, policy)
        else:
            # Default: tenant_admin members
            from app.models.role import Role

            result = await self.db.execute(
                select(UserRole.user_id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    UserRole.tenant_id == tenant_id,
                    Role.name == "tenant_admin",
                )
                .distinct()
            )
            approver_ids = [str(row[0]) for row in result.all()]

        # Exclude requester from approvers
        approver_ids = [uid for uid in approver_ids if uid != requester_id]

        if not approver_ids:
            raise ApprovalError(
                "No approvers available for this operation",
                "NO_APPROVERS",
            )

        for i, approver_id in enumerate(approver_ids):
            step_order = i if chain_mode == ApprovalChainMode.SEQUENTIAL else 0
            step = ApprovalStep(
                tenant_id=tenant_id,
                approval_request_id=request.id,
                step_order=step_order,
                approver_id=approver_id,
                status=ApprovalStepStatus.PENDING,
            )
            self.db.add(step)

        await self.db.flush()

        # Re-fetch with steps
        result = await self.db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.steps))
            .where(ApprovalRequest.id == request.id)
        )
        return result.scalar_one()

    async def get_request(
        self, tenant_id: str, request_id: str
    ) -> ApprovalRequest | None:
        """Get a single approval request with eager-loaded steps."""
        result = await self.db.execute(
            select(ApprovalRequest)
            .options(selectinload(ApprovalRequest.steps))
            .where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_requests(
        self,
        tenant_id: str,
        status: str | None = None,
        requester_id: str | None = None,
        approver_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ApprovalRequest], int]:
        """List approval requests with optional filters."""
        conditions = [ApprovalRequest.tenant_id == tenant_id]
        if status:
            conditions.append(ApprovalRequest.status == ApprovalRequestStatus(status))
        if requester_id:
            conditions.append(ApprovalRequest.requester_id == requester_id)

        if approver_id:
            # Join to steps to filter by approver
            stmt = (
                select(ApprovalRequest)
                .join(ApprovalStep, ApprovalStep.approval_request_id == ApprovalRequest.id)
                .where(
                    *conditions,
                    or_(
                        ApprovalStep.approver_id == approver_id,
                        ApprovalStep.delegate_to_id == approver_id,
                    ),
                )
                .distinct()
            )
        else:
            stmt = select(ApprovalRequest).where(*conditions)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Paginated results
        result = await self.db.execute(
            stmt.options(selectinload(ApprovalRequest.steps))
            .order_by(ApprovalRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().unique().all())
        return items, total

    async def get_pending_for_user(
        self, tenant_id: str, user_id: str, offset: int = 0, limit: int = 50
    ) -> tuple[list[ApprovalRequest], int]:
        """Get approval requests where user has a PENDING step (inbox query)."""
        stmt = (
            select(ApprovalRequest)
            .join(ApprovalStep, ApprovalStep.approval_request_id == ApprovalRequest.id)
            .where(
                ApprovalRequest.tenant_id == tenant_id,
                ApprovalRequest.status == ApprovalRequestStatus.PENDING,
                ApprovalStep.status == ApprovalStepStatus.PENDING,
                or_(
                    ApprovalStep.approver_id == user_id,
                    ApprovalStep.delegate_to_id == user_id,
                ),
            )
            .distinct()
        )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        result = await self.db.execute(
            stmt.options(selectinload(ApprovalRequest.steps))
            .order_by(ApprovalRequest.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        items = list(result.scalars().unique().all())
        return items, total

    async def submit_decision(
        self,
        tenant_id: str,
        step_id: str,
        approver_id: str,
        decision: str,
        reason: str | None = None,
    ) -> ApprovalStep:
        """Submit an approve/reject decision for a step."""
        result = await self.db.execute(
            select(ApprovalStep).where(
                ApprovalStep.id == step_id,
                ApprovalStep.tenant_id == tenant_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise ApprovalError("Approval step not found", "STEP_NOT_FOUND")
        if step.status != ApprovalStepStatus.PENDING:
            raise ApprovalError("Step is not pending", "INVALID_STEP_STATE")

        # Validate approver matches step or delegate
        effective_approver = (
            str(step.delegate_to_id) if step.delegate_to_id else str(step.approver_id)
        )
        if approver_id != effective_approver:
            raise ApprovalError(
                "You are not the assigned approver for this step",
                "NOT_AUTHORIZED",
            )

        step.status = (
            ApprovalStepStatus.APPROVED if decision == "approve"
            else ApprovalStepStatus.REJECTED
        )
        step.decision_at = datetime.now(UTC)
        step.reason = reason
        await self.db.flush()

        # Check if the overall request is resolved
        request = await self.get_request(tenant_id, str(step.approval_request_id))
        if request:
            resolved_status = self.check_resolution(request)
            if resolved_status:
                request.status = resolved_status
                request.resolved_at = datetime.now(UTC)
                await self.db.flush()

        return step

    async def delegate_step(
        self,
        tenant_id: str,
        step_id: str,
        approver_id: str,
        delegate_to_id: str,
    ) -> ApprovalStep:
        """Delegate a pending step to another user."""
        result = await self.db.execute(
            select(ApprovalStep).where(
                ApprovalStep.id == step_id,
                ApprovalStep.tenant_id == tenant_id,
            )
        )
        step = result.scalar_one_or_none()
        if not step:
            raise ApprovalError("Approval step not found", "STEP_NOT_FOUND")
        if step.status != ApprovalStepStatus.PENDING:
            raise ApprovalError("Step is not pending", "INVALID_STEP_STATE")

        effective_approver = (
            str(step.delegate_to_id) if step.delegate_to_id else str(step.approver_id)
        )
        if approver_id != effective_approver:
            raise ApprovalError(
                "You are not the assigned approver for this step",
                "NOT_AUTHORIZED",
            )

        # Mark original step as DELEGATED
        step.status = ApprovalStepStatus.DELEGATED
        step.delegate_to_id = uuid.UUID(delegate_to_id)
        step.decision_at = datetime.now(UTC)
        step.reason = f"Delegated to {delegate_to_id}"

        # Create new PENDING step for the delegate
        new_step = ApprovalStep(
            tenant_id=tenant_id,
            approval_request_id=step.approval_request_id,
            step_order=step.step_order,
            approver_id=uuid.UUID(delegate_to_id),
            status=ApprovalStepStatus.PENDING,
        )
        self.db.add(new_step)
        await self.db.flush()
        return new_step

    async def cancel_request(self, tenant_id: str, request_id: str) -> bool:
        """Cancel a pending approval request."""
        request = await self.get_request(tenant_id, request_id)
        if not request:
            return False
        if request.status != ApprovalRequestStatus.PENDING:
            return False

        request.status = ApprovalRequestStatus.CANCELLED
        request.resolved_at = datetime.now(UTC)

        # Mark remaining PENDING steps as SKIPPED
        for step in request.steps:
            if step.status == ApprovalStepStatus.PENDING:
                step.status = ApprovalStepStatus.SKIPPED
                step.decision_at = datetime.now(UTC)
                step.reason = "Request cancelled"

        await self.db.flush()
        return True

    def check_resolution(
        self, request: ApprovalRequest
    ) -> ApprovalRequestStatus | None:
        """Check if an approval chain is resolved based on mode.

        Returns the final status if resolved, None if still pending.
        """
        steps = request.steps or []
        if not steps:
            return None

        chain_mode = request.chain_mode
        quorum_required = request.quorum_required

        active_steps = [
            s for s in steps
            if s.status not in (ApprovalStepStatus.DELEGATED, ApprovalStepStatus.SKIPPED)
        ]

        approved = sum(1 for s in active_steps if s.status == ApprovalStepStatus.APPROVED)
        rejected = sum(1 for s in active_steps if s.status == ApprovalStepStatus.REJECTED)
        pending = sum(1 for s in active_steps if s.status == ApprovalStepStatus.PENDING)
        expired = sum(1 for s in active_steps if s.status == ApprovalStepStatus.EXPIRED)
        total = len(active_steps)

        if chain_mode == ApprovalChainMode.QUORUM.value:
            if approved >= quorum_required:
                return ApprovalRequestStatus.APPROVED
            # If it's impossible to reach quorum
            if rejected > (total - quorum_required):
                return ApprovalRequestStatus.REJECTED
            if pending == 0 and expired > 0:
                return ApprovalRequestStatus.EXPIRED
        elif chain_mode in (
            ApprovalChainMode.SEQUENTIAL.value,
            ApprovalChainMode.PARALLEL.value,
        ):
            if rejected > 0:
                return ApprovalRequestStatus.REJECTED
            if approved == total:
                return ApprovalRequestStatus.APPROVED
            if pending == 0 and expired > 0:
                return ApprovalRequestStatus.EXPIRED

        return None

    async def expire_pending_steps(
        self, tenant_id: str, request_id: str
    ) -> None:
        """Mark all remaining PENDING steps on a request as EXPIRED."""
        result = await self.db.execute(
            select(ApprovalStep).where(
                ApprovalStep.approval_request_id == request_id,
                ApprovalStep.tenant_id == tenant_id,
                ApprovalStep.status == ApprovalStepStatus.PENDING,
            )
        )
        steps = list(result.scalars().all())
        now = datetime.now(UTC)
        for step in steps:
            step.status = ApprovalStepStatus.EXPIRED
            step.decision_at = now
            step.reason = "Timed out"
        await self.db.flush()

    async def resolve_request(
        self, tenant_id: str, request_id: str, status: str
    ) -> None:
        """Update an approval request to its final status."""
        result = await self.db.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.id == request_id,
                ApprovalRequest.tenant_id == tenant_id,
            )
        )
        request = result.scalar_one_or_none()
        if request and request.status == ApprovalRequestStatus.PENDING:
            request.status = ApprovalRequestStatus(status)
            request.resolved_at = datetime.now(UTC)
            await self.db.flush()
