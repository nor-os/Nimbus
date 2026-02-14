"""
Overview: Deployment workflow generator — auto-generates deployment workflows from topologies.
Architecture: Service that converts topology graphs into executable deployment workflows (Section 5)
Dependencies: app.services.architecture, app.services.workflow.definition_service
Concepts: Topology-to-workflow conversion, parallel deployment groups, Kahn's algorithm reuse
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_definition import WorkflowDefinition, WorkflowType
from app.services.architecture.topology_service import TopologyService
from app.services.workflow.definition_service import (
    WorkflowDefinitionError,
    WorkflowDefinitionService,
)

logger = logging.getLogger(__name__)


@dataclass
class GeneratorOptions:
    add_approval_gates: bool = False
    add_notifications: bool = False


class DeploymentWorkflowGenerator:
    """Generates deployment workflow definitions from published topologies."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._topology_svc = TopologyService(db)
        self._definition_svc = WorkflowDefinitionService(db)

    async def generate_from_topology(
        self,
        tenant_id: str,
        topology_id: str,
        created_by: str,
        options: GeneratorOptions | None = None,
    ) -> WorkflowDefinition:
        """Generate a deployment workflow from a published topology.

        Returns a DRAFT WorkflowDefinition with workflow_type=DEPLOYMENT.
        """
        opts = options or GeneratorOptions()

        # Load the topology
        topology = await self._topology_svc.get(tenant_id, topology_id)
        if not topology:
            raise WorkflowDefinitionError(
                f"Topology '{topology_id}' not found", "NOT_FOUND"
            )

        if not topology.graph:
            raise WorkflowDefinitionError(
                "Topology has no graph data", "NO_GRAPH"
            )

        # Compute deployment order (list of parallel groups)
        deployment_order = TopologyService.get_deployment_order(topology.graph)
        if not deployment_order:
            raise WorkflowDefinitionError(
                "Topology has no stacks to deploy", "EMPTY_TOPOLOGY"
            )

        # Build stack label map
        stack_map: dict[str, str] = {}
        for s in topology.graph.get("stacks", []):
            sid = s.get("id")
            if sid:
                stack_map[sid] = s.get("label", sid)

        # Build the workflow graph
        graph = self._build_graph(
            topology_id, deployment_order, stack_map, opts
        )

        # Create the definition
        definition = await self._definition_svc.create(
            tenant_id=tenant_id,
            created_by=created_by,
            data={
                "name": f"Deploy: {topology.name}",
                "description": f"Auto-generated deployment workflow for topology '{topology.name}'",
                "graph": graph,
                "workflow_type": WorkflowType.DEPLOYMENT,
                "source_topology_id": topology_id,
                "timeout_seconds": 7200,
            },
        )

        return definition

    def _build_graph(
        self,
        topology_id: str,
        deployment_order: list[list[str]],
        stack_map: dict[str, str],
        options: GeneratorOptions,
    ) -> dict[str, Any]:
        """Build a workflow graph JSONB from deployment order."""
        nodes: list[dict[str, Any]] = []
        connections: list[dict[str, Any]] = []

        x_offset = 100
        x_step = 250
        y_center = 300

        # Start node
        start_id = "start"
        nodes.append({
            "id": start_id,
            "type": "start",
            "config": {},
            "position": {"x": x_offset, "y": y_center},
            "label": "Start",
        })

        # Topology resolve node
        resolve_id = "resolve"
        x_offset += x_step
        nodes.append({
            "id": resolve_id,
            "type": "topology_resolve",
            "config": {
                "topology_id": topology_id,
                "validate_completeness": True,
            },
            "position": {"x": x_offset, "y": y_center},
            "label": "Resolve Parameters",
        })
        connections.append({
            "source": start_id,
            "target": resolve_id,
            "sourcePort": "out",
            "targetPort": "in",
        })

        prev_node_id = resolve_id
        prev_port = "out"

        # For each deployment group
        for group_idx, group in enumerate(deployment_order):
            x_offset += x_step

            # Optional approval gate before each group
            if options.add_approval_gates:
                gate_id = f"gate_{group_idx}"
                nodes.append({
                    "id": gate_id,
                    "type": "deployment_gate",
                    "config": {
                        "title": f"Approve Deployment Group {group_idx + 1}",
                        "description": f"Stacks: {', '.join(stack_map.get(s, s) for s in group)}",
                        "deployment_context": f"Group {group_idx + 1} of {len(deployment_order)}",
                    },
                    "position": {"x": x_offset, "y": y_center},
                    "label": f"Approve Group {group_idx + 1}",
                })
                connections.append({
                    "source": prev_node_id,
                    "target": gate_id,
                    "sourcePort": prev_port,
                    "targetPort": "in",
                })
                prev_node_id = gate_id
                prev_port = "approved"
                x_offset += x_step

            if len(group) == 1:
                # Single stack — no parallel wrapper needed
                stack_id = group[0]
                deploy_id = f"deploy_{stack_id}"
                nodes.append({
                    "id": deploy_id,
                    "type": "stack_deploy",
                    "config": {
                        "stack_id": stack_id,
                        "topology_id": topology_id,
                    },
                    "position": {"x": x_offset, "y": y_center},
                    "label": f"Deploy: {stack_map.get(stack_id, stack_id)}",
                })
                connections.append({
                    "source": prev_node_id,
                    "target": deploy_id,
                    "sourcePort": prev_port,
                    "targetPort": "in",
                })
                prev_node_id = deploy_id
                prev_port = "out"

            else:
                # Multiple stacks — parallel fan-out and merge
                parallel_id = f"parallel_{group_idx}"
                merge_id = f"merge_{group_idx}"

                nodes.append({
                    "id": parallel_id,
                    "type": "parallel",
                    "config": {"branches": len(group)},
                    "position": {"x": x_offset, "y": y_center},
                    "label": f"Parallel Group {group_idx + 1}",
                })
                connections.append({
                    "source": prev_node_id,
                    "target": parallel_id,
                    "sourcePort": prev_port,
                    "targetPort": "in",
                })

                deploy_x = x_offset + x_step
                y_fan = y_center - (len(group) - 1) * 60

                for i, stack_id in enumerate(group):
                    deploy_id = f"deploy_{stack_id}"
                    y_pos = y_fan + i * 120
                    nodes.append({
                        "id": deploy_id,
                        "type": "stack_deploy",
                        "config": {
                            "stack_id": stack_id,
                            "topology_id": topology_id,
                        },
                        "position": {"x": deploy_x, "y": y_pos},
                        "label": f"Deploy: {stack_map.get(stack_id, stack_id)}",
                    })
                    connections.append({
                        "source": parallel_id,
                        "target": deploy_id,
                        "sourcePort": f"branch_{i}",
                        "targetPort": "in",
                    })

                merge_x = deploy_x + x_step
                nodes.append({
                    "id": merge_id,
                    "type": "parallel",
                    "config": {"mode": "merge"},
                    "position": {"x": merge_x, "y": y_center},
                    "label": f"Merge Group {group_idx + 1}",
                })

                for i, stack_id in enumerate(group):
                    deploy_id = f"deploy_{stack_id}"
                    connections.append({
                        "source": deploy_id,
                        "target": merge_id,
                        "sourcePort": "out",
                        "targetPort": f"branch_{i}",
                    })

                x_offset = merge_x
                prev_node_id = merge_id
                prev_port = "out"

            # Optional notification after each group
            if options.add_notifications:
                x_offset += x_step
                notify_id = f"notify_{group_idx}"
                nodes.append({
                    "id": notify_id,
                    "type": "notification",
                    "config": {
                        "channel": "in_app",
                        "title": f"Deployment Group {group_idx + 1} Complete",
                        "body": f"Stacks deployed: {', '.join(stack_map.get(s, s) for s in group)}",
                    },
                    "position": {"x": x_offset, "y": y_center},
                    "label": f"Notify Group {group_idx + 1}",
                })
                connections.append({
                    "source": prev_node_id,
                    "target": notify_id,
                    "sourcePort": prev_port,
                    "targetPort": "in",
                })
                prev_node_id = notify_id
                prev_port = "out"

        # CMDB record node
        x_offset += x_step
        cmdb_id = "cmdb_record"
        nodes.append({
            "id": cmdb_id,
            "type": "cmdb_record",
            "config": {
                "action": "record_deployment",
                "attributes": {"topology_id": topology_id},
            },
            "position": {"x": x_offset, "y": y_center},
            "label": "Record in CMDB",
        })
        connections.append({
            "source": prev_node_id,
            "target": cmdb_id,
            "sourcePort": prev_port,
            "targetPort": "in",
        })

        # End node
        x_offset += x_step
        end_id = "end"
        nodes.append({
            "id": end_id,
            "type": "end",
            "config": {},
            "position": {"x": x_offset, "y": y_center},
            "label": "End",
        })
        connections.append({
            "source": cmdb_id,
            "target": end_id,
            "sourcePort": "out",
            "targetPort": "in",
        })

        return {"nodes": nodes, "connections": connections}
