"""
Overview: In-app notification service — create, list, mark-read, delete notifications.
Architecture: In-app delivery channel for the notification subsystem (Section 4)
Dependencies: sqlalchemy, app.models.notification
Concepts: In-app notifications, unread count, pagination, soft delete
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationCategory

logger = logging.getLogger(__name__)


class InAppService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_notification(
        self,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        category: NotificationCategory,
        event_type: str,
        title: str,
        body: str,
        related_resource_type: str | None = None,
        related_resource_id: str | None = None,
    ) -> Notification:
        """Create an in-app notification for a user."""
        notification = Notification(
            tenant_id=uuid.UUID(str(tenant_id)),
            user_id=uuid.UUID(str(user_id)),
            category=category,
            event_type=event_type,
            title=title,
            body=body,
            related_resource_type=related_resource_type,
            related_resource_id=related_resource_id,
        )
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def list_notifications(
        self,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        is_read: bool | None = None,
        category: NotificationCategory | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[Notification], int, int]:
        """List notifications with optional filters.

        Returns (items, total_count, unread_count).
        """
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))

        base = select(Notification).where(
            Notification.tenant_id == tid,
            Notification.user_id == uid,
            Notification.deleted_at.is_(None),
        )

        if is_read is not None:
            base = base.where(Notification.is_read == is_read)
        if category is not None:
            base = base.where(Notification.category == category)

        # Total count
        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Unread count (always unfiltered by is_read/category)
        unread_count = await self.get_unread_count(tenant_id, user_id)

        # Items
        items_stmt = base.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total, unread_count

    async def get_unread_count(
        self, tenant_id: str | uuid.UUID, user_id: str | uuid.UUID
    ) -> int:
        """Get total unread notification count for a user."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        stmt = select(func.count()).where(
            Notification.tenant_id == tid,
            Notification.user_id == uid,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def mark_read(
        self,
        notification_id: str | uuid.UUID,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> Notification | None:
        """Mark a single notification as read."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        nid = uuid.UUID(str(notification_id))

        stmt = select(Notification).where(
            Notification.id == nid,
            Notification.tenant_id == tid,
            Notification.user_id == uid,
            Notification.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        notification = result.scalar_one_or_none()
        if not notification:
            return None

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(UTC)
            await self.db.flush()

        return notification

    async def mark_all_read(
        self, tenant_id: str | uuid.UUID, user_id: str | uuid.UUID
    ) -> int:
        """Mark all unread notifications as read. Returns count updated."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        now = datetime.now(UTC)

        stmt = select(Notification).where(
            Notification.tenant_id == tid,
            Notification.user_id == uid,
            Notification.is_read.is_(False),
            Notification.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        notifications = result.scalars().all()
        count = 0
        for n in notifications:
            n.is_read = True
            n.read_at = now
            count += 1
        if count:
            await self.db.flush()
        return count

    async def delete_notification(
        self,
        notification_id: str | uuid.UUID,
        tenant_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
    ) -> bool:
        """Soft-delete a notification."""
        tid = uuid.UUID(str(tenant_id))
        uid = uuid.UUID(str(user_id))
        nid = uuid.UUID(str(notification_id))

        stmt = select(Notification).where(
            Notification.id == nid,
            Notification.tenant_id == tid,
            Notification.user_id == uid,
            Notification.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        notification = result.scalar_one_or_none()
        if not notification:
            return False

        notification.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
