"""
Overview: Webhook delivery service — queue, dispatch, retry, and dead letter management.
Architecture: Webhook delivery pipeline for the notification subsystem (Section 4)
Dependencies: sqlalchemy, temporalio, app.models.webhook_delivery, app.models.webhook_config
Concepts: Delivery queue, batch dispatch via Temporal, retry with backoff, dead letter queue
"""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook_config import WebhookConfig
from app.models.webhook_delivery import WebhookDelivery, WebhookDeliveryStatus

logger = logging.getLogger(__name__)


class WebhookDeliveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_delivery(
        self,
        tenant_id: str | uuid.UUID,
        config_id: str | uuid.UUID,
        payload: dict,
    ) -> WebhookDelivery:
        """Queue a new webhook delivery."""
        delivery = WebhookDelivery(
            tenant_id=uuid.UUID(str(tenant_id)),
            webhook_config_id=uuid.UUID(str(config_id)),
            payload=payload,
            status=WebhookDeliveryStatus.PENDING,
            next_retry_at=datetime.now(UTC),
        )
        self.db.add(delivery)
        await self.db.flush()
        return delivery

    async def dispatch_pending(
        self, tenant_id: str | uuid.UUID, config_id: str | uuid.UUID
    ) -> bool:
        """Dispatch pending deliveries for a config via Temporal activity.

        Groups deliveries into batches based on the config's batch_size.
        Returns True if dispatched successfully.
        """
        tid = uuid.UUID(str(tenant_id))
        cid = uuid.UUID(str(config_id))

        # Get config for batch settings and auth
        config_stmt = select(WebhookConfig).where(
            WebhookConfig.id == cid,
            WebhookConfig.tenant_id == tid,
            WebhookConfig.deleted_at.is_(None),
        )
        config_result = await self.db.execute(config_stmt)
        config = config_result.scalar_one_or_none()
        if not config:
            return False

        # Get pending deliveries
        now = datetime.now(UTC)
        pending_stmt = (
            select(WebhookDelivery)
            .where(
                WebhookDelivery.webhook_config_id == cid,
                WebhookDelivery.tenant_id == tid,
                WebhookDelivery.status == WebhookDeliveryStatus.PENDING,
                WebhookDelivery.next_retry_at <= now,
            )
            .order_by(WebhookDelivery.created_at)
            .limit(config.batch_size)
        )
        result = await self.db.execute(pending_stmt)
        deliveries = list(result.scalars().all())
        if not deliveries:
            return True

        delivery_ids = [str(d.id) for d in deliveries]
        payloads = [d.payload for d in deliveries]

        try:
            from app.core.config import get_settings
            from app.core.temporal import get_temporal_client
            from app.workflows.activities.notification import (
                SendWebhookBatchInput,
                WebhookTarget,
            )
            from app.workflows.send_webhook_batch import SendWebhookBatchWorkflow

            settings = get_settings()
            client = await get_temporal_client()

            target = WebhookTarget(
                url=config.url,
                auth_type=config.auth_type.value,
                auth_config=config.auth_config,
                secret=config.secret,
            )

            await client.start_workflow(
                SendWebhookBatchWorkflow.run,
                SendWebhookBatchInput(
                    delivery_ids=delivery_ids,
                    target=target,
                    payloads=payloads,
                ),
                id=f"webhook-batch-{uuid.uuid4()}",
                task_queue=settings.temporal_task_queue,
            )
            return True
        except Exception:
            logger.warning(
                "Failed to dispatch webhook batch for config %s", config_id, exc_info=True
            )
            return False

    async def mark_delivered(self, delivery_id: str | uuid.UUID) -> WebhookDelivery | None:
        """Mark a delivery as successfully delivered."""
        did = uuid.UUID(str(delivery_id))
        stmt = select(WebhookDelivery).where(WebhookDelivery.id == did)
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = WebhookDeliveryStatus.DELIVERED
        delivery.attempts += 1
        delivery.last_attempt_at = datetime.now(UTC)
        delivery.next_retry_at = None
        await self.db.flush()
        return delivery

    async def mark_failed(
        self, delivery_id: str | uuid.UUID, error: str
    ) -> WebhookDelivery | None:
        """Mark a delivery as failed. Moves to DEAD_LETTER if max_attempts exceeded."""
        did = uuid.UUID(str(delivery_id))
        stmt = select(WebhookDelivery).where(WebhookDelivery.id == did)
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        now = datetime.now(UTC)
        delivery.attempts += 1
        delivery.last_attempt_at = now
        delivery.last_error = error[:2000]

        if delivery.attempts >= delivery.max_attempts:
            delivery.status = WebhookDeliveryStatus.DEAD_LETTER
            delivery.next_retry_at = None
        else:
            delivery.status = WebhookDeliveryStatus.FAILED
            # Exponential backoff: 30s, 60s, 120s, 240s, ...
            backoff = timedelta(seconds=30 * (2 ** (delivery.attempts - 1)))
            delivery.next_retry_at = now + backoff

        await self.db.flush()
        return delivery

    async def mark_dead_letter(self, delivery_id: str | uuid.UUID) -> WebhookDelivery | None:
        """Manually move a delivery to the dead letter queue."""
        did = uuid.UUID(str(delivery_id))
        stmt = select(WebhookDelivery).where(WebhookDelivery.id == did)
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = WebhookDeliveryStatus.DEAD_LETTER
        delivery.next_retry_at = None
        await self.db.flush()
        return delivery

    async def retry_dead_letter(
        self, delivery_id: str | uuid.UUID, tenant_id: str | uuid.UUID
    ) -> WebhookDelivery | None:
        """Reset a dead-letter delivery to PENDING for retry."""
        did = uuid.UUID(str(delivery_id))
        tid = uuid.UUID(str(tenant_id))
        stmt = select(WebhookDelivery).where(
            WebhookDelivery.id == did,
            WebhookDelivery.tenant_id == tid,
            WebhookDelivery.status == WebhookDeliveryStatus.DEAD_LETTER,
        )
        result = await self.db.execute(stmt)
        delivery = result.scalar_one_or_none()
        if not delivery:
            return None

        delivery.status = WebhookDeliveryStatus.PENDING
        delivery.attempts = 0
        delivery.next_retry_at = datetime.now(UTC)
        delivery.last_error = None
        await self.db.flush()
        return delivery

    async def list_deliveries(
        self,
        tenant_id: str | uuid.UUID,
        config_id: str | uuid.UUID | None = None,
        status: WebhookDeliveryStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[WebhookDelivery], int]:
        """List deliveries with optional filters. Returns (items, total)."""
        tid = uuid.UUID(str(tenant_id))

        base = select(WebhookDelivery).where(WebhookDelivery.tenant_id == tid)
        if config_id:
            base = base.where(WebhookDelivery.webhook_config_id == uuid.UUID(str(config_id)))
        if status:
            base = base.where(WebhookDelivery.status == status)

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        items_stmt = base.order_by(WebhookDelivery.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total
