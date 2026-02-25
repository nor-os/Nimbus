"""
Overview: GraphQL mutations for notifications, preferences, templates, and webhooks.
Architecture: GraphQL mutation resolvers for the notification subsystem (Section 7.2)
Dependencies: strawberry, app.services.notification
Concepts: Notification management, preference updates, template CRUD, webhook CRUD
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.notification import (
    _to_notification_type,
    _to_preference_type,
    _to_template_type,
    _to_webhook_config_type,
    _to_webhook_delivery_type,
)
from app.api.graphql.types.notification import (
    NotificationPreferenceType,
    NotificationPreferenceUpdateInput,
    NotificationTemplateCreateInput,
    NotificationTemplateType,
    NotificationTemplateUpdateInput,
    NotificationType,
    WebhookConfigCreateInput,
    WebhookConfigType,
    WebhookConfigUpdateInput,
    WebhookDeliveryType,
    WebhookTestResultType,
)

logger = logging.getLogger(__name__)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class NotificationMutation:
    @strawberry.mutation
    async def mark_notification_read(
        self, info: Info, tenant_id: uuid.UUID, notification_id: uuid.UUID
    ) -> NotificationType | None:
        """Mark a single notification as read."""
        user_id = await check_graphql_permission(
            info, "notification:notification:read", str(tenant_id)
        )
        from app.services.notification.in_app_service import InAppService

        db = await _get_session(info)
        service = InAppService(db)
        notification = await service.mark_read(
            str(notification_id), str(tenant_id), user_id
        )
        await db.commit()
        if not notification:
            return None
        return _to_notification_type(notification)

    @strawberry.mutation
    async def mark_all_notifications_read(
        self, info: Info, tenant_id: uuid.UUID
    ) -> int:
        """Mark all notifications as read. Returns count updated."""
        user_id = await check_graphql_permission(
            info, "notification:notification:read", str(tenant_id)
        )
        from app.services.notification.in_app_service import InAppService

        db = await _get_session(info)
        service = InAppService(db)
        count = await service.mark_all_read(str(tenant_id), user_id)
        await db.commit()
        return count

    @strawberry.mutation
    async def delete_notification(
        self, info: Info, tenant_id: uuid.UUID, notification_id: uuid.UUID
    ) -> bool:
        """Delete a notification (soft delete)."""
        user_id = await check_graphql_permission(
            info, "notification:notification:read", str(tenant_id)
        )
        from app.services.notification.in_app_service import InAppService

        db = await _get_session(info)
        service = InAppService(db)
        deleted = await service.delete_notification(
            str(notification_id), str(tenant_id), user_id
        )
        await db.commit()
        return deleted

    @strawberry.mutation
    async def update_notification_preferences(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        updates: list[NotificationPreferenceUpdateInput],
    ) -> list[NotificationPreferenceType]:
        """Bulk update notification preferences."""
        user_id = await check_graphql_permission(
            info, "notification:preference:manage", str(tenant_id)
        )
        from app.services.notification.preference_service import PreferenceService

        update_dicts = [
            {"category": u.category.value, "channel": u.channel.value, "enabled": u.enabled}
            for u in updates
        ]

        db = await _get_session(info)
        service = PreferenceService(db)
        prefs = await service.update_preferences(str(tenant_id), user_id, update_dicts)
        await db.commit()
        return [_to_preference_type(p) for p in prefs]

    # -- Template mutations ---------------------------------------------------

    @strawberry.mutation
    async def create_notification_template(
        self, info: Info, tenant_id: uuid.UUID, input: NotificationTemplateCreateInput
    ) -> NotificationTemplateType:
        """Create a notification template."""
        await check_graphql_permission(
            info, "notification:template:manage", str(tenant_id)
        )
        from app.models.notification import NotificationCategory, NotificationChannel
        from app.services.notification.template_service import TemplateService

        db = await _get_session(info)
        service = TemplateService(db)
        template = await service.create_template(
            tenant_id=str(tenant_id),
            category=NotificationCategory(input.category.value),
            event_type=input.event_type,
            channel=NotificationChannel(input.channel.value),
            body_template=input.body_template,
            subject_template=input.subject_template,
            is_active=input.is_active,
        )
        await db.commit()
        return _to_template_type(template)

    @strawberry.mutation
    async def update_notification_template(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
        input: NotificationTemplateUpdateInput,
    ) -> NotificationTemplateType | None:
        """Update a notification template."""
        await check_graphql_permission(
            info, "notification:template:manage", str(tenant_id)
        )
        from app.services.notification.template_service import TemplateService

        kwargs = {}
        if input.subject_template is not None:
            kwargs["subject_template"] = input.subject_template
        if input.body_template is not None:
            kwargs["body_template"] = input.body_template
        if input.is_active is not None:
            kwargs["is_active"] = input.is_active

        db = await _get_session(info)
        service = TemplateService(db)
        template = await service.update_template(
            str(template_id), str(tenant_id), **kwargs
        )
        if not template:
            return None
        await db.commit()
        return _to_template_type(template)

    @strawberry.mutation
    async def delete_notification_template(
        self, info: Info, tenant_id: uuid.UUID, template_id: uuid.UUID
    ) -> bool:
        """Delete a notification template (soft delete)."""
        await check_graphql_permission(
            info, "notification:template:manage", str(tenant_id)
        )
        from app.services.notification.template_service import TemplateService

        db = await _get_session(info)
        service = TemplateService(db)
        deleted = await service.delete_template(str(template_id), str(tenant_id))
        await db.commit()
        return deleted

    # -- Webhook mutations ----------------------------------------------------

    @strawberry.mutation
    async def create_webhook_config(
        self, info: Info, tenant_id: uuid.UUID, input: WebhookConfigCreateInput
    ) -> WebhookConfigType:
        """Create a webhook configuration."""
        await check_graphql_permission(
            info, "notification:webhook:manage", str(tenant_id)
        )
        from app.models.webhook_config import WebhookAuthType
        from app.services.notification.webhook_service import WebhookService

        db = await _get_session(info)
        service = WebhookService(db)
        config = await service.create_config(
            tenant_id=str(tenant_id),
            name=input.name,
            url=input.url,
            auth_type=WebhookAuthType(input.auth_type.value),
            auth_config=input.auth_config,
            event_filter=input.event_filter,
            batch_size=input.batch_size,
            batch_interval_seconds=input.batch_interval_seconds,
            secret=input.secret,
            is_active=input.is_active,
        )
        await db.commit()
        return _to_webhook_config_type(config)

    @strawberry.mutation
    async def update_webhook_config(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        config_id: uuid.UUID,
        input: WebhookConfigUpdateInput,
    ) -> WebhookConfigType | None:
        """Update a webhook configuration."""
        await check_graphql_permission(
            info, "notification:webhook:manage", str(tenant_id)
        )
        from app.models.webhook_config import WebhookAuthType
        from app.services.notification.webhook_service import WebhookService

        kwargs = {}
        if input.name is not None:
            kwargs["name"] = input.name
        if input.url is not None:
            kwargs["url"] = input.url
        if input.auth_type is not None:
            kwargs["auth_type"] = WebhookAuthType(input.auth_type.value)
        if input.auth_config is not None:
            kwargs["auth_config"] = input.auth_config
        if input.event_filter is not None:
            kwargs["event_filter"] = input.event_filter
        if input.batch_size is not None:
            kwargs["batch_size"] = input.batch_size
        if input.batch_interval_seconds is not None:
            kwargs["batch_interval_seconds"] = input.batch_interval_seconds
        if input.secret is not None:
            kwargs["secret"] = input.secret
        if input.is_active is not None:
            kwargs["is_active"] = input.is_active

        db = await _get_session(info)
        service = WebhookService(db)
        config = await service.update_config(str(config_id), str(tenant_id), **kwargs)
        if not config:
            return None
        await db.commit()
        return _to_webhook_config_type(config)

    @strawberry.mutation
    async def delete_webhook_config(
        self, info: Info, tenant_id: uuid.UUID, config_id: uuid.UUID
    ) -> bool:
        """Delete a webhook configuration (soft delete)."""
        await check_graphql_permission(
            info, "notification:webhook:manage", str(tenant_id)
        )
        from app.services.notification.webhook_service import WebhookService

        db = await _get_session(info)
        service = WebhookService(db)
        deleted = await service.delete_config(str(config_id), str(tenant_id))
        await db.commit()
        return deleted

    @strawberry.mutation
    async def test_webhook(
        self, info: Info, tenant_id: uuid.UUID, config_id: uuid.UUID
    ) -> WebhookTestResultType:
        """Send a test payload to a webhook."""
        await check_graphql_permission(
            info, "notification:webhook:manage", str(tenant_id)
        )
        from app.services.notification.webhook_service import WebhookService

        db = await _get_session(info)
        service = WebhookService(db)
        result = await service.test_webhook(str(config_id), str(tenant_id))
        return WebhookTestResultType(
            success=result.get("success", False),
            message=result.get("message"),
            error=result.get("error"),
        )

    @strawberry.mutation
    async def retry_webhook_delivery(
        self, info: Info, tenant_id: uuid.UUID, delivery_id: uuid.UUID
    ) -> WebhookDeliveryType | None:
        """Retry a dead-letter webhook delivery."""
        await check_graphql_permission(
            info, "notification:webhook:manage", str(tenant_id)
        )
        from app.services.notification.webhook_delivery_service import WebhookDeliveryService

        db = await _get_session(info)
        service = WebhookDeliveryService(db)
        delivery = await service.retry_dead_letter(str(delivery_id), str(tenant_id))
        if not delivery:
            return None
        await db.commit()
        return _to_webhook_delivery_type(delivery)
