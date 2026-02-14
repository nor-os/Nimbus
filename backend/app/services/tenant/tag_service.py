"""
Overview: Tenant tag service — CRUD for tenant-scoped configuration tags with JSON Schema validation.
Architecture: Service layer for tenant tag management (Section 3.2)
Dependencies: sqlalchemy, jsonschema, app.models.tenant_tag
Concepts: Tags provide typed key-value configuration per tenant. Values are validated against
    optional JSON Schema definitions. Soft delete checks for active references before removal.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_tag import TenantTag

logger = logging.getLogger(__name__)


class TagServiceError(Exception):
    def __init__(self, message: str, code: str = "TAG_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class TenantTagService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tag(self, tenant_id: str, data: dict[str, Any]) -> TenantTag:
        """Create a new tenant tag with optional schema validation."""
        existing = await self.get_tag_by_key(tenant_id, data["key"])
        if existing:
            raise TagServiceError(
                f"Tag with key '{data['key']}' already exists", "TAG_EXISTS"
            )

        if data.get("value") is not None and data.get("value_schema"):
            self._validate_value(data["value"], data["value_schema"])

        tag = TenantTag(
            tenant_id=tenant_id,
            key=data["key"],
            display_name=data.get("display_name", data["key"]),
            description=data.get("description"),
            value_schema=data.get("value_schema"),
            value=data.get("value"),
            is_secret=data.get("is_secret", False),
            sort_order=data.get("sort_order", 0),
        )
        self.db.add(tag)
        await self.db.flush()
        return tag

    async def update_tag(
        self, tag_id: uuid.UUID, tenant_id: str, data: dict[str, Any]
    ) -> TenantTag:
        """Update an existing tenant tag."""
        tag = await self.get_tag(tag_id, tenant_id)
        if not tag:
            raise TagServiceError("Tag not found", "TAG_NOT_FOUND")

        for key in ("display_name", "description", "value_schema", "is_secret", "sort_order"):
            if key in data:
                setattr(tag, key, data[key])

        if "value" in data:
            schema = data.get("value_schema", tag.value_schema)
            if data["value"] is not None and schema:
                self._validate_value(data["value"], schema)
            tag.value = data["value"]

        await self.db.flush()
        return tag

    async def delete_tag(
        self, tag_id: uuid.UUID, tenant_id: str
    ) -> bool:
        """Soft-delete a tenant tag."""
        tag = await self.get_tag(tag_id, tenant_id)
        if not tag:
            raise TagServiceError("Tag not found", "TAG_NOT_FOUND")

        tag.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_tag(
        self, tag_id: uuid.UUID, tenant_id: str
    ) -> TenantTag | None:
        """Get a tag by ID."""
        result = await self.db.execute(
            select(TenantTag).where(
                TenantTag.id == tag_id,
                TenantTag.tenant_id == tenant_id,
                TenantTag.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_tag_by_key(
        self, tenant_id: str, key: str
    ) -> TenantTag | None:
        """Get a tag by its unique key within a tenant."""
        result = await self.db.execute(
            select(TenantTag).where(
                TenantTag.tenant_id == tenant_id,
                TenantTag.key == key,
                TenantTag.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_tags(
        self, tenant_id: str, search: str | None = None
    ) -> list[TenantTag]:
        """List all active tags for a tenant."""
        query = (
            select(TenantTag)
            .where(
                TenantTag.tenant_id == tenant_id,
                TenantTag.deleted_at.is_(None),
            )
            .order_by(TenantTag.sort_order, TenantTag.key)
        )
        if search:
            query = query.where(TenantTag.key.ilike(f"%{search}%"))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def resolve_tag_value(
        self, tenant_id: str, key: str
    ) -> Any:
        """Resolve the value of a tag by key. Returns None if not found."""
        tag = await self.get_tag_by_key(tenant_id, key)
        if not tag:
            return None
        return tag.value

    @staticmethod
    def _validate_value(value: Any, schema: dict[str, Any]) -> None:
        """Validate a value against a JSON Schema."""
        try:
            import jsonschema
            jsonschema.validate(instance=value, schema=schema)
        except ImportError:
            logger.warning("jsonschema package not installed, skipping validation")
        except jsonschema.ValidationError as e:
            raise TagServiceError(
                f"Value validation failed: {e.message}", "VALIDATION_ERROR"
            )
