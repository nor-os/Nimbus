"""
Overview: Temporal workflow for durable webhook batch delivery.
Architecture: Notification webhook workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.notification
Concepts: Durable webhook delivery, batch dispatch, retry policy
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.notification import (
        SendWebhookBatchInput,
        SendWebhookBatchResult,
        send_webhook_batch_activity,
    )


@workflow.defn
class SendWebhookBatchWorkflow:
    @workflow.run
    async def run(self, input: SendWebhookBatchInput) -> SendWebhookBatchResult:
        """Execute webhook batch delivery with retry."""
        return await workflow.execute_activity(
            send_webhook_batch_activity,
            input,
            start_to_close_timeout=timedelta(seconds=120),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=10),
                backoff_coefficient=2.0,
            ),
        )
