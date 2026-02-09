"""
Overview: Temporal activities for workflow node execution — dispatches to registered executors.
Architecture: Activity layer for dynamic workflow execution (Section 9)
Dependencies: temporalio, app.services.workflow.node_registry, app.services.workflow.node_types.base
Concepts: Node execution dispatch, status tracking, activity functions
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from temporalio import activity

logger = logging.getLogger(__name__)


@dataclass
class ExecuteNodeInput:
    execution_id: str
    tenant_id: str
    node_id: str
    node_type: str
    config: str  # JSON
    variables: str  # JSON
    node_outputs: str  # JSON
    workflow_input: str  # JSON
    is_test: bool = False
    mock_config: str | None = None  # JSON or None


@dataclass
class UpdateNodeStatusInput:
    execution_id: str
    node_id: str
    node_type: str
    status: str
    output: str | None = None  # JSON
    error: str | None = None


@dataclass
class UpdateExecutionStatusInput:
    execution_id: str
    status: str
    output: str | None = None  # JSON
    error: str | None = None


@dataclass
class CreateWorkflowApprovalInput:
    tenant_id: str
    execution_id: str
    node_id: str
    title: str
    description: str = ""
    approver_role_names: list[str] = field(default_factory=list)
    approver_user_ids: list[str] = field(default_factory=list)
    chain_mode: str = "SEQUENTIAL"
    timeout_minutes: int = 1440


@dataclass
class CompileSubworkflowInput:
    tenant_id: str
    definition_id: str
    parent_execution_id: str
    workflow_input: str = "{}"  # JSON


@activity.defn
async def execute_node(input: ExecuteNodeInput) -> str:
    """Execute a single workflow node via its registered executor."""
    from app.services.workflow.expression_engine import ExpressionContext
    from app.services.workflow.node_registry import get_registry
    from app.services.workflow.node_types.base import NodeExecutionContext, NodeOutput

    # Ensure node types are registered
    import app.services.workflow.node_types  # noqa: F401

    registry = get_registry()
    definition = registry.get(input.node_type)

    if not definition:
        return json.dumps({"error": f"Unknown node type: {input.node_type}", "data": {}})

    if not definition.executor_class:
        return json.dumps({"error": f"No executor for node type: {input.node_type}", "data": {}})

    config = json.loads(input.config)
    variables = json.loads(input.variables)
    node_outputs = json.loads(input.node_outputs)
    workflow_input = json.loads(input.workflow_input)
    mock_config = json.loads(input.mock_config) if input.mock_config else None

    # Build input data from upstream node outputs
    input_data: dict[str, Any] = {}
    for _node_id, node_out in node_outputs.items():
        if isinstance(node_out, dict) and "output" in node_out:
            input_data.update(node_out["output"])

    context = NodeExecutionContext(
        node_id=input.node_id,
        node_type=input.node_type,
        config=config,
        input_data=input_data,
        variables=variables,
        node_outputs=node_outputs,
        workflow_input=workflow_input,
        tenant_id=input.tenant_id,
        execution_id=input.execution_id,
        is_test=input.is_test,
        mock_config=mock_config,
    )

    executor = definition.executor_class()

    try:
        result: NodeOutput = await executor.execute(context)
        return json.dumps({
            "data": result.data,
            "next_port": result.next_port,
            "next_ports": result.next_ports,
            "error": result.error,
        })
    except Exception as e:
        logger.exception("Node execution failed: %s/%s", input.node_type, input.node_id)
        return json.dumps({"error": str(e), "data": {}})


@activity.defn
async def update_node_status(input: UpdateNodeStatusInput) -> None:
    """Update the status of a workflow node execution record."""
    import uuid as _uuid

    try:
        _uuid.UUID(input.execution_id)
    except (ValueError, AttributeError):
        activity.logger.warning(
            "Skipping node status update — invalid execution_id: %s", input.execution_id
        )
        return

    from app.db.session import async_session_factory
    from app.models.workflow_execution import WorkflowNodeExecution, WorkflowNodeExecutionStatus

    from sqlalchemy import select, update

    async with async_session_factory() as db:
        # Check if node execution record exists
        result = await db.execute(
            select(WorkflowNodeExecution).where(
                WorkflowNodeExecution.execution_id == input.execution_id,
                WorkflowNodeExecution.node_id == input.node_id,
            )
        )
        existing = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if existing:
            values: dict[str, Any] = {
                "status": WorkflowNodeExecutionStatus(input.status),
            }
            if input.status == "RUNNING":
                values["started_at"] = now
            if input.status in ("COMPLETED", "FAILED", "SKIPPED", "CANCELLED"):
                values["completed_at"] = now
            if input.output:
                values["output"] = json.loads(input.output)
            if input.error:
                values["error"] = input.error

            await db.execute(
                update(WorkflowNodeExecution)
                .where(WorkflowNodeExecution.id == existing.id)
                .values(**values)
            )
        else:
            node_exec = WorkflowNodeExecution(
                execution_id=input.execution_id,
                node_id=input.node_id,
                node_type=input.node_type,
                status=WorkflowNodeExecutionStatus(input.status),
                started_at=now if input.status == "RUNNING" else None,
                completed_at=now if input.status in ("COMPLETED", "FAILED", "SKIPPED") else None,
                output=json.loads(input.output) if input.output else None,
                error=input.error,
            )
            db.add(node_exec)

        await db.commit()


@activity.defn
async def update_execution_status(input: UpdateExecutionStatusInput) -> None:
    """Update the status of a workflow execution record."""
    import uuid as _uuid

    # Guard against stale workflows with invalid execution IDs
    try:
        _uuid.UUID(input.execution_id)
    except (ValueError, AttributeError):
        activity.logger.warning(
            "Skipping status update — invalid execution_id: %s", input.execution_id
        )
        return

    from app.db.session import async_session_factory
    from app.models.workflow_execution import WorkflowExecution, WorkflowExecutionStatus

    from sqlalchemy import update

    async with async_session_factory() as db:
        values: dict[str, Any] = {
            "status": WorkflowExecutionStatus(input.status),
        }
        if input.status in ("COMPLETED", "FAILED", "CANCELLED"):
            values["completed_at"] = datetime.now(UTC)
        if input.output:
            values["output"] = json.loads(input.output)
        if input.error:
            values["error"] = input.error

        await db.execute(
            update(WorkflowExecution)
            .where(WorkflowExecution.id == input.execution_id)
            .values(**values)
        )
        await db.commit()


@activity.defn
async def create_workflow_approval(input: CreateWorkflowApprovalInput) -> str:
    """Create an approval request for a workflow approval_gate node.
    Resolves role names to user IDs, creates the request via ApprovalService."""
    from app.db.session import async_session_factory
    from app.models.role import Role
    from app.models.user_role import UserRole
    from app.services.approval.service import ApprovalService

    from sqlalchemy import select

    async with async_session_factory() as db:
        all_approver_ids = list(input.approver_user_ids)

        # Resolve role names to user IDs
        if input.approver_role_names:
            stmt = (
                select(UserRole.user_id)
                .join(Role, UserRole.role_id == Role.id)
                .where(
                    Role.name.in_(input.approver_role_names),
                    Role.tenant_id == input.tenant_id,
                )
            )
            result = await db.execute(stmt)
            role_user_ids = [str(row[0]) for row in result.all()]
            all_approver_ids.extend(role_user_ids)

        # Deduplicate
        all_approver_ids = list(dict.fromkeys(all_approver_ids))

        if not all_approver_ids:
            return json.dumps({
                "error": "No approvers resolved from user IDs or role names",
            })

        service = ApprovalService(db)
        request = await service.create_request(
            tenant_id=input.tenant_id,
            requester_id="system",
            operation_type="workflow.approval_gate",
            title=input.title,
            description=input.description,
            context={
                "workflow_execution_id": input.execution_id,
                "node_id": input.node_id,
            },
        )

        # Get policy for timeout info
        policy = await service.get_policy(input.tenant_id, "workflow.approval_gate")
        timeout_minutes = input.timeout_minutes
        if policy and policy.timeout_minutes:
            timeout_minutes = policy.timeout_minutes

        approver_ids = [str(s.approver_id) for s in request.steps] if request.steps else all_approver_ids

        await db.commit()

        return json.dumps({
            "request_id": str(request.id),
            "approver_ids": approver_ids,
            "chain_mode": input.chain_mode,
            "quorum_required": 1,
            "timeout_minutes": timeout_minutes,
        })


@activity.defn
async def compile_subworkflow(input: CompileSubworkflowInput) -> str:
    """Load a workflow definition by ID, compile it to an execution plan, and create an execution record."""
    import uuid as _uuid

    from app.db.session import async_session_factory
    from app.models.workflow_definition import WorkflowDefinition, WorkflowDefinitionStatus
    from app.models.workflow_execution import WorkflowExecution, WorkflowExecutionStatus
    from app.services.workflow.compiler import WorkflowCompiler

    from sqlalchemy import select

    workflow_input = json.loads(input.workflow_input) if input.workflow_input else {}

    async with async_session_factory() as db:
        # Load the target definition
        stmt = select(WorkflowDefinition).where(
            WorkflowDefinition.id == input.definition_id,
            WorkflowDefinition.tenant_id == input.tenant_id,
            WorkflowDefinition.status == WorkflowDefinitionStatus.PUBLISHED,
        )
        result = await db.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            return json.dumps({
                "error": f"Workflow definition {input.definition_id} not found or not published",
            })

        # Compile the graph
        try:
            compiler = WorkflowCompiler()
            plan = compiler.compile(
                definition_id=str(definition.id),
                version=definition.version,
                graph=definition.graph,
                timeout_seconds=definition.timeout_seconds or 3600,
            )
        except Exception as e:
            return json.dumps({"error": f"Compilation failed: {e}"})

        # Create child execution record
        temporal_workflow_id = f"subwf-{input.parent_execution_id}-{_uuid.uuid4().hex[:8]}"
        execution = WorkflowExecution(
            tenant_id=input.tenant_id,
            definition_id=definition.id,
            definition_version=definition.version,
            temporal_workflow_id=temporal_workflow_id,
            status=WorkflowExecutionStatus.PENDING,
            input=workflow_input,
            started_by="system",
            is_test=False,
        )
        db.add(execution)
        await db.flush()

        execution_id = str(execution.id)
        plan_json = plan.to_json()

        await db.commit()

        return json.dumps({
            "execution_id": execution_id,
            "plan_json": plan_json,
        })
