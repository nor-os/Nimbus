"""
Overview: Pydantic schemas for notification endpoints — request/response validation.
Architecture: API schema definitions for notification subsystem (Section 7.1, 7.2)
Dependencies: pydantic, app.models.notification, app.models.webhook_config
Concepts: Notifications, preferences, templates, webhooks, data validation, serialization
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

# -- Enum mirrors for Pydantic ------------------------------------------------


class NotificationCategoryEnum(StrEnum):
    APPROVAL = "APPROVAL"
    SECURITY = "SECURITY"
    SYSTEM = "SYSTEM"
    AUDIT = "AUDIT"
    DRIFT = "DRIFT"
    WORKFLOW = "WORKFLOW"
    USER = "USER"


class NotificationChannelEnum(StrEnum):
    EMAIL = "EMAIL"
    IN_APP = "IN_APP"
    WEBHOOK = "WEBHOOK"


class WebhookAuthTypeEnum(StrEnum):
    NONE = "NONE"
    API_KEY = "API_KEY"
    BASIC = "BASIC"
    BEARER = "BEARER"


class WebhookDeliveryStatusEnum(StrEnum):
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    DEAD_LETTER = "DEAD_LETTER"


# -- Notification schemas -----------------------------------------------------


class NotificationResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    category: NotificationCategoryEnum
    event_type: str
    title: str
    body: str
    related_resource_type: str | None = None
    related_resource_id: str | None = None
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationResponse]
    total: int
    unread_count: int
    offset: int
    limit: int


# -- Preference schemas -------------------------------------------------------


class NotificationPreferenceResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    user_id: uuid.UUID
    category: NotificationCategoryEnum
    channel: NotificationChannelEnum
    enabled: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationPreferenceUpdate(BaseModel):
    category: NotificationCategoryEnum
    channel: NotificationChannelEnum
    enabled: bool


# -- Template schemas ---------------------------------------------------------


class NotificationTemplateCreate(BaseModel):
    category: NotificationCategoryEnum
    event_type: str = Field(..., min_length=1, max_length=255)
    channel: NotificationChannelEnum
    subject_template: str | None = Field(None, max_length=1000)
    body_template: str = Field(..., min_length=1)
    is_active: bool = True


class NotificationTemplateUpdate(BaseModel):
    subject_template: str | None = None
    body_template: str | None = None
    is_active: bool | None = None


class NotificationTemplateResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    category: NotificationCategoryEnum
    event_type: str
    channel: NotificationChannelEnum
    subject_template: str | None = None
    body_template: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -- Webhook config schemas ---------------------------------------------------


class WebhookConfigCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., min_length=1, max_length=2048)
    auth_type: WebhookAuthTypeEnum = WebhookAuthTypeEnum.NONE
    auth_config: dict | None = None
    event_filter: dict | None = None
    batch_size: int = Field(1, ge=1, le=100)
    batch_interval_seconds: int = Field(0, ge=0, le=3600)
    secret: str | None = None
    is_active: bool = True


class WebhookConfigUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    url: str | None = Field(None, min_length=1, max_length=2048)
    auth_type: WebhookAuthTypeEnum | None = None
    auth_config: dict | None = None
    event_filter: dict | None = None
    batch_size: int | None = Field(None, ge=1, le=100)
    batch_interval_seconds: int | None = Field(None, ge=0, le=3600)
    secret: str | None = None
    is_active: bool | None = None


class WebhookConfigResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    url: str
    auth_type: WebhookAuthTypeEnum
    event_filter: dict | None = None
    batch_size: int
    batch_interval_seconds: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# -- Webhook delivery schemas -------------------------------------------------


class WebhookDeliveryResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    webhook_config_id: uuid.UUID
    payload: dict
    status: WebhookDeliveryStatusEnum
    attempts: int
    max_attempts: int
    last_attempt_at: datetime | None = None
    last_error: str | None = None
    next_retry_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
    total: int
    offset: int
    limit: int
