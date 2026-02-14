"""
Overview: Topology resolve node — resolves parameters for a topology and computes deployment order.
Architecture: Deployment node type for visual workflow editor (Section 5)
Dependencies: app.services.workflow.node_types.base, app.services.architecture
Concepts: Parameter resolution, deployment order, topology readiness check
"""

from __future__ import annotations

import logging

from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
    get_registry,
)
from app.services.workflow.node_types.base import BaseNodeExecutor, NodeExecutionContext, NodeOutput

logger = logging.getLogger(__name__)


class TopologyResolveNodeExecutor(BaseNodeExecutor):
    """Resolves parameters for a topology and computes deployment order."""

    async def execute(self, context: NodeExecutionContext) -> NodeOutput:
        topology_id = context.config.get("topology_id", "")
        validate_completeness = context.config.get("validate_completeness", True)

        if not topology_id:
            return NodeOutput(error="topology_id is required")

        if context.is_test:
            mock_order = [["stack-1"], ["stack-2", "stack-3"]]
            return NodeOutput(
                data={
                    "resolution": {
                        "topology_id": topology_id,
                        "stacks": [],
                        "all_complete": True,
                        "total_unresolved": 0,
                    },
                    "deployment_order": mock_order,
                    "all_complete": True,
                },
                next_port="out",
            )

        try:
            from app.db.session import async_session_factory
            from app.services.architecture.parameter_resolution_service import (
                ParameterResolutionService,
            )

            async with async_session_factory() as db:
                svc = ParameterResolutionService(db)
                preview = await svc.preview_resolution(context.tenant_id, topology_id)

            all_complete = preview.all_complete

            if validate_completeness and not all_complete:
                return NodeOutput(
                    data={
                        "resolution": {
                            "topology_id": topology_id,
                            "total_unresolved": preview.total_unresolved,
                            "all_complete": False,
                        },
                        "deployment_order": preview.deployment_order,
                        "all_complete": False,
                    },
                    next_port="error",
                )

            return NodeOutput(
                data={
                    "resolution": {
                        "topology_id": topology_id,
                        "stacks": [
                            {
                                "stack_id": s.stack_id,
                                "stack_label": s.stack_label,
                                "blueprint_id": s.blueprint_id,
                                "is_complete": s.is_complete,
                                "unresolved_count": s.unresolved_count,
                            }
                            for s in preview.stacks
                        ],
                        "all_complete": all_complete,
                        "total_unresolved": preview.total_unresolved,
                    },
                    "deployment_order": preview.deployment_order,
                    "all_complete": all_complete,
                },
                next_port="out",
            )
        except Exception as e:
            logger.exception("Topology resolve failed: %s", e)
            return NodeOutput(error=f"Topology resolution failed: {e}")


def register() -> None:
    get_registry().register(NodeTypeDefinition(
        type_id="topology_resolve",
        label="Topology Resolve",
        category=NodeCategory.DEPLOYMENT,
        description="Resolves parameters for a topology and computes deployment order.",
        icon="&#128269;",
        ports=[
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Output"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ],
        config_schema={
            "type": "object",
            "properties": {
                "topology_id": {"type": "string", "description": "ID of the topology to resolve"},
                "validate_completeness": {
                    "type": "boolean",
                    "default": True,
                    "description": "If true, routes to error port when parameters are incomplete",
                },
            },
            "required": ["topology_id"],
        },
        executor_class=TopologyResolveNodeExecutor,
    ))
