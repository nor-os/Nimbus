"""
Overview: Resolver definition CRUD service — manages resolver type definitions and provider compatibility.
Architecture: Service layer for resolver definitions (Section 11)
Dependencies: sqlalchemy, app.models.resolver
Concepts: Provider-level entity management for resolver definitions, including provider compatibility.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resolver import Resolver, ResolverProviderCompatibility


class ResolverDefinitionService:

    async def create(
        self,
        db: AsyncSession,
        *,
        resolver_type: str,
        display_name: str,
        handler_class: str,
        description: str | None = None,
        input_schema: dict | None = None,
        output_schema: dict | None = None,
        instance_config_schema: dict | None = None,
        code: str | None = None,
        category: str | None = None,
        supports_release: bool = False,
        supports_update: bool = False,
        compatible_provider_ids: list[uuid.UUID] | None = None,
    ) -> Resolver:
        resolver = Resolver(
            resolver_type=resolver_type,
            display_name=display_name,
            handler_class=handler_class,
            description=description,
            input_schema=input_schema,
            output_schema=output_schema,
            instance_config_schema=instance_config_schema,
            code=code,
            category=category,
            supports_release=supports_release,
            supports_update=supports_update,
            is_system=False,
        )
        db.add(resolver)
        await db.flush()

        if compatible_provider_ids:
            await self._set_provider_compatibility(db, resolver.id, compatible_provider_ids)

        await db.refresh(resolver)
        return resolver

    async def update(
        self,
        db: AsyncSession,
        resolver_id: uuid.UUID,
        **kwargs,
    ) -> Resolver:
        resolver = await self.get(db, resolver_id)
        if not resolver:
            raise ValueError(f"Resolver {resolver_id} not found")

        compatible_provider_ids = kwargs.pop("compatible_provider_ids", None)

        for key, value in kwargs.items():
            if value is not None and hasattr(resolver, key) and key not in ("id", "resolver_type", "is_system", "created_at"):
                setattr(resolver, key, value)

        if compatible_provider_ids is not None:
            await self._set_provider_compatibility(db, resolver_id, compatible_provider_ids)

        await db.flush()
        await db.refresh(resolver)
        return resolver

    async def delete(self, db: AsyncSession, resolver_id: uuid.UUID) -> None:
        resolver = await self.get(db, resolver_id)
        if not resolver:
            raise ValueError(f"Resolver {resolver_id} not found")
        if resolver.is_system:
            raise ValueError("Cannot delete a system resolver")
        resolver.deleted_at = datetime.now(timezone.utc)
        await db.flush()

    async def get(self, db: AsyncSession, resolver_id: uuid.UUID) -> Resolver | None:
        result = await db.execute(
            select(Resolver).where(
                Resolver.id == resolver_id,
                Resolver.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_all(
        self,
        db: AsyncSession,
        provider_id: uuid.UUID | None = None,
    ) -> list[Resolver]:
        stmt = select(Resolver).where(Resolver.deleted_at.is_(None))

        if provider_id:
            stmt = stmt.join(
                ResolverProviderCompatibility,
                ResolverProviderCompatibility.resolver_id == Resolver.id,
            ).where(
                ResolverProviderCompatibility.provider_id == provider_id,
            )

        stmt = stmt.order_by(Resolver.resolver_type)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def set_provider_compatibility(
        self,
        db: AsyncSession,
        resolver_id: uuid.UUID,
        provider_ids: list[uuid.UUID],
    ) -> None:
        await self._set_provider_compatibility(db, resolver_id, provider_ids)

    async def _set_provider_compatibility(
        self,
        db: AsyncSession,
        resolver_id: uuid.UUID,
        provider_ids: list[uuid.UUID],
    ) -> None:
        # Remove existing
        result = await db.execute(
            select(ResolverProviderCompatibility).where(
                ResolverProviderCompatibility.resolver_id == resolver_id,
            )
        )
        for existing in result.scalars().all():
            await db.delete(existing)
        await db.flush()

        # Add new
        for pid in provider_ids:
            compat = ResolverProviderCompatibility(
                resolver_id=resolver_id,
                provider_id=pid,
            )
            db.add(compat)
        await db.flush()
