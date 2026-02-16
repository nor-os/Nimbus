"""
Overview: Pydantic schemas for tenant CRUD, settings, quotas, hierarchy, and stats.
Architecture: API schema definitions for tenant endpoints (Section 7.1, 7.2)
Dependencies: pydantic
Concepts: Multi-tenancy, tenant hierarchy, quotas, settings
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    parent_id: uuid.UUID | None = None
    contact_email: EmailStr | None = None
    billing_info: dict | None = None
    description: str | None = None
    invoice_currency: str | None = Field(None, min_length=3, max_length=3)
    primary_region_id: uuid.UUID | None = None
    provider_id_for_backend: uuid.UUID | None = None


class TenantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    contact_email: EmailStr | None = None
    billing_info: dict | None = None
    description: str | None = None
    invoice_currency: str | None = Field(None, min_length=3, max_length=3)
    primary_region_id: uuid.UUID | None = None


class TenantResponse(BaseModel):
    id: uuid.UUID
    name: str
    parent_id: uuid.UUID | None
    provider_id: uuid.UUID
    contact_email: str | None
    is_root: bool
    level: int
    description: str | None
    invoice_currency: str | None
    primary_region_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantDetailResponse(TenantResponse):
    billing_info: dict | None
    children_count: int = 0
    users_count: int = 0


class TenantSettingCreate(BaseModel):
    key: str = Field(..., min_length=1, max_length=255)
    value: str
    value_type: str = "string"


class TenantSettingResponse(BaseModel):
    id: uuid.UUID
    key: str
    value: str
    value_type: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuotaCreate(BaseModel):
    quota_type: str
    limit_value: int = Field(..., ge=0)
    enforcement: str = "hard"


class QuotaUpdate(BaseModel):
    limit_value: int | None = Field(None, ge=0)
    enforcement: str | None = None


class QuotaResponse(BaseModel):
    id: uuid.UUID
    quota_type: str
    limit_value: int
    current_usage: int
    enforcement: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TenantHierarchyResponse(BaseModel):
    id: uuid.UUID
    name: str
    level: int
    is_root: bool
    children: list["TenantHierarchyResponse"] = []

    model_config = {"from_attributes": True}


class TenantStatsResponse(BaseModel):
    tenant_id: uuid.UUID
    name: str
    total_users: int = 0
    total_compartments: int = 0
    total_children: int = 0
    quotas: list[QuotaResponse] = []
