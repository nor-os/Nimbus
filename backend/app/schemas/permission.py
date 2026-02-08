"""
Overview: Pydantic schemas for permissions, roles, groups, and ABAC policies.
Architecture: Request/response validation for permission system endpoints (Section 7.1)
Dependencies: pydantic
Concepts: RBAC, ABAC, permissions, roles, groups, policy management
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── Permission schemas ───────────────────────────────────────────────


class PermissionResponse(BaseModel):
    id: uuid.UUID
    domain: str
    resource: str
    action: str
    subtype: str | None
    description: str | None
    is_system: bool
    key: str

    model_config = {"from_attributes": True}


class PermissionCheckRequest(BaseModel):
    permission_key: str
    resource: dict | None = None
    context: dict | None = None


class PermissionCheckResponse(BaseModel):
    allowed: bool
    permission_key: str
    source: str | None = None


class EffectivePermissionResponse(BaseModel):
    permission_key: str
    source: str
    role_name: str | None = None
    group_name: str | None = None
    source_tenant_id: str = ""
    source_tenant_name: str = ""
    is_inherited: bool = False
    is_denied: bool = False
    deny_source: str | None = None


class PermissionSimulateRequest(BaseModel):
    user_id: uuid.UUID
    permission_key: str
    resource: dict | None = None
    context: dict | None = None


class PermissionSimulateResponse(BaseModel):
    allowed: bool
    permission_key: str
    source: str | None = None
    evaluation_steps: list[str] = Field(default_factory=list)


# ── Role schemas ─────────────────────────────────────────────────────


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    scope: str | None = Field("tenant", pattern="^(provider|tenant)$")
    parent_role_id: uuid.UUID | None = None
    permission_ids: list[uuid.UUID] = Field(default_factory=list)
    max_level: int | None = None


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None
    permission_ids: list[uuid.UUID] | None = None
    max_level: int | None = None


class RoleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    is_system: bool
    is_custom: bool
    scope: str
    parent_role_id: uuid.UUID | None
    max_level: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoleDetailResponse(RoleResponse):
    permissions: list[PermissionResponse] = Field(default_factory=list)


class RoleAssignRequest(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID
    compartment_id: uuid.UUID | None = None
    expires_at: datetime | None = None


class RoleUnassignRequest(BaseModel):
    user_id: uuid.UUID
    role_id: uuid.UUID


# ── Permission Override schemas ──────────────────────────────────────


class PermissionOverrideCreate(BaseModel):
    permission_id: uuid.UUID
    principal_type: str = Field(..., pattern="^(user|group|role)$")
    principal_id: uuid.UUID
    reason: str | None = None


class PermissionOverrideResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    permission_id: uuid.UUID
    permission_key: str = ""
    principal_type: str
    principal_id: uuid.UUID
    principal_name: str = ""
    effect: str
    reason: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Group schemas ────────────────────────────────────────────────────


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = None


class GroupResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupMembersResponse(BaseModel):
    users: list = Field(default_factory=list)
    groups: list[GroupResponse] = Field(default_factory=list)


class GroupMemberRequest(BaseModel):
    user_id: uuid.UUID


class GroupChildRequest(BaseModel):
    group_id: uuid.UUID


class GroupRoleRequest(BaseModel):
    role_id: uuid.UUID


# ── ABAC schemas ─────────────────────────────────────────────────────


class ABACPolicyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    expression: str = Field(..., min_length=1)
    effect: str = Field(..., pattern="^(allow|deny)$")
    priority: int = 0
    is_enabled: bool = True
    target_permission_id: uuid.UUID | None = None


class ABACPolicyUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    expression: str | None = Field(None, min_length=1)
    effect: str | None = Field(None, pattern="^(allow|deny)$")
    priority: int | None = None
    is_enabled: bool | None = None
    target_permission_id: uuid.UUID | None = None


class ABACPolicyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    expression: str
    effect: str
    priority: int
    is_enabled: bool
    target_permission_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ABACValidateRequest(BaseModel):
    expression: str


class ABACValidateResponse(BaseModel):
    valid: bool
    error: str | None = None
