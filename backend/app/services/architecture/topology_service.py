"""
Overview: Topology service — CRUD, versioning, publish, clone, export/import, template management.
Architecture: Service layer for architecture topology management (Section 5)
Dependencies: sqlalchemy, app.models.architecture_topology, app.services.architecture.topology_validator
Concepts: Topology lifecycle, draft/published/archived, versioning, approval integration, notifications
"""

from __future__ import annotations

import copy
import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import yaml
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.architecture_topology import ArchitectureTopology, TopologyStatus
from app.services.architecture.topology_validator import TopologyValidator

logger = logging.getLogger(__name__)


class TopologyError(Exception):
    def __init__(self, message: str, code: str = "TOPOLOGY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TopologyService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._validator = TopologyValidator(db)

    async def create(
        self, tenant_id: str, created_by: str, data: dict[str, Any]
    ) -> ArchitectureTopology:
        """Create a new draft topology at version 0."""
        topology = ArchitectureTopology(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            version=0,
            graph=data.get("graph"),
            status=TopologyStatus.DRAFT,
            is_template=data.get("is_template", False),
            is_system=False,
            tags=data.get("tags"),
            created_by=created_by,
        )
        self.db.add(topology)
        await self.db.flush()

        await self._audit(tenant_id, created_by, "architecture.topology.created", topology)
        return topology

    async def update(
        self, tenant_id: str, topology_id: str, data: dict[str, Any]
    ) -> ArchitectureTopology:
        """Update a draft topology. Only drafts can be updated."""
        topology = await self._get_or_raise(tenant_id, topology_id)

        if topology.status != TopologyStatus.DRAFT:
            raise TopologyError(
                "Only draft topologies can be updated", "NOT_DRAFT"
            )

        for field in ("name", "description", "graph", "tags"):
            if field in data and data[field] is not None:
                setattr(topology, field, data[field])

        await self.db.flush()
        await self._audit(
            tenant_id, str(topology.created_by),
            "architecture.topology.updated", topology,
        )
        return topology

    async def publish(
        self, tenant_id: str, topology_id: str, user_id: str
    ) -> ArchitectureTopology:
        """Validate graph, check approval policy, publish or request approval."""
        topology = await self._get_or_raise(tenant_id, topology_id)

        if topology.status != TopologyStatus.DRAFT:
            raise TopologyError(
                "Only draft topologies can be published", "NOT_DRAFT"
            )

        if not topology.graph:
            raise TopologyError(
                "Cannot publish a topology without a graph", "NO_GRAPH"
            )

        # Validate graph
        result = await self._validator.validate(topology.graph)
        if not result.valid:
            error_msgs = "; ".join(e.message for e in result.errors)
            raise TopologyError(
                f"Graph validation failed: {error_msgs}", "VALIDATION_FAILED"
            )

        # Check approval policy
        try:
            from app.services.approval.service import ApprovalService
            approval_svc = ApprovalService(self.db)
            policy = await approval_svc.get_policy(tenant_id, "architecture:publish")

            if policy:
                request = await approval_svc.create_request(
                    tenant_id=tenant_id,
                    requester_id=user_id,
                    operation_type="architecture:publish",
                    resource_type="architecture_topology",
                    resource_id=str(topology.id),
                    context={
                        "topology_name": topology.name,
                        "topology_version": topology.version,
                    },
                )
                await self._notify_approval_requested(tenant_id, user_id, topology)
                logger.info(
                    "Approval request %s created for topology %s",
                    request.id, topology.id,
                )
                return topology
        except Exception:
            logger.debug("Approval service unavailable, publishing directly")

        # No approval policy — publish directly
        return await self._do_publish(tenant_id, topology, user_id)

    async def _do_publish(
        self, tenant_id: str, topology: ArchitectureTopology, user_id: str
    ) -> ArchitectureTopology:
        """Archive previous published version and publish the topology."""
        prev_published = await self.db.execute(
            select(ArchitectureTopology).where(
                ArchitectureTopology.tenant_id == tenant_id,
                ArchitectureTopology.name == topology.name,
                ArchitectureTopology.status == TopologyStatus.PUBLISHED,
                ArchitectureTopology.deleted_at.is_(None),
            )
        )
        for prev in prev_published.scalars().all():
            prev.status = TopologyStatus.ARCHIVED

        topology.version += 1
        topology.status = TopologyStatus.PUBLISHED

        await self.db.flush()
        await self._audit(tenant_id, user_id, "architecture.topology.published", topology)
        await self._notify_published(tenant_id, user_id, topology)
        return topology

    async def archive(
        self, tenant_id: str, topology_id: str
    ) -> ArchitectureTopology:
        """Archive a topology."""
        topology = await self._get_or_raise(tenant_id, topology_id)
        topology.status = TopologyStatus.ARCHIVED
        await self.db.flush()
        await self._audit(
            tenant_id, str(topology.created_by),
            "architecture.topology.archived", topology,
        )
        return topology

    async def get(
        self, tenant_id: str, topology_id: str
    ) -> ArchitectureTopology | None:
        """Get a topology by ID (tenant-scoped or system)."""
        result = await self.db.execute(
            select(ArchitectureTopology).where(
                ArchitectureTopology.id == topology_id,
                or_(
                    ArchitectureTopology.tenant_id == tenant_id,
                    ArchitectureTopology.tenant_id.is_(None),
                ),
                ArchitectureTopology.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        status: str | None = None,
        is_template: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ArchitectureTopology]:
        """List topologies for a tenant, including system templates."""
        query = (
            select(ArchitectureTopology)
            .where(
                or_(
                    ArchitectureTopology.tenant_id == tenant_id,
                    ArchitectureTopology.tenant_id.is_(None),
                ),
                ArchitectureTopology.deleted_at.is_(None),
            )
            .order_by(ArchitectureTopology.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if status:
            query = query.where(
                ArchitectureTopology.status == TopologyStatus(status)
            )

        if is_template is not None:
            query = query.where(ArchitectureTopology.is_template == is_template)

        if search:
            query = query.where(ArchitectureTopology.name.ilike(f"%{search}%"))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def clone(
        self, tenant_id: str, topology_id: str, created_by: str
    ) -> ArchitectureTopology:
        """Clone a topology as a new draft."""
        source = await self._get_or_raise(tenant_id, topology_id)

        clone = ArchitectureTopology(
            tenant_id=tenant_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            version=0,
            graph=copy.deepcopy(source.graph) if source.graph else None,
            status=TopologyStatus.DRAFT,
            is_template=False,
            is_system=False,
            tags=list(source.tags) if source.tags else None,
            created_by=created_by,
        )
        self.db.add(clone)
        await self.db.flush()

        await self._audit(tenant_id, created_by, "architecture.topology.cloned", clone)
        return clone

    async def delete(
        self, tenant_id: str, topology_id: str
    ) -> bool:
        """Soft delete a topology."""
        topology = await self._get_or_raise(tenant_id, topology_id)
        topology.deleted_at = datetime.now(UTC)
        await self.db.flush()
        await self._audit(
            tenant_id, str(topology.created_by),
            "architecture.topology.deleted", topology,
        )
        return True

    async def export_json(
        self, tenant_id: str, topology_id: str
    ) -> dict[str, Any]:
        """Export a topology as a portable JSON dict."""
        topology = await self._get_or_raise(tenant_id, topology_id)
        return {
            "name": topology.name,
            "description": topology.description,
            "graph": topology.graph,
            "tags": topology.tags,
            "version": topology.version,
            "is_template": topology.is_template,
        }

    async def export_yaml(
        self, tenant_id: str, topology_id: str
    ) -> str:
        """Export a topology as YAML."""
        data = await self.export_json(tenant_id, topology_id)
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    async def import_topology(
        self, tenant_id: str, created_by: str, data: dict[str, Any]
    ) -> ArchitectureTopology:
        """Import a topology from an exported JSON dict."""
        return await self.create(tenant_id, created_by, data)

    async def create_template(
        self, tenant_id: str, topology_id: str, created_by: str
    ) -> ArchitectureTopology:
        """Create a template from an existing topology."""
        source = await self._get_or_raise(tenant_id, topology_id)

        template = ArchitectureTopology(
            tenant_id=tenant_id,
            name=f"{source.name} (Template)",
            description=source.description,
            version=0,
            graph=copy.deepcopy(source.graph) if source.graph else None,
            status=TopologyStatus.DRAFT,
            is_template=True,
            is_system=False,
            tags=list(source.tags) if source.tags else None,
            created_by=created_by,
        )
        self.db.add(template)
        await self.db.flush()

        await self._audit(
            tenant_id, created_by,
            "architecture.template.created", template,
        )
        return template

    async def get_versions(
        self, tenant_id: str, name: str
    ) -> list[ArchitectureTopology]:
        """Get all versions of a topology by name."""
        result = await self.db.execute(
            select(ArchitectureTopology)
            .where(
                ArchitectureTopology.tenant_id == tenant_id,
                ArchitectureTopology.name == name,
                ArchitectureTopology.deleted_at.is_(None),
            )
            .order_by(ArchitectureTopology.version.desc())
        )
        return list(result.scalars().all())

    async def validate_graph(
        self, graph: dict[str, Any]
    ) -> Any:
        """Validate a topology graph without saving."""
        return await self._validator.validate(graph)

    @staticmethod
    def resolve_compartment_chain(
        graph: dict[str, Any], compartment_id: str
    ) -> list[dict[str, Any]]:
        """Walk parent chain for a compartment, returning innermost-first list."""
        compartments = graph.get("compartments", [])
        comp_map: dict[str, dict[str, Any]] = {}
        for c in compartments:
            cid = c.get("id")
            if cid:
                comp_map[cid] = c

        chain: list[dict[str, Any]] = []
        visited: set[str] = set()
        current = compartment_id
        while current and current in comp_map and current not in visited:
            visited.add(current)
            chain.append(comp_map[current])
            current = comp_map[current].get("parentCompartmentId")
        return chain

    @staticmethod
    def resolve_compartment_defaults(
        graph: dict[str, Any], compartment_id: str
    ) -> dict[str, Any]:
        """Merge defaults walking up the compartment chain (innermost wins)."""
        chain = TopologyService.resolve_compartment_chain(graph, compartment_id)
        merged: dict[str, Any] = {}
        # Walk outermost → innermost so innermost overrides
        for comp in reversed(chain):
            defaults = comp.get("defaults", {})
            if defaults:
                merged.update(defaults)
        return merged

    @staticmethod
    def get_deployment_order(graph: dict[str, Any]) -> list[list[str]]:
        """Topological sort of stacks by dependsOn into parallel groups."""
        stacks = graph.get("stacks", [])
        if not stacks:
            return []

        stack_map: dict[str, dict[str, Any]] = {}
        for s in stacks:
            sid = s.get("id")
            if sid:
                stack_map[sid] = s

        # Build in-degree map
        in_degree: dict[str, int] = {sid: 0 for sid in stack_map}
        adj: dict[str, list[str]] = {sid: [] for sid in stack_map}
        for sid, s in stack_map.items():
            for dep in s.get("dependsOn", []):
                if dep in stack_map:
                    adj[dep].append(sid)
                    in_degree[sid] += 1

        # Kahn's algorithm with parallel grouping
        groups: list[list[str]] = []
        ready = [sid for sid, deg in in_degree.items() if deg == 0]

        while ready:
            groups.append(sorted(ready))
            next_ready: list[str] = []
            for sid in ready:
                for neighbor in adj[sid]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_ready.append(neighbor)
            ready = next_ready

        return groups

    async def _get_or_raise(
        self, tenant_id: str, topology_id: str
    ) -> ArchitectureTopology:
        topology = await self.get(tenant_id, topology_id)
        if not topology:
            raise TopologyError(
                f"Topology '{topology_id}' not found", "NOT_FOUND"
            )
        return topology

    async def _audit(
        self, tenant_id: str, user_id: str, action: str, topology: ArchitectureTopology
    ) -> None:
        """Log audit event."""
        try:
            from app.services.audit.service import AuditService
            audit_svc = AuditService(self.db)
            await audit_svc.log(
                tenant_id=tenant_id,
                actor_id=user_id,
                action=action,
                resource_type="architecture_topology",
                resource_id=str(topology.id),
                new_values={"name": topology.name, "status": topology.status.value},
            )
        except Exception:
            logger.debug("Audit logging unavailable, skipping", exc_info=True)

    async def _notify_published(
        self, tenant_id: str, user_id: str, topology: ArchitectureTopology
    ) -> None:
        """Send notification when a topology is published."""
        try:
            from app.models.notification import NotificationCategory
            from app.services.notification.service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.send(
                tenant_id=tenant_id,
                user_ids=[user_id],
                category=NotificationCategory.SYSTEM,
                event_type="topology.published",
                title="Topology Published",
                body=f"Topology '{topology.name}' v{topology.version} has been published.",
                related_resource_type="architecture_topology",
                related_resource_id=str(topology.id),
            )
        except Exception:
            logger.debug("Notification service unavailable, skipping", exc_info=True)

    async def _notify_approval_requested(
        self, tenant_id: str, user_id: str, topology: ArchitectureTopology
    ) -> None:
        """Send notification when approval is requested."""
        try:
            from app.models.notification import NotificationCategory
            from app.services.notification.service import NotificationService
            notif_svc = NotificationService(self.db)
            await notif_svc.send(
                tenant_id=tenant_id,
                user_ids=[user_id],
                category=NotificationCategory.SYSTEM,
                event_type="topology.approval_requested",
                title="Topology Approval Requested",
                body=f"Topology '{topology.name}' has been submitted for approval.",
                related_resource_type="architecture_topology",
                related_resource_id=str(topology.id),
            )
        except Exception:
            logger.debug("Notification service unavailable, skipping", exc_info=True)
