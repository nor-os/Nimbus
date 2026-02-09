"""
Overview: CI class seeding — syncs semantic resource types to CI classes at runtime.
Architecture: Ensures system CI classes stay in sync with the semantic layer (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.ci_class, app.models.semantic_type
Concepts: New concrete semantic types automatically get a corresponding CI class. Existing
    classes are updated with the latest schema from the semantic type.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cmdb.ci_class import CIClass
from app.models.semantic_type import SemanticResourceType

logger = logging.getLogger(__name__)


async def sync_semantic_types_to_ci_classes(db: AsyncSession) -> int:
    """Create or update system CI classes from concrete semantic resource types.

    Returns the number of classes created or updated.
    """
    result = await db.execute(
        select(SemanticResourceType).where(
            SemanticResourceType.is_abstract.is_(False),
            SemanticResourceType.deleted_at.is_(None),
        )
    )
    semantic_types = result.scalars().all()

    existing_result = await db.execute(
        select(CIClass).where(
            CIClass.is_system.is_(True),
            CIClass.deleted_at.is_(None),
        )
    )
    existing_by_semantic_id = {
        c.semantic_type_id: c for c in existing_result.scalars().all()
    }

    count = 0
    for stype in semantic_types:
        existing = existing_by_semantic_id.get(stype.id)
        if existing:
            if (
                existing.schema != stype.properties_schema
                or existing.icon != stype.icon
                or existing.display_name != stype.display_name
            ):
                existing.schema = stype.properties_schema
                existing.icon = stype.icon
                existing.display_name = stype.display_name
                count += 1
        else:
            ci_class = CIClass(
                tenant_id=None,
                name=stype.name,
                display_name=stype.display_name,
                semantic_type_id=stype.id,
                schema=stype.properties_schema,
                icon=stype.icon,
                is_system=True,
                is_active=True,
            )
            db.add(ci_class)
            count += 1

    if count > 0:
        await db.flush()
        logger.info("Synced %d CI classes from semantic types", count)

    return count
