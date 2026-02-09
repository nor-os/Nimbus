"""
Overview: Switch node — evaluates expression and routes to matching case port or default.
Architecture: Flow control node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Multi-way branching, case matching, default fallback
"""

from app.services.workflow.expression_engine import (
    ExpressionContext,
    evaluate_expression,
)
from app.services.workflow.expression_functions import BUILTIN_FUNCTIONS
from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput


class SwitchNodeExecutor(BaseNodeExecutor):
    """Evaluates an expression and routes to the matching case port."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        expression = context.config.get("expression", "")
        cases: list[dict] = context.config.get("cases", [])

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        value = evaluate_expression(expression, expr_ctx, BUILTIN_FUNCTIONS)

        for case in cases:
            if case.get("value") == value:
                return NodeOutput(
                    data={"value": value, "matched_case": case.get("label", "")},
                    next_port=case.get("port", "default"),
                )

        return NodeOutput(
            data={"value": value, "matched_case": "default"},
            next_port="default",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="switch",
        label="Switch",
        category=NodeCategory.FLOW_CONTROL,
        description="Evaluates an expression and routes to the matching case.",
        icon="&#9670;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("default", PortDirection.OUTPUT, PortType.FLOW, "Default"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "x-ui-widget": "expression",
                },
                "cases": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "value": {},
                            "label": {"type": "string"},
                            "port": {"type": "string"},
                        },
                    },
                    "x-ui-widget": "switch-cases",
                },
            },
            "required": ["expression"],
        },
        executor_class=SwitchNodeExecutor,
    ))
