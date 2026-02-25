"""
Overview: CLI entrypoint for the event worker process.
Architecture: Standalone consumer process with graceful shutdown (Section 11.6)
Dependencies: app.services.events.event_worker
Concepts: Signal handling, graceful shutdown, consumer lifecycle
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    """Start the event worker with graceful shutdown."""
    from app.services.events.event_worker import EventWorker
    from app.services.events.system_events import register_system_events

    # Register system events
    register_system_events()

    worker = EventWorker()

    # Set up signal handlers
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, worker.stop)

    logger.info("Event worker starting...")
    try:
        await worker.start()
    except asyncio.CancelledError:
        pass
    finally:
        from app.services.events.valkey_client import close_client
        await close_client()
        logger.info("Event worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Event worker interrupted")
        sys.exit(0)
