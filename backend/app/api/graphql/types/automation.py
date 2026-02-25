"""
Overview: Strawberry GraphQL types for automated activities, versions, executions, and config changes.
Architecture: GraphQL type definitions for activity catalog (Section 11.5)
Dependencies: strawberry
Concepts: Activity types, version types, execution tracking, config mutation types
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ────────────────────────────────────────────────


@strawberry.enum
class OperationKindGQL(Enum):
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    REMEDIATE = "REMEDIATE"
    VALIDATE = "VALIDATE"
    BACKUP = "BACKUP"
    RESTORE = "RESTORE"


@strawberry.enum
class ImplementationTypeGQL(Enum):
    PYTHON_SCRIPT = "PYTHON_SCRIPT"
    HTTP_WEBHOOK = "HTTP_WEBHOOK"
    PULUMI_OPERATION = "PULUMI_OPERATION"
    SHELL_SCRIPT = "SHELL_SCRIPT"
    MANUAL = "MANUAL"


@strawberry.enum
class MutationTypeGQL(Enum):
    SET = "SET"
    SET_FROM_INPUT = "SET_FROM_INPUT"
    INCREMENT = "INCREMENT"
    DECREMENT = "DECREMENT"
    APPEND = "APPEND"
    REMOVE = "REMOVE"


@strawberry.enum
class ActivityScopeGQL(Enum):
    COMPONENT = "COMPONENT"
    WORKFLOW = "WORKFLOW"


@strawberry.enum
class ActivityExecutionStatusGQL(Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


# ── Output Types ─────────────────────────────────────────


@strawberry.type
class AutomatedActivityType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    slug: str
    description: str | None
    category: str | None
    semantic_activity_type_id: uuid.UUID | None
    semantic_type_id: uuid.UUID | None
    provider_id: uuid.UUID | None
    operation_kind: OperationKindGQL
    implementation_type: ImplementationTypeGQL
    scope: ActivityScopeGQL
    idempotent: bool
    timeout_seconds: int
    is_system: bool
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime
    versions: list["AutomatedActivityVersionType"]


@strawberry.type
class AutomatedActivityVersionType:
    id: uuid.UUID
    activity_id: uuid.UUID
    version: int
    source_code: str | None
    input_schema: strawberry.scalars.JSON | None
    output_schema: strawberry.scalars.JSON | None
    config_mutations: strawberry.scalars.JSON | None
    rollback_mutations: strawberry.scalars.JSON | None
    changelog: str | None
    published_at: datetime | None
    published_by: uuid.UUID | None
    runtime_config: strawberry.scalars.JSON | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ActivityExecutionType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    activity_version_id: uuid.UUID
    workflow_execution_id: uuid.UUID | None
    ci_id: uuid.UUID | None
    deployment_id: uuid.UUID | None
    input_snapshot: strawberry.scalars.JSON | None
    output_snapshot: strawberry.scalars.JSON | None
    status: ActivityExecutionStatusGQL
    error: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    config_changes: list["ConfigurationChangeType"]


@strawberry.type
class ConfigurationChangeType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    deployment_id: uuid.UUID
    activity_execution_id: uuid.UUID | None
    version: int
    parameter_path: str
    mutation_type: str
    old_value: strawberry.scalars.JSON | None
    new_value: strawberry.scalars.JSON | None
    applied_at: datetime
    applied_by: uuid.UUID | None
    rollback_of: uuid.UUID | None


# ── Input Types ──────────────────────────────────────────


@strawberry.input
class AutomatedActivityCreateInput:
    name: str
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    semantic_activity_type_id: uuid.UUID | None = None
    semantic_type_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    operation_kind: str = "UPDATE"
    implementation_type: str = "PYTHON_SCRIPT"
    scope: str = "WORKFLOW"
    idempotent: bool = False
    timeout_seconds: int = 300


@strawberry.input
class AutomatedActivityUpdateInput:
    name: str | None = None
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    semantic_activity_type_id: uuid.UUID | None = None
    semantic_type_id: uuid.UUID | None = None
    provider_id: uuid.UUID | None = None
    operation_kind: str | None = None
    implementation_type: str | None = None
    scope: str | None = None
    idempotent: bool | None = None
    timeout_seconds: int | None = None


@strawberry.input
class ActivityVersionCreateInput:
    source_code: str | None = None
    input_schema: strawberry.scalars.JSON | None = None
    output_schema: strawberry.scalars.JSON | None = None
    config_mutations: strawberry.scalars.JSON | None = None
    rollback_mutations: strawberry.scalars.JSON | None = None
    changelog: str | None = None
    runtime_config: strawberry.scalars.JSON | None = None


@strawberry.input
class ActivityExecutionStartInput:
    activity_id: uuid.UUID
    version_id: uuid.UUID | None = None  # None = latest published
    ci_id: uuid.UUID | None = None
    deployment_id: uuid.UUID | None = None
    input_data: strawberry.scalars.JSON | None = None


# ── Converter Functions ──────────────────────────────────


def activity_to_type(a) -> AutomatedActivityType:
    """Convert AutomatedActivity ORM model to GraphQL type."""
    return AutomatedActivityType(
        id=a.id,
        tenant_id=a.tenant_id,
        name=a.name,
        slug=a.slug,
        description=a.description,
        category=a.category,
        semantic_activity_type_id=a.semantic_activity_type_id,
        semantic_type_id=a.semantic_type_id,
        provider_id=a.provider_id,
        operation_kind=OperationKindGQL(a.operation_kind.value),
        implementation_type=ImplementationTypeGQL(a.implementation_type.value),
        scope=ActivityScopeGQL(a.scope.value),
        idempotent=a.idempotent,
        timeout_seconds=a.timeout_seconds,
        is_system=a.is_system,
        created_by=a.created_by,
        created_at=a.created_at,
        updated_at=a.updated_at,
        versions=[version_to_type(v) for v in (a.versions or [])],
    )


def activity_summary_to_type(a) -> AutomatedActivityType:
    """Convert without loading versions (for list queries)."""
    return AutomatedActivityType(
        id=a.id,
        tenant_id=a.tenant_id,
        name=a.name,
        slug=a.slug,
        description=a.description,
        category=a.category,
        semantic_activity_type_id=a.semantic_activity_type_id,
        semantic_type_id=a.semantic_type_id,
        provider_id=a.provider_id,
        operation_kind=OperationKindGQL(a.operation_kind.value),
        implementation_type=ImplementationTypeGQL(a.implementation_type.value),
        scope=ActivityScopeGQL(a.scope.value),
        idempotent=a.idempotent,
        timeout_seconds=a.timeout_seconds,
        is_system=a.is_system,
        created_by=a.created_by,
        created_at=a.created_at,
        updated_at=a.updated_at,
        versions=[],
    )


def version_to_type(v) -> AutomatedActivityVersionType:
    """Convert AutomatedActivityVersion ORM model to GraphQL type."""
    return AutomatedActivityVersionType(
        id=v.id,
        activity_id=v.activity_id,
        version=v.version,
        source_code=v.source_code,
        input_schema=v.input_schema,
        output_schema=v.output_schema,
        config_mutations=v.config_mutations,
        rollback_mutations=v.rollback_mutations,
        changelog=v.changelog,
        published_at=v.published_at,
        published_by=v.published_by,
        runtime_config=v.runtime_config,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


def execution_to_type(e) -> ActivityExecutionType:
    """Convert ActivityExecution ORM model to GraphQL type."""
    return ActivityExecutionType(
        id=e.id,
        tenant_id=e.tenant_id,
        activity_version_id=e.activity_version_id,
        workflow_execution_id=e.workflow_execution_id,
        ci_id=e.ci_id,
        deployment_id=e.deployment_id,
        input_snapshot=e.input_snapshot,
        output_snapshot=e.output_snapshot,
        status=ActivityExecutionStatusGQL(e.status.value),
        error=e.error,
        started_at=e.started_at,
        completed_at=e.completed_at,
        created_at=e.created_at,
        updated_at=e.updated_at,
        config_changes=[config_change_to_type(c) for c in (e.config_changes or [])],
    )


def config_change_to_type(c) -> ConfigurationChangeType:
    """Convert ConfigurationChange ORM model to GraphQL type."""
    return ConfigurationChangeType(
        id=c.id,
        tenant_id=c.tenant_id,
        deployment_id=c.deployment_id,
        activity_execution_id=c.activity_execution_id,
        version=c.version,
        parameter_path=c.parameter_path,
        mutation_type=c.mutation_type,
        old_value=c.old_value,
        new_value=c.new_value,
        applied_at=c.applied_at,
        applied_by=c.applied_by,
        rollback_of=c.rollback_of,
    )
