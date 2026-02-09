"""
Overview: CI template service — CRUD and instantiation of CI templates.
Architecture: Template management for rapid CI creation (Section 8)
Dependencies: sqlalchemy, app.models.cmdb.ci_template, app.services.cmdb.ci_service
Concepts: Templates store pre-configured attributes, tags, and relationship blueprints.
    Instantiation creates a CI from a template with optional overrides.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cmdb.ci_template import CITemplate

logger = logging.getLogger(__name__)


class TemplateServiceError(Exception):
    def __init__(self, message: str, code: str = "TEMPLATE_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(
        self, template_id: str, tenant_id: str
    ) -> CITemplate | None:
        """Get a template by ID."""
        result = await self.db.execute(
            select(CITemplate)
            .where(
                CITemplate.id == template_id,
                CITemplate.tenant_id == tenant_id,
                CITemplate.deleted_at.is_(None),
            )
            .options(selectinload(CITemplate.ci_class))
        )
        return result.scalar_one_or_none()

    async def list_templates(
        self,
        tenant_id: str,
        ci_class_id: str | None = None,
        active_only: bool = True,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CITemplate], int]:
        """List templates, optionally filtered by class."""
        stmt = select(CITemplate).where(
            CITemplate.tenant_id == tenant_id,
            CITemplate.deleted_at.is_(None),
        )

        if active_only:
            stmt = stmt.where(CITemplate.is_active.is_(True))
        if ci_class_id:
            stmt = stmt.where(CITemplate.ci_class_id == ci_class_id)

        count_stmt = select(func.count()).select_from(stmt.subquery())
        count_result = await self.db.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = stmt.options(selectinload(CITemplate.ci_class))
        stmt = stmt.order_by(CITemplate.name)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def create_template(
        self, tenant_id: str, data: dict
    ) -> CITemplate:
        """Create a new CI template."""
        template = CITemplate(
            tenant_id=tenant_id,
            name=data["name"],
            description=data.get("description"),
            ci_class_id=data["ci_class_id"],
            attributes=data.get("attributes") or {},
            tags=data.get("tags") or {},
            relationship_templates=data.get("relationship_templates"),
            constraints=data.get("constraints"),
            is_active=data.get("is_active", True),
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self, template_id: str, tenant_id: str, data: dict
    ) -> CITemplate:
        """Update a CI template. Increments version on attribute changes."""
        template = await self.get_template(template_id, tenant_id)
        if not template:
            raise TemplateServiceError("Template not found", "NOT_FOUND")

        version_bump = False
        for field in ("name", "description", "ci_class_id", "is_active"):
            if field in data and data[field] is not None:
                setattr(template, field, data[field])

        for field in ("attributes", "tags", "relationship_templates", "constraints"):
            if field in data:
                old_val = getattr(template, field)
                if old_val != data[field]:
                    setattr(template, field, data[field])
                    version_bump = True

        if version_bump:
            template.version += 1

        await self.db.flush()
        return template

    async def delete_template(
        self, template_id: str, tenant_id: str
    ) -> bool:
        """Soft-delete a template."""
        template = await self.get_template(template_id, tenant_id)
        if not template:
            raise TemplateServiceError("Template not found", "NOT_FOUND")

        template.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    def build_ci_data_from_template(
        self,
        template: CITemplate,
        overrides: dict | None = None,
    ) -> dict:
        """Build CI creation data from a template with optional overrides.

        Returns a dict suitable for CIService.create_ci().
        """
        data = {
            "ci_class_id": template.ci_class_id,
            "name": overrides.get("name", template.name) if overrides else template.name,
            "description": (
                overrides.get("description", template.description)
                if overrides
                else template.description
            ),
            "attributes": {
                **template.attributes,
                **(overrides.get("attributes") or {} if overrides else {}),
            },
            "tags": {
                **template.tags,
                **(overrides.get("tags") or {} if overrides else {}),
            },
        }

        if overrides and "compartment_id" in overrides:
            data["compartment_id"] = overrides["compartment_id"]
        if overrides and "lifecycle_state" in overrides:
            data["lifecycle_state"] = overrides["lifecycle_state"]

        return data
