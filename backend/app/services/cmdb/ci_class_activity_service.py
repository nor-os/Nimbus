"""
Overview: CI class ↔ activity template association service — CRUD for configurable
    associations with relationship type suggestions.
Architecture: Catalog CI class / activity linkage service (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.ci_class_activity_association,
    app.models.semantic_type.SemanticRelationshipKind
Concepts: Manages tenant-scoped many-to-many associations between CI classes and activity
    templates. Provides relationship type suggestions seeded from semantic relationship kinds
    and extended with user-entered values.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import select, union_all
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.ci_class_activity_association import CIClassActivityAssociation
from app.models.cmdb.relationship_type import RelationshipType
from app.models.semantic_type import SemanticRelationshipKind

logger = logging.getLogger(__name__)


class CIClassActivityServiceError(Exception):
    def __init__(self, message: str, code: str = "ACTIVITY_ASSOC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CIClassActivityService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_for_ci_class(
        self, tenant_id: str, ci_class_id: str
    ) -> list[CIClassActivityAssociation]:
        result = await self.db.execute(
            select(CIClassActivityAssociation)
            .where(
                CIClassActivityAssociation.tenant_id == tenant_id,
                CIClassActivityAssociation.ci_class_id == ci_class_id,
                CIClassActivityAssociation.deleted_at.is_(None),
            )
            .order_by(CIClassActivityAssociation.created_at)
        )
        return list(result.scalars().all())

    async def list_for_activity_template(
        self, tenant_id: str, activity_template_id: str
    ) -> list[CIClassActivityAssociation]:
        result = await self.db.execute(
            select(CIClassActivityAssociation)
            .where(
                CIClassActivityAssociation.tenant_id == tenant_id,
                CIClassActivityAssociation.activity_template_id == activity_template_id,
                CIClassActivityAssociation.deleted_at.is_(None),
            )
            .order_by(CIClassActivityAssociation.created_at)
        )
        return list(result.scalars().all())

    async def create_association(
        self, tenant_id: str, data: dict
    ) -> CIClassActivityAssociation:
        # Check for existing (including soft-deleted for uniqueness)
        existing = await self.db.execute(
            select(CIClassActivityAssociation).where(
                CIClassActivityAssociation.tenant_id == tenant_id,
                CIClassActivityAssociation.ci_class_id == data["ci_class_id"],
                CIClassActivityAssociation.activity_template_id == data["activity_template_id"],
                CIClassActivityAssociation.relationship_type == data.get("relationship_type"),
                CIClassActivityAssociation.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise CIClassActivityServiceError(
                "This association already exists", "DUPLICATE"
            )

        assoc = CIClassActivityAssociation(
            tenant_id=tenant_id,
            ci_class_id=data["ci_class_id"],
            activity_template_id=data["activity_template_id"],
            relationship_type=data.get("relationship_type"),
            relationship_type_id=data.get("relationship_type_id"),
        )
        self.db.add(assoc)
        await self.db.flush()
        return assoc

    async def delete_association(
        self, association_id: str, tenant_id: str
    ) -> bool:
        result = await self.db.execute(
            select(CIClassActivityAssociation).where(
                CIClassActivityAssociation.id == association_id,
                CIClassActivityAssociation.tenant_id == tenant_id,
                CIClassActivityAssociation.deleted_at.is_(None),
            )
        )
        assoc = result.scalar_one_or_none()
        if not assoc:
            raise CIClassActivityServiceError(
                "Association not found", "NOT_FOUND"
            )
        assoc.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_operational_relationship_types(self) -> list[RelationshipType]:
        """Return relationship types applicable to operational (activity) context."""
        result = await self.db.execute(
            select(RelationshipType).where(
                RelationshipType.domain.in_(["operational", "both"]),
                RelationshipType.deleted_at.is_(None),
            ).order_by(RelationshipType.name)
        )
        return list(result.scalars().all())

    async def list_relationship_type_suggestions(
        self, tenant_id: str
    ) -> list[str]:
        """Union of semantic relationship kind display names and distinct existing types."""
        # Semantic kinds
        semantic_stmt = select(SemanticRelationshipKind.display_name).where(
            SemanticRelationshipKind.deleted_at.is_(None)
        )

        # Existing user-entered types
        existing_stmt = (
            select(CIClassActivityAssociation.relationship_type)
            .where(
                CIClassActivityAssociation.tenant_id == tenant_id,
                CIClassActivityAssociation.deleted_at.is_(None),
                CIClassActivityAssociation.relationship_type.isnot(None),
                CIClassActivityAssociation.relationship_type != "",
            )
            .distinct()
        )

        combined = union_all(semantic_stmt, existing_stmt).subquery()
        result = await self.db.execute(
            select(combined.c[0]).distinct().order_by(combined.c[0])
        )
        return [str(row) for row in result.scalars().all()]
