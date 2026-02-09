"""
Overview: Variable manipulation nodes — VariableSet, VariableGet, and VariableTransform.
Architecture: Data node types for workflow variable management (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Workflow variables, data passing, variable transformation
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


class VariableSetNodeExecutor(BaseNodeExecutor):
    """Sets one or more workflow variables from expressions."""

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
                value = evaluate_expression(expression, expr_ctx, BUILTIN_FUNCTIONS)
                results[var_name] = value
                # Update context so subsequent assignments can reference earlier ones
                expr_ctx.variables[var_name] = value

        return NodeOutput(
            data={"set_variables": results},
            next_port="out",
        )


class VariableGetNodeExecutor(BaseNodeExecutor):
    """Reads workflow variables and passes them as output."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        variable_names: list[str] = context.config.get("variables", [])

        results: dict = {}
        for name in variable_names:
            results[name] = context.variables.get(name)

        return NodeOutput(
            data=results,
            next_port="out",
        )


class VariableTransformNodeExecutor(BaseNodeExecutor):
    """Applies a transformation expression to a variable."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        source_var = context.config.get("source", "")
        expression = context.config.get("expression", "$vars." + source_var)
        target_var = context.config.get("target", source_var)

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        result = evaluate_expression(expression, expr_ctx, BUILTIN_FUNCTIONS)

        return NodeOutput(
            data={"transformed": {target_var: result}},
            next_port="out",
        )


def register() -> None:
    registry = get_registry()

    registry.register(NodeTypeDefinition(
        type_id="variable_set",
        label="Set Variable",
        category=NodeCategory.DATA,
        description="Sets workflow variables from expressions.",
        icon="&#9998;",
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
        executor_class=VariableSetNodeExecutor,
    ))

    registry.register(NodeTypeDefinition(
        type_id="variable_get",
        label="Get Variable",
        category=NodeCategory.DATA,
        description="Reads workflow variables into the data flow.",
        icon="&#128269;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "variables": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of variable names to read",
                    "x-ui-widget": "string-list",
                },
            },
        },
        executor_class=VariableGetNodeExecutor,
    ))

    registry.register(NodeTypeDefinition(
        type_id="variable_transform",
        label="Transform Variable",
        category=NodeCategory.DATA,
        description="Applies a transformation expression to a variable.",
        icon="&#10227;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "source": {"type": "string", "description": "Source variable name"},
                "expression": {
                    "type": "string",
                    "description": "Transformation expression",
                    "x-ui-widget": "expression",
                },
                "target": {"type": "string", "description": "Target variable name (defaults to source)"},
            },
            "required": ["source", "expression"],
        },
        executor_class=VariableTransformNodeExecutor,
    ))
