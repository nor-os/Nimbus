"""
Overview: Pydantic schemas for approval workflow endpoints — request/response validation.
Architecture: API schema definitions for approval policies, requests, steps (Section 7.1, 7.2)
Dependencies: pydantic
Concepts: Approval chains, policy configuration, decision submission, delegation
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ApprovalChainModeEnum(StrEnum):
    SEQUENTIAL = "SEQUENTIAL"
    PARALLEL = "PARALLEL"
    QUORUM = "QUORUM"


class ApprovalRequestStatusEnum(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ApprovalStepStatusEnum(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DELEGATED = "DELEGATED"
    SKIPPED = "SKIPPED"
    EXPIRED = "EXPIRED"


# ── Policy Schemas ───────────────────────────────────────


class ApprovalPolicyCreate(BaseModel):
    operation_type: str = Field(..., min_length=1, max_length=100)
    chain_mode: ApprovalChainModeEnum = ApprovalChainModeEnum.SEQUENTIAL
    quorum_required: int = Field(1, ge=1, le=100)
    timeout_minutes: int = Field(1440, ge=1, le=43200)
    escalation_user_ids: list[uuid.UUID] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[uuid.UUID] | None = None
    approver_group_ids: list[uuid.UUID] | None = None
    is_active: bool = True


class ApprovalPolicyUpdate(BaseModel):
    chain_mode: ApprovalChainModeEnum | None = None
    quorum_required: int | None = Field(None, ge=1, le=100)
    timeout_minutes: int | None = Field(None, ge=1, le=43200)
    escalation_user_ids: list[uuid.UUID] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[uuid.UUID] | None = None
    approver_group_ids: list[uuid.UUID] | None = None
    is_active: bool | None = None


class ApprovalPolicyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    operation_type: str
    chain_mode: ApprovalChainModeEnum
    quorum_required: int
    timeout_minutes: int
    escalation_user_ids: list[uuid.UUID] | None = None
    approver_role_names: list[str] | None = None
    approver_user_ids: list[uuid.UUID] | None = None
    approver_group_ids: list[uuid.UUID] | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Step Schemas ─────────────────────────────────────────


class ApprovalStepResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    approval_request_id: uuid.UUID
    step_order: int
    approver_id: uuid.UUID
    delegate_to_id: uuid.UUID | None = None
    status: ApprovalStepStatusEnum
    decision_at: datetime | None = None
    reason: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Request Schemas ──────────────────────────────────────


class ApprovalRequestResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    operation_type: str
    requester_id: uuid.UUID
    workflow_id: str | None = None
    parent_workflow_id: str | None = None
    chain_mode: str
    quorum_required: int
    status: ApprovalRequestStatusEnum
    title: str
    description: str | None = None
    context: dict | None = None
    resolved_at: datetime | None = None
    steps: list[ApprovalStepResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApprovalRequestListResponse(BaseModel):
    items: list[ApprovalRequestResponse]
    total: int


# ── Decision/Delegate Schemas ────────────────────────────


class ApprovalDecisionInput(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = Field(None, max_length=2000)


class ApprovalDelegateInput(BaseModel):
    delegate_to_id: uuid.UUID
