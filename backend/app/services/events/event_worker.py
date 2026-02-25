"""
Overview: Event worker — background Valkey Stream consumer that dispatches subscriptions.
Architecture: Consumer-side event processing (Section 11.6)
Dependencies: app.services.events.valkey_client, app.services.events.handlers, app.services.events.filter_engine
Concepts: Valkey Streams, consumer groups, subscription matching, delivery tracking
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventDelivery, EventDeliveryStatus, EventLog, EventSubscription
from app.services.events.filter_engine import evaluate_filter
from app.services.events.registry import get_subscription_registry
from app.services.events.valkey_client import (
    CONSUMER_GROUP,
    STREAM_PREFIX,
    ensure_consumer_group,
    xack,
    xreadgroup,
)

logger = logging.getLogger(__name__)

CONSUMER_NAME = f"worker-{os.getpid()}-{uuid.uuid4().hex[:8]}"


class EventWorker:
    """Background consumer that reads from Valkey Streams and dispatches handlers."""

    def __init__(self, tenant_ids: list[str] | None = None):
        self._running = False
        self._tenant_ids = tenant_ids or []

    async def start(self) -> None:
        """Start the consumer loop."""
        self._running = True
        logger.info("Event worker starting (consumer=%s)", CONSUMER_NAME)

        # Ensure consumer groups exist
        for tid in self._tenant_ids:
            await ensure_consumer_group(tid)

        while self._running:
            try:
                await self._poll()
            except Exception as e:
                logger.error("Event worker poll error: %s", e)
                import asyncio
                await asyncio.sleep(1)

    def stop(self) -> None:
        """Signal the worker to stop."""
        self._running = False
        logger.info("Event worker stopping")

    async def _poll(self) -> None:
        """Poll streams for new entries and process them."""
        streams = [f"{STREAM_PREFIX}{tid}" for tid in self._tenant_ids]
        if not streams:
            # Discover streams from Valkey
            streams = await self._discover_streams()

        if not streams:
            import asyncio
            await asyncio.sleep(2)
            return

        result = await xreadgroup(CONSUMER_NAME, streams, count=10, block=5000)
        if not result:
            return

        for stream_name, entries in result:
            for entry_id, fields in entries:
                await self._process_entry(stream_name, entry_id, fields)

    async def _process_entry(
        self, stream: str, entry_id: str, fields: dict[str, Any]
    ) -> None:
        """Process a single stream entry."""
        event_log_id = fields.get("event_log_id", "")
        event_type_name = fields.get("event_type_name", "")
        payload_str = fields.get("payload", "{}")
        source = fields.get("source", "")

        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            payload = {}

        # Extract tenant_id from stream key
        tenant_id = stream.replace(STREAM_PREFIX, "")

        logger.debug(
            "Processing event %s (type=%s, log=%s)",
            entry_id, event_type_name, event_log_id,
        )

        try:
            from app.db.session import async_session_factory

            async with async_session_factory() as db:
                # Get matching subscriptions
                subscriptions = await self._get_matching_subscriptions(
                    db, tenant_id, event_type_name, event_log_id
                )

                # Get the EventLog record
                event_log = None
                if event_log_id:
                    result = await db.execute(
                        select(EventLog).where(EventLog.id == event_log_id)
                    )
                    event_log = result.scalar_one_or_none()

                if not event_log:
                    logger.warning("EventLog %s not found, skipping", event_log_id)
                    await xack(stream, entry_id)
                    return

                # Process each subscription
                for sub in subscriptions:
                    await self._dispatch_subscription(db, sub, event_log, payload)

                await db.commit()

            # ACK the stream entry
            await xack(stream, entry_id)

        except Exception as e:
            logger.error("Failed to process entry %s: %s", entry_id, e)

    async def _get_matching_subscriptions(
        self,
        db: AsyncSession,
        tenant_id: str,
        event_type_name: str,
        event_log_id: str,
    ) -> list[EventSubscription]:
        """Find DB subscriptions that match the event type."""
        from app.models.event import EventType

        # Find by event type name → get type ID → query subscriptions
        type_result = await db.execute(
            select(EventType).where(
                EventType.name == event_type_name,
                EventType.deleted_at.is_(None),
            )
        )
        event_type = type_result.scalar_one_or_none()
        if not event_type:
            return []

        sub_result = await db.execute(
            select(EventSubscription).where(
                EventSubscription.event_type_id == event_type.id,
                EventSubscription.tenant_id == tenant_id,
                EventSubscription.is_active.is_(True),
                EventSubscription.deleted_at.is_(None),
            ).order_by(EventSubscription.priority)
        )
        return list(sub_result.scalars().all())

    async def _dispatch_subscription(
        self,
        db: AsyncSession,
        subscription: EventSubscription,
        event_log: EventLog,
        payload: dict[str, Any],
    ) -> None:
        """Evaluate filter and dispatch a single subscription."""
        # Evaluate filter expression
        if subscription.filter_expression:
            if not evaluate_filter(subscription.filter_expression, payload):
                logger.debug(
                    "Filter rejected subscription %s for event %s",
                    subscription.id, event_log.id,
                )
                return

        # Create delivery record
        delivery = EventDelivery(
            event_log_id=event_log.id,
            subscription_id=subscription.id,
            status=EventDeliveryStatus.PROCESSING.value,
            attempts=1,
            started_at=datetime.now(timezone.utc),
        )
        db.add(delivery)
        await db.flush()

        # Dispatch
        from app.services.events.handlers import dispatch as dispatch_handler

        try:
            result = await dispatch_handler(subscription, event_log, delivery)

            if result.get("error"):
                delivery.status = EventDeliveryStatus.FAILED.value
                delivery.error = result["error"]
            else:
                delivery.status = EventDeliveryStatus.DELIVERED.value
                delivery.handler_output = result
                delivery.delivered_at = datetime.now(timezone.utc)

        except Exception as e:
            delivery.status = EventDeliveryStatus.FAILED.value
            delivery.error = str(e)
            logger.error(
                "Delivery %s failed for subscription %s: %s",
                delivery.id, subscription.id, e,
            )

    async def _discover_streams(self) -> list[str]:
        """Discover tenant streams from Valkey keys."""
        from app.services.events.valkey_client import get_valkey_client

        client = await get_valkey_client()
        if not client:
            return []

        try:
            keys = []
            async for key in client.scan_iter(match=f"{STREAM_PREFIX}*", count=100):
                keys.append(key)
                # Ensure consumer group exists
                tenant_id = key.replace(STREAM_PREFIX, "")
                await ensure_consumer_group(tenant_id)
            return keys
        except Exception as e:
            logger.error("Failed to discover streams: %s", e)
            return []
