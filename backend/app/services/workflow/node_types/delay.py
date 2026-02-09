"""
Overview: Delay node — pauses workflow execution for a configurable duration.
Architecture: Utility node type (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.workflow.expression_engine
Concepts: Timed delay, configurable pause, expression-based duration
"""

import asyncio

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

MAX_DELAY_SECONDS = 86400  # 24 hours


class DelayNodeExecutor(BaseNodeExecutor):
    """Pauses execution for a specified number of seconds."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        seconds_config = context.config.get("seconds", 0)

        if isinstance(seconds_config, str):
            expr_ctx = ExpressionContext(
                variables=context.variables,
                nodes=context.node_outputs,
                loop=context.loop_context or {},
                input_data=context.workflow_input,
            )
            seconds = float(evaluate_expression(seconds_config, expr_ctx, BUILTIN_FUNCTIONS))
        else:
            seconds = float(seconds_config)

        seconds = max(0, min(seconds, MAX_DELAY_SECONDS))

        if not context.is_test:
            await asyncio.sleep(seconds)

        return NodeOutput(
            data={"delayed_seconds": seconds},
            next_port="out",
        )


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="delay",
        label="Delay",
        category=NodeCategory.UTILITY,
        description="Pauses execution for a configurable duration.",
        icon="&#9202;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "seconds": {
                    "oneOf": [
                        {"type": "number", "minimum": 0, "maximum": 86400},
                        {"type": "string", "description": "Expression evaluating to seconds"},
                    ],
                    "default": 0,
                },
            },
        },
        executor_class=DelayNodeExecutor,
    ))
