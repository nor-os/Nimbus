"""
Overview: Strawberry GraphQL types for event system — types, subscriptions, log, deliveries.
Architecture: GraphQL type definitions for event bus (Section 11.6)
Dependencies: strawberry
Concepts: Event types, subscription types, log entries, delivery tracking
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


# ── Enums ────────────────────────────────────────────────


@strawberry.enum
class EventHandlerTypeGQL(Enum):
    INTERNAL = "INTERNAL"
    WORKFLOW = "WORKFLOW"
    NOTIFICATION = "NOTIFICATION"
    ACTIVITY = "ACTIVITY"
    WEBHOOK = "WEBHOOK"


@strawberry.enum
class EventDeliveryStatusGQL(Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"


@strawberry.enum
class EventCategoryGQL(Enum):
    AUTHENTICATION = "AUTHENTICATION"
    APPROVAL = "APPROVAL"
    DEPLOYMENT = "DEPLOYMENT"
    ENVIRONMENT = "ENVIRONMENT"
    CMDB = "CMDB"
    AUTOMATION = "AUTOMATION"
    WORKFLOW = "WORKFLOW"
    CUSTOM = "CUSTOM"


# ── Output Types ─────────────────────────────────────────


@strawberry.type
class EventTypeGQL:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    description: str | None
    category: str
    payload_schema: strawberry.scalars.JSON | None
    source_validators: strawberry.scalars.JSON | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EventSubscriptionGQL:
    id: uuid.UUID
    tenant_id: uuid.UUID
    event_type_id: uuid.UUID
    name: str
    handler_type: str
    handler_config: strawberry.scalars.JSON
    filter_expression: str | None
    priority: int
    is_active: bool
    is_system: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class EventDeliveryGQL:
    id: uuid.UUID
    event_log_id: uuid.UUID
    subscription_id: uuid.UUID
    status: str
    handler_output: strawberry.scalars.JSON | None
    error: str | None
    attempts: int
    started_at: datetime | None
    delivered_at: datetime | None
    created_at: datetime


@strawberry.type
class EventLogGQL:
    id: uuid.UUID
    tenant_id: uuid.UUID
    event_type_id: uuid.UUID | None
    event_type_name: str
    source: str
    payload: strawberry.scalars.JSON
    emitted_at: datetime
    emitted_by: uuid.UUID | None
    trace_id: str | None
    deliveries: list[EventDeliveryGQL]


# ── Input Types ──────────────────────────────────────────


@strawberry.input
class EventTypeCreateInput:
    name: str
    description: str | None = None
    category: str = "CUSTOM"
    payload_schema: strawberry.scalars.JSON | None = None
    source_validators: strawberry.scalars.JSON | None = None


@strawberry.input
class EventTypeUpdateInput:
    name: str | None = None
    description: str | None = None
    category: str | None = None
    payload_schema: strawberry.scalars.JSON | None = None
    source_validators: strawberry.scalars.JSON | None = None
    is_active: bool | None = None


@strawberry.input
class EventSubscriptionCreateInput:
    event_type_id: uuid.UUID
    name: str
    handler_type: str
    handler_config: strawberry.scalars.JSON
    filter_expression: str | None = None
    priority: int = 100
    is_active: bool = True


@strawberry.input
class EventSubscriptionUpdateInput:
    name: str | None = None
    handler_type: str | None = None
    handler_config: strawberry.scalars.JSON | None = None
    filter_expression: str | None = None
    priority: int | None = None
    is_active: bool | None = None


# ── Converter Functions ──────────────────────────────────


def event_type_to_gql(et) -> EventTypeGQL:
    return EventTypeGQL(
        id=et.id,
        tenant_id=et.tenant_id,
        name=et.name,
        description=et.description,
        category=et.category,
        payload_schema=et.payload_schema,
        source_validators=et.source_validators,
        is_system=et.is_system,
        is_active=et.is_active,
        created_at=et.created_at,
        updated_at=et.updated_at,
    )


def subscription_to_gql(sub) -> EventSubscriptionGQL:
    return EventSubscriptionGQL(
        id=sub.id,
        tenant_id=sub.tenant_id,
        event_type_id=sub.event_type_id,
        name=sub.name,
        handler_type=sub.handler_type,
        handler_config=sub.handler_config,
        filter_expression=sub.filter_expression,
        priority=sub.priority,
        is_active=sub.is_active,
        is_system=sub.is_system,
        created_at=sub.created_at,
        updated_at=sub.updated_at,
    )


def delivery_to_gql(d) -> EventDeliveryGQL:
    return EventDeliveryGQL(
        id=d.id,
        event_log_id=d.event_log_id,
        subscription_id=d.subscription_id,
        status=d.status,
        handler_output=d.handler_output,
        error=d.error,
        attempts=d.attempts,
        started_at=d.started_at,
        delivered_at=d.delivered_at,
        created_at=d.created_at,
    )


def event_log_to_gql(el, include_deliveries: bool = False) -> EventLogGQL:
    deliveries = []
    if include_deliveries and hasattr(el, "deliveries") and el.deliveries:
        deliveries = [delivery_to_gql(d) for d in el.deliveries]

    return EventLogGQL(
        id=el.id,
        tenant_id=el.tenant_id,
        event_type_id=el.event_type_id,
        event_type_name=el.event_type_name,
        source=el.source,
        payload=el.payload,
        emitted_at=el.emitted_at,
        emitted_by=el.emitted_by,
        trace_id=el.trace_id,
        deliveries=deliveries,
    )
