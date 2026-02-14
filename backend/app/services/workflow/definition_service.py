"""
Overview: Workflow definition service — CRUD, versioning, publish, clone, export/import.
Architecture: Service layer for workflow definition management (Section 5)
Dependencies: sqlalchemy, app.models.workflow_definition, app.services.workflow.graph_validator
Concepts: Definition lifecycle, draft/active/archived, versioning, graph validation
"""

from __future__ import annotations

import copy
import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workflow_definition import WorkflowDefinition, WorkflowDefinitionStatus, WorkflowType
from app.services.workflow.graph_validator import GraphValidator

logger = logging.getLogger(__name__)


class WorkflowDefinitionError(Exception):
    def __init__(self, message: str, code: str = "DEFINITION_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class WorkflowDefinitionService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._validator = GraphValidator()

    async def create(
        self, tenant_id: str, created_by: str, data: dict[str, Any]
    ) -> WorkflowDefinition:
        """Create a new draft workflow definition at version 0."""
        wf_type_str = data.get("workflow_type", "AUTOMATION")
        wf_type = WorkflowType(wf_type_str) if isinstance(wf_type_str, str) else wf_type_str

        definition = WorkflowDefinition(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            version=0,
            graph=data.get("graph"),
            status=WorkflowDefinitionStatus.DRAFT,
            created_by=created_by,
            timeout_seconds=data.get("timeout_seconds", 3600),
            max_concurrent=data.get("max_concurrent", 10),
            workflow_type=wf_type,
            source_topology_id=data.get("source_topology_id"),
            is_system=data.get("is_system", False),
        )
        self.db.add(definition)
        await self.db.flush()
        return definition

    async def update(
        self, tenant_id: str, definition_id: str, data: dict[str, Any]
    ) -> WorkflowDefinition:
        """Update a draft definition. Only drafts can be updated."""
        definition = await self._get_or_raise(tenant_id, definition_id)

        if definition.status != WorkflowDefinitionStatus.DRAFT:
            raise WorkflowDefinitionError(
                "Only draft definitions can be updated", "NOT_DRAFT"
            )

        for field in ("name", "description", "graph", "timeout_seconds", "max_concurrent"):
            if field in data and data[field] is not None:
                setattr(definition, field, data[field])

        await self.db.flush()
        return definition

    async def publish(
        self, tenant_id: str, definition_id: str
    ) -> WorkflowDefinition:
        """Validate graph, increment version, set ACTIVE, archive previous version."""
        definition = await self._get_or_raise(tenant_id, definition_id)

        if definition.status != WorkflowDefinitionStatus.DRAFT:
            raise WorkflowDefinitionError(
                "Only draft definitions can be published", "NOT_DRAFT"
            )

        if not definition.graph:
            raise WorkflowDefinitionError(
                "Cannot publish a definition without a graph", "NO_GRAPH"
            )

        # Validate graph
        result = self._validator.validate(definition.graph)
        if not result.valid:
            error_msgs = "; ".join(e.message for e in result.errors)
            raise WorkflowDefinitionError(
                f"Graph validation failed: {error_msgs}", "VALIDATION_FAILED"
            )

        # Archive previous active version with same name
        prev_active = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.name == definition.name,
                WorkflowDefinition.status == WorkflowDefinitionStatus.ACTIVE,
                WorkflowDefinition.deleted_at.is_(None),
            )
        )
        for prev in prev_active.scalars().all():
            prev.status = WorkflowDefinitionStatus.ARCHIVED

        # Increment version and activate
        definition.version += 1
        definition.status = WorkflowDefinitionStatus.ACTIVE

        await self.db.flush()
        return definition

    async def archive(
        self, tenant_id: str, definition_id: str
    ) -> WorkflowDefinition:
        """Archive a definition."""
        definition = await self._get_or_raise(tenant_id, definition_id)
        definition.status = WorkflowDefinitionStatus.ARCHIVED
        await self.db.flush()
        return definition

    async def get(
        self, tenant_id: str, definition_id: str
    ) -> WorkflowDefinition | None:
        """Get a definition by ID."""
        result = await self.db.execute(
            select(WorkflowDefinition).where(
                WorkflowDefinition.id == definition_id,
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        status: str | None = None,
        workflow_type: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[WorkflowDefinition]:
        """List definitions for a tenant, optionally filtered by status and/or workflow_type."""
        query = (
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.deleted_at.is_(None),
            )
            .order_by(WorkflowDefinition.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )

        if status:
            query = query.where(
                WorkflowDefinition.status == WorkflowDefinitionStatus(status)
            )

        if workflow_type:
            query = query.where(
                WorkflowDefinition.workflow_type == WorkflowType(workflow_type)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def list_by_topology(
        self, tenant_id: str, topology_id: str
    ) -> list[WorkflowDefinition]:
        """List deployment workflows linked to a specific topology."""
        result = await self.db.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.source_topology_id == topology_id,
                WorkflowDefinition.deleted_at.is_(None),
            )
            .order_by(WorkflowDefinition.updated_at.desc())
        )
        return list(result.scalars().all())

    async def clone(
        self, tenant_id: str, definition_id: str, created_by: str
    ) -> WorkflowDefinition:
        """Clone a definition as a new draft."""
        source = await self._get_or_raise(tenant_id, definition_id)

        clone = WorkflowDefinition(
            tenant_id=tenant_id,
            name=f"{source.name} (Copy)",
            description=source.description,
            version=0,
            graph=copy.deepcopy(source.graph) if source.graph else None,
            status=WorkflowDefinitionStatus.DRAFT,
            created_by=created_by,
            timeout_seconds=source.timeout_seconds,
            max_concurrent=source.max_concurrent,
        )
        self.db.add(clone)
        await self.db.flush()
        return clone

    async def delete(
        self, tenant_id: str, definition_id: str
    ) -> bool:
        """Soft delete a definition."""
        definition = await self._get_or_raise(tenant_id, definition_id)
        definition.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_versions(
        self, tenant_id: str, name: str
    ) -> list[WorkflowDefinition]:
        """Get all versions of a definition by name."""
        result = await self.db.execute(
            select(WorkflowDefinition)
            .where(
                WorkflowDefinition.tenant_id == tenant_id,
                WorkflowDefinition.name == name,
                WorkflowDefinition.deleted_at.is_(None),
            )
            .order_by(WorkflowDefinition.version.desc())
        )
        return list(result.scalars().all())

    async def export_definition(
        self, tenant_id: str, definition_id: str
    ) -> dict[str, Any]:
        """Export a definition as a portable JSON dict."""
        definition = await self._get_or_raise(tenant_id, definition_id)
        return {
            "name": definition.name,
            "description": definition.description,
            "graph": definition.graph,
            "timeout_seconds": definition.timeout_seconds,
            "max_concurrent": definition.max_concurrent,
        }

    async def import_definition(
        self, tenant_id: str, created_by: str, data: dict[str, Any]
    ) -> WorkflowDefinition:
        """Import a definition from an exported JSON dict."""
        return await self.create(tenant_id, created_by, data)

    async def _get_or_raise(
        self, tenant_id: str, definition_id: str
    ) -> WorkflowDefinition:
        definition = await self.get(tenant_id, definition_id)
        if not definition:
            raise WorkflowDefinitionError(
                f"Workflow definition '{definition_id}' not found", "NOT_FOUND"
            )
        return definition
