"""
Overview: Pydantic schemas for user management CRUD operations.
Architecture: Request/response validation for user endpoints (Section 7.1)
Dependencies: pydantic
Concepts: User management, CRUD schemas, validation
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str | None = Field(None, min_length=8, max_length=128)
    display_name: str | None = Field(None, max_length=255)
    role_ids: list[uuid.UUID] = Field(default_factory=list)
    group_ids: list[uuid.UUID] = Field(default_factory=list)
    identity_provider_id: uuid.UUID | None = None
    external_id: str | None = None


class UserUpdate(BaseModel):
    display_name: str | None = Field(None, max_length=255)
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_active: bool
    provider_id: uuid.UUID
    identity_provider_id: uuid.UUID | None
    external_id: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserRoleInfo(BaseModel):
    id: uuid.UUID
    role_id: uuid.UUID
    role_name: str
    tenant_id: uuid.UUID
    compartment_id: uuid.UUID | None
    granted_at: datetime
    expires_at: datetime | None

    model_config = {"from_attributes": True}


class UserGroupInfo(BaseModel):
    id: uuid.UUID
    group_id: uuid.UUID
    group_name: str

    model_config = {"from_attributes": True}


class UserDetailResponse(UserResponse):
    roles: list[UserRoleInfo] = Field(default_factory=list)
    groups: list[UserGroupInfo] = Field(default_factory=list)
    effective_permissions: list[str] = Field(default_factory=list)


class UserListResponse(BaseModel):
    items: list[UserResponse]
    total: int
    offset: int
    limit: int
