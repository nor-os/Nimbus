"""
Overview: Strawberry GraphQL types for audit logs, retention, redaction, saved queries, and taxonomy.
Architecture: GraphQL type definitions (Section 7.2)
Dependencies: strawberry
Concepts: Audit logging, GraphQL schema, event taxonomy
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry


@strawberry.enum
class AuditActionGQL(Enum):
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


@strawberry.enum
class AuditPriorityGQL(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERR = "ERR"
    CRITICAL = "CRITICAL"


@strawberry.enum
class EventCategoryGQL(Enum):
    API = "API"
    AUTH = "AUTH"
    DATA = "DATA"
    PERMISSION = "PERMISSION"
    SYSTEM = "SYSTEM"
    SECURITY = "SECURITY"
    TENANT = "TENANT"
    USER = "USER"


@strawberry.enum
class ActorTypeGQL(Enum):
    USER = "USER"
    SYSTEM = "SYSTEM"
    SERVICE = "SERVICE"
    ANONYMOUS = "ANONYMOUS"


@strawberry.type
class AuditLogType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_email: str | None
    actor_ip: str | None
    action: AuditActionGQL
    event_category: EventCategoryGQL | None = None
    event_type: str | None = None
    actor_type: ActorTypeGQL | None = None
    impersonator_id: uuid.UUID | None = None
    resource_type: str | None
    resource_id: str | None
    resource_name: str | None
    old_values: strawberry.scalars.JSON | None
    new_values: strawberry.scalars.JSON | None
    trace_id: str | None
    priority: AuditPriorityGQL
    hash: str | None
    previous_hash: str | None
    metadata: strawberry.scalars.JSON | None
    user_agent: str | None = None
    request_method: str | None = None
    request_path: str | None = None
    request_body: strawberry.scalars.JSON | None = None
    response_status: int | None = None
    response_body: strawberry.scalars.JSON | None = None
    archived_at: datetime | None = None
    created_at: datetime


@strawberry.type
class AuditLogListType:
    items: list[AuditLogType]
    total: int
    offset: int
    limit: int


@strawberry.type
class RetentionPolicyType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    hot_days: int
    cold_days: int
    archive_enabled: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class RedactionRuleType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    field_pattern: str
    replacement: str
    is_active: bool
    priority: int
    created_at: datetime
    updated_at: datetime


@strawberry.type
class SavedQueryType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    name: str
    query_params: strawberry.scalars.JSON
    is_shared: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class VerifyChainResultType:
    valid: bool
    total_checked: int
    broken_links: strawberry.scalars.JSON


@strawberry.type
class ExportStatusType:
    export_id: str
    status: str
    download_url: str | None = None
    warnings: list[str] | None = None


# ── Taxonomy Types ─────────────────────────────────────


@strawberry.type
class TaxonomyEventTypeGQL:
    key: str
    label: str
    description: str
    default_priority: str


@strawberry.type
class TaxonomyCategoryGQL:
    category: str
    label: str
    event_types: list[TaxonomyEventTypeGQL]


@strawberry.type
class TaxonomyResponseGQL:
    categories: list[TaxonomyCategoryGQL]


# ── Inputs ──────────────────────────────────────────────


@strawberry.input
class AuditSearchInput:
    date_from: datetime | None = None
    date_to: datetime | None = None
    actor_id: uuid.UUID | None = None
    action: AuditActionGQL | None = None
    event_categories: list[EventCategoryGQL] | None = None
    event_types: list[str] | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    priority: AuditPriorityGQL | None = None
    trace_id: str | None = None
    full_text: str | None = None
    offset: int = 0
    limit: int = 50


@strawberry.input
class RetentionPolicyInput:
    hot_days: int | None = None
    cold_days: int | None = None
    archive_enabled: bool | None = None


@strawberry.input
class RedactionRuleCreateInput:
    field_pattern: str
    replacement: str = "[REDACTED]"
    is_active: bool = True
    priority: int = 0


@strawberry.input
class RedactionRuleUpdateInput:
    field_pattern: str | None = None
    replacement: str | None = None
    is_active: bool | None = None
    priority: int | None = None


@strawberry.input
class SavedQueryCreateInput:
    name: str
    query_params: strawberry.scalars.JSON
    is_shared: bool = False


@strawberry.input
class ExportRequestInput:
    format: str = "json"
    date_from: datetime | None = None
    date_to: datetime | None = None
    action: AuditActionGQL | None = None
    resource_type: str | None = None
    priority: AuditPriorityGQL | None = None
