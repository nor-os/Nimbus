"""
Overview: Dynamic workflow executor — Temporal workflow that executes compiled workflow plans.
Architecture: Generic workflow executor using interpreter pattern (Section 9)
Dependencies: temporalio, app.services.workflow.execution_plan
Concepts: Interpreter pattern, dynamic execution, signals, queries, step traversal
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from app.services.workflow.execution_plan import ExecutionPlan
    from app.workflows.activities.workflow_nodes import (
        CompileSubworkflowInput,
        CreateWorkflowApprovalInput,
        ExecuteNodeInput,
        UpdateExecutionStatusInput,
        UpdateNodeStatusInput,
        compile_subworkflow,
        create_workflow_approval,
        execute_node,
        update_execution_status,
        update_node_status,
    )
    from app.workflows.approval import ApprovalChainInput, ApprovalChainWorkflow


@dataclass
class DynamicWorkflowInput:
    execution_id: str
    tenant_id: str
    plan_json: str
    workflow_input: dict[str, Any] = field(default_factory=dict)
    is_test: bool = False
    mock_configs: dict[str, dict] = field(default_factory=dict)


@dataclass
class DynamicWorkflowResult:
    success: bool
    output: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@workflow.defn
class DynamicWorkflowExecutor:
    """Executes a compiled workflow plan step-by-step."""

    def __init__(self) -> None:
        self._variables: dict[str, Any] = {}
        self._node_outputs: dict[str, dict[str, Any]] = {}
        self._paused = False
        self._cancelled = False
        self._pause_at_nodes: set[str] = set()
        self._current_node: str | None = None
        self._status = "RUNNING"

    # ── Signals ──────────────────────────────────────

    @workflow.signal
    async def pause(self) -> None:
        self._paused = True

    @workflow.signal
    async def resume(self) -> None:
        self._paused = False

    @workflow.signal
    async def cancel(self) -> None:
        self._cancelled = True
        self._paused = False

    @workflow.signal
    async def inject_variable(self, name: str, value: Any) -> None:
        self._variables[name] = value

    @workflow.signal
    async def pause_at_node(self, node_id: str) -> None:
        self._pause_at_nodes.add(node_id)

    @workflow.signal
    async def continue_execution(self) -> None:
        self._paused = False
        self._pause_at_nodes.clear()

    # ── Queries ──────────────────────────────────────

    @workflow.query
    def get_status(self) -> dict:
        return {
            "status": self._status,
            "current_node": self._current_node,
            "paused": self._paused,
            "cancelled": self._cancelled,
            "variables": self._variables,
            "node_outputs": self._node_outputs,
        }

    @workflow.query
    def get_variables(self) -> dict:
        return dict(self._variables)

    # ── Main Execution ───────────────────────────────

    @workflow.run
    async def run(self, input: DynamicWorkflowInput) -> DynamicWorkflowResult:
        plan = ExecutionPlan.from_json(input.plan_json)
        self._variables = dict(plan.variables)

        # Update execution to RUNNING
        await workflow.execute_activity(
            update_execution_status,
            UpdateExecutionStatusInput(
                execution_id=input.execution_id,
                status="RUNNING",
            ),
            start_to_close_timeout=timedelta(seconds=30),
        )

        try:
            # Build dependency tracking
            completed_nodes: set[str] = set()
            step_map = {s.node_id: s for s in plan.steps}

            for step in plan.steps:
                if self._cancelled:
                    break

                # Wait for pause/breakpoints
                if step.node_id in self._pause_at_nodes:
                    self._paused = True

                if self._paused:
                    await workflow.wait_condition(
                        lambda: not self._paused or self._cancelled,
                    )

                if self._cancelled:
                    break

                self._current_node = step.node_id

                # Update node status to RUNNING
                await workflow.execute_activity(
                    update_node_status,
                    UpdateNodeStatusInput(
                        execution_id=input.execution_id,
                        node_id=step.node_id,
                        node_type=step.node_type,
                        status="RUNNING",
                    ),
                    start_to_close_timeout=timedelta(seconds=30),
                )

                # Execute the node
                mock_config = input.mock_configs.get(step.node_id)
                if mock_config and mock_config.get("skip"):
                    # Skip this node in test mode
                    node_result = {
                        "data": mock_config.get("output", {}),
                        "next_port": "out",
                    }
                    await workflow.execute_activity(
                        update_node_status,
                        UpdateNodeStatusInput(
                            execution_id=input.execution_id,
                            node_id=step.node_id,
                            node_type=step.node_type,
                            status="SKIPPED",
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                    )
                else:
                    node_result = await workflow.execute_activity(
                        execute_node,
                        ExecuteNodeInput(
                            execution_id=input.execution_id,
                            tenant_id=input.tenant_id,
                            node_id=step.node_id,
                            node_type=step.node_type,
                            config=json.dumps(step.config),
                            variables=json.dumps(self._variables),
                            node_outputs=json.dumps(self._node_outputs),
                            workflow_input=json.dumps(input.workflow_input),
                            is_test=input.is_test,
                            mock_config=json.dumps(mock_config) if mock_config else None,
                        ),
                        start_to_close_timeout=timedelta(seconds=300),
                    )

                    if isinstance(node_result, str):
                        node_result = json.loads(node_result)

                    # Check for error
                    if node_result.get("error"):
                        await workflow.execute_activity(
                            update_node_status,
                            UpdateNodeStatusInput(
                                execution_id=input.execution_id,
                                node_id=step.node_id,
                                node_type=step.node_type,
                                status="FAILED",
                                error=node_result["error"],
                            ),
                            start_to_close_timeout=timedelta(seconds=30),
                        )
                        raise RuntimeError(
                            f"Node '{step.node_id}' failed: {node_result['error']}"
                        )

                    # ── Child workflow handling ───────────────
                    node_result = await self._handle_child_workflows(
                        step, node_result, input,
                    )

                    # Update node status to COMPLETED
                    await workflow.execute_activity(
                        update_node_status,
                        UpdateNodeStatusInput(
                            execution_id=input.execution_id,
                            node_id=step.node_id,
                            node_type=step.node_type,
                            status="COMPLETED",
                            output=json.dumps(node_result.get("data", {})),
                        ),
                        start_to_close_timeout=timedelta(seconds=30),
                    )

                # Store node output
                self._node_outputs[step.node_id] = {
                    "output": node_result.get("data", {}),
                    "next_port": node_result.get("next_port"),
                }

                # Update variables if node set any
                node_data = node_result.get("data", {})
                if "set_variables" in node_data:
                    self._variables.update(node_data["set_variables"])
                if "transformed" in node_data:
                    self._variables.update(node_data["transformed"])

                completed_nodes.add(step.node_id)

            # Final status
            final_status = "CANCELLED" if self._cancelled else "COMPLETED"
            output = self._collect_output()

            await workflow.execute_activity(
                update_execution_status,
                UpdateExecutionStatusInput(
                    execution_id=input.execution_id,
                    status=final_status,
                    output=json.dumps(output),
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )

            return DynamicWorkflowResult(
                success=not self._cancelled,
                output=output,
            )

        except Exception as e:
            error_msg = str(e)
            await workflow.execute_activity(
                update_execution_status,
                UpdateExecutionStatusInput(
                    execution_id=input.execution_id,
                    status="FAILED",
                    error=error_msg,
                ),
                start_to_close_timeout=timedelta(seconds=30),
            )
            return DynamicWorkflowResult(
                success=False,
                error=error_msg,
            )

    async def _handle_child_workflows(
        self,
        step: Any,
        node_result: dict,
        input: DynamicWorkflowInput,
    ) -> dict:
        """Handle approval_gate and subworkflow nodes by starting child workflows."""

        # ── Approval Gate: start ApprovalChainWorkflow as child ──
        if step.node_type == "approval_gate" and node_result.get("next_port") == "pending":
            approval_config = node_result.get("data", {}).get("approval_config", {})

            # Create an approval request via activity
            approval_raw = await workflow.execute_activity(
                create_workflow_approval,
                CreateWorkflowApprovalInput(
                    tenant_id=input.tenant_id,
                    execution_id=input.execution_id,
                    node_id=step.node_id,
                    title=approval_config.get("title", "Workflow Approval Required"),
                    description=approval_config.get("description", ""),
                    approver_role_names=approval_config.get("approver_role_names", []),
                    approver_user_ids=approval_config.get("approver_user_ids", []),
                    chain_mode=approval_config.get("chain_mode", "SEQUENTIAL"),
                    timeout_minutes=approval_config.get("timeout_minutes", 1440),
                ),
                start_to_close_timeout=timedelta(seconds=60),
            )

            if isinstance(approval_raw, str):
                approval_raw = json.loads(approval_raw)

            # Start ApprovalChainWorkflow as a child workflow
            child_wf_id = f"approval-{input.execution_id}-{step.node_id}"
            chain_result = await workflow.execute_child_workflow(
                ApprovalChainWorkflow.run,
                ApprovalChainInput(
                    request_id=approval_raw["request_id"],
                    tenant_id=input.tenant_id,
                    requester_id="system",
                    approver_ids=approval_raw["approver_ids"],
                    chain_mode=approval_raw["chain_mode"],
                    quorum_required=approval_raw.get("quorum_required", 1),
                    timeout_minutes=approval_raw.get("timeout_minutes", 1440),
                    title=approval_config.get("title", ""),
                    description=approval_config.get("description", ""),
                ),
                id=child_wf_id,
            )

            approved = chain_result.approved
            node_result = {
                "data": {
                    "approved": approved,
                    "decision": chain_result.status,
                    "request_id": approval_raw["request_id"],
                    "steps": chain_result.steps,
                },
                "next_port": "approved" if approved else "rejected",
            }

        # ── Subworkflow: start DynamicWorkflowExecutor as child ──
        elif step.node_type == "subworkflow":
            definition_id = node_result.get("data", {}).get("definition_id", "")
            child_input = node_result.get("data", {}).get("child_input", {})

            if definition_id:
                # Compile the subworkflow via activity
                sub_raw = await workflow.execute_activity(
                    compile_subworkflow,
                    CompileSubworkflowInput(
                        tenant_id=input.tenant_id,
                        definition_id=definition_id,
                        parent_execution_id=input.execution_id,
                        workflow_input=json.dumps(child_input),
                    ),
                    start_to_close_timeout=timedelta(seconds=60),
                )

                if isinstance(sub_raw, str):
                    sub_raw = json.loads(sub_raw)

                if sub_raw.get("error"):
                    node_result = {
                        "data": {},
                        "error": sub_raw["error"],
                        "next_port": "out",
                    }
                else:
                    # Start DynamicWorkflowExecutor as a child workflow
                    child_wf_id = f"subwf-{input.execution_id}-{step.node_id}-{uuid.uuid4().hex[:8]}"
                    child_result = await workflow.execute_child_workflow(
                        DynamicWorkflowExecutor.run,
                        DynamicWorkflowInput(
                            execution_id=sub_raw["execution_id"],
                            tenant_id=input.tenant_id,
                            plan_json=sub_raw["plan_json"],
                            workflow_input=child_input,
                            is_test=input.is_test,
                        ),
                        id=child_wf_id,
                    )

                    node_result = {
                        "data": {
                            "child_execution_id": sub_raw["execution_id"],
                            "child_success": child_result.success,
                            "child_output": child_result.output,
                        },
                        "next_port": "out",
                    }

                    if not child_result.success:
                        node_result["data"]["child_error"] = child_result.error

        return node_result

    def _collect_output(self) -> dict[str, Any]:
        """Collect output from End nodes."""
        output: dict[str, Any] = {}
        for node_id, data in self._node_outputs.items():
            node_output = data.get("output", {})
            if isinstance(node_output, dict):
                output.update(node_output)
        return output
