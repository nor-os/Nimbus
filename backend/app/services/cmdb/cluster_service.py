"""
Overview: Service cluster service — CRUD for blueprint clusters and their slots.
Architecture: Service layer for cluster management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_cluster
Concepts: Clusters are pure blueprint templates defining slot shapes. CI assignment
    happens at deployment time, not on the blueprint itself.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.service_cluster import (
    ServiceCluster,
    ServiceClusterSlot,
)

logger = logging.getLogger(__name__)


class ClusterServiceError(Exception):
    def __init__(self, message: str, code: str = "CLUSTER_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ClusterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Cluster CRUD ──────────────────────────────────────────────────

    async def create_cluster(
        self, tenant_id: str, data: dict, user_id: str | None = None
    ) -> ServiceCluster:
        """Create a service cluster with optional inline slots."""
        existing = await self.db.execute(
            select(ServiceCluster).where(
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.name == data["name"],
                ServiceCluster.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ClusterServiceError(
                f"Cluster '{data['name']}' already exists", "CLUSTER_EXISTS"
            )

        cluster = ServiceCluster(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            cluster_type=data.get("cluster_type", "service_cluster"),
            architecture_topology_id=data.get("architecture_topology_id"),
            topology_node_id=data.get("topology_node_id"),
            tags=data.get("tags", {}),
            stack_tag_key=data.get("stack_tag_key"),
            metadata_=data.get("metadata"),
        )
        self.db.add(cluster)
        await self.db.flush()

        # Create inline slots if provided
        for i, slot_data in enumerate(data.get("slots", [])):
            slot = ServiceClusterSlot(
                cluster_id=cluster.id,
                name=slot_data["name"],
                display_name=slot_data.get("display_name", slot_data["name"]),
                description=slot_data.get("description"),
                allowed_ci_class_ids=slot_data.get("allowed_ci_class_ids"),
                semantic_category_id=slot_data.get("semantic_category_id"),
                semantic_type_id=slot_data.get("semantic_type_id"),
                min_count=slot_data.get("min_count", 1),
                max_count=slot_data.get("max_count"),
                is_required=slot_data.get("is_required", True),
                sort_order=slot_data.get("sort_order", i),
            )
            self.db.add(slot)

        await self.db.flush()
        return await self.get_cluster(cluster.id, tenant_id)

    async def update_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceCluster:
        """Partial update of a service cluster."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        for key in ("name", "description", "cluster_type",
                     "tags", "stack_tag_key", "architecture_topology_id", "topology_node_id"):
            if key in data:
                if key == "metadata":
                    cluster.metadata_ = data[key]
                else:
                    setattr(cluster, key, data[key])
        if "metadata" in data:
            cluster.metadata_ = data["metadata"]

        await self.db.flush()
        return cluster

    async def delete_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a cluster and cascade to slots."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        now = datetime.now(UTC)
        cluster.deleted_at = now
        for slot in cluster.slots:
            slot.deleted_at = now

        await self.db.flush()
        return True

    async def get_cluster(
        self, cluster_id: uuid.UUID, tenant_id: str
    ) -> ServiceCluster | None:
        """Get a cluster with slots eagerly loaded."""
        result = await self.db.execute(
            select(ServiceCluster)
            .where(
                ServiceCluster.id == cluster_id,
                ServiceCluster.tenant_id == tenant_id,
                ServiceCluster.deleted_at.is_(None),
            )
            .options(
                selectinload(ServiceCluster.slots),
            )
        )
        return result.scalar_one_or_none()

    async def list_clusters(
        self,
        tenant_id: str,
        cluster_type: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceCluster], int]:
        """List clusters with pagination and filtering."""
        base = select(ServiceCluster).where(
            ServiceCluster.tenant_id == tenant_id,
            ServiceCluster.deleted_at.is_(None),
        )

        if cluster_type:
            base = base.where(ServiceCluster.cluster_type == cluster_type)
        if search:
            base = base.where(ServiceCluster.name.ilike(f"%{search}%"))

        count_result = await self.db.execute(
            select(func.count()).select_from(base.subquery())
        )
        total = count_result.scalar() or 0

        query = (
            base
            .options(
                selectinload(ServiceCluster.slots),
            )
            .order_by(ServiceCluster.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().unique().all()), total

    # ── Slot Management ───────────────────────────────────────────────

    async def add_slot(
        self, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceClusterSlot:
        """Add a slot to a cluster."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        # Check unique name within cluster
        for existing_slot in cluster.slots:
            if existing_slot.name == data["name"] and not existing_slot.deleted_at:
                raise ClusterServiceError(
                    f"Slot '{data['name']}' already exists", "SLOT_EXISTS"
                )

        slot = ServiceClusterSlot(
            cluster_id=cluster_id,
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            description=data.get("description"),
            allowed_ci_class_ids=data.get("allowed_ci_class_ids"),
            semantic_category_id=data.get("semantic_category_id"),
            semantic_type_id=data.get("semantic_type_id"),
            min_count=data.get("min_count", 1),
            max_count=data.get("max_count"),
            is_required=data.get("is_required", True),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(slot)
        await self.db.flush()
        return slot

    async def update_slot(
        self, slot_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str, data: dict
    ) -> ServiceClusterSlot:
        """Update a slot definition."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        slot = None
        for s in cluster.slots:
            if s.id == slot_id and not s.deleted_at:
                slot = s
                break
        if not slot:
            raise ClusterServiceError("Slot not found", "SLOT_NOT_FOUND")

        for key in ("display_name", "description", "allowed_ci_class_ids",
                     "semantic_category_id", "semantic_type_id",
                     "min_count", "max_count", "is_required", "sort_order"):
            if key in data:
                setattr(slot, key, data[key])

        await self.db.flush()
        return slot

    async def remove_slot(
        self, slot_id: uuid.UUID, cluster_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a slot."""
        cluster = await self.get_cluster(cluster_id, tenant_id)
        if not cluster:
            raise ClusterServiceError("Cluster not found", "CLUSTER_NOT_FOUND")

        now = datetime.now(UTC)
        for slot in cluster.slots:
            if slot.id == slot_id and not slot.deleted_at:
                slot.deleted_at = now
                await self.db.flush()
                return True

        raise ClusterServiceError("Slot not found", "SLOT_NOT_FOUND")

    # ── Blueprint Stacks ───────────────────────────────────────────────

    async def list_blueprint_stacks(
        self, blueprint_id: str, tenant_id: str
    ) -> dict | None:
        """List deployed stacks by querying CIs with the blueprint's stack_tag_key."""
        cluster = await self.get_cluster(blueprint_id, tenant_id)
        if not cluster or not cluster.stack_tag_key:
            return None

        tag_key = cluster.stack_tag_key

        # Query CIs that have this tag key, grouped by tag value
        from sqlalchemy import case, literal_column

        stmt = (
            select(
                ConfigurationItem.tags[tag_key].astext.label("tag_value"),
                func.count(ConfigurationItem.id).label("ci_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "active", literal_column("1")),
                )).label("active_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "planned", literal_column("1")),
                )).label("planned_count"),
                func.count(case(
                    (ConfigurationItem.lifecycle_state == "maintenance", literal_column("1")),
                )).label("maintenance_count"),
            )
            .where(
                ConfigurationItem.tenant_id == tenant_id,
                ConfigurationItem.deleted_at.is_(None),
                ConfigurationItem.tags[tag_key].astext.isnot(None),
            )
            .group_by(ConfigurationItem.tags[tag_key].astext)
            .order_by(ConfigurationItem.tags[tag_key].astext)
        )

        result = await self.db.execute(stmt)
        rows = result.all()

        stacks = [
            {
                "tag_value": row.tag_value,
                "ci_count": row.ci_count,
                "active_count": row.active_count,
                "planned_count": row.planned_count,
                "maintenance_count": row.maintenance_count,
            }
            for row in rows
            if row.tag_value  # Skip null values
        ]

        return {
            "blueprint_id": str(cluster.id),
            "blueprint_name": cluster.name,
            "tag_key": tag_key,
            "stacks": stacks,
        }
