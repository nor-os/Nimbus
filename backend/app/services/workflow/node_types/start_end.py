"""
Overview: Start and End node executors — entry and exit points of a workflow graph.
Architecture: Flow control node types (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.node_registry
Concepts: Workflow start, workflow end, input injection, output capture
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


class StartNodeExecutor(BaseNodeExecutor):
    """Injects workflow input data as the starting point."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        return NodeOutput(
            data=context.workflow_input,
            next_port="out",
        )


class EndNodeExecutor(BaseNodeExecutor):
    """Captures workflow output from incoming data."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        output_key = context.config.get("output_key", "result")
        return NodeOutput(
            data={output_key: context.input_data},
        )


def register() -> None:
    registry = get_registry()

    registry.register(NodeTypeDefinition(
        type_id="start",
        label="Start",
        category=NodeCategory.FLOW_CONTROL,
        description="Entry point of the workflow. Injects workflow input.",
        icon="&#9654;",
        ports=[
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        executor_class=StartNodeExecutor,
    ))

    registry.register(NodeTypeDefinition(
        type_id="end",
        label="End",
        category=NodeCategory.FLOW_CONTROL,
        description="Exit point of the workflow. Captures final output.",
        icon="&#9632;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "output_key": {"type": "string", "default": "result"},
            },
        },
        executor_class=EndNodeExecutor,
    ))
