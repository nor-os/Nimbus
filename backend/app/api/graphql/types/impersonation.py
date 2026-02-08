"""
Overview: GraphQL types for impersonation data.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: GraphQL types, impersonation sessions, configuration
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry


@strawberry.enum
class ImpersonationModeGQL(Enum):
    STANDARD = "STANDARD"
    OVERRIDE = "OVERRIDE"


@strawberry.enum
class ImpersonationStatusGQL(Enum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    ENDED = "ENDED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


@strawberry.type
class ImpersonationSessionType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    requester_id: uuid.UUID
    target_user_id: uuid.UUID
    mode: ImpersonationModeGQL
    status: ImpersonationStatusGQL
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


@strawberry.type
class ImpersonationConfigType:
    standard_duration_minutes: int
    override_duration_minutes: int
    standard_requires_approval: bool
    override_requires_approval: bool
    max_duration_minutes: int
