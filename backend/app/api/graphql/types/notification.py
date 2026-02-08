"""
Overview: Strawberry GraphQL types, enums, and inputs for the notification subsystem.
Architecture: GraphQL type definitions for notifications, preferences, templates (Section 7.2)
Dependencies: strawberry
Concepts: Notification types, webhook types, preference types, template types
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
from strawberry.scalars import JSON

# -- Enums --------------------------------------------------------------------


@strawberry.enum
class NotificationCategoryGQL(Enum):
    APPROVAL = "APPROVAL"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AUDIT = "AUDIT"
    DRIFT = "DRIFT"
    WORKFLOW = "WORKFLOW"
    USER = "USER"


@strawberry.enum
class NotificationChannelGQL(Enum):
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"


@strawberry.enum
class WebhookAuthTypeGQL(Enum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BASIC = "BASIC"
    BEARER = "BEARER"


@strawberry.enum
class WebhookDeliveryStatusGQL(Enum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


# -- Object types -------------------------------------------------------------


@strawberry.type
class NotificationType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    category: NotificationCategoryGQL
    event_type: str
    title: str
    body: str
    related_resource_type: str | None = None
    related_resource_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime


@strawberry.type
class NotificationListType:
    items: list[NotificationType]
    total: int
    unread_count: int
    offset: int
    limit: int


@strawberry.type
class NotificationPreferenceType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    category: NotificationCategoryGQL
    channel: NotificationChannelGQL
    enabled: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class NotificationTemplateType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    category: NotificationCategoryGQL
    event_type: str
    channel: NotificationChannelGQL
    subject_template: str | None = None
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class WebhookConfigType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    url: str
    auth_type: WebhookAuthTypeGQL
    event_filter: JSON | None = None
    batch_size: int
    batch_interval_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


@strawberry.type
class WebhookDeliveryType:
    id: uuid.UUID
    tenant_id: uuid.UUID
    webhook_config_id: uuid.UUID
    payload: JSON
    status: WebhookDeliveryStatusGQL
    attempts: int
    max_attempts: int
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime


@strawberry.type
class WebhookDeliveryListType:
    items: list[WebhookDeliveryType]
    total: int
    offset: int
    limit: int


@strawberry.type
class WebhookTestResultType:
    success: bool
    message: str | None = None
    error: str | None = None


# -- Input types --------------------------------------------------------------


@strawberry.input
class NotificationPreferenceUpdateInput:
    category: NotificationCategoryGQL
    channel: NotificationChannelGQL
    enabled: bool


@strawberry.input
class NotificationTemplateCreateInput:
    category: NotificationCategoryGQL
    event_type: str
    channel: NotificationChannelGQL
    body_template: str
    subject_template: str | None = None
    is_active: bool = True


@strawberry.input
class NotificationTemplateUpdateInput:
    subject_template: str | None = None
    body_template: str | None = None
    is_active: bool | None = None


@strawberry.input
class WebhookConfigCreateInput:
    name: str
    url: str
    auth_type: WebhookAuthTypeGQL = WebhookAuthTypeGQL.NONE
    auth_config: JSON | None = None
    event_filter: JSON | None = None
    batch_size: int = 1
    batch_interval_seconds: int = 0
    secret: str | None = None
    is_active: bool = True


@strawberry.input
class WebhookConfigUpdateInput:
    name: str | None = None
    url: str | None = None
    auth_type: WebhookAuthTypeGQL | None = None
    auth_config: JSON | None = None
    event_filter: JSON | None = None
    batch_size: int | None = None
    batch_interval_seconds: int | None = None
    secret: str | None = None
    is_active: bool | None = None
