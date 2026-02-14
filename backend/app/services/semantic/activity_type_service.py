"""
Overview: Semantic activity type service — CRUD for abstract activity archetypes.
Architecture: Service layer for semantic activity type operations (Section 5)
Dependencies: sqlalchemy, app.models.semantic_activity_type
Concepts: CRUD operations with is_system protection. System records cannot be deleted or renamed.
    No tenant scoping — semantic activity types are global.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.semantic_activity_type import SemanticActivityType

logger = logging.getLogger(__name__)


class ActivityTypeServiceError(Exception):
    def __init__(self, message: str, code: str = "ACTIVITY_TYPE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class ActivityTypeService:
    """Service for querying and managing semantic activity types."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_activity_types(
        self, category: str | None = None
    ) -> list[SemanticActivityType]:
        """List all activity types, optionally filtered by category."""
        stmt = (
            select(SemanticActivityType)
            .where(SemanticActivityType.deleted_at.is_(None))
            .order_by(SemanticActivityType.sort_order, SemanticActivityType.name)
        )
        if category:
            stmt = stmt.where(SemanticActivityType.category == category)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_activity_type(self, activity_type_id: str) -> SemanticActivityType | None:
        """Get a single activity type by ID."""
        result = await self.db.execute(
            select(SemanticActivityType).where(
                SemanticActivityType.id == activity_type_id,
                SemanticActivityType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_activity_type(self, data: dict) -> SemanticActivityType:
        """Create a new activity type."""
        # Check for duplicate name
        existing = await self.db.execute(
            select(SemanticActivityType).where(
                SemanticActivityType.name == data["name"],
                SemanticActivityType.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ActivityTypeServiceError(
                f"Activity type '{data['name']}' already exists", "DUPLICATE"
            )

        at = SemanticActivityType(
            name=data["name"],
            display_name=data["display_name"],
            category=data.get("category"),
            description=data.get("description"),
            icon=data.get("icon"),
            applicable_semantic_categories=data.get("applicable_semantic_categories"),
            applicable_semantic_types=data.get("applicable_semantic_types"),
            default_relationship_kind_id=data.get("default_relationship_kind_id"),
            properties_schema=data.get("properties_schema"),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(at)
        await self.db.flush()
        return at

    async def update_activity_type(
        self, activity_type_id: str, data: dict
    ) -> SemanticActivityType | None:
        """Update an activity type."""
        at = await self.get_activity_type(activity_type_id)
        if not at:
            raise ActivityTypeServiceError("Activity type not found", "NOT_FOUND")

        if at.is_system and "name" in data and data["name"] != at.name:
            raise ActivityTypeServiceError(
                "Cannot rename a system activity type", "SYSTEM_RECORD"
            )

        for key in (
            "display_name", "category", "description", "icon",
            "applicable_semantic_categories", "applicable_semantic_types",
            "default_relationship_kind_id", "properties_schema", "sort_order",
        ):
            if key in data:
                setattr(at, key, data[key])

        at.updated_at = datetime.now(UTC)
        await self.db.flush()
        return at

    async def delete_activity_type(self, activity_type_id: str) -> bool:
        """Soft-delete an activity type."""
        at = await self.get_activity_type(activity_type_id)
        if not at:
            raise ActivityTypeServiceError("Activity type not found", "NOT_FOUND")

        if at.is_system:
            raise ActivityTypeServiceError(
                "Cannot delete a system activity type", "SYSTEM_RECORD"
            )

        at.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_applicable_types(
        self,
        semantic_category: str | None = None,
        semantic_type: str | None = None,
    ) -> list[SemanticActivityType]:
        """Get activity types applicable to a given semantic category/type."""
        all_types = await self.list_activity_types()
        results = []
        for at in all_types:
            # If no constraints, it's universally applicable
            if not at.applicable_semantic_categories and not at.applicable_semantic_types:
                results.append(at)
                continue
            # Check category
            if semantic_category and at.applicable_semantic_categories:
                if semantic_category in at.applicable_semantic_categories:
                    results.append(at)
                    continue
            # Check type
            if semantic_type and at.applicable_semantic_types:
                if semantic_type in at.applicable_semantic_types:
                    results.append(at)
                    continue
            # If no filter provided but constraints exist, include all
            if not semantic_category and not semantic_type:
                results.append(at)
        return results
