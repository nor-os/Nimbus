"""
Overview: Pydantic schemas for authentication requests and responses.
Architecture: API schema definitions for auth endpoints (Section 7.1)
Dependencies: pydantic
Concepts: Authentication, request validation, tenant context
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    current_tenant_id: str | None = None


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    provider_id: uuid.UUID
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SessionResponse(BaseModel):
    id: uuid.UUID
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    expires_at: datetime
    is_current: bool = False

    model_config = {"from_attributes": True}


class SwitchTenantRequest(BaseModel):
    tenant_id: uuid.UUID


class UserTenantResponse(BaseModel):
    tenant_id: uuid.UUID
    tenant_name: str
    parent_id: uuid.UUID | None = None
    is_default: bool
    is_root: bool
    level: int
    joined_at: datetime

    model_config = {"from_attributes": True}


# ── Discovery schemas ────────────────────────────────────────────────


class DiscoverRequest(BaseModel):
    email: EmailStr


class SSOProviderInfoSchema(BaseModel):
    id: str
    name: str
    idp_type: str


class DiscoverResponse(BaseModel):
    found: bool
    tenant_id: str | None = None
    tenant_name: str | None = None
    tenant_slug: str | None = None
    has_local_auth: bool = False
    sso_providers: list[SSOProviderInfoSchema] = []


class TenantLoginInfoResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    slug: str
    has_local_auth: bool
    sso_providers: list[SSOProviderInfoSchema]
