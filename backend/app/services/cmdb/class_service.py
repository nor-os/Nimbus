"""
Overview: CI class service — CRUD for CI class definitions with system record protection.
Architecture: Service layer for CI class management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.ci_class
Concepts: System CI classes are seeded from semantic types and cannot be deleted. Custom classes
    are tenant-scoped. Class hierarchy supports single inheritance.
"""

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci_class import CIAttributeDefinition, CIClass

logger = logging.getLogger(__name__)


class ClassServiceError(Exception):
    def __init__(self, message: str, code: str = "CLASS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ClassService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_class(self, class_id: uuid.UUID) -> CIClass | None:
        """Get a CI class by ID."""
        result = await self.db.execute(
            select(CIClass)
            .where(CIClass.id == class_id, CIClass.deleted_at.is_(None))
            .options(selectinload(CIClass.attribute_definitions))
        )
        return result.scalar_one_or_none()

    async def list_classes(
        self,
        tenant_id: str | None = None,
        include_system: bool = True,
        active_only: bool = True,
    ) -> list[CIClass]:
        """List CI classes, optionally filtered by tenant and system status."""
        stmt = select(CIClass).where(CIClass.deleted_at.is_(None))
        if active_only:
            stmt = stmt.where(CIClass.is_active.is_(True))

        if tenant_id and include_system:
            stmt = stmt.where(
                (CIClass.tenant_id == tenant_id) | (CIClass.tenant_id.is_(None))
            )
        elif tenant_id:
            stmt = stmt.where(CIClass.tenant_id == tenant_id)
        elif include_system:
            stmt = stmt.where(CIClass.tenant_id.is_(None))

        stmt = stmt.options(selectinload(CIClass.attribute_definitions))
        stmt = stmt.order_by(CIClass.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def create_class(self, tenant_id: str, data: dict) -> CIClass:
        """Create a custom CI class for a tenant."""
        existing = await self.db.execute(
            select(CIClass).where(
                CIClass.tenant_id == tenant_id,
                CIClass.name == data["name"],
                CIClass.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ClassServiceError(
                f"CI class '{data['name']}' already exists", "CLASS_EXISTS"
            )

        ci_class = CIClass(
            tenant_id=tenant_id,
            name=data["name"],
            display_name=data["display_name"],
            parent_class_id=data.get("parent_class_id"),
            schema=data.get("schema"),
            icon=data.get("icon"),
            is_system=False,
            is_active=True,
        )
        self.db.add(ci_class)
        await self.db.flush()
        return ci_class

    async def update_class(
        self, class_id: uuid.UUID, tenant_id: str, data: dict
    ) -> CIClass:
        """Update a CI class. System classes can only update display_name and icon."""
        ci_class = await self.get_class(class_id)
        if not ci_class:
            raise ClassServiceError("CI class not found", "CLASS_NOT_FOUND")

        if ci_class.is_system:
            allowed = {"display_name", "icon", "is_active"}
            for key in data:
                if key not in allowed:
                    raise ClassServiceError(
                        f"Cannot modify '{key}' on system CI class",
                        "SYSTEM_RECORD",
                    )

        if not ci_class.is_system and ci_class.tenant_id != uuid.UUID(tenant_id):
            raise ClassServiceError("Not authorized to modify this class", "UNAUTHORIZED")

        for key, value in data.items():
            if hasattr(ci_class, key):
                setattr(ci_class, key, value)

        await self.db.flush()
        return ci_class

    async def delete_class(self, class_id: uuid.UUID, tenant_id: str) -> bool:
        """Soft-delete a CI class. System classes cannot be deleted."""
        ci_class = await self.get_class(class_id)
        if not ci_class:
            raise ClassServiceError("CI class not found", "CLASS_NOT_FOUND")
        if ci_class.is_system:
            raise ClassServiceError(
                "Cannot delete system CI class", "SYSTEM_RECORD"
            )
        if ci_class.tenant_id != uuid.UUID(tenant_id):
            raise ClassServiceError("Not authorized to delete this class", "UNAUTHORIZED")

        ci_class.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def add_attribute_definition(
        self, class_id: uuid.UUID, data: dict
    ) -> CIAttributeDefinition:
        """Add a custom attribute definition to a CI class."""
        attr_def = CIAttributeDefinition(
            ci_class_id=class_id,
            name=data["name"],
            display_name=data["display_name"],
            data_type=data["data_type"],
            is_required=data.get("is_required", False),
            default_value=data.get("default_value"),
            validation_rules=data.get("validation_rules"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(attr_def)
        await self.db.flush()
        return attr_def
