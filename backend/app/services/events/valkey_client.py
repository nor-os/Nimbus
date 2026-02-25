"""
Overview: Valkey (Redis-compatible) client for event stream transport.
Architecture: Async Valkey client with stream helpers (Section 11.6)
Dependencies: valkey
Concepts: Valkey Streams, consumer groups, event dispatch queue
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

VALKEY_URL = os.getenv("VALKEY_URL", "redis://localhost:6379")
STREAM_PREFIX = "nimbus:events:"
CONSUMER_GROUP = "nimbus-event-handlers"

_client = None


async def get_valkey_client():
    """Get or create the async Valkey client singleton."""
    global _client
    if _client is None:
        try:
            import valkey.asyncio as avalkey
            _client = avalkey.from_url(VALKEY_URL, decode_responses=True)
            logger.info("Connected to Valkey at %s", VALKEY_URL)
        except ImportError:
            logger.warning("valkey package not installed; event streams disabled")
            return None
        except Exception as e:
            logger.error("Failed to connect to Valkey: %s", e)
            return None
    return _client


def stream_key(tenant_id: str) -> str:
    """Build the Valkey stream key for a tenant."""
    return f"{STREAM_PREFIX}{tenant_id}"


async def xadd_event(
    tenant_id: str,
    event_log_id: str,
    event_type_name: str,
    payload_json: str,
    source: str,
    emitted_by: str | None = None,
    trace_id: str | None = None,
) -> str | None:
    """Add an event to the tenant's stream. Returns the stream entry ID."""
    client = await get_valkey_client()
    if client is None:
        return None

    key = stream_key(tenant_id)
    entry: dict[str, Any] = {
        "event_log_id": event_log_id,
        "event_type_name": event_type_name,
        "payload": payload_json,
        "source": source,
        "emitted_by": emitted_by or "",
        "trace_id": trace_id or "",
    }

    try:
        entry_id = await client.xadd(key, entry)
        logger.debug("XADD %s -> %s", key, entry_id)
        return entry_id
    except Exception as e:
        logger.error("Failed to XADD event to %s: %s", key, e)
        return None


async def create_consumer_group(tenant_id: str | None = None) -> None:
    """Create the consumer group for event processing.

    If tenant_id is None, creates a wildcard-safe group that works for any stream.
    """
    client = await get_valkey_client()
    if client is None:
        return

    # Create group on the default stream; individual tenant streams
    # will have their groups auto-created on first read
    key = stream_key(tenant_id or "default")
    try:
        await client.xgroup_create(key, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info("Created consumer group '%s' on stream '%s'", CONSUMER_GROUP, key)
    except Exception as e:
        # Group already exists
        if "BUSYGROUP" in str(e):
            logger.debug("Consumer group '%s' already exists on '%s'", CONSUMER_GROUP, key)
        else:
            logger.error("Failed to create consumer group: %s", e)


async def ensure_consumer_group(tenant_id: str) -> None:
    """Ensure the consumer group exists for a tenant stream."""
    client = await get_valkey_client()
    if client is None:
        return

    key = stream_key(tenant_id)
    try:
        await client.xgroup_create(key, CONSUMER_GROUP, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error("Failed to ensure consumer group for %s: %s", key, e)


async def xreadgroup(
    consumer_name: str,
    streams: list[str],
    count: int = 10,
    block: int = 5000,
) -> list | None:
    """Read from consumer group across multiple streams."""
    client = await get_valkey_client()
    if client is None:
        return None

    try:
        stream_dict = {s: ">" for s in streams}
        result = await client.xreadgroup(
            CONSUMER_GROUP, consumer_name, stream_dict,
            count=count, block=block,
        )
        return result
    except Exception as e:
        logger.error("Failed to XREADGROUP: %s", e)
        return None


async def xack(stream: str, *entry_ids: str) -> int:
    """Acknowledge processed entries."""
    client = await get_valkey_client()
    if client is None:
        return 0

    try:
        return await client.xack(stream, CONSUMER_GROUP, *entry_ids)
    except Exception as e:
        logger.error("Failed to XACK %s: %s", stream, e)
        return 0


async def close_client() -> None:
    """Close the Valkey client on shutdown."""
    global _client
    if _client is not None:
        await _client.close()
        _client = None
        logger.info("Valkey client closed")
