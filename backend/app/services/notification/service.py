"""
Overview: Central notification dispatch service — single entry point for all downstream phases.
Architecture: Notification orchestrator routing to in-app, email, and webhook channels (Section 4)
Dependencies: app.services.notification.*, sqlalchemy
Concepts: Multi-channel dispatch, preference-based routing, tenant-level webhooks, broadcast
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationCategory, NotificationChannel
from app.models.user import User

logger = logging.getLogger(__name__)


class NotificationService:
    """Central dispatch — the single entry point downstream phases call."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def send(
        self,
        tenant_id: str | uuid.UUID,
        user_ids: list[str | uuid.UUID],
        category: NotificationCategory,
        event_type: str,
        title: str,
        body: str,
        related_resource_type: str | None = None,
        related_resource_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Dispatch notifications to multiple users across all enabled channels.

        Per-user flow:
        1. Check preferences → route to enabled channels
        2. IN_APP enabled → create in-app notification
        3. EMAIL enabled → queue email via Temporal
        4. Always → fire matching webhooks (tenant-level, preference-independent)

        Returns summary dict: {"in_app": N, "email": N, "webhook": N}
        """
        from app.services.notification.email_service import EmailService
        from app.services.notification.in_app_service import InAppService
        from app.services.notification.preference_service import PreferenceService
        from app.services.notification.webhook_delivery_service import WebhookDeliveryService
        from app.services.notification.webhook_service import WebhookService

        pref_service = PreferenceService(self.db)
        in_app_service = InAppService(self.db)
        email_service = EmailService(self.db)
        webhook_service = WebhookService(self.db)
        delivery_service = WebhookDeliveryService(self.db)

        stats = {"in_app": 0, "email": 0, "webhook": 0}
        category_str = category.value if isinstance(category, NotificationCategory) else category

        for uid in user_ids:
            uid_str = str(uid)

            # 1. Check preferences
            prefs = await pref_service.get_effective_preferences(tenant_id, uid_str, category)

            # 2. In-app
            if prefs.get(NotificationChannel.IN_APP, True):
                try:
                    await in_app_service.create_notification(
                        tenant_id=tenant_id,
                        user_id=uid_str,
                        category=category,
                        event_type=event_type,
                        title=title,
                        body=body,
                        related_resource_type=related_resource_type,
                        related_resource_id=related_resource_id,
                    )
                    stats["in_app"] += 1
                except Exception:
                    logger.warning("In-app notification failed for user %s", uid_str, exc_info=True)

            # 3. Email
            if prefs.get(NotificationChannel.EMAIL, True):
                try:
                    user_email = await self._get_user_email(uid_str)
                    if user_email:
                        sent = await email_service.send(
                            tenant_id=tenant_id,
                            user_email=user_email,
                            category=category,
                            event_type=event_type,
                            title=title,
                            body=body,
                            context=context,
                        )
                        if sent:
                            stats["email"] += 1
                except Exception:
                    logger.warning("Email notification failed for user %s", uid_str, exc_info=True)

        # 4. Webhooks — tenant-level, independent of user preferences
        try:
            matching_configs = await webhook_service.get_matching_configs(
                tenant_id, category_str, event_type
            )
            webhook_payload = {
                "event": event_type,
                "category": category_str,
                "title": title,
                "body": body,
                "related_resource_type": related_resource_type,
                "related_resource_id": related_resource_id,
                "data": context or {},
            }
            for config in matching_configs:
                await delivery_service.queue_delivery(
                    tenant_id=tenant_id,
                    config_id=config.id,
                    payload=webhook_payload,
                )
                await delivery_service.dispatch_pending(tenant_id, config.id)
                stats["webhook"] += 1
        except Exception:
            logger.warning("Webhook dispatch failed for tenant %s", tenant_id, exc_info=True)

        return stats

    async def send_to_user(
        self,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        category: NotificationCategory,
        event_type: str,
        title: str,
        body: str,
        related_resource_type: str | None = None,
        related_resource_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Send a notification to a single user."""
        return await self.send(
            tenant_id=tenant_id,
            user_ids=[user_id],
            category=category,
            event_type=event_type,
            title=title,
            body=body,
            related_resource_type=related_resource_type,
            related_resource_id=related_resource_id,
            context=context,
        )

    async def broadcast(
        self,
        tenant_id: str | uuid.UUID,
        category: NotificationCategory,
        event_type: str,
        title: str,
        body: str,
        related_resource_type: str | None = None,
        related_resource_id: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Broadcast a notification to all users in a tenant."""
        from app.models.user_tenant import UserTenant

        tid = uuid.UUID(str(tenant_id))
        stmt = select(UserTenant.user_id).where(UserTenant.tenant_id == tid)
        result = await self.db.execute(stmt)
        user_ids = [str(row[0]) for row in result.all()]

        if not user_ids:
            return {"in_app": 0, "email": 0, "webhook": 0}

        return await self.send(
            tenant_id=tenant_id,
            user_ids=user_ids,
            category=category,
            event_type=event_type,
            title=title,
            body=body,
            related_resource_type=related_resource_type,
            related_resource_id=related_resource_id,
            context=context,
        )

    async def _get_user_email(self, user_id: str) -> str | None:
        """Look up a user's email address."""
        uid = uuid.UUID(user_id)
        stmt = select(User.email).where(User.id == uid, User.deleted_at.is_(None))
        result = await self.db.execute(stmt)
        row = result.first()
        return row[0] if row else None
