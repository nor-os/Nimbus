"""
Overview: Script node — evaluates expressions without side effects for data transformation.
Architecture: Data node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Expression evaluation, data transformation, no side effects
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


class ScriptNodeExecutor(BaseNodeExecutor):
    """Evaluates one or more expressions and stores results in output variables."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        assignments: list[dict] = context.config.get("assignments", [])

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        results: dict = {}
        for assignment in assignments:
            var_name = assignment.get("variable", "")
            expression = assignment.get("expression", "null")
            if var_name:
                results[var_name] = evaluate_expression(
                    expression, expr_ctx, BUILTIN_FUNCTIONS
                )

        return NodeOutput(
            data=results,
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="script",
        label="Script",
        category=NodeCategory.DATA,
        description="Evaluates expressions for data transformation (no side effects).",
        icon="&#128196;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "assignments": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "variable": {"type": "string"},
                            "expression": {"type": "string"},
                        },
                        "required": ["variable", "expression"],
                    },
                    "x-ui-widget": "key-value-list",
                    "x-ui-key-label": "Variable",
                    "x-ui-value-label": "Expression",
                },
            },
        },
        executor_class=ScriptNodeExecutor,
    ))
