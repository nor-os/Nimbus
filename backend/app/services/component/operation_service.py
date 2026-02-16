"""
Overview: Component operation service — CRUD for day-2 operations declared on components.
Architecture: Component service layer (Section 11)
Dependencies: sqlalchemy, app.models.component
Concepts: Operations are workflow-backed day-2 actions on deployed resources. Each operation
    references a workflow definition that orchestrates the multi-step execution.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.component import ComponentOperation, EstimatedDowntime

logger = logging.getLogger(__name__)


class ComponentOperationService:
    """Service for managing component day-2 operations."""

    async def list_operations(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> list[ComponentOperation]:
        result = await db.execute(
            select(ComponentOperation)
            .where(
                ComponentOperation.component_id == component_id,
                ComponentOperation.deleted_at.is_(None),
            )
            .order_by(ComponentOperation.sort_order, ComponentOperation.name)
        )
        return list(result.scalars().all())

    async def get_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
    ) -> ComponentOperation | None:
        result = await db.execute(
            select(ComponentOperation).where(
                ComponentOperation.id == operation_id,
                ComponentOperation.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_operation(
        self,
        db: AsyncSession,
        *,
        component_id: uuid.UUID,
        name: str,
        display_name: str,
        workflow_definition_id: uuid.UUID,
        description: str | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        is_destructive: bool = False,
        requires_approval: bool = False,
        estimated_downtime: EstimatedDowntime = EstimatedDowntime.NONE,
        sort_order: int = 0,
    ) -> ComponentOperation:
        op = ComponentOperation(
            component_id=component_id,
            name=name,
            display_name=display_name,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            workflow_definition_id=workflow_definition_id,
            is_destructive=is_destructive,
            requires_approval=requires_approval,
            estimated_downtime=estimated_downtime,
            sort_order=sort_order,
        )
        db.add(op)
        await db.flush()
        await db.refresh(op)
        return op

    async def update_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
        **kwargs,
    ) -> ComponentOperation:
        op = await self.get_operation(db, operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found")

        allowed = {
            "name", "display_name", "description", "input_schema", "output_schema",
            "workflow_definition_id", "is_destructive", "requires_approval",
            "estimated_downtime", "sort_order",
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(op, key, value)

        await db.flush()
        await db.refresh(op)
        return op

    async def delete_operation(
        self,
        db: AsyncSession,
        operation_id: uuid.UUID,
    ) -> None:
        from sqlalchemy import func

        op = await self.get_operation(db, operation_id)
        if not op:
            raise ValueError(f"Operation '{operation_id}' not found")
        op.deleted_at = func.now()
        await db.flush()
