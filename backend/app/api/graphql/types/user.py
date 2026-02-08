"""
Overview: GraphQL types for user data.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: GraphQL types, user management
"""

import uuid
from datetime import datetime

import strawberry


@strawberry.type
class UserType:
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    provider_id: uuid.UUID
    identity_provider_id: uuid.UUID | None
    external_id: str | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class UserDetailType(UserType):
    roles: list[str] = strawberry.field(default_factory=list)
    groups: list[str] = strawberry.field(default_factory=list)
    effective_permissions: list[str] = strawberry.field(default_factory=list)
