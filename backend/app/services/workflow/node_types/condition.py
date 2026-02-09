"""
Overview: If/Else condition node — evaluates expression and routes to true/false output port.
Architecture: Flow control node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Conditional branching, expression evaluation, true/false routing
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


class ConditionNodeExecutor(BaseNodeExecutor):
    """Evaluates a condition expression and routes to true or false port."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        expression = context.config.get("expression", "false")

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        result = evaluate_expression(expression, expr_ctx, BUILTIN_FUNCTIONS)
        port = "true" if bool(result) else "false"

        return NodeOutput(
            data={"result": bool(result), "input": context.input_data},
            next_port=port,
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="condition",
        label="If/Else",
        category=NodeCategory.FLOW_CONTROL,
        description="Evaluates an expression and routes to true or false branch.",
        icon="&#10070;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("true", PortDirection.OUTPUT, PortType.FLOW, "True"),
            PortDef("false", PortDirection.OUTPUT, PortType.FLOW, "False"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Condition expression",
                    "x-ui-widget": "expression",
                },
            },
            "required": ["expression"],
        },
        executor_class=ConditionNodeExecutor,
    ))
