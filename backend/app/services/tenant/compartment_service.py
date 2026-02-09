"""
Overview: Compartment service — CRUD and tree operations for resource organization.
Architecture: Compartment management within tenant scope (Section 4.2)
Dependencies: sqlalchemy, app.models.compartment
Concepts: Compartments, hierarchical organization, circular reference prevention
"""

from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.compartment import Compartment
from app.services.tenant.quota_service import QuotaService


class CompartmentError(Exception):
    def __init__(self, message: str, code: str = "COMPARTMENT_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CompartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_compartment(
        self,
        tenant_id: str,
        name: str,
        parent_id: str | None = None,
        description: str | None = None,
    ) -> Compartment:
        """Create a new compartment within a tenant."""
        # Check quota
        quota_service = QuotaService(self.db)
        await quota_service.check_quota(tenant_id, "max_compartments")

        if parent_id:
            parent = await self.get_compartment(parent_id, tenant_id)
            if not parent:
                raise CompartmentError("Parent compartment not found", "PARENT_NOT_FOUND")

        compartment = Compartment(
            tenant_id=tenant_id,
            parent_id=parent_id,
            name=name,
            description=description,
        )
        self.db.add(compartment)
        await self.db.flush()

        await quota_service.increment_usage(tenant_id, "max_compartments")
        return compartment

    async def get_compartment(
        self, compartment_id: str, tenant_id: str
    ) -> Compartment | None:
        """Get a compartment by ID within a tenant scope."""
        result = await self.db.execute(
            select(Compartment).where(
                Compartment.id == compartment_id,
                Compartment.tenant_id == tenant_id,
                Compartment.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def update_compartment(
        self,
        compartment_id: str,
        tenant_id: str,
        name: str | None = None,
        parent_id: str | None = None,
        description: str | None = None,
    ) -> Compartment:
        """Update a compartment. Validates no circular references on parent change."""
        compartment = await self.get_compartment(compartment_id, tenant_id)
        if not compartment:
            raise CompartmentError("Compartment not found", "COMPARTMENT_NOT_FOUND")

        if parent_id is not None and parent_id != str(compartment.parent_id):
            if parent_id == compartment_id:
                raise CompartmentError(
                    "Compartment cannot be its own parent", "CIRCULAR_REFERENCE"
                )
            await self._check_circular_reference(compartment_id, parent_id, tenant_id)
            compartment.parent_id = parent_id if parent_id else None

        if name is not None:
            compartment.name = name
        if description is not None:
            compartment.description = description
        return compartment

    async def delete_compartment(
        self, compartment_id: str, tenant_id: str
    ) -> Compartment:
        """Soft-delete a compartment."""
        compartment = await self.get_compartment(compartment_id, tenant_id)
        if not compartment:
            raise CompartmentError("Compartment not found", "COMPARTMENT_NOT_FOUND")

        # Check for active children
        result = await self.db.execute(
            select(func.count()).select_from(Compartment).where(
                Compartment.parent_id == compartment_id,
                Compartment.tenant_id == tenant_id,
                Compartment.deleted_at.is_(None),
            )
        )
        if result.scalar_one() > 0:
            raise CompartmentError(
                "Cannot delete compartment with active children",
                "HAS_ACTIVE_CHILDREN",
            )

        compartment.deleted_at = datetime.now(UTC)

        quota_service = QuotaService(self.db)
        await quota_service.decrement_usage(tenant_id, "max_compartments")
        return compartment

    async def list_compartments(
        self, tenant_id: str, parent_id: str | None = None
    ) -> list[Compartment]:
        """List compartments for a tenant, optionally filtered by parent."""
        query = select(Compartment).where(
            Compartment.tenant_id == tenant_id,
            Compartment.deleted_at.is_(None),
        )
        if parent_id is not None:
            query = query.where(Compartment.parent_id == parent_id)
        result = await self.db.execute(query.order_by(Compartment.name))
        return list(result.scalars().all())

    async def get_compartment_tree(self, tenant_id: str) -> list[dict]:
        """Get the full compartment tree using a recursive CTE."""
        cte_query = text("""
            WITH RECURSIVE compartment_tree AS (
                SELECT id, name, description, parent_id, 0 as depth
                FROM compartments
                WHERE tenant_id = CAST(:tid AS uuid) AND parent_id IS NULL AND deleted_at IS NULL
                UNION ALL
                SELECT c.id, c.name, c.description, c.parent_id, ct.depth + 1
                FROM compartments c
                JOIN compartment_tree ct ON c.parent_id = ct.id
                WHERE c.deleted_at IS NULL
            )
            SELECT id, name, description, parent_id, depth
            FROM compartment_tree
            ORDER BY depth, name
        """).bindparams(tid=tenant_id)

        result = await self.db.execute(cte_query)
        rows = result.fetchall()

        # Build tree from flat list
        nodes: dict[str, dict] = {}
        roots: list[dict] = []

        for row in rows:
            node = {
                "id": row.id,
                "name": row.name,
                "description": row.description,
                "children": [],
            }
            nodes[str(row.id)] = node
            if row.parent_id is None:
                roots.append(node)
            else:
                parent = nodes.get(str(row.parent_id))
                if parent:
                    parent["children"].append(node)

        return roots

    async def _check_circular_reference(
        self, compartment_id: str, new_parent_id: str, tenant_id: str
    ) -> None:
        """Check that setting new_parent_id won't create a circular reference."""
        cte_query = text("""
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id
                FROM compartments
                WHERE id = :parent_id AND tenant_id = :tid AND deleted_at IS NULL
                UNION ALL
                SELECT c.id, c.parent_id
                FROM compartments c
                JOIN ancestors a ON c.id = a.parent_id
                WHERE c.deleted_at IS NULL
            )
            SELECT id FROM ancestors WHERE id = :comp_id
        """).bindparams(parent_id=new_parent_id, tid=tenant_id, comp_id=compartment_id)

        result = await self.db.execute(cte_query)
        if result.scalar_one_or_none() is not None:
            raise CompartmentError(
                "Moving compartment would create a circular reference",
                "CIRCULAR_REFERENCE",
            )
