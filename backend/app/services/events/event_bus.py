"""
Overview: EventBus — core emit logic that persists to PostgreSQL and dispatches via Valkey Streams.
Architecture: Hybrid event bus (audit trail + dispatch queue) (Section 11.6)
Dependencies: sqlalchemy, app.models.event, app.services.events.registry, app.services.events.valkey_client
Concepts: Event emission, source validation, payload validation, fire-and-forget
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import EventLog, EventType
from app.services.events.registry import get_event_type_registry
from app.services.events.valkey_client import xadd_event

logger = logging.getLogger(__name__)


class EventBus:
    """Emits events to PostgreSQL (audit trail) and Valkey Streams (dispatch queue)."""

    def __init__(self, db: AsyncSession):
        self._db = db

    async def emit(
        self,
        event_type_name: str,
        payload: dict[str, Any],
        tenant_id: str,
        source: str,
        emitted_by: str | None = None,
        trace_id: str | None = None,
    ) -> EventLog:
        """Emit an event: validate, persist to DB, push to Valkey stream.

        Returns the EventLog record.
        """
        # 1. Look up event type (DB first, then registry fallback)
        event_type = await self._resolve_event_type(event_type_name, tenant_id)

        # 2. Validate source
        if event_type and event_type.source_validators:
            if source not in event_type.source_validators:
                logger.warning(
                    "Source '%s' not in validators %s for event '%s'",
                    source, event_type.source_validators, event_type_name,
                )

        # 3. Persist to PostgreSQL (audit trail)
        event_log = EventLog(
            tenant_id=tenant_id,
            event_type_id=event_type.id if event_type else None,
            event_type_name=event_type_name,
            source=source,
            payload=payload,
            emitted_by=emitted_by,
            trace_id=trace_id,
        )
        self._db.add(event_log)
        await self._db.flush()

        # 4. Push to Valkey Stream (dispatch queue)
        try:
            await xadd_event(
                tenant_id=tenant_id,
                event_log_id=str(event_log.id),
                event_type_name=event_type_name,
                payload_json=json.dumps(payload),
                source=source,
                emitted_by=emitted_by,
                trace_id=trace_id,
            )
        except Exception as e:
            logger.error("Failed to push event to Valkey: %s", e)

        return event_log

    async def _resolve_event_type(
        self, name: str, tenant_id: str
    ) -> EventType | None:
        """Look up event type from DB, falling back to registry check."""
        result = await self._db.execute(
            select(EventType).where(
                EventType.name == name,
                EventType.deleted_at.is_(None),
            )
        )
        db_type = result.scalar_one_or_none()
        if db_type:
            return db_type

        # Check registry (system types may not be in DB yet during startup)
        registry = get_event_type_registry()
        if registry.has(name):
            logger.debug("Event type '%s' found in registry but not DB", name)
        else:
            logger.warning("Unknown event type '%s'", name)

        return None


async def emit_event(
    event_type_name: str,
    payload: dict[str, Any],
    tenant_id: str,
    source: str,
    emitted_by: str | None = None,
    trace_id: str | None = None,
) -> EventLog | None:
    """Convenience function: create session, emit, commit."""
    from app.db.session import async_session_factory

    try:
        async with async_session_factory() as db:
            bus = EventBus(db)
            event_log = await bus.emit(
                event_type_name, payload, tenant_id, source, emitted_by, trace_id
            )
            await db.commit()
            return event_log
    except Exception as e:
        logger.error("Failed to emit event '%s': %s", event_type_name, e)
        return None


def emit_event_async(
    event_type_name: str,
    payload: dict[str, Any],
    tenant_id: str,
    source: str,
    emitted_by: str | None = None,
    trace_id: str | None = None,
) -> None:
    """Fire-and-forget event emission via asyncio.create_task."""
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(
            emit_event(event_type_name, payload, tenant_id, source, emitted_by, trace_id)
        )
    except RuntimeError:
        logger.warning("No running event loop; cannot emit event '%s' async", event_type_name)
