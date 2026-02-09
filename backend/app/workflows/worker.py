"""
Overview: Temporal worker entrypoint — polls the nimbus-workflows task queue.
Architecture: Worker process for executing workflows and activities (Section 9)
Dependencies: temporalio, app.core.config, app.core.temporal
Concepts: Temporal worker, task queue polling, schedule registration

Usage: uv run python -m app.workflows.worker
"""

import asyncio
import logging
import signal

from temporalio.client import (
    Client,
    Schedule,
    ScheduleActionStartWorkflow,
    ScheduleAlreadyRunningError,
    ScheduleSpec,
)
from temporalio.worker import Worker

from app.core.config import get_settings
from app.core.temporal import get_temporal_client
from app.workflows.activities.approval import (
    create_approval_request_activity,
    expire_approval_steps,
    record_approval_audit,
    resolve_approval_request,
    send_approval_notification,
)
from app.workflows.activities.audit import (
    archive_tenant_audit_logs,
    execute_audit_export,
    find_tenants_for_archival,
)
from app.workflows.activities.example import say_hello
from app.workflows.activities.impersonation import (
    activate_impersonation_session,
    end_impersonation_session,
    expire_impersonation_session,
    notify_approver,
    record_impersonation_audit,
    reject_impersonation_session,
)
from app.workflows.activities.notification import (
    send_email_activity,
    send_webhook_batch_activity,
)
from app.workflows.activities.tenant_export import execute_tenant_export
from app.workflows.activities.tenant_purge import (
    find_purgeable_tenants,
    purge_single_tenant,
)
from app.workflows.approval import ApprovalChainWorkflow
from app.workflows.audit_archive import AuditArchiveWorkflow
from app.workflows.audit_export import AuditExportWorkflow
from app.workflows.example import ExampleWorkflow
from app.workflows.impersonation import ImpersonationWorkflow
from app.workflows.schedules import SCHEDULES
from app.workflows.send_email import SendEmailWorkflow
from app.workflows.send_webhook_batch import SendWebhookBatchWorkflow
from app.workflows.tenant_export import TenantExportWorkflow
from app.workflows.tenant_purge import TenantPurgeWorkflow

logger = logging.getLogger(__name__)


async def register_schedules(client: Client, task_queue: str) -> None:
    """Register all declared schedules, skipping those that already exist."""
    for defn in SCHEDULES:
        try:
            await client.create_schedule(
                defn.schedule_id,
                Schedule(
                    action=ScheduleActionStartWorkflow(
                        defn.workflow_name,
                        id=f"{defn.schedule_id}-run",
                        task_queue=task_queue,
                    ),
                    spec=ScheduleSpec(cron_expressions=[defn.cron]),
                ),
            )
            logger.info("Created schedule '%s': %s", defn.schedule_id, defn.description)
        except ScheduleAlreadyRunningError:
            logger.info("Schedule '%s' already exists, skipping", defn.schedule_id)
        except Exception:
            logger.warning(
                "Failed to create schedule '%s'", defn.schedule_id, exc_info=True
            )


async def run_worker() -> None:
    """Start the Temporal worker and run until interrupted."""
    settings = get_settings()
    client = await get_temporal_client()

    # Register recurring schedules before starting the worker
    await register_schedules(client, settings.temporal_task_queue)

    worker = Worker(
        client,
        task_queue=settings.temporal_task_queue,
        workflows=[
            ApprovalChainWorkflow,
            ExampleWorkflow,
            TenantPurgeWorkflow,
            TenantExportWorkflow,
            AuditArchiveWorkflow,
            AuditExportWorkflow,
            ImpersonationWorkflow,
            SendEmailWorkflow,
            SendWebhookBatchWorkflow,
        ],
        activities=[
            create_approval_request_activity,
            expire_approval_steps,
            record_approval_audit,
            resolve_approval_request,
            send_approval_notification,
            say_hello,
            find_purgeable_tenants,
            purge_single_tenant,
            execute_tenant_export,
            archive_tenant_audit_logs,
            find_tenants_for_archival,
            execute_audit_export,
            activate_impersonation_session,
            end_impersonation_session,
            expire_impersonation_session,
            notify_approver,
            record_impersonation_audit,
            reject_impersonation_session,
            send_email_activity,
            send_webhook_batch_activity,
        ],
    )

    shutdown_event = asyncio.Event()

    def _signal_handler():
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _signal_handler)

    logger.info("Temporal worker started, polling queue: %s", settings.temporal_task_queue)

    async with worker:
        await shutdown_event.wait()

    logger.info("Temporal worker shut down gracefully")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_worker())
