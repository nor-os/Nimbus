"""
Overview: ForEach and While loop node executors — iteration markers for the workflow executor.
Architecture: Flow control node types (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Loop iteration, max iterations safety, forEach collection, while condition
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

DEFAULT_MAX_ITERATIONS = 1000


class ForEachNodeExecutor(BaseNodeExecutor):
    """Marker node — DynamicWorkflowExecutor handles actual iteration.
    Resolves the collection expression for the executor to iterate over."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        collection_expr = context.config.get("collection", "[]")
        max_iterations = context.config.get("max_iterations", DEFAULT_MAX_ITERATIONS)

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        collection = evaluate_expression(collection_expr, expr_ctx, BUILTIN_FUNCTIONS)
        if not isinstance(collection, (list, tuple)):
            return NodeOutput(
                error=f"ForEach collection must be a list, got {type(collection).__name__}"
            )

        if len(collection) > max_iterations:
            collection = collection[:max_iterations]

        return NodeOutput(
            data={
                "collection": list(collection),
                "max_iterations": max_iterations,
                "total": len(collection),
            },
            next_port="body",
        )


class WhileNodeExecutor(BaseNodeExecutor):
    """Marker node — DynamicWorkflowExecutor handles actual looping.
    Evaluates the condition expression for the executor."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        condition_expr = context.config.get("condition", "false")
        max_iterations = context.config.get("max_iterations", DEFAULT_MAX_ITERATIONS)

        expr_ctx = ExpressionContext(
            variables=context.variables,
            nodes=context.node_outputs,
            loop=context.loop_context or {},
            input_data=context.workflow_input,
        )

        result = evaluate_expression(condition_expr, expr_ctx, BUILTIN_FUNCTIONS)
        should_continue = bool(result)

        port = "body" if should_continue else "done"
        return NodeOutput(
            data={
                "condition_result": should_continue,
                "max_iterations": max_iterations,
            },
            next_port=port,
        )


def register() -> None:
    registry = get_registry()

    registry.register(NodeTypeDefinition(
        type_id="forEach",
        label="For Each",
        category=NodeCategory.FLOW_CONTROL,
        description="Iterates over a collection, executing the body for each item.",
        icon="&#8634;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("body", PortDirection.OUTPUT, PortType.FLOW, "Loop Body"),
            PortDef("done", PortDirection.OUTPUT, PortType.FLOW, "Done"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "collection": {
                    "type": "string",
                    "description": "Expression evaluating to a list",
                    "x-ui-widget": "expression",
                },
                "max_iterations": {"type": "integer", "default": 1000},
            },
            "required": ["collection"],
        },
        executor_class=ForEachNodeExecutor,
        is_marker=True,
    ))

    registry.register(NodeTypeDefinition(
        type_id="while",
        label="While Loop",
        category=NodeCategory.FLOW_CONTROL,
        description="Repeats the body while the condition is true.",
        icon="&#8635;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("body", PortDirection.OUTPUT, PortType.FLOW, "Loop Body"),
            PortDef("done", PortDirection.OUTPUT, PortType.FLOW, "Done"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "condition": {
                    "type": "string",
                    "description": "Condition expression",
                    "x-ui-widget": "expression",
                },
                "max_iterations": {"type": "integer", "default": 1000},
            },
            "required": ["condition"],
        },
        executor_class=WhileNodeExecutor,
        is_marker=True,
    ))
