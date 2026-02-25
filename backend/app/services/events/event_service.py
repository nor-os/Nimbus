"""
Overview: Event CRUD service — manages event types, subscriptions, and event log queries.
Architecture: Service layer for event management (Section 11.6)
Dependencies: sqlalchemy, app.models.event, app.services.events.registry
Concepts: Event type CRUD, subscription management, event log querying
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.event import (
    EventDelivery,
    EventLog,
    EventSubscription,
    EventType,
)
from app.services.events.registry import get_event_type_registry

logger = logging.getLogger(__name__)


class EventService:
    """CRUD operations for event types, subscriptions, and event log."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # -- Event Types -----------------------------------------------------------

    async def list_event_types(
        self,
        tenant_id: str | None = None,
        category: str | None = None,
        search: str | None = None,
    ) -> list[EventType]:
        """List event types — merges system (tenant_id=NULL) + tenant custom."""
        from sqlalchemy import or_

        query = select(EventType).where(EventType.deleted_at.is_(None))

        conditions = [EventType.tenant_id.is_(None)]  # Always include system
        if tenant_id:
            conditions.append(EventType.tenant_id == tenant_id)
        query = query.where(or_(*conditions))

        if category:
            query = query.where(EventType.category == category)
        if search:
            query = query.where(EventType.name.ilike(f"%{search}%"))

        query = query.order_by(EventType.category, EventType.name)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_event_type(self, event_type_id: str) -> EventType | None:
        result = await self._db.execute(
            select(EventType).where(
                EventType.id == event_type_id,
                EventType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_event_type(
        self, tenant_id: str, data: dict[str, Any]
    ) -> EventType:
        event_type = EventType(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            category=data.get("category", "CUSTOM"),
            payload_schema=data.get("payload_schema"),
            source_validators=data.get("source_validators"),
            is_system=False,
            is_active=True,
        )
        self._db.add(event_type)
        await self._db.flush()
        return event_type

    async def update_event_type(
        self, event_type_id: str, data: dict[str, Any]
    ) -> EventType:
        et = await self.get_event_type(event_type_id)
        if not et:
            raise ValueError("Event type not found")
        if et.is_system:
            raise ValueError("Cannot modify system event types")

        for key in ("name", "description", "category", "payload_schema",
                     "source_validators", "is_active"):
            if key in data:
                setattr(et, key, data[key])

        return et

    async def delete_event_type(self, event_type_id: str) -> bool:
        et = await self.get_event_type(event_type_id)
        if not et:
            return False
        if et.is_system:
            raise ValueError("Cannot delete system event types")

        et.deleted_at = datetime.now(timezone.utc)
        return True

    # -- Subscriptions ---------------------------------------------------------

    async def list_subscriptions(
        self,
        tenant_id: str,
        event_type_id: str | None = None,
    ) -> list[EventSubscription]:
        query = select(EventSubscription).where(
            EventSubscription.tenant_id == tenant_id,
            EventSubscription.deleted_at.is_(None),
        )
        if event_type_id:
            query = query.where(EventSubscription.event_type_id == event_type_id)

        query = query.order_by(EventSubscription.priority)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_subscription(
        self, subscription_id: str
    ) -> EventSubscription | None:
        result = await self._db.execute(
            select(EventSubscription).where(
                EventSubscription.id == subscription_id,
                EventSubscription.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_subscription(
        self, tenant_id: str, data: dict[str, Any]
    ) -> EventSubscription:
        sub = EventSubscription(
            tenant_id=tenant_id,
            event_type_id=data["event_type_id"],
            name=data["name"],
            handler_type=data["handler_type"],
            handler_config=data.get("handler_config", {}),
            filter_expression=data.get("filter_expression"),
            priority=data.get("priority", 100),
            is_active=data.get("is_active", True),
            is_system=False,
        )
        self._db.add(sub)
        await self._db.flush()
        return sub

    async def update_subscription(
        self, subscription_id: str, data: dict[str, Any]
    ) -> EventSubscription:
        sub = await self.get_subscription(subscription_id)
        if not sub:
            raise ValueError("Subscription not found")
        if sub.is_system:
            raise ValueError("Cannot modify system subscriptions")

        for key in ("name", "handler_type", "handler_config", "filter_expression",
                     "priority", "is_active"):
            if key in data:
                setattr(sub, key, data[key])

        return sub

    async def delete_subscription(self, subscription_id: str) -> bool:
        sub = await self.get_subscription(subscription_id)
        if not sub:
            return False
        if sub.is_system:
            raise ValueError("Cannot delete system subscriptions")

        sub.deleted_at = datetime.now(timezone.utc)
        return True

    # -- Event Log -------------------------------------------------------------

    async def list_event_log(
        self,
        tenant_id: str,
        event_type_name: str | None = None,
        source: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[EventLog]:
        query = select(EventLog).where(EventLog.tenant_id == tenant_id)

        if event_type_name:
            query = query.where(EventLog.event_type_name == event_type_name)
        if source:
            query = query.where(EventLog.source == source)

        query = query.order_by(EventLog.emitted_at.desc()).offset(offset).limit(limit)
        result = await self._db.execute(query)
        return list(result.scalars().all())

    async def get_event_log_entry(self, entry_id: str) -> EventLog | None:
        result = await self._db.execute(
            select(EventLog)
            .options(selectinload(EventLog.deliveries))
            .where(EventLog.id == entry_id)
        )
        return result.scalar_one_or_none()
