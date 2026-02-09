"""
Overview: Parallel fan-out and Merge fan-in node executors.
Architecture: Flow control node types for concurrent execution (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Parallel execution, fan-out, fan-in, AND/OR merge modes
"""

from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput


class ParallelNodeExecutor(BaseNodeExecutor):
    """Marker node — fans out to multiple parallel branches.
    DynamicWorkflowExecutor handles actual parallel execution."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        branches: list[str] = context.config.get("branches", ["branch_0", "branch_1"])
        return NodeOutput(
            data={"branches": branches, "input": context.input_data},
            next_ports=branches,
        )


class MergeNodeExecutor(BaseNodeExecutor):
    """Collects results from parallel branches.
    Mode: AND (wait for all) or OR (first to complete)."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        mode = context.config.get("mode", "AND")
        # The DynamicWorkflowExecutor collects branch results into input_data
        return NodeOutput(
            data={
                "mode": mode,
                "merged_results": context.input_data,
            },
            next_port="out",
        )


def register() -> None:
    registry = get_registry()

    registry.register(NodeTypeDefinition(
        type_id="parallel",
        label="Parallel",
        category=NodeCategory.FLOW_CONTROL,
        description="Fans out to multiple parallel branches.",
        icon="&#9544;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("branch_0", PortDirection.OUTPUT, PortType.FLOW, "Branch 1"),
            PortDef("branch_1", PortDirection.OUTPUT, PortType.FLOW, "Branch 2"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "branches": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of output port names",
                },
            },
        },
        executor_class=ParallelNodeExecutor,
        is_marker=True,
    ))

    registry.register(NodeTypeDefinition(
        type_id="merge",
        label="Merge",
        category=NodeCategory.FLOW_CONTROL,
        description="Collects results from parallel branches.",
        icon="&#9547;",
        ports=[
            PortDef("branch_0", PortDirection.INPUT, PortType.FLOW, "Branch 1"),
            PortDef("branch_1", PortDirection.INPUT, PortType.FLOW, "Branch 2"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["AND", "OR"],
                    "default": "AND",
                    "description": "AND waits for all branches, OR proceeds on first",
                },
            },
        },
        executor_class=MergeNodeExecutor,
        is_marker=True,
    ))
