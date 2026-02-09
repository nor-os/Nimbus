"""
Overview: GraphQL types for approval workflow data.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: GraphQL types, approval policies, requests, steps
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry


@strawberry.enum
class ApprovalChainModeGQL(Enum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    QUORUM = "QUORUM"


@strawberry.enum
class ApprovalRequestStatusGQL(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@strawberry.enum
class ApprovalStepStatusGQL(Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELEGATED = "DELEGATED"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"


@strawberry.type
class ApprovalPolicyType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    operation_type: str
    chain_mode: ApprovalChainModeGQL
    quorum_required: int
    timeout_minutes: int
    escalation_user_ids: list[str] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[str] | None = None
    approver_group_ids: list[str] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ApprovalStepType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    approval_request_id: uuid.UUID
    step_order: int
    approver_id: uuid.UUID
    delegate_to_id: uuid.UUID | None = None
    status: ApprovalStepStatusGQL
    decision_at: datetime | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ApprovalRequestType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    operation_type: str
    requester_id: uuid.UUID
    workflow_id: str | None = None
    parent_workflow_id: str | None = None
    chain_mode: str
    quorum_required: int
    status: ApprovalRequestStatusGQL
    title: str
    description: str | None = None
    context: strawberry.scalars.JSON | None = None
    resolved_at: datetime | None = None
    steps: list[ApprovalStepType]
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ApprovalRequestListType:
    items: list[ApprovalRequestType]
    total: int


@strawberry.input
class ApprovalPolicyInput:
    operation_type: str
    chain_mode: ApprovalChainModeGQL = ApprovalChainModeGQL.SEQUENTIAL
    quorum_required: int = 1
    timeout_minutes: int = 1440
    escalation_user_ids: list[str] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[str] | None = None
    approver_group_ids: list[str] | None = None
    is_active: bool = True


@strawberry.input
class ApprovalPolicyUpdateInput:
    chain_mode: ApprovalChainModeGQL | None = None
    quorum_required: int | None = None
    timeout_minutes: int | None = None
    escalation_user_ids: list[str] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[str] | None = None
    approver_group_ids: list[str] | None = None
    is_active: bool | None = None


@strawberry.input
class ApprovalDecisionGQLInput:
    step_id: uuid.UUID
    decision: str  # "approve" | "reject"
    reason: str | None = None


@strawberry.input
class ApprovalDelegateGQLInput:
    step_id: uuid.UUID
    delegate_to_id: uuid.UUID
