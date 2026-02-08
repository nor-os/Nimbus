"""
Overview: Temporal client factory for connecting to Temporal Server.
Architecture: Temporal integration layer (Section 9)
Dependencies: temporalio, app.core.config
Concepts: Temporal workflow engine, client connection, health probing
"""

import logging
from datetime import timedelta

from temporalio.client import Client

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: Client | None = None


async def get_temporal_client() -> Client:
    """Get or create an async Temporal client (singleton)."""
    global _client
    if _client is None:
        settings = get_settings()
        logger.info(
            "Connecting to Temporal at %s (namespace=%s)",
            settings.temporal_address,
            settings.temporal_namespace,
        )
        _client = await Client.connect(
            settings.temporal_address,
            namespace=settings.temporal_namespace,
        )
        logger.info("Temporal client connected")
    return _client


def reset_temporal_client() -> None:
    """Clear the singleton client (for tests or reconnection)."""
    global _client
    _client = None


async def check_temporal_health() -> tuple[bool, str]:
    """Probe Temporal Server connectivity.

    Returns (healthy, detail) — uses a lightweight count_workflows RPC
    with a short timeout so it fails fast when Temporal is unreachable.
    """
    try:
        client = await get_temporal_client()
        await client.count_workflows(rpc_timeout=timedelta(seconds=2))
        return True, "connected"
    except Exception as exc:
        # Connection failure — reset so next call retries
        reset_temporal_client()
        return False, str(exc)
