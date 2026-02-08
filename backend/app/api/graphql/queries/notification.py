"""
Overview: GraphQL queries for notifications, preferences, templates, webhooks, and deliveries.
Architecture: GraphQL query resolvers for the notification subsystem (Section 7.2)
Dependencies: strawberry, app.services.notification
Concepts: Notification queries, unread count, webhook delivery history
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.notification import (
    NotificationCategoryGQL,
    NotificationListType,
    NotificationPreferenceType,
    NotificationTemplateType,
    NotificationType,
    WebhookConfigType,
    WebhookDeliveryListType,
    WebhookDeliveryStatusGQL,
    WebhookDeliveryType,
)


@strawberry.type
class NotificationQuery:
    @strawberry.field
    async def notifications(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        is_read: bool | None = None,
        category: NotificationCategoryGQL | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> NotificationListType:
        """List notifications for the authenticated user."""
        user_id = await check_graphql_permission(
            info, "notification:notification:read", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.in_app_service import InAppService

        cat = None
        if category is not None:
            from app.models.notification import NotificationCategory
            cat = NotificationCategory(category.value)

        async with async_session_factory() as db:
            service = InAppService(db)
            items, total, unread_count = await service.list_notifications(
                tenant_id=str(tenant_id),
                user_id=user_id,
                is_read=is_read,
                category=cat,
                offset=offset,
                limit=limit,
            )
            return NotificationListType(
                items=[_to_notification_type(n) for n in items],
                total=total,
                unread_count=unread_count,
                offset=offset,
                limit=limit,
            )

    @strawberry.field
    async def unread_notification_count(
        self, info: Info, tenant_id: uuid.UUID
    ) -> int:
        """Get unread notification count for the authenticated user."""
        user_id = await check_graphql_permission(
            info, "notification:notification:read", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.in_app_service import InAppService

        async with async_session_factory() as db:
            service = InAppService(db)
            return await service.get_unread_count(str(tenant_id), user_id)

    @strawberry.field
    async def notification_preferences(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[NotificationPreferenceType]:
        """Get notification preferences for the authenticated user."""
        user_id = await check_graphql_permission(
            info, "notification:preference:manage", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.preference_service import PreferenceService

        async with async_session_factory() as db:
            service = PreferenceService(db)
            prefs = await service.get_preferences(str(tenant_id), user_id)
            return [_to_preference_type(p) for p in prefs]

    @strawberry.field
    async def notification_templates(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[NotificationTemplateType]:
        """List notification templates (tenant + system)."""
        await check_graphql_permission(
            info, "notification:template:read", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.template_service import TemplateService

        async with async_session_factory() as db:
            service = TemplateService(db)
            templates = await service.list_templates(str(tenant_id))
            return [_to_template_type(t) for t in templates]

    @strawberry.field
    async def webhook_configs(
        self, info: Info, tenant_id: uuid.UUID
    ) -> list[WebhookConfigType]:
        """List webhook configurations for a tenant."""
        await check_graphql_permission(
            info, "notification:webhook:read", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.webhook_service import WebhookService

        async with async_session_factory() as db:
            service = WebhookService(db)
            configs = await service.list_configs(str(tenant_id))
            return [_to_webhook_config_type(c) for c in configs]

    @strawberry.field
    async def webhook_deliveries(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        config_id: uuid.UUID | None = None,
        status: WebhookDeliveryStatusGQL | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> WebhookDeliveryListType:
        """List webhook deliveries with optional filters."""
        await check_graphql_permission(
            info, "notification:webhook:read", str(tenant_id)
        )
        from app.db.session import async_session_factory
        from app.services.notification.webhook_delivery_service import WebhookDeliveryService

        delivery_status = None
        if status is not None:
            from app.models.webhook_delivery import WebhookDeliveryStatus
            delivery_status = WebhookDeliveryStatus(status.value)

        async with async_session_factory() as db:
            service = WebhookDeliveryService(db)
            items, total = await service.list_deliveries(
                tenant_id=str(tenant_id),
                config_id=str(config_id) if config_id else None,
                status=delivery_status,
                offset=offset,
                limit=limit,
            )
            return WebhookDeliveryListType(
                items=[_to_webhook_delivery_type(d) for d in items],
                total=total,
                offset=offset,
                limit=limit,
            )


# -- Converters ---------------------------------------------------------------


def _to_notification_type(n) -> NotificationType:
    from app.api.graphql.types.notification import NotificationCategoryGQL

    return NotificationType(
        id=n.id,
        tenant_id=n.tenant_id,
        user_id=n.user_id,
        category=NotificationCategoryGQL(n.category.value),
        event_type=n.event_type,
        title=n.title,
        body=n.body,
        related_resource_type=n.related_resource_type,
        related_resource_id=n.related_resource_id,
        is_read=n.is_read,
        read_at=n.read_at,
        created_at=n.created_at,
    )


def _to_preference_type(p) -> NotificationPreferenceType:
    from app.api.graphql.types.notification import (
        NotificationCategoryGQL,
        NotificationChannelGQL,
    )

    return NotificationPreferenceType(
        id=p.id,
        tenant_id=p.tenant_id,
        user_id=p.user_id,
        category=NotificationCategoryGQL(p.category.value),
        channel=NotificationChannelGQL(p.channel.value),
        enabled=p.enabled,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _to_template_type(t) -> NotificationTemplateType:
    from app.api.graphql.types.notification import (
        NotificationCategoryGQL,
        NotificationChannelGQL,
    )

    return NotificationTemplateType(
        id=t.id,
        tenant_id=t.tenant_id,
        category=NotificationCategoryGQL(t.category.value),
        event_type=t.event_type,
        channel=NotificationChannelGQL(t.channel.value),
        subject_template=t.subject_template,
        body_template=t.body_template,
        is_active=t.is_active,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _to_webhook_config_type(c) -> WebhookConfigType:
    from app.api.graphql.types.notification import WebhookAuthTypeGQL

    return WebhookConfigType(
        id=c.id,
        tenant_id=c.tenant_id,
        name=c.name,
        url=c.url,
        auth_type=WebhookAuthTypeGQL(c.auth_type.value),
        event_filter=c.event_filter,
        batch_size=c.batch_size,
        batch_interval_seconds=c.batch_interval_seconds,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


def _to_webhook_delivery_type(d) -> WebhookDeliveryType:
    from app.api.graphql.types.notification import WebhookDeliveryStatusGQL

    return WebhookDeliveryType(
        id=d.id,
        tenant_id=d.tenant_id,
        webhook_config_id=d.webhook_config_id,
        payload=d.payload,
        status=WebhookDeliveryStatusGQL(d.status.value),
        attempts=d.attempts,
        max_attempts=d.max_attempts,
        last_attempt_at=d.last_attempt_at,
        last_error=d.last_error,
        next_retry_at=d.next_retry_at,
        created_at=d.created_at,
    )
