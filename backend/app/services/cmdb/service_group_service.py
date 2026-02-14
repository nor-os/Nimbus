"""
Overview: Service group service — CRUD for service groups and group item composition with lifecycle.
Architecture: Service group management (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.service_group
Concepts: Service groups bundle multiple service offerings; lifecycle: draft -> published -> archived.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.service_group import ServiceGroup, ServiceGroupItem
from app.services.cmdb.catalog_service import CatalogServiceError


class ServiceGroupService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Group CRUD ───────────────────────────────────────────────────

    async def create_group(
        self, tenant_id: str | None, data: dict
    ) -> ServiceGroup:
        group = ServiceGroup(
            tenant_id=tenant_id,
            name=data["name"],
            display_name=data.get("display_name"),
            description=data.get("description"),
            status="draft",
        )
        self.db.add(group)
        await self.db.flush()
        return group

    async def get_group(
        self, group_id: str, tenant_id: str | None = None
    ) -> ServiceGroup | None:
        stmt = select(ServiceGroup).where(
            ServiceGroup.id == group_id,
            ServiceGroup.deleted_at.is_(None),
        )
        if tenant_id:
            stmt = stmt.where(
                (ServiceGroup.tenant_id == tenant_id)
                | (ServiceGroup.tenant_id.is_(None))
            )
        stmt = stmt.options(selectinload(ServiceGroup.items))
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_groups(
        self,
        tenant_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[ServiceGroup], int]:
        stmt = select(ServiceGroup).where(ServiceGroup.deleted_at.is_(None))
        if tenant_id:
            stmt = stmt.where(
                (ServiceGroup.tenant_id == tenant_id)
                | (ServiceGroup.tenant_id.is_(None))
            )
        if status:
            stmt = stmt.where(ServiceGroup.status == status)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = (
            stmt.options(selectinload(ServiceGroup.items))
            .order_by(ServiceGroup.name)
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all()), total

    async def update_group(
        self, group_id: str, data: dict
    ) -> ServiceGroup:
        group = await self.get_group(group_id)
        if not group:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")
        if group.status != "draft":
            raise CatalogServiceError(
                "Only draft groups can be edited", "INVALID_STATUS"
            )
        for key, val in data.items():
            if hasattr(group, key) and val is not None:
                setattr(group, key, val)
        await self.db.flush()
        return group

    async def delete_group(self, group_id: str) -> bool:
        group = await self.get_group(group_id)
        if not group:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")
        group.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Lifecycle ─────────────────────────────────────────────────────

    async def publish_group(self, group_id: str) -> ServiceGroup:
        group = await self.get_group(group_id)
        if not group:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")
        if group.status != "draft":
            raise CatalogServiceError(
                "Only draft groups can be published", "INVALID_STATUS"
            )
        group.status = "published"
        await self.db.flush()
        return group

    async def archive_group(self, group_id: str) -> ServiceGroup:
        group = await self.get_group(group_id)
        if not group:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")
        if group.status != "published":
            raise CatalogServiceError(
                "Only published groups can be archived", "INVALID_STATUS"
            )
        group.status = "archived"
        await self.db.flush()
        return group

    async def clone_group(
        self, group_id: str, tenant_id: str | None = None
    ) -> ServiceGroup:
        source = await self.get_group(group_id)
        if not source:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")

        clone = ServiceGroup(
            tenant_id=tenant_id or source.tenant_id,
            name=f"{source.name}-copy",
            display_name=(
                f"{source.display_name} (Copy)" if source.display_name else None
            ),
            description=source.description,
            status="draft",
        )
        self.db.add(clone)
        await self.db.flush()

        # Copy items
        for item in source.items:
            if getattr(item, "deleted_at", None):
                continue
            new_item = ServiceGroupItem(
                group_id=clone.id,
                service_offering_id=item.service_offering_id,
                is_required=item.is_required,
                sort_order=item.sort_order,
            )
            self.db.add(new_item)

        await self.db.flush()
        # Reload with items
        return await self.get_group(str(clone.id))

    # ── Group Items ──────────────────────────────────────────────────

    async def add_item(
        self,
        group_id: str,
        service_offering_id: str,
        is_required: bool = True,
        sort_order: int = 0,
    ) -> ServiceGroupItem:
        group = await self.get_group(group_id)
        if not group:
            raise CatalogServiceError("Service group not found", "NOT_FOUND")
        if group.status != "draft":
            raise CatalogServiceError(
                "Items can only be added to draft groups", "INVALID_STATUS"
            )
        item = ServiceGroupItem(
            group_id=group_id,
            service_offering_id=service_offering_id,
            is_required=is_required,
            sort_order=sort_order,
        )
        self.db.add(item)
        await self.db.flush()
        return item

    async def remove_item(self, item_id: str) -> bool:
        result = await self.db.execute(
            select(ServiceGroupItem).where(
                ServiceGroupItem.id == item_id,
                ServiceGroupItem.deleted_at.is_(None),
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise CatalogServiceError("Group item not found", "NOT_FOUND")
        # Check parent group status
        group = await self.get_group(str(item.group_id))
        if group and group.status != "draft":
            raise CatalogServiceError(
                "Items can only be removed from draft groups", "INVALID_STATUS"
            )
        item.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def list_items(self, group_id: str) -> list[ServiceGroupItem]:
        result = await self.db.execute(
            select(ServiceGroupItem)
            .where(
                ServiceGroupItem.group_id == group_id,
                ServiceGroupItem.deleted_at.is_(None),
            )
            .order_by(ServiceGroupItem.sort_order)
        )
        return list(result.scalars().all())
