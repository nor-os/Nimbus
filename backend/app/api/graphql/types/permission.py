"""
Overview: GraphQL types for permissions, roles, groups, and effective permissions.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: GraphQL types, RBAC, permissions
"""

import uuid
from datetime import datetime

import strawberry


@strawberry.type
class PermissionType:
    id: uuid.UUID
    domain: str
    resource: str
    action: str
    subtype: str | None
    description: str | None
    is_system: bool
    key: str


@strawberry.type
class RoleType:
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


@strawberry.type
class GroupType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EffectivePermissionType:
    permission_key: str
    source: str
    role_name: str | None = None
    group_name: str | None = None
    source_tenant_id: str | None = None
    source_tenant_name: str | None = None
    is_inherited: bool = False
    is_denied: bool = False
    deny_source: str | None = None


@strawberry.type
class PermissionCheckResultType:
    allowed: bool
    permission_key: str
    source: str | None = None
