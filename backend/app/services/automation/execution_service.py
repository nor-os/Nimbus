"""
Overview: Activity execution service — orchestrates activity runs, sandbox dispatch, and config mutations.
Architecture: Execution orchestration for automated activities (Section 11.5)
Dependencies: sqlalchemy, app.services.automation.activity_service, sandbox_executor, mutation_engine
Concepts: Execution lifecycle, sandbox dispatch, output validation, config mutation application
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.automated_activity import (
    ActivityExecution,
    ActivityExecutionStatus,
    AutomatedActivityVersion,
    ImplementationType,
)

logger = logging.getLogger(__name__)


class ExecutionServiceError(Exception):
    def __init__(self, message: str, code: str = "EXECUTION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ExecutionService:
    """Orchestrates automated activity executions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def start_execution(
        self,
        tenant_id: str,
        activity_id: str,
        version_id: str | None,
        started_by: str,
        input_data: dict[str, Any] | None = None,
        ci_id: str | None = None,
        deployment_id: str | None = None,
        workflow_execution_id: str | None = None,
    ) -> ActivityExecution:
        """Start an activity execution.

        1. Resolve version (latest published if not specified)
        2. Validate input against schema
        3. Create execution record
        4. Dispatch to appropriate executor
        5. On success: apply config mutations if deployment_id provided
        """
        from app.services.automation.activity_service import ActivityService

        svc = ActivityService(self.db)
        activity = await svc.get(tenant_id, activity_id)
        if not activity:
            raise ExecutionServiceError("Activity not found", "NOT_FOUND")

        # Resolve version
        if version_id:
            version = await svc.get_version(activity_id, version_id)
        else:
            version = await svc.get_latest_published(activity_id)

        if not version:
            raise ExecutionServiceError("No published version available", "NO_VERSION")

        if not version.published_at:
            raise ExecutionServiceError("Version is not published", "NOT_PUBLISHED")

        # Validate input against schema
        if version.input_schema and input_data:
            errors = self._validate_against_schema(input_data, version.input_schema)
            if errors:
                raise ExecutionServiceError(
                    f"Input validation failed: {'; '.join(errors)}", "INVALID_INPUT"
                )

        # Create execution record
        execution = ActivityExecution(
            tenant_id=tenant_id,
            activity_version_id=version.id,
            workflow_execution_id=workflow_execution_id,
            ci_id=ci_id,
            deployment_id=deployment_id,
            input_snapshot=input_data,
            status=ActivityExecutionStatus.RUNNING,
            started_at=datetime.now(UTC),
        )
        self.db.add(execution)
        await self.db.flush()

        # Dispatch based on implementation type
        try:
            result = await self._dispatch(activity, version, input_data or {})

            if result.get("success", False):
                execution.status = ActivityExecutionStatus.SUCCEEDED
                execution.output_snapshot = result.get("output", {})
                execution.completed_at = datetime.now(UTC)

                # Apply config mutations if deployment provided
                if deployment_id and version.config_mutations:
                    from app.services.automation.mutation_engine import MutationEngine

                    engine = MutationEngine(self.db)
                    await engine.apply_mutations(
                        deployment_id=deployment_id,
                        tenant_id=tenant_id,
                        execution_id=str(execution.id),
                        mutations=version.config_mutations,
                        activity_output=execution.output_snapshot,
                        applied_by=started_by,
                    )
            else:
                execution.status = ActivityExecutionStatus.FAILED
                execution.error = result.get("error", "Unknown error")
                execution.completed_at = datetime.now(UTC)

        except Exception as e:
            execution.status = ActivityExecutionStatus.FAILED
            execution.error = str(e)
            execution.completed_at = datetime.now(UTC)
            logger.exception("Activity execution failed: %s", execution.id)

        await self.db.flush()

        # Emit event
        from app.services.events.event_bus import emit_event_async

        if execution.status == ActivityExecutionStatus.SUCCEEDED:
            emit_event_async("activity.execution.completed", {
                "execution_id": str(execution.id), "activity_id": activity_id,
                "output": execution.output_snapshot,
            }, tenant_id, "execution_service", started_by)
        elif execution.status == ActivityExecutionStatus.FAILED:
            emit_event_async("activity.execution.failed", {
                "execution_id": str(execution.id), "activity_id": activity_id,
                "error": execution.error,
            }, tenant_id, "execution_service", started_by)

        return execution

    async def cancel_execution(
        self, tenant_id: str, execution_id: str
    ) -> ActivityExecution:
        """Cancel a running execution."""
        execution = await self._get_or_raise(tenant_id, execution_id)
        if execution.status != ActivityExecutionStatus.RUNNING:
            raise ExecutionServiceError(
                f"Cannot cancel execution in status {execution.status.value}",
                "INVALID_STATUS",
            )
        execution.status = ActivityExecutionStatus.CANCELLED
        execution.completed_at = datetime.now(UTC)
        await self.db.flush()
        return execution

    async def rollback_execution(
        self, tenant_id: str, execution_id: str, rolled_back_by: str
    ) -> ActivityExecution:
        """Rollback config mutations from a successful execution."""
        execution = await self._get_or_raise(tenant_id, execution_id)
        if execution.status != ActivityExecutionStatus.SUCCEEDED:
            raise ExecutionServiceError(
                "Can only rollback succeeded executions", "INVALID_STATUS"
            )
        if not execution.deployment_id:
            raise ExecutionServiceError(
                "No deployment associated with execution", "NO_DEPLOYMENT"
            )

        # Get the version for rollback rules
        version = await self.db.execute(
            select(AutomatedActivityVersion).where(
                AutomatedActivityVersion.id == execution.activity_version_id
            )
        )
        ver = version.scalar_one_or_none()

        from app.services.automation.mutation_engine import MutationEngine

        engine = MutationEngine(self.db)

        # Get original changes
        from app.models.automated_activity import ConfigurationChange

        changes_result = await self.db.execute(
            select(ConfigurationChange).where(
                ConfigurationChange.activity_execution_id == str(execution.id),
                ConfigurationChange.rollback_of.is_(None),
            )
        )
        original_changes = list(changes_result.scalars().all())

        await engine.rollback_mutations(
            deployment_id=str(execution.deployment_id),
            tenant_id=tenant_id,
            execution_id=str(execution.id),
            rollback_mutations=ver.rollback_mutations if ver else [],
            original_changes=original_changes,
            applied_by=rolled_back_by,
        )

        await self.db.flush()
        return execution

    async def get(
        self, tenant_id: str, execution_id: str
    ) -> ActivityExecution | None:
        """Get an execution by ID."""
        result = await self.db.execute(
            select(ActivityExecution)
            .options(selectinload(ActivityExecution.config_changes))
            .where(
                ActivityExecution.id == execution_id,
                ActivityExecution.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        activity_id: str | None = None,
        status: str | None = None,
        deployment_id: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ActivityExecution]:
        """List executions with filters."""
        query = select(ActivityExecution).where(
            ActivityExecution.tenant_id == tenant_id
        )

        if activity_id:
            # Filter by activity (via version)
            query = query.join(AutomatedActivityVersion).where(
                AutomatedActivityVersion.activity_id == activity_id
            )
        if status:
            query = query.where(ActivityExecution.status == status)
        if deployment_id:
            query = query.where(ActivityExecution.deployment_id == deployment_id)

        query = query.order_by(ActivityExecution.created_at.desc()).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    # ── Internal ───────────────────────────────────────

    async def _dispatch(
        self, activity, version: AutomatedActivityVersion, input_data: dict
    ) -> dict[str, Any]:
        """Dispatch execution to the appropriate executor."""
        impl_type = activity.implementation_type

        if impl_type == ImplementationType.PYTHON_SCRIPT:
            from app.services.automation.sandbox_executor import ContainerSandboxExecutor

            executor = ContainerSandboxExecutor()
            result = await executor.execute(
                source_code=version.source_code or "",
                input_data=input_data,
                runtime_config=version.runtime_config,
                timeout_seconds=activity.timeout_seconds,
            )
            return {
                "success": result.success,
                "output": result.output or {},
                "error": result.error,
            }

        if impl_type == ImplementationType.SHELL_SCRIPT:
            from app.services.automation.sandbox_executor import ContainerSandboxExecutor

            executor = ContainerSandboxExecutor()
            # Wrap shell script in Python subprocess call
            wrapper = f'''
import subprocess, json, sys
input_data = json.loads(sys.stdin.readline())
env = {{k: str(v) for k, v in input_data.items() if isinstance(v, (str, int, float, bool))}}
result = subprocess.run(
    ["sh", "-c", """{version.source_code or ''}"""],
    capture_output=True, text=True, env={{**__import__('os').environ, **env}},
    timeout={activity.timeout_seconds}
)
if result.returncode != 0:
    print(json.dumps({{"error": result.stderr}}), file=sys.stderr)
    sys.exit(1)
output = {{"stdout": result.stdout.strip(), "returncode": result.returncode}}
print(json.dumps(output))
'''
            result = await executor.execute(
                source_code=wrapper,
                input_data=input_data,
                runtime_config=version.runtime_config,
                timeout_seconds=activity.timeout_seconds,
            )
            return {
                "success": result.success,
                "output": result.output or {},
                "error": result.error,
            }

        if impl_type == ImplementationType.HTTP_WEBHOOK:
            from app.services.automation.sandbox_executor import WebhookExecutor

            executor = WebhookExecutor()
            webhook_url = (version.runtime_config or {}).get("webhook_url", "")
            if not webhook_url:
                return {"success": False, "error": "No webhook_url in runtime_config"}
            headers = (version.runtime_config or {}).get("headers", {})
            result = await executor.execute(
                webhook_url=webhook_url,
                input_data=input_data,
                timeout_seconds=activity.timeout_seconds,
                headers=headers,
            )
            return {
                "success": result.success,
                "output": result.output or {},
                "error": result.error,
            }

        if impl_type == ImplementationType.MANUAL:
            # Manual activities just succeed immediately (human confirmation handled externally)
            return {"success": True, "output": {"manual": True}}

        if impl_type == ImplementationType.PULUMI_OPERATION:
            # Deferred to Phase 12
            return {"success": False, "error": "Pulumi operations not yet implemented"}

        return {"success": False, "error": f"Unknown implementation type: {impl_type}"}

    def _validate_against_schema(
        self, data: dict[str, Any], schema: dict[str, Any]
    ) -> list[str]:
        """Basic JSON Schema validation. Returns error messages."""
        errors: list[str] = []
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        for key, value in data.items():
            if key in properties:
                prop = properties[key]
                expected_type = prop.get("type")
                if expected_type and not self._check_type(value, expected_type):
                    errors.append(f"Field '{key}' should be type '{expected_type}'")

        return errors

    def _check_type(self, value: Any, expected: str) -> bool:
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        expected_type = type_map.get(expected)
        if expected_type is None:
            return True
        return isinstance(value, expected_type)

    async def _get_or_raise(
        self, tenant_id: str, execution_id: str
    ) -> ActivityExecution:
        execution = await self.get(tenant_id, execution_id)
        if not execution:
            raise ExecutionServiceError("Execution not found", "NOT_FOUND")
        return execution
