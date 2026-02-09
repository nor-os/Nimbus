"""
Overview: Workflow execution service — start, cancel, get, list, retry executions.
Architecture: Service layer for workflow execution management (Section 5)
Dependencies: sqlalchemy, temporalio, app.models.workflow_*, app.services.workflow.compiler
Concepts: Workflow execution lifecycle, Temporal integration, concurrent limit enforcement
"""

from __future__ import annotations

import json
import logging
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.workflow_definition import WorkflowDefinition, WorkflowDefinitionStatus
from app.models.workflow_execution import (
    WorkflowExecution,
    WorkflowExecutionStatus,
    WorkflowNodeExecution,
)
from app.services.workflow.compiler import WorkflowCompiler

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    def __init__(self, message: str, code: str = "EXECUTION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class WorkflowExecutionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._compiler = WorkflowCompiler()

    async def start(
        self,
        tenant_id: str,
        started_by: str,
        definition_id: str,
        input_data: dict[str, Any] | None = None,
        is_test: bool = False,
        mock_configs: dict[str, dict] | None = None,
    ) -> WorkflowExecution:
        """Start a workflow execution: validate, compile, create record, start Temporal."""
        # Get the active definition
        result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == definition_id,
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.deleted_at.is_(None),
            )
        )
        definition = result.scalar_one_or_none()
        if not definition:
            raise WorkflowExecutionError(
                f"Definition '{definition_id}' not found", "NOT_FOUND"
            )

        if definition.status != WorkflowDefinitionStatus.ACTIVE and not is_test:
            raise WorkflowExecutionError(
                "Only active definitions can be executed", "NOT_ACTIVE"
            )

        # Check concurrent execution limit
        if not is_test:
            running_count = await self._count_running(tenant_id, definition_id)
            if running_count >= definition.max_concurrent:
                raise WorkflowExecutionError(
                    f"Concurrent execution limit reached ({definition.max_concurrent})",
                    "CONCURRENT_LIMIT",
                )

        # Compile the graph
        if not definition.graph:
            raise WorkflowExecutionError("Definition has no graph", "NO_GRAPH")

        plan = self._compiler.compile(
            definition_id=str(definition.id),
            version=definition.version,
            graph=definition.graph,
            timeout_seconds=definition.timeout_seconds,
        )

        # Create execution record
        temporal_workflow_id = f"wf-{uuid.uuid4()}"
        execution = WorkflowExecution(
            tenant_id=tenant_id,
            definition_id=definition.id,
            definition_version=definition.version,
            temporal_workflow_id=temporal_workflow_id,
            status=WorkflowExecutionStatus.PENDING,
            input=input_data or {},
            started_by=started_by,
            is_test=is_test,
        )
        self.db.add(execution)
        await self.db.flush()

        # Start Temporal workflow
        try:
            from app.core.temporal import get_temporal_client
            from app.workflows.dynamic_workflow import DynamicWorkflowExecutor, DynamicWorkflowInput

            client = await get_temporal_client()
            await client.start_workflow(
                DynamicWorkflowExecutor.run,
                DynamicWorkflowInput(
                    execution_id=str(execution.id),
                    tenant_id=tenant_id,
                    plan_json=plan.to_json(),
                    workflow_input=input_data or {},
                    is_test=is_test,
                    mock_configs=mock_configs or {},
                ),
                id=temporal_workflow_id,
                task_queue="nimbus-workflows",
            )
        except Exception as e:
            execution.status = WorkflowExecutionStatus.FAILED
            execution.error = f"Failed to start Temporal workflow: {e}"
            await self.db.flush()
            logger.exception("Failed to start Temporal workflow for execution %s", execution.id)

        return execution

    async def cancel(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecution:
        """Cancel a running workflow execution."""
        execution = await self._get_or_raise(tenant_id, execution_id)

        if execution.status not in (
            WorkflowExecutionStatus.PENDING,
            WorkflowExecutionStatus.RUNNING,
        ):
            raise WorkflowExecutionError(
                "Can only cancel pending or running executions", "INVALID_STATUS"
            )

        # Signal Temporal to cancel
        if execution.temporal_workflow_id:
            try:
                from app.core.temporal import get_temporal_client
                from app.workflows.dynamic_workflow import DynamicWorkflowExecutor

                client = await get_temporal_client()
                handle = client.get_workflow_handle(execution.temporal_workflow_id)
                await handle.signal(DynamicWorkflowExecutor.cancel)
            except Exception:
                logger.warning(
                    "Failed to signal cancel for workflow %s",
                    execution.temporal_workflow_id,
                    exc_info=True,
                )

        execution.status = WorkflowExecutionStatus.CANCELLED
        await self.db.flush()
        return execution

    async def get(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecution | None:
        """Get an execution by ID with node executions."""
        result = await self.db.execute(
            select(WorkflowExecution)
            .options(selectinload(WorkflowExecution.node_executions))
            .where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        definition_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[WorkflowExecution]:
        """List executions for a tenant."""
        query = (
            select(WorkflowExecution)
            .where(WorkflowExecution.tenant_id == tenant_id)
            .order_by(WorkflowExecution.started_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if definition_id:
            query = query.where(WorkflowExecution.definition_id == definition_id)
        if status:
            query = query.where(
                WorkflowExecution.status == WorkflowExecutionStatus(status)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def retry(
        self, tenant_id: str, execution_id: str, started_by: str
    ) -> WorkflowExecution:
        """Retry a failed execution by creating a new one with the same parameters."""
        original = await self._get_or_raise(tenant_id, execution_id)

        if original.status != WorkflowExecutionStatus.FAILED:
            raise WorkflowExecutionError(
                "Can only retry failed executions", "INVALID_STATUS"
            )

        return await self.start(
            tenant_id=tenant_id,
            started_by=started_by,
            definition_id=str(original.definition_id),
            input_data=original.input,
            is_test=original.is_test,
        )

    async def get_node_executions(
        self, tenant_id: str, execution_id: str
    ) -> list[WorkflowNodeExecution]:
        """Get node executions for a workflow execution."""
        execution = await self._get_or_raise(tenant_id, execution_id)
        result = await self.db.execute(
            select(WorkflowNodeExecution)
            .where(WorkflowNodeExecution.execution_id == execution.id)
            .order_by(WorkflowNodeExecution.started_at)
        )
        return list(result.scalars().all())

    async def _count_running(
        self, tenant_id: str, definition_id: str
    ) -> int:
        """Count running executions for a definition."""
        result = await self.db.execute(
            select(func.count(WorkflowExecution.id)).where(
                WorkflowExecution.tenant_id == tenant_id,
                WorkflowExecution.definition_id == definition_id,
                WorkflowExecution.status.in_([
                    WorkflowExecutionStatus.PENDING,
                    WorkflowExecutionStatus.RUNNING,
                ]),
            )
        )
        return result.scalar() or 0

    async def _get_or_raise(
        self, tenant_id: str, execution_id: str
    ) -> WorkflowExecution:
        execution = await self.get(tenant_id, execution_id)
        if not execution:
            raise WorkflowExecutionError(
                f"Execution '{execution_id}' not found", "NOT_FOUND"
            )
        return execution
