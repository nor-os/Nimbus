"""
Overview: Pydantic schemas for audit log endpoints — request/response validation.
Architecture: API schema definitions for audit endpoints (Section 7.1, 7.2)
Dependencies: pydantic, app.models.audit
Concepts: Audit logging, data validation, serialization, event taxonomy
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class AuditActionEnum(StrEnum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    PERMISSION_CHANGE = "PERMISSION_CHANGE"
    BREAK_GLASS = "BREAK_GLASS"
    EXPORT = "EXPORT"
    ARCHIVE = "ARCHIVE"
    SYSTEM = "SYSTEM"
    IMPERSONATE = "IMPERSONATE"
    OVERRIDE = "OVERRIDE"


class AuditPriorityEnum(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERR = "ERR"
    CRITICAL = "CRITICAL"


class EventCategoryEnum(StrEnum):
    API = "API"
    AUTH = "AUTH"
    DATA = "DATA"
    PERMISSION = "PERMISSION"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    TENANT = "TENANT"
    USER = "USER"


class ActorTypeEnum(StrEnum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"
    ANONYMOUS = "ANONYMOUS"


# ── Audit Log ────────────────────────────────────────────


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_ip: str | None
    action: AuditActionEnum
    event_category: EventCategoryEnum | None = None
    event_type: str | None = None
    actor_type: ActorTypeEnum | None = None
    impersonator_id: uuid.UUID | None = None
    resource_type: str | None
    resource_id: str | None
    resource_name: str | None
    old_values: dict | None
    new_values: dict | None
    trace_id: str | None
    priority: AuditPriorityEnum
    hash: str | None
    previous_hash: str | None
    metadata_: dict | None = Field(None, serialization_alias="metadata")
    user_agent: str | None = None
    request_method: str | None = None
    request_path: str | None = None
    request_body: dict | None = None
    response_status: int | None = None
    response_body: dict | None = None
    archived_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class AuditLogListResponse(BaseModel):
    items: list[AuditLogResponse]
    total: int
    offset: int
    limit: int


# ── Search / Query ───────────────────────────────────────


class AuditSearchParams(BaseModel):
    date_from: datetime | None = None
    date_to: datetime | None = None
    actor_id: uuid.UUID | None = None
    action: AuditActionEnum | None = None
    event_categories: list[EventCategoryEnum] | None = None
    event_types: list[str] | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    priority: AuditPriorityEnum | None = None
    trace_id: str | None = None
    full_text: str | None = None
    offset: int = Field(0, ge=0)
    limit: int = Field(50, ge=1, le=500)


# ── Hash Chain ───────────────────────────────────────────


class VerifyChainRequest(BaseModel):
    start: int = Field(0, ge=0)
    limit: int = Field(1000, ge=1, le=10000)


class VerifyChainResponse(BaseModel):
    valid: bool
    total_checked: int
    broken_links: list[dict]


# ── Retention Policy ────────────────────────────────────


class CategoryRetentionOverrideResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    event_category: EventCategoryEnum
    hot_days: int
    cold_days: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CategoryRetentionOverrideUpsert(BaseModel):
    event_category: EventCategoryEnum
    hot_days: int = Field(..., ge=1)
    cold_days: int = Field(..., ge=1)


class RetentionPolicyResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    hot_days: int
    cold_days: int
    archive_enabled: bool
    category_overrides: list[CategoryRetentionOverrideResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RetentionPolicyUpdate(BaseModel):
    hot_days: int | None = Field(None, ge=1)
    cold_days: int | None = Field(None, ge=1)
    archive_enabled: bool | None = None


# ── Redaction Rule ──────────────────────────────────────


class RedactionRuleCreate(BaseModel):
    field_pattern: str = Field(..., min_length=1, max_length=500)
    replacement: str = Field("[REDACTED]", max_length=255)
    is_active: bool = True
    priority: int = Field(0, ge=0)


class RedactionRuleUpdate(BaseModel):
    field_pattern: str | None = Field(None, min_length=1, max_length=500)
    replacement: str | None = Field(None, max_length=255)
    is_active: bool | None = None
    priority: int | None = Field(None, ge=0)


class RedactionRuleResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    field_pattern: str
    replacement: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Saved Query ─────────────────────────────────────────


class SavedQueryCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    query_params: dict
    is_shared: bool = False


class SavedQueryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    query_params: dict
    is_shared: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Export ───────────────────────────────────────────────


class ExportRequest(BaseModel):
    format: str = Field("json", pattern="^(json|csv)$")
    date_from: datetime | None = None
    date_to: datetime | None = None
    action: AuditActionEnum | None = None
    resource_type: str | None = None
    priority: AuditPriorityEnum | None = None


class ExportResponse(BaseModel):
    export_id: str
    status: str = "pending"
    warnings: list[str] | None = None


class ExportStatusResponse(BaseModel):
    export_id: str
    status: str
    download_url: str | None = None


# ── Archive ──────────────────────────────────────────────


class ArchiveResponse(BaseModel):
    key: str
    size: int
    last_modified: datetime


# ── Taxonomy ─────────────────────────────────────────────


class TaxonomyEventTypeResponse(BaseModel):
    key: str
    label: str
    description: str
    default_priority: str


class TaxonomyCategoryResponse(BaseModel):
    category: str
    label: str
    event_types: list[TaxonomyEventTypeResponse]


class TaxonomyResponse(BaseModel):
    categories: list[TaxonomyCategoryResponse]


# ── Logging Config ─────────────────────────────────────────


class AuditLoggingConfigResponse(BaseModel):
    log_api_reads: bool
    log_api_writes: bool
    log_auth_events: bool
    log_graphql: bool
    log_errors: bool


class AuditLoggingConfigUpdate(BaseModel):
    log_api_reads: bool | None = None
    log_api_writes: bool | None = None
    log_auth_events: bool | None = None
    log_graphql: bool | None = None
    log_errors: bool | None = None
