"""
Overview: Notification preference service — per-user channel opt-in/opt-out management.
Architecture: Preference lookup and bulk upsert for notification routing (Section 4)
Dependencies: sqlalchemy, app.models.notification_preference
Concepts: Channel preferences, category-based routing, default-all-enabled semantics
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationCategory, NotificationChannel
from app.models.notification_preference import NotificationPreference

logger = logging.getLogger(__name__)


class PreferenceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_preferences(
        self, tenant_id: str | uuid.UUID, user_id: str | uuid.UUID
    ) -> list[NotificationPreference]:
        """Get all explicit preferences for a user."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tid,
            NotificationPreference.user_id == uid,
            NotificationPreference.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_effective_preferences(
        self, tenant_id: str | uuid.UUID, user_id: str | uuid.UUID, category: NotificationCategory
    ) -> dict[NotificationChannel, bool]:
        """Get effective channel preferences for a category. Defaults to all enabled."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))

        # Start with all channels enabled by default
        result: dict[NotificationChannel, bool] = {
            channel: True for channel in NotificationChannel
        }

        stmt = select(NotificationPreference).where(
            NotificationPreference.tenant_id == tid,
            NotificationPreference.user_id == uid,
            NotificationPreference.category == category,
            NotificationPreference.deleted_at.is_(None),
        )
        rows = await self.db.execute(stmt)
        for pref in rows.scalars().all():
            result[pref.channel] = pref.enabled

        return result

    async def is_channel_enabled(
        self,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        category: NotificationCategory,
        channel: NotificationChannel,
    ) -> bool:
        """Check if a specific channel is enabled for a user/category. Default: True."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        stmt = (
            select(NotificationPreference)
            .where(
                NotificationPreference.tenant_id == tid,
                NotificationPreference.user_id == uid,
                NotificationPreference.category == category,
                NotificationPreference.channel == channel,
                NotificationPreference.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        pref = result.scalar_one_or_none()
        if pref is None:
            return True  # Default enabled
        return pref.enabled

    async def update_preferences(
        self,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        updates: list[dict],
    ) -> list[NotificationPreference]:
        """Bulk upsert preferences. Each dict has: category, channel, enabled."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        results = []

        for update in updates:
            category = NotificationCategory(update["category"])
            channel = NotificationChannel(update["channel"])
            enabled = update["enabled"]

            stmt = (
                select(NotificationPreference)
                .where(
                    NotificationPreference.tenant_id == tid,
                    NotificationPreference.user_id == uid,
                    NotificationPreference.category == category,
                    NotificationPreference.channel == channel,
                    NotificationPreference.deleted_at.is_(None),
                )
                .limit(1)
            )
            result = await self.db.execute(stmt)
            pref = result.scalar_one_or_none()

            if pref:
                pref.enabled = enabled
            else:
                pref = NotificationPreference(
                    tenant_id=tid,
                    user_id=uid,
                    category=category,
                    channel=channel,
                    enabled=enabled,
                )
                self.db.add(pref)

            await self.db.flush()
            results.append(pref)

        return results
