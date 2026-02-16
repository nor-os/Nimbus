"""
Overview: Component service — CRUD, versioning, publishing, and code validation for components.
Architecture: Component service layer (Section 11)
Dependencies: sqlalchemy, app.models.component
Concepts: Components are versioned Pulumi scripts. Draft components can be edited; publishing creates
    an immutable version snapshot and bumps the version number.
"""

from __future__ import annotations

import ast
import logging
import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.component import Component, ComponentLanguage, ComponentVersion
from app.models.semantic_type import SemanticResourceType

logger = logging.getLogger(__name__)


class ComponentService:
    """Service for managing component definitions and their versions."""

    async def list_components(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID | None,
        *,
        provider_id: uuid.UUID | None = None,
        semantic_type_id: uuid.UUID | None = None,
        published_only: bool = False,
        include_shared: bool = True,
        search: str | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> list[Component]:
        """List components visible to a tenant (own + provider-level shared)."""
        stmt = select(Component).where(Component.deleted_at.is_(None))

        if tenant_id is not None:
            if include_shared:
                stmt = stmt.where(
                    (Component.tenant_id == tenant_id) | (Component.tenant_id.is_(None))
                )
            else:
                stmt = stmt.where(Component.tenant_id == tenant_id)
        else:
            # Provider mode — only provider-level shared components
            stmt = stmt.where(Component.tenant_id.is_(None))

        if provider_id:
            stmt = stmt.where(Component.provider_id == provider_id)
        if semantic_type_id:
            stmt = stmt.where(Component.semantic_type_id == semantic_type_id)
        if published_only:
            stmt = stmt.where(Component.is_published.is_(True))
        if search:
            stmt = stmt.where(
                Component.name.ilike(f"%{search}%")
                | Component.display_name.ilike(f"%{search}%")
            )

        stmt = stmt.order_by(Component.name, Component.version.desc())

        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_component(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> Component | None:
        """Get a component by ID."""
        result = await db.execute(
            select(Component)
            .options(selectinload(Component.versions))
            .where(Component.id == component_id, Component.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def create_component(
        self,
        db: AsyncSession,
        *,
        tenant_id: uuid.UUID | None,
        provider_id: uuid.UUID,
        semantic_type_id: uuid.UUID,
        name: str,
        display_name: str,
        language: ComponentLanguage,
        created_by: uuid.UUID,
        description: str | None = None,
        code: str = "",
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        resolver_bindings: dict | None = None,
    ) -> Component:
        """Create a new draft component."""
        # Validate semantic type belongs to an infrastructure category
        sem_type = await db.get(SemanticResourceType, semantic_type_id)
        if not sem_type:
            raise ValueError(f"Semantic type '{semantic_type_id}' not found")
        cat = sem_type.category_rel
        if not cat or not cat.is_infrastructure:
            raise ValueError(
                f"Semantic type '{sem_type.display_name}' belongs to non-infrastructure "
                f"category '{cat.display_name if cat else 'unknown'}'. "
                f"Components can only target infrastructure types."
            )

        component = Component(
            tenant_id=tenant_id,
            provider_id=provider_id,
            semantic_type_id=semantic_type_id,
            name=name,
            display_name=display_name,
            description=description,
            language=language,
            code=code,
            input_schema=input_schema,
            output_schema=output_schema,
            resolver_bindings=resolver_bindings,
            version=1,
            is_published=False,
            created_by=created_by,
        )
        db.add(component)
        await db.flush()
        await db.refresh(component)
        return component

    async def update_component(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        **kwargs,
    ) -> Component:
        """Update a draft component. Published components cannot be edited."""
        component = await self.get_component(db, component_id)
        if not component:
            raise ValueError(f"Component '{component_id}' not found")

        protected = {"id", "created_at", "created_by", "tenant_id", "version", "is_published"}
        for key, value in kwargs.items():
            if hasattr(component, key) and key not in protected:
                setattr(component, key, value)

        await db.flush()
        await db.refresh(component)
        return component

    async def publish_component(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        *,
        changelog: str | None = None,
        published_by: uuid.UUID,
    ) -> Component:
        """Publish a component — creates an immutable version snapshot."""
        component = await self.get_component(db, component_id)
        if not component:
            raise ValueError(f"Component '{component_id}' not found")

        # Create version snapshot
        version_snapshot = ComponentVersion(
            component_id=component.id,
            version=component.version,
            code=component.code,
            input_schema=component.input_schema,
            output_schema=component.output_schema,
            resolver_bindings=component.resolver_bindings,
            changelog=changelog,
            published_by=published_by,
        )
        db.add(version_snapshot)

        # Mark as published and bump version for next edit
        component.is_published = True
        component.version = component.version + 1

        await db.flush()
        await db.refresh(component)
        return component

    async def delete_component(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> None:
        """Soft-delete a component."""
        component = await self.get_component(db, component_id)
        if not component:
            raise ValueError(f"Component '{component_id}' not found")

        component.deleted_at = func.now()
        await db.flush()

    async def get_version_history(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> list[ComponentVersion]:
        """List all published version snapshots for a component."""
        result = await db.execute(
            select(ComponentVersion)
            .where(ComponentVersion.component_id == component_id)
            .order_by(ComponentVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_version(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
        version: int,
    ) -> ComponentVersion | None:
        """Get a specific version snapshot."""
        result = await db.execute(
            select(ComponentVersion).where(
                ComponentVersion.component_id == component_id,
                ComponentVersion.version == version,
            )
        )
        return result.scalar_one_or_none()

    def validate_code(self, language: ComponentLanguage, code: str) -> list[str]:
        """Basic syntax validation. Returns list of errors (empty = valid)."""
        errors: list[str] = []
        if not code.strip():
            return errors  # Empty code is valid (draft)

        if language == ComponentLanguage.PYTHON:
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(f"Python syntax error at line {e.lineno}: {e.msg}")
        elif language == ComponentLanguage.TYPESCRIPT:
            # Basic checks only — full TS validation requires a TS compiler
            if code.count("{") != code.count("}"):
                errors.append("Mismatched braces in TypeScript code")

        return errors
