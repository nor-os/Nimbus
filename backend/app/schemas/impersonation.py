"""
Overview: Pydantic schemas for impersonation endpoints — request/response validation.
Architecture: API schema definitions for impersonation (Section 7.1, 7.2)
Dependencies: pydantic
Concepts: Impersonation, session lifecycle, configuration
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ImpersonationModeEnum(StrEnum):
    STANDARD = "STANDARD"
    OVERRIDE = "OVERRIDE"


class ImpersonationStatusEnum(StrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


# ── Requests ──────────────────────────────────────────────


class ImpersonationRequest(BaseModel):
    target_user_id: uuid.UUID
    tenant_id: uuid.UUID
    mode: ImpersonationModeEnum = ImpersonationModeEnum.STANDARD
    reason: str = Field(..., min_length=10, max_length=2000)
    password: str = Field(..., min_length=1, description="Re-authenticate requester")


class ImpersonationApprovalRequest(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    reason: str | None = Field(None, max_length=2000)


class ImpersonationExtendRequest(BaseModel):
    minutes: int = Field(..., ge=5, le=240)


class ImpersonationConfigUpdate(BaseModel):
    standard_duration_minutes: int | None = Field(None, ge=5, le=480)
    override_duration_minutes: int | None = Field(None, ge=5, le=480)
    standard_requires_approval: bool | None = None
    override_requires_approval: bool | None = None
    max_duration_minutes: int | None = Field(None, ge=5, le=1440)


# ── Responses ─────────────────────────────────────────────


class ImpersonationSessionResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    requester_id: uuid.UUID
    target_user_id: uuid.UUID
    mode: ImpersonationModeEnum
    status: ImpersonationStatusEnum
    reason: str
    rejection_reason: str | None = None
    approver_id: uuid.UUID | None = None
    approval_decision_at: datetime | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None
    ended_at: datetime | None = None
    end_reason: str | None = None
    workflow_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImpersonationSessionListResponse(BaseModel):
    items: list[ImpersonationSessionResponse]
    total: int


class ImpersonationConfigResponse(BaseModel):
    standard_duration_minutes: int = 30
    override_duration_minutes: int = 60
    standard_requires_approval: bool = True
    override_requires_approval: bool = True
    max_duration_minutes: int = 240


class ImpersonationStatusResponse(BaseModel):
    is_impersonating: bool
    session_id: uuid.UUID | None = None
    original_user_id: uuid.UUID | None = None
    original_tenant_id: uuid.UUID | None = None
    target_user_email: str | None = None
    started_at: datetime | None = None
    expires_at: datetime | None = None


class ImpersonationTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    session_id: uuid.UUID
