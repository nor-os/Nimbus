"""
Overview: Dynamic activity palette provider — generates NodeTypeDefinitions from published activities.
Architecture: Dynamic node type generation for workflow editor (Section 11.5)
Dependencies: app.services.automation.activity_service, app.services.workflow.node_registry
Concepts: Dynamic palette, schema-to-port mapping, no-restart updates
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.workflow.node_registry import (
    NodeCategory,
    NodeTypeDefinition,
    PortDef,
    PortDirection,
    PortType,
)

logger = logging.getLogger(__name__)


class PaletteProvider:
    """Generates NodeTypeDefinitions from published activities at query time."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_activity_palette(
        self, tenant_id: str
    ) -> list[NodeTypeDefinition]:
        """Generate palette entries for all published activities."""
        from app.services.automation.activity_service import ActivityService

        svc = ActivityService(self.db)
        activities = await svc.list(tenant_id, limit=200)

        palette: list[NodeTypeDefinition] = []
        for activity in activities:
            latest = None
            for v in (activity.versions or []):
                if v.published_at and (latest is None or v.version > latest.version):
                    latest = v

            if not latest:
                continue

            ports = self._build_ports(latest.input_schema, latest.output_schema)

            palette.append(NodeTypeDefinition(
                type_id=f"activity:{activity.slug}",
                label=activity.name,
                category=NodeCategory.ACTIVITY,
                description=activity.description or "",
                icon="&#9881;",
                ports=ports,
                config_schema={
                    "type": "object",
                    "properties": {
                        "activity_id": {"type": "string", "const": str(activity.id)},
                        "version_id": {"type": "string", "default": str(latest.id)},
                        "parameter_bindings": {
                            "type": "object",
                            "properties": self._build_binding_schema(latest.input_schema),
                        },
                    },
                },
            ))

        return palette

    def _build_ports(
        self, input_schema: dict | None, output_schema: dict | None
    ) -> list[PortDef]:
        """Build typed ports from input/output schemas."""
        ports = [
            PortDef("in", PortDirection.INPUT, PortType.FLOW, "Input"),
            PortDef("out", PortDirection.OUTPUT, PortType.FLOW, "Success"),
            PortDef("error", PortDirection.OUTPUT, PortType.FLOW, "Error"),
        ]

        # Add data input ports from input schema
        if input_schema and "properties" in input_schema:
            for name, prop in input_schema["properties"].items():
                required = name in input_schema.get("required", [])
                ports.append(PortDef(
                    f"in:{name}",
                    PortDirection.INPUT,
                    PortType.DATA,
                    prop.get("title", name),
                    required=required,
                ))

        # Add data output ports from output schema
        if output_schema and "properties" in output_schema:
            for name, prop in output_schema["properties"].items():
                ports.append(PortDef(
                    f"out:{name}",
                    PortDirection.OUTPUT,
                    PortType.DATA,
                    prop.get("title", name),
                    required=False,
                ))

        return ports

    def _build_binding_schema(self, input_schema: dict | None) -> dict:
        """Build parameter binding config schema from input schema."""
        if not input_schema or "properties" not in input_schema:
            return {}
        return {
            name: {"type": "string", "description": prop.get("description", "")}
            for name, prop in input_schema["properties"].items()
        }
