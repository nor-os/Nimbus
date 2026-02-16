"""
Overview: Semantic layer service — queries and manages semantic types, categories, relationship
    kinds, and providers.
Architecture: Service layer for semantic catalog operations (Section 5)
Dependencies: sqlalchemy, app.models.semantic_type
Concepts: CRUD operations with is_system protection. System records cannot be deleted or renamed.
    No tenant scoping — semantic types are global.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.semantic_type import (
    SemanticCategory,
    SemanticProvider,
    SemanticRelationshipKind,
    SemanticResourceType,
)

logger = logging.getLogger(__name__)


class SemanticServiceError(Exception):
    """Base error for semantic service operations."""


class SystemRecordError(SemanticServiceError):
    """Raised when trying to delete or rename a system record."""


class DuplicateNameError(SemanticServiceError):
    """Raised when a name conflicts with an existing record."""


class ForeignKeyError(SemanticServiceError):
    """Raised when a referenced record does not exist."""


class SemanticService:
    """Service for querying and managing the semantic type catalog."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Categories (read) -------------------------------------------------

    async def list_categories(self) -> list[SemanticCategory]:
        """List all semantic categories with their types."""
        types_path = selectinload(SemanticCategory.types)
        children_path = types_path.selectinload(SemanticResourceType.children)
        result = await self.db.execute(
            select(SemanticCategory)
            .where(SemanticCategory.deleted_at.is_(None))
            .options(
                types_path.joinedload(SemanticResourceType.category_rel),
                types_path.joinedload(SemanticResourceType.parent_type),
                children_path.joinedload(SemanticResourceType.category_rel),
                children_path.joinedload(SemanticResourceType.parent_type),
                children_path.selectinload(SemanticResourceType.children),
            )
            .order_by(SemanticCategory.sort_order)
        )
        return list(result.scalars().unique().all())

    async def get_category(self, category_id: uuid.UUID) -> SemanticCategory | None:
        """Get a single category by ID."""
        result = await self.db.execute(
            select(SemanticCategory).where(
                SemanticCategory.id == category_id,
                SemanticCategory.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # -- Categories (write) ------------------------------------------------

    async def create_category(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
        icon: str | None = None,
        sort_order: int = 0,
    ) -> SemanticCategory:
        """Create a new semantic category."""
        existing = await self._get_category_by_name(name)
        if existing:
            raise DuplicateNameError(f"Category with name '{name}' already exists")

        category = SemanticCategory(
            name=name,
            display_name=display_name,
            description=description,
            icon=icon,
            sort_order=sort_order,
            is_system=False,
        )
        self.db.add(category)
        await self.db.flush()
        return category

    async def update_category(
        self, category_id: uuid.UUID, **kwargs: object
    ) -> SemanticCategory | None:
        """Update a category. System records cannot have their name changed."""
        category = await self.get_category(category_id)
        if not category:
            return None

        if category.is_system and "name" in kwargs:
            raise SystemRecordError("Cannot rename a system category")

        for key, value in kwargs.items():
            if hasattr(category, key):
                setattr(category, key, value)
        await self.db.flush()
        return category

    async def delete_category(self, category_id: uuid.UUID) -> bool:
        """Soft-delete a category. System records cannot be deleted."""
        category = await self.get_category(category_id)
        if not category:
            return False

        if category.is_system:
            raise SystemRecordError("Cannot delete a system category")

        category.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def _get_category_by_name(self, name: str) -> SemanticCategory | None:
        result = await self.db.execute(
            select(SemanticCategory).where(
                SemanticCategory.name == name,
                SemanticCategory.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # -- Types (read) ------------------------------------------------------

    async def list_types(
        self,
        category: str | None = None,
        is_abstract: bool | None = None,
        infrastructure_only: bool | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[SemanticResourceType], int]:
        """List semantic types with filtering and pagination."""
        conditions = [SemanticResourceType.deleted_at.is_(None)]

        if category:
            conditions.append(
                SemanticResourceType.category_id.in_(
                    select(SemanticCategory.id).where(
                        SemanticCategory.name == category,
                        SemanticCategory.deleted_at.is_(None),
                    )
                )
            )

        if infrastructure_only:
            conditions.append(
                SemanticResourceType.category_id.in_(
                    select(SemanticCategory.id).where(
                        SemanticCategory.is_infrastructure.is_(True),
                        SemanticCategory.deleted_at.is_(None),
                    )
                )
            )

        if is_abstract is not None:
            conditions.append(SemanticResourceType.is_abstract == is_abstract)

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    SemanticResourceType.name.ilike(pattern),
                    SemanticResourceType.display_name.ilike(pattern),
                    SemanticResourceType.description.ilike(pattern),
                )
            )

        stmt = select(SemanticResourceType).where(*conditions)

        # Count
        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        # Fetch with eager loading for async safety
        children_path = selectinload(SemanticResourceType.children)
        result = await self.db.execute(
            stmt.order_by(
                SemanticResourceType.sort_order,
                SemanticResourceType.name,
            )
            .offset(offset)
            .limit(limit)
            .options(
                joinedload(SemanticResourceType.category_rel),
                joinedload(SemanticResourceType.parent_type),
                children_path.joinedload(SemanticResourceType.category_rel),
                children_path.joinedload(SemanticResourceType.parent_type),
                children_path.selectinload(SemanticResourceType.children),
            )
        )
        items = list(result.scalars().unique().all())
        return items, total

    async def get_type(self, type_id: uuid.UUID) -> SemanticResourceType | None:
        """Get a single type by ID."""
        result = await self.db.execute(
            select(SemanticResourceType).where(
                SemanticResourceType.id == type_id,
                SemanticResourceType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_type_by_name(self, name: str) -> SemanticResourceType | None:
        """Get a single type by name."""
        result = await self.db.execute(
            select(SemanticResourceType).where(
                SemanticResourceType.name == name,
                SemanticResourceType.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_type_with_mappings(
        self, type_id: uuid.UUID
    ) -> SemanticResourceType | None:
        """Get a type with its children eagerly loaded."""
        children_path = selectinload(SemanticResourceType.children)
        result = await self.db.execute(
            select(SemanticResourceType)
            .where(
                SemanticResourceType.id == type_id,
                SemanticResourceType.deleted_at.is_(None),
            )
            .options(
                joinedload(SemanticResourceType.category_rel),
                joinedload(SemanticResourceType.parent_type),
                children_path.joinedload(SemanticResourceType.category_rel),
                children_path.joinedload(SemanticResourceType.parent_type),
                children_path.selectinload(SemanticResourceType.children),
            )
        )
        return result.scalar_one_or_none()

    async def search_types(self, query: str) -> list[SemanticResourceType]:
        """Search types by name, display_name, or description."""
        pattern = f"%{query}%"
        result = await self.db.execute(
            select(SemanticResourceType)
            .where(
                SemanticResourceType.deleted_at.is_(None),
                or_(
                    SemanticResourceType.name.ilike(pattern),
                    SemanticResourceType.display_name.ilike(pattern),
                    SemanticResourceType.description.ilike(pattern),
                ),
            )
            .order_by(SemanticResourceType.sort_order, SemanticResourceType.name)
        )
        return list(result.scalars().unique().all())

    # -- Types (write) -----------------------------------------------------

    async def create_type(
        self,
        name: str,
        display_name: str,
        category_id: uuid.UUID,
        description: str | None = None,
        icon: str | None = None,
        is_abstract: bool = False,
        parent_type_id: uuid.UUID | None = None,
        properties_schema: list | None = None,
        allowed_relationship_kinds: list | None = None,
        sort_order: int = 0,
    ) -> SemanticResourceType:
        """Create a new semantic resource type."""
        existing = await self.get_type_by_name(name)
        if existing:
            raise DuplicateNameError(f"Type with name '{name}' already exists")

        cat = await self.get_category(category_id)
        if not cat:
            raise ForeignKeyError(f"Category '{category_id}' does not exist")

        if parent_type_id:
            parent = await self.get_type(parent_type_id)
            if not parent:
                raise ForeignKeyError(f"Parent type '{parent_type_id}' does not exist")

        stype = SemanticResourceType(
            name=name,
            display_name=display_name,
            category_id=category_id,
            description=description,
            icon=icon,
            is_abstract=is_abstract,
            parent_type_id=parent_type_id,
            properties_schema=properties_schema,
            allowed_relationship_kinds=allowed_relationship_kinds,
            sort_order=sort_order,
            is_system=False,
        )
        self.db.add(stype)
        await self.db.flush()

        # Reload with relationships
        return await self.get_type_with_mappings(stype.id)  # type: ignore[return-value]

    async def update_type(
        self, type_id: uuid.UUID, **kwargs: object
    ) -> SemanticResourceType | None:
        """Update a resource type. System records cannot have their name changed."""
        stype = await self.get_type(type_id)
        if not stype:
            return None

        if stype.is_system and "name" in kwargs:
            raise SystemRecordError("Cannot rename a system type")

        # Validate FK references if being changed
        if "category_id" in kwargs and kwargs["category_id"] is not None:
            cat = await self.get_category(kwargs["category_id"])  # type: ignore[arg-type]
            if not cat:
                raise ForeignKeyError(f"Category '{kwargs['category_id']}' does not exist")

        if "parent_type_id" in kwargs and kwargs["parent_type_id"] is not None:
            parent = await self.get_type(kwargs["parent_type_id"])  # type: ignore[arg-type]
            if not parent:
                raise ForeignKeyError(
                    f"Parent type '{kwargs['parent_type_id']}' does not exist"
                )

        for key, value in kwargs.items():
            if hasattr(stype, key):
                setattr(stype, key, value)
        await self.db.flush()

        # Reload with relationships
        return await self.get_type_with_mappings(type_id)

    async def delete_type(self, type_id: uuid.UUID) -> bool:
        """Soft-delete a resource type. System records cannot be deleted."""
        stype = await self.get_type(type_id)
        if not stype:
            return False

        if stype.is_system:
            raise SystemRecordError("Cannot delete a system type")

        stype.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -- Relationship kinds (read) -----------------------------------------

    async def list_relationship_kinds(self) -> list[SemanticRelationshipKind]:
        """List all relationship kinds."""
        result = await self.db.execute(
            select(SemanticRelationshipKind)
            .where(SemanticRelationshipKind.deleted_at.is_(None))
            .order_by(SemanticRelationshipKind.name)
        )
        return list(result.scalars().all())

    async def get_relationship_kind(
        self, kind_id: uuid.UUID
    ) -> SemanticRelationshipKind | None:
        """Get a single relationship kind by ID."""
        result = await self.db.execute(
            select(SemanticRelationshipKind).where(
                SemanticRelationshipKind.id == kind_id,
                SemanticRelationshipKind.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # -- Relationship kinds (write) ----------------------------------------

    async def create_relationship_kind(
        self,
        name: str,
        display_name: str,
        inverse_name: str,
        description: str | None = None,
    ) -> SemanticRelationshipKind:
        """Create a new relationship kind."""
        existing = await self._get_relationship_kind_by_name(name)
        if existing:
            raise DuplicateNameError(
                f"Relationship kind with name '{name}' already exists"
            )

        kind = SemanticRelationshipKind(
            name=name,
            display_name=display_name,
            description=description,
            inverse_name=inverse_name,
            is_system=False,
        )
        self.db.add(kind)
        await self.db.flush()
        return kind

    async def update_relationship_kind(
        self, kind_id: uuid.UUID, **kwargs: object
    ) -> SemanticRelationshipKind | None:
        """Update a relationship kind. System records cannot have their name changed."""
        kind = await self.get_relationship_kind(kind_id)
        if not kind:
            return None

        if kind.is_system and "name" in kwargs:
            raise SystemRecordError("Cannot rename a system relationship kind")

        for key, value in kwargs.items():
            if hasattr(kind, key):
                setattr(kind, key, value)
        await self.db.flush()
        return kind

    async def delete_relationship_kind(self, kind_id: uuid.UUID) -> bool:
        """Soft-delete a relationship kind. System records cannot be deleted."""
        kind = await self.get_relationship_kind(kind_id)
        if not kind:
            return False

        if kind.is_system:
            raise SystemRecordError("Cannot delete a system relationship kind")

        kind.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    async def _get_relationship_kind_by_name(
        self, name: str
    ) -> SemanticRelationshipKind | None:
        result = await self.db.execute(
            select(SemanticRelationshipKind).where(
                SemanticRelationshipKind.name == name,
                SemanticRelationshipKind.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # -- Providers (read) --------------------------------------------------

    async def list_providers(self) -> list[SemanticProvider]:
        """List all providers."""
        result = await self.db.execute(
            select(SemanticProvider)
            .where(SemanticProvider.deleted_at.is_(None))
            .order_by(SemanticProvider.name)
        )
        return list(result.scalars().unique().all())

    async def get_provider(self, provider_id: uuid.UUID) -> SemanticProvider | None:
        """Get a single provider by ID."""
        result = await self.db.execute(
            select(SemanticProvider)
            .where(
                SemanticProvider.id == provider_id,
                SemanticProvider.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_provider_by_name(self, name: str) -> SemanticProvider | None:
        """Get a single provider by name."""
        result = await self.db.execute(
            select(SemanticProvider).where(
                SemanticProvider.name == name,
                SemanticProvider.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    # -- Providers (write) -------------------------------------------------

    async def create_provider(
        self,
        name: str,
        display_name: str,
        description: str | None = None,
        icon: str | None = None,
        provider_type: str = "custom",
        website_url: str | None = None,
        documentation_url: str | None = None,
    ) -> SemanticProvider:
        """Create a new provider."""
        existing = await self.get_provider_by_name(name)
        if existing:
            raise DuplicateNameError(f"Provider with name '{name}' already exists")

        provider = SemanticProvider(
            name=name,
            display_name=display_name,
            description=description,
            icon=icon,
            provider_type=provider_type,
            website_url=website_url,
            documentation_url=documentation_url,
            is_system=False,
        )
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def update_provider(
        self, provider_id: uuid.UUID, **kwargs: object
    ) -> SemanticProvider | None:
        """Update a provider. System records cannot have their name changed."""
        provider = await self.get_provider(provider_id)
        if not provider:
            return None

        if provider.is_system and "name" in kwargs:
            raise SystemRecordError("Cannot rename a system provider")

        for key, value in kwargs.items():
            if hasattr(provider, key):
                setattr(provider, key, value)
        await self.db.flush()
        return provider

    async def delete_provider(self, provider_id: uuid.UUID) -> bool:
        """Soft-delete a provider. System records cannot be deleted."""
        provider = await self.get_provider(provider_id)
        if not provider:
            return False

        if provider.is_system:
            raise SystemRecordError("Cannot delete a system provider")

        provider.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
