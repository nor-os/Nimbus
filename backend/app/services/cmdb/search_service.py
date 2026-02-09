"""
Overview: CMDB search service — full-text search, filters, and saved searches.
Architecture: Search and filtering for configuration items (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.*
Concepts: Full-text search across CI names/descriptions with filtering by class, compartment,
    lifecycle state, and tags. Saved searches persist user queries for reuse.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci import ConfigurationItem
from app.models.cmdb.ci_relationship import CIRelationship
from app.models.cmdb.saved_search import SavedSearch

logger = logging.getLogger(__name__)


class SearchServiceError(Exception):
    def __init__(self, message: str, code: str = "SEARCH_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SearchService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def search_cis(
        self,
        tenant_id: str,
        query: str | None = None,
        ci_class_id: str | None = None,
        compartment_id: str | None = None,
        lifecycle_state: str | None = None,
        tags: dict | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConfigurationItem], int]:
        """Search CIs with full-text query and filters."""
        stmt = select(ConfigurationItem).where(
            ConfigurationItem.tenant_id == tenant_id,
            ConfigurationItem.deleted_at.is_(None),
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    ConfigurationItem.name.ilike(pattern),
                    ConfigurationItem.description.ilike(pattern),
                    ConfigurationItem.cloud_resource_id.ilike(pattern),
                    ConfigurationItem.pulumi_urn.ilike(pattern),
                )
            )

        if ci_class_id:
            stmt = stmt.where(ConfigurationItem.ci_class_id == ci_class_id)
        if compartment_id:
            stmt = stmt.where(ConfigurationItem.compartment_id == compartment_id)
        if lifecycle_state:
            stmt = stmt.where(ConfigurationItem.lifecycle_state == lifecycle_state)
        if tags:
            for key, value in tags.items():
                stmt = stmt.where(
                    ConfigurationItem.tags[key].astext == str(value)
                )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ConfigurationItem.ci_class))
        stmt = stmt.order_by(ConfigurationItem.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def search_connected_cis(
        self,
        tenant_id: str,
        ci_id: str,
        query: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ConfigurationItem], int]:
        """Search CIs connected to a specific CI."""
        rel_stmt = select(CIRelationship).where(
            CIRelationship.tenant_id == tenant_id,
            CIRelationship.deleted_at.is_(None),
            or_(
                CIRelationship.source_ci_id == ci_id,
                CIRelationship.target_ci_id == ci_id,
            ),
        )
        rel_result = await self.db.execute(rel_stmt)
        relationships = list(rel_result.scalars().all())

        connected_ids = set()
        for rel in relationships:
            if str(rel.source_ci_id) != ci_id:
                connected_ids.add(rel.source_ci_id)
            if str(rel.target_ci_id) != ci_id:
                connected_ids.add(rel.target_ci_id)

        if not connected_ids:
            return [], 0

        stmt = select(ConfigurationItem).where(
            ConfigurationItem.tenant_id == tenant_id,
            ConfigurationItem.deleted_at.is_(None),
            ConfigurationItem.id.in_(connected_ids),
        )

        if query:
            pattern = f"%{query}%"
            stmt = stmt.where(
                or_(
                    ConfigurationItem.name.ilike(pattern),
                    ConfigurationItem.description.ilike(pattern),
                )
            )

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(ConfigurationItem.ci_class))
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    # ── Saved searches ────────────────────────────────────────────────

    async def save_search(
        self,
        tenant_id: str,
        user_id: str,
        name: str,
        query_text: str | None = None,
        filters: dict | None = None,
        sort_config: dict | None = None,
    ) -> SavedSearch:
        """Save a search query for later reuse."""
        saved = SavedSearch(
            tenant_id=tenant_id,
            user_id=user_id,
            name=name,
            query_text=query_text,
            filters=filters,
            sort_config=sort_config,
        )
        self.db.add(saved)
        await self.db.flush()
        return saved

    async def list_saved_searches(
        self,
        tenant_id: str,
        user_id: str,
    ) -> list[SavedSearch]:
        """List saved searches for a user."""
        result = await self.db.execute(
            select(SavedSearch)
            .where(
                SavedSearch.tenant_id == tenant_id,
                SavedSearch.user_id == user_id,
                SavedSearch.deleted_at.is_(None),
            )
            .order_by(SavedSearch.name)
        )
        return list(result.scalars().all())

    async def delete_saved_search(
        self,
        search_id: str,
        tenant_id: str,
        user_id: str,
    ) -> bool:
        """Soft-delete a saved search."""
        result = await self.db.execute(
            select(SavedSearch).where(
                SavedSearch.id == search_id,
                SavedSearch.tenant_id == tenant_id,
                SavedSearch.user_id == user_id,
                SavedSearch.deleted_at.is_(None),
            )
        )
        saved = result.scalar_one_or_none()
        if not saved:
            raise SearchServiceError("Saved search not found", "NOT_FOUND")

        saved.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True
