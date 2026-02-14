"""
Overview: Service for OS image catalog CRUD — images and provider mappings.
Architecture: Service layer for OS image management (Section 5)
Dependencies: sqlalchemy, app.models.os_image
Concepts: Full CRUD for OS images and their per-provider mappings. System records
    (is_system=True) cannot be deleted.
"""

from __future__ import annotations

from datetime import datetime, timezone

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.os_image import OsImage, OsImageProviderMapping, OsImageTenantAssignment


class ImageService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # -- Image CRUD ----------------------------------------------------------

    async def create_image(
        self,
        name: str,
        display_name: str,
        os_family: str,
        version: str,
        architecture: str = "x86_64",
        description: str | None = None,
        icon: str | None = None,
        sort_order: int = 0,
    ) -> OsImage:
        image = OsImage(
            id=uuid.uuid4(),
            name=name,
            display_name=display_name,
            os_family=os_family,
            version=version,
            architecture=architecture,
            description=description,
            icon=icon,
            sort_order=sort_order,
        )
        self.db.add(image)
        await self.db.flush()
        return image

    async def get_image(self, image_id: uuid.UUID) -> OsImage | None:
        stmt = (
            select(OsImage)
            .options(
                selectinload(OsImage.provider_mappings),
                selectinload(OsImage.tenant_assignments),
            )
            .where(OsImage.id == image_id, OsImage.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_images(
        self,
        os_family: str | None = None,
        architecture: str | None = None,
        search: str | None = None,
        tenant_id: uuid.UUID | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[OsImage], int]:
        base = select(OsImage).where(OsImage.deleted_at.is_(None))

        if tenant_id is not None:
            base = base.where(
                OsImage.id.in_(
                    select(OsImageTenantAssignment.os_image_id).where(
                        OsImageTenantAssignment.tenant_id == tenant_id
                    )
                )
            )
        if os_family:
            base = base.where(OsImage.os_family == os_family)
        if architecture:
            base = base.where(OsImage.architecture == architecture)
        if search:
            term = f"%{search}%"
            base = base.where(
                or_(
                    OsImage.name.ilike(term),
                    OsImage.display_name.ilike(term),
                    OsImage.description.ilike(term),
                )
            )

        count_stmt = select(func.count()).select_from(base.subquery())
        total = (await self.db.execute(count_stmt)).scalar_one()

        items_stmt = (
            base.options(
                selectinload(OsImage.provider_mappings),
                selectinload(OsImage.tenant_assignments),
            )
            .order_by(OsImage.sort_order, OsImage.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(items_stmt)
        items = list(result.scalars().all())

        return items, total

    async def update_image(self, image_id: uuid.UUID, **kwargs) -> OsImage | None:
        image = await self.get_image(image_id)
        if not image:
            return None
        for key, value in kwargs.items():
            setattr(image, key, value)
        await self.db.flush()
        return image

    async def delete_image(self, image_id: uuid.UUID) -> bool:
        image = await self.get_image(image_id)
        if not image:
            return False
        if image.is_system:
            raise ValueError("Cannot delete system OS image")
        image.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True

    # -- Tenant Assignment ---------------------------------------------------

    async def set_image_tenants(
        self, os_image_id: uuid.UUID, tenant_ids: list[uuid.UUID]
    ) -> list[OsImageTenantAssignment]:
        # Get current assignments
        stmt = select(OsImageTenantAssignment).where(
            OsImageTenantAssignment.os_image_id == os_image_id
        )
        result = await self.db.execute(stmt)
        current = list(result.scalars().all())
        current_tenant_ids = {a.tenant_id for a in current}
        desired_tenant_ids = set(tenant_ids)

        # Remove extra
        to_remove = current_tenant_ids - desired_tenant_ids
        if to_remove:
            for assignment in current:
                if assignment.tenant_id in to_remove:
                    await self.db.delete(assignment)

        # Add missing
        to_add = desired_tenant_ids - current_tenant_ids
        for tid in to_add:
            self.db.add(OsImageTenantAssignment(
                id=uuid.uuid4(),
                os_image_id=os_image_id,
                tenant_id=tid,
            ))

        await self.db.flush()

        # Return refreshed list
        stmt = select(OsImageTenantAssignment).where(
            OsImageTenantAssignment.os_image_id == os_image_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # -- Provider Mapping CRUD -----------------------------------------------

    async def create_provider_mapping(
        self,
        os_image_id: uuid.UUID,
        provider_id: uuid.UUID,
        image_reference: str,
        notes: str | None = None,
    ) -> OsImageProviderMapping:
        mapping = OsImageProviderMapping(
            id=uuid.uuid4(),
            os_image_id=os_image_id,
            provider_id=provider_id,
            image_reference=image_reference,
            notes=notes,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    async def get_provider_mapping(self, mapping_id: uuid.UUID) -> OsImageProviderMapping | None:
        stmt = (
            select(OsImageProviderMapping)
            .where(
                OsImageProviderMapping.id == mapping_id,
                OsImageProviderMapping.deleted_at.is_(None),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_provider_mappings(
        self,
        os_image_id: uuid.UUID | None = None,
        provider_id: uuid.UUID | None = None,
    ) -> list[OsImageProviderMapping]:
        stmt = select(OsImageProviderMapping).where(
            OsImageProviderMapping.deleted_at.is_(None)
        )
        if os_image_id:
            stmt = stmt.where(OsImageProviderMapping.os_image_id == os_image_id)
        if provider_id:
            stmt = stmt.where(OsImageProviderMapping.provider_id == provider_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_provider_mapping(
        self, mapping_id: uuid.UUID, **kwargs
    ) -> OsImageProviderMapping | None:
        mapping = await self.get_provider_mapping(mapping_id)
        if not mapping:
            return None
        for key, value in kwargs.items():
            setattr(mapping, key, value)
        await self.db.flush()
        return mapping

    async def delete_provider_mapping(self, mapping_id: uuid.UUID) -> bool:
        mapping = await self.get_provider_mapping(mapping_id)
        if not mapping:
            return False
        if mapping.is_system:
            raise ValueError("Cannot delete system provider mapping")
        mapping.deleted_at = datetime.now(timezone.utc)
        await self.db.flush()
        return True
