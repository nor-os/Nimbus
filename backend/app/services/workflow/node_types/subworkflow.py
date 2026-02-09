"""
Overview: Sub-workflow node — invokes another workflow definition by ID with isolated scope.
Architecture: Integration node type (Section 5)
Dependencies: app.services.workflow.node_types.base
Concepts: Sub-workflow invocation, isolated scope, recursive execution
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


class SubworkflowNodeExecutor(BaseNodeExecutor):
    """Invokes another workflow definition as a child workflow.
    The DynamicWorkflowExecutor handles the actual Temporal child workflow invocation."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        definition_id = context.config.get("definition_id", "")
        input_mapping: dict = context.config.get("input_mapping", {})

        if not definition_id:
            return NodeOutput(error="Sub-workflow definition_id is required")

        # Build child input from mapping
        child_input: dict = {}
        for key, source in input_mapping.items():
            if source.startswith("$"):
                # Will be resolved by the executor's expression engine
                child_input[key] = source
            else:
                child_input[key] = context.input_data.get(source, source)

        return NodeOutput(
            data={
                "definition_id": definition_id,
                "child_input": child_input,
                "input": context.input_data,
            },
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="subworkflow",
        label="Sub-Workflow",
        category=NodeCategory.INTEGRATION,
        description="Invokes another workflow definition by ID.",
        icon="&#9881;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "definition_id": {
                    "type": "string",
                    "description": "UUID of the target definition",
                    "x-ui-widget": "workflow-picker",
                },
                "input_mapping": {
                    "type": "object",
                    "additionalProperties": {"type": "string"},
                    "description": "Map of child input keys to source expressions",
                    "x-ui-widget": "key-value-map",
                },
            },
            "required": ["definition_id"],
        },
        executor_class=SubworkflowNodeExecutor,
    ))
