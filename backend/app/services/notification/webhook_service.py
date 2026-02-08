"""
Overview: Webhook configuration service — CRUD, event matching, test dispatch.
Architecture: Webhook management layer for the notification subsystem (Section 4)
Dependencies: sqlalchemy, app.models.webhook_config
Concepts: Webhook configs, event filtering, JSONB-based filter matching, tenant-level endpoints
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_config import WebhookAuthType, WebhookConfig

logger = logging.getLogger(__name__)


class WebhookService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_config(
        self,
        tenant_id: str | uuid.UUID,
        name: str,
        url: str,
        auth_type: WebhookAuthType = WebhookAuthType.NONE,
        auth_config: dict | None = None,
        event_filter: dict | None = None,
        batch_size: int = 1,
        batch_interval_seconds: int = 0,
        secret: str | None = None,
        is_active: bool = True,
    ) -> WebhookConfig:
        """Create a webhook configuration."""
        config = WebhookConfig(
            tenant_id=uuid.UUID(str(tenant_id)),
            name=name,
            url=url,
            auth_type=auth_type,
            auth_config=auth_config,
            event_filter=event_filter,
            batch_size=batch_size,
            batch_interval_seconds=batch_interval_seconds,
            secret=secret,
            is_active=is_active,
        )
        self.db.add(config)
        await self.db.flush()
        return config

    async def get_config(
        self, config_id: str | uuid.UUID, tenant_id: str | uuid.UUID
    ) -> WebhookConfig | None:
        """Get a single webhook config by ID within a tenant."""
        tid = uuid.UUID(str(tenant_id))
        cid = uuid.UUID(str(config_id))
        stmt = select(WebhookConfig).where(
            WebhookConfig.id == cid,
            WebhookConfig.tenant_id == tid,
            WebhookConfig.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_configs(
        self, tenant_id: str | uuid.UUID
    ) -> list[WebhookConfig]:
        """List all webhook configs for a tenant."""
        tid = uuid.UUID(str(tenant_id))
        stmt = (
            select(WebhookConfig)
            .where(
                WebhookConfig.tenant_id == tid,
                WebhookConfig.deleted_at.is_(None),
            )
            .order_by(WebhookConfig.name)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_config(
        self, config_id: str | uuid.UUID, tenant_id: str | uuid.UUID, **kwargs
    ) -> WebhookConfig | None:
        """Update a webhook config."""
        config = await self.get_config(config_id, tenant_id)
        if not config:
            return None
        for key, value in kwargs.items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
        await self.db.flush()
        return config

    async def delete_config(
        self, config_id: str | uuid.UUID, tenant_id: str | uuid.UUID
    ) -> bool:
        """Soft-delete a webhook config."""
        config = await self.get_config(config_id, tenant_id)
        if not config:
            return False
        config.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_matching_configs(
        self, tenant_id: str | uuid.UUID, category: str, event_type: str
    ) -> list[WebhookConfig]:
        """Find active webhook configs whose event_filter matches the given category/event_type.

        event_filter JSONB structure:
        {
            "categories": ["APPROVAL", "SECURITY"],   // optional allowlist
            "event_types": ["approval_requested"]      // optional allowlist
        }

        If event_filter is null/empty, the webhook matches ALL events.
        """
        tid = uuid.UUID(str(tenant_id))
        stmt = select(WebhookConfig).where(
            WebhookConfig.tenant_id == tid,
            WebhookConfig.is_active.is_(True),
            WebhookConfig.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        configs = result.scalars().all()

        matching = []
        for config in configs:
            if _matches_filter(config.event_filter, category, event_type):
                matching.append(config)
        return matching

    async def test_webhook(
        self, config_id: str | uuid.UUID, tenant_id: str | uuid.UUID
    ) -> dict:
        """Send a test payload to a webhook and return the result."""
        config = await self.get_config(config_id, tenant_id)
        if not config:
            return {"success": False, "error": "Webhook config not found"}

        test_payload = {
            "event": "webhook.test",
            "category": "SYSTEM",
            "event_type": "webhook_test",
            "data": {"message": "This is a test webhook delivery from Nimbus."},
        }

        try:
            from app.core.config import get_settings
            from app.core.temporal import get_temporal_client
            from app.workflows.activities.notification import (
                SendWebhookBatchInput,
                WebhookTarget,
            )

            settings = get_settings()
            client = await get_temporal_client()

            target = WebhookTarget(
                url=config.url,
                auth_type=config.auth_type.value,
                auth_config=config.auth_config,
                secret=config.secret,
            )

            await client.start_workflow(
                "SendWebhookTestWorkflow",
                SendWebhookBatchInput(
                    delivery_ids=[str(uuid.uuid4())],
                    target=target,
                    payloads=[test_payload],
                ),
                id=f"webhook-test-{uuid.uuid4()}",
                task_queue=settings.temporal_task_queue,
            )
            return {"success": True, "message": "Test webhook dispatched"}
        except Exception as e:
            logger.warning("Webhook test failed for config %s: %s", config_id, e)
            return {"success": False, "error": str(e)}


def _matches_filter(
    event_filter: dict | None, category: str, event_type: str
) -> bool:
    """Check if an event matches a webhook's event_filter."""
    if not event_filter:
        return True

    categories = event_filter.get("categories")
    if categories and category not in categories:
        return False

    event_types = event_filter.get("event_types")
    return not (event_types and event_type not in event_types)
