"""
Overview: Stack parameter service — manages blueprint parameter definitions with auto-sync from slots.
Architecture: Service layer for blueprint parameter management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.blueprint_parameter, app.models.cmdb.service_cluster
Concepts: Parameters are either slot_derived (auto-created from slot semantic type properties_schema)
    or custom (user-defined). sync_slot_parameters reads each slot's semantic type to generate
    parameter definitions automatically.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.blueprint_parameter import StackBlueprintParameter
from app.models.cmdb.service_cluster import ServiceCluster, ServiceClusterSlot
from app.models.semantic_type import SemanticResourceType

logger = logging.getLogger(__name__)


class ParameterServiceError(Exception):
    def __init__(self, message: str, code: str = "PARAMETER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class StackParameterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_slot_parameters(self, cluster_id: uuid.UUID, tenant_id: str) -> list[StackBlueprintParameter]:
        """Sync slot-derived parameters from each slot's semantic type properties_schema."""
        # Load cluster with slots
        result = await self.db.execute(
            select(ServiceCluster).where(
                ServiceCluster.id == cluster_id,
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.deleted_at.is_(None),
            )
        )
        cluster = result.scalar_one_or_none()
        if not cluster:
            raise ParameterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        # Load existing slot-derived parameters
        existing_result = await self.db.execute(
            select(StackBlueprintParameter).where(
                StackBlueprintParameter.cluster_id == cluster_id,
                StackBlueprintParameter.source_type == "slot_derived",
                StackBlueprintParameter.deleted_at.is_(None),
            )
        )
        existing_params = {
            (str(p.source_slot_id), p.source_property_path): p
            for p in existing_result.scalars().all()
        }

        # Load slots (already eager-loaded or fetch)
        slot_result = await self.db.execute(
            select(ServiceClusterSlot).where(
                ServiceClusterSlot.cluster_id == cluster_id,
                ServiceClusterSlot.deleted_at.is_(None),
            )
        )
        slots = slot_result.scalars().all()

        # Collect semantic type IDs
        type_ids = {s.semantic_type_id for s in slots if s.semantic_type_id}
        type_map: dict[str, SemanticResourceType] = {}
        if type_ids:
            st_result = await self.db.execute(
                select(SemanticResourceType).where(
                    SemanticResourceType.id.in_(list(type_ids))
                )
            )
            for st in st_result.scalars().all():
                type_map[str(st.id)] = st

        synced = []
        seen_keys: set[tuple[str, str | None]] = set()
        sort_idx = 0

        for slot in slots:
            if not slot.semantic_type_id:
                continue
            st = type_map.get(str(slot.semantic_type_id))
            if not st or not st.properties_schema:
                continue

            schema_props = st.properties_schema.get("properties", {})
            required_props = set(st.properties_schema.get("required", []))

            for prop_name, prop_def in schema_props.items():
                key = (str(slot.id), prop_name)
                seen_keys.add(key)
                param_name = f"{slot.name}.{prop_name}"

                if key in existing_params:
                    # Update existing
                    param = existing_params[key]
                    param.display_name = f"{slot.display_name} — {prop_def.get('title', prop_name)}"
                    param.parameter_schema = prop_def
                    param.is_required = prop_name in required_props
                    param.sort_order = sort_idx
                    synced.append(param)
                else:
                    # Create new
                    param = StackBlueprintParameter(
                        cluster_id=cluster_id,
                        name=param_name,
                        display_name=f"{slot.display_name} — {prop_def.get('title', prop_name)}",
                        description=prop_def.get("description"),
                        parameter_schema=prop_def,
                        default_value=prop_def.get("default"),
                        source_type="slot_derived",
                        source_slot_id=slot.id,
                        source_property_path=prop_name,
                        is_required=prop_name in required_props,
                        sort_order=sort_idx,
                    )
                    self.db.add(param)
                    synced.append(param)

                sort_idx += 1

        # Soft-delete slot-derived params that no longer have a matching slot+property
        for key, param in existing_params.items():
            if key not in seen_keys:
                param.deleted_at = datetime.now(UTC)

        await self.db.flush()
        return synced

    async def add_custom_parameter(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict[str, Any]
    ) -> StackBlueprintParameter:
        """Add a user-defined custom parameter to a blueprint."""
        # Verify cluster exists
        result = await self.db.execute(
            select(ServiceCluster).where(
                ServiceCluster.id == cluster_id,
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.deleted_at.is_(None),
            )
        )
        if not result.scalar_one_or_none():
            raise ParameterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        # Check name uniqueness
        existing = await self.db.execute(
            select(StackBlueprintParameter).where(
                StackBlueprintParameter.cluster_id == cluster_id,
                StackBlueprintParameter.name == data["name"],
                StackBlueprintParameter.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ParameterServiceError(
                f"Parameter '{data['name']}' already exists", "PARAM_EXISTS"
            )

        param = StackBlueprintParameter(
            cluster_id=cluster_id,
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description"),
            parameter_schema=data.get("parameter_schema"),
            default_value=data.get("default_value"),
            source_type="custom",
            is_required=data.get("is_required", False),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(param)
        await self.db.flush()
        return param

    async def update_parameter(
        self, param_id: uuid.UUID, cluster_id: uuid.UUID, data: dict[str, Any]
    ) -> StackBlueprintParameter:
        """Update a parameter (custom parameters only for most fields)."""
        param = await self._get_param(param_id, cluster_id)
        if not param:
            raise ParameterServiceError("Parameter not found", "PARAM_NOT_FOUND")

        for key in ("display_name", "description", "parameter_schema",
                     "default_value", "is_required", "sort_order"):
            if key in data:
                setattr(param, key, data[key])

        await self.db.flush()
        return param

    async def delete_parameter(
        self, param_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> bool:
        """Soft-delete a parameter."""
        param = await self._get_param(param_id, cluster_id)
        if not param:
            raise ParameterServiceError("Parameter not found", "PARAM_NOT_FOUND")

        param.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_parameters(
        self, cluster_id: uuid.UUID
    ) -> list[StackBlueprintParameter]:
        """List all active parameters for a cluster."""
        result = await self.db.execute(
            select(StackBlueprintParameter)
            .where(
                StackBlueprintParameter.cluster_id == cluster_id,
                StackBlueprintParameter.deleted_at.is_(None),
            )
            .order_by(StackBlueprintParameter.sort_order, StackBlueprintParameter.name)
        )
        return list(result.scalars().all())

    async def get_aggregated_schema(self, cluster_id: uuid.UUID) -> dict[str, Any]:
        """Build a merged JSON Schema of all parameters for a blueprint."""
        params = await self.list_parameters(cluster_id)
        properties: dict[str, Any] = {}
        required: list[str] = []

        for p in params:
            prop_schema = dict(p.parameter_schema) if p.parameter_schema else {"type": "string"}
            if p.default_value is not None:
                prop_schema["default"] = p.default_value
            prop_schema["title"] = p.display_name
            if p.description:
                prop_schema["description"] = p.description
            properties[p.name] = prop_schema
            if p.is_required:
                required.append(p.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    async def _get_param(
        self, param_id: uuid.UUID, cluster_id: uuid.UUID
    ) -> StackBlueprintParameter | None:
        result = await self.db.execute(
            select(StackBlueprintParameter).where(
                StackBlueprintParameter.id == param_id,
                StackBlueprintParameter.cluster_id == cluster_id,
                StackBlueprintParameter.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()
