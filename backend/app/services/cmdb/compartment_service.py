"""
Overview: CMDB compartment extension service — adds cloud_id and provider_type to compartments.
Architecture: Extends Phase 2 CompartmentService with CMDB cloud resource mapping (Section 8)
Dependencies: sqlalchemy, app.models.compartment
Concepts: Compartments can represent cloud provider accounts, subscriptions, or projects.
    cloud_id stores the provider-specific identifier, provider_type stores the provider name.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.compartment import Compartment

logger = logging.getLogger(__name__)


class CMDBCompartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_compartment(
        self, compartment_id: str, tenant_id: str
    ) -> Compartment | None:
        """Get a compartment by ID."""
        result = await self.db.execute(
            select(Compartment)
            .where(
                Compartment.id == compartment_id,
                Compartment.tenant_id == tenant_id,
                Compartment.deleted_at.is_(None),
            )
            .options(selectinload(Compartment.children))
        )
        return result.scalar_one_or_none()

    async def list_compartments(
        self,
        tenant_id: str,
        parent_id: str | None = None,
    ) -> list[Compartment]:
        """List compartments for a tenant, optionally filtered by parent."""
        stmt = select(Compartment).where(
            Compartment.tenant_id == tenant_id,
            Compartment.deleted_at.is_(None),
        )

        if parent_id is not None:
            stmt = stmt.where(Compartment.parent_id == parent_id)
        else:
            stmt = stmt.where(Compartment.parent_id.is_(None))

        stmt = stmt.options(selectinload(Compartment.children))
        stmt = stmt.order_by(Compartment.name)
        result = await self.db.execute(stmt)
        return list(result.scalars().unique().all())

    async def get_compartment_tree(
        self, tenant_id: str
    ) -> list[dict]:
        """Build a hierarchical tree of compartments."""
        all_comps = await self.db.execute(
            select(Compartment).where(
                Compartment.tenant_id == tenant_id,
                Compartment.deleted_at.is_(None),
            ).order_by(Compartment.name)
        )
        compartments = list(all_comps.scalars().all())

        by_parent: dict[str | None, list] = {}
        for c in compartments:
            parent_key = str(c.parent_id) if c.parent_id else None
            by_parent.setdefault(parent_key, []).append(c)

        def build_tree(parent_id: str | None) -> list[dict]:
            nodes = []
            for c in by_parent.get(parent_id, []):
                nodes.append({
                    "id": str(c.id),
                    "name": c.name,
                    "description": c.description,
                    "cloud_id": c.cloud_id,
                    "provider_type": c.provider_type,
                    "children": build_tree(str(c.id)),
                })
            return nodes

        return build_tree(None)

    async def update_compartment_cloud_info(
        self,
        compartment_id: str,
        tenant_id: str,
        cloud_id: str | None = None,
        provider_type: str | None = None,
    ) -> Compartment:
        """Update cloud-specific fields on a compartment."""
        comp = await self.get_compartment(compartment_id, tenant_id)
        if not comp:
            raise ValueError("Compartment not found")

        if cloud_id is not None:
            comp.cloud_id = cloud_id
        if provider_type is not None:
            comp.provider_type = provider_type

        await self.db.flush()
        return comp
