"""
Overview: Temporal workflow for durable email delivery.
Architecture: Notification email workflow (Section 9)
Dependencies: temporalio, app.workflows.activities.notification
Concepts: Durable email delivery, retry policy, SMTP
"""

from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from app.workflows.activities.notification import (
        SendEmailInput,
        SendEmailResult,
        send_email_activity,
    )


@workflow.defn
class SendEmailWorkflow:
    @workflow.run
    async def run(self, input: SendEmailInput) -> SendEmailResult:
        """Execute email delivery with retry."""
        return await workflow.execute_activity(
            send_email_activity,
            input,
            start_to_close_timeout=timedelta(seconds=60),
            retry_policy=RetryPolicy(
                maximum_attempts=3,
                initial_interval=timedelta(seconds=5),
                backoff_coefficient=2.0,
            ),
        )
