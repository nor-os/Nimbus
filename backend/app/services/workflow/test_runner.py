"""
Overview: Workflow test runner — thin wrapper for starting test executions with mocks/breakpoints.
Architecture: Test execution layer for the workflow editor (Section 5)
Dependencies: app.services.workflow.execution_service
Concepts: Test mode, mock configurations, breakpoints, dry-run execution
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_execution import WorkflowExecution
from app.services.workflow.execution_service import WorkflowExecutionService


class WorkflowTestRunner:
    """Starts workflow executions in test mode with mock configs and breakpoints."""

    def __init__(self, db: AsyncSession):
        self._execution_service = WorkflowExecutionService(db)

    async def start_test(
        self,
        tenant_id: str,
        started_by: str,
        definition_id: str,
        input_data: dict[str, Any] | None = None,
        mock_configs: dict[str, dict] | None = None,
    ) -> WorkflowExecution:
        """Start a test execution with optional mock configurations.

        mock_configs format per node_id:
            {
                "skip": true,              # Skip this node entirely
                "output": {...},           # Fixed output data
                "delay": 0,               # Simulate delay (seconds)
                "fail": false,            # Simulate failure
                "decision": "approve",     # For approval gates
                "response": {...},         # For HTTP request nodes
            }
        """
        return await self._execution_service.start(
            tenant_id=tenant_id,
            started_by=started_by,
            definition_id=definition_id,
            input_data=input_data,
            is_test=True,
            mock_configs=mock_configs,
        )
