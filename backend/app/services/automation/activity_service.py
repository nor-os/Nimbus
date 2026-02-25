"""
Overview: Activity catalog service — CRUD and versioning for automated activities.
Architecture: Service layer for activity management (Section 11.5)
Dependencies: sqlalchemy, app.models.automated_activity
Concepts: Activity lifecycle, slug generation, version immutability, publish flow
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.automated_activity import (
    ActivityExecutionStatus,
    ActivityScope,
    AutomatedActivity,
    AutomatedActivityVersion,
    ImplementationType,
    OperationKind,
)

logger = logging.getLogger(__name__)


class ActivityServiceError(Exception):
    def __init__(self, message: str, code: str = "ACTIVITY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


def _slugify(name: str) -> str:
    """Generate a URL-safe slug from a name."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9]+', '_', slug)
    slug = slug.strip('_')
    return slug or 'activity'


class ActivityService:
    """Service for managing the automated activity catalog."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Activity CRUD ──────────────────────────────────

    async def create(
        self, tenant_id: str, created_by: str, data: dict[str, Any]
    ) -> AutomatedActivity:
        """Create a new automated activity."""
        slug = data.get("slug") or _slugify(data["name"])

        # Check slug uniqueness
        existing = await self.db.execute(
            select(AutomatedActivity).where(
                AutomatedActivity.tenant_id == tenant_id,
                AutomatedActivity.slug == slug,
                AutomatedActivity.deleted_at.is_(None),
            )
        )
        if existing.scalar_one_or_none():
            raise ActivityServiceError(f"Activity with slug '{slug}' already exists", "DUPLICATE_SLUG")

        activity = AutomatedActivity(
            tenant_id=tenant_id,
            name=data["name"],
            slug=slug,
            description=data.get("description"),
            category=data.get("category"),
            semantic_activity_type_id=data.get("semantic_activity_type_id"),
            semantic_type_id=data.get("semantic_type_id"),
            provider_id=data.get("provider_id"),
            operation_kind=OperationKind(data["operation_kind"]) if data.get("operation_kind") else OperationKind.UPDATE,
            implementation_type=ImplementationType(data["implementation_type"]) if data.get("implementation_type") else ImplementationType.PYTHON_SCRIPT,
            scope=ActivityScope(data["scope"]) if data.get("scope") else ActivityScope.WORKFLOW,
            idempotent=data.get("idempotent", False),
            timeout_seconds=data.get("timeout_seconds", 300),
            is_system=data.get("is_system", False),
            created_by=created_by,
        )
        self.db.add(activity)
        await self.db.flush()
        return activity

    async def get(self, tenant_id: str, activity_id: str) -> AutomatedActivity | None:
        """Get an activity by ID (tenant-scoped or system)."""
        result = await self.db.execute(
            select(AutomatedActivity)
            .options(selectinload(AutomatedActivity.versions))
            .where(
                AutomatedActivity.id == activity_id,
                or_(
                    AutomatedActivity.tenant_id == tenant_id,
                    AutomatedActivity.tenant_id.is_(None),
                ),
                AutomatedActivity.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, tenant_id: str, slug: str) -> AutomatedActivity | None:
        """Get an activity by slug (tenant-scoped or system)."""
        result = await self.db.execute(
            select(AutomatedActivity)
            .options(selectinload(AutomatedActivity.versions))
            .where(
                AutomatedActivity.slug == slug,
                or_(
                    AutomatedActivity.tenant_id == tenant_id,
                    AutomatedActivity.tenant_id.is_(None),
                ),
                AutomatedActivity.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        tenant_id: str,
        category: str | None = None,
        operation_kind: str | None = None,
        provider_id: str | None = None,
        scope: str | None = None,
        search: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AutomatedActivity]:
        """List activities with optional filters (includes system activities)."""
        query = select(AutomatedActivity).where(
            or_(
                AutomatedActivity.tenant_id == tenant_id,
                AutomatedActivity.tenant_id.is_(None),
            ),
            AutomatedActivity.deleted_at.is_(None),
        )

        if category:
            query = query.where(AutomatedActivity.category == category)
        if operation_kind:
            query = query.where(AutomatedActivity.operation_kind == OperationKind(operation_kind))
        if provider_id:
            query = query.where(AutomatedActivity.provider_id == provider_id)
        if scope:
            query = query.where(AutomatedActivity.scope == ActivityScope(scope))
        if search:
            query = query.where(
                AutomatedActivity.name.ilike(f"%{search}%")
                | AutomatedActivity.description.ilike(f"%{search}%")
            )

        query = query.order_by(AutomatedActivity.name).offset(offset).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(
        self, tenant_id: str, activity_id: str, data: dict[str, Any]
    ) -> AutomatedActivity:
        """Update an activity's metadata."""
        activity = await self._get_or_raise(tenant_id, activity_id)

        if activity.is_system:
            raise ActivityServiceError("Cannot modify system activities", "SYSTEM_ACTIVITY")

        for field in ("name", "description", "category", "semantic_activity_type_id",
                       "semantic_type_id", "provider_id", "idempotent", "timeout_seconds"):
            if field in data:
                setattr(activity, field, data[field])

        if "operation_kind" in data:
            activity.operation_kind = OperationKind(data["operation_kind"])
        if "implementation_type" in data:
            activity.implementation_type = ImplementationType(data["implementation_type"])
        if "scope" in data:
            activity.scope = ActivityScope(data["scope"])
        if "slug" in data:
            activity.slug = data["slug"]

        activity.updated_at = datetime.now(UTC)
        await self.db.flush()
        return activity

    async def delete(self, tenant_id: str, activity_id: str) -> bool:
        """Soft-delete an activity."""
        activity = await self._get_or_raise(tenant_id, activity_id)
        if activity.is_system:
            raise ActivityServiceError("Cannot delete system activities", "SYSTEM_ACTIVITY")
        activity.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    # ── Version Management ─────────────────────────────

    async def create_version(
        self, tenant_id: str, activity_id: str, data: dict[str, Any]
    ) -> AutomatedActivityVersion:
        """Create a new version (draft) of an activity."""
        activity = await self._get_or_raise(tenant_id, activity_id)

        # Get next version number
        result = await self.db.execute(
            select(func.coalesce(func.max(AutomatedActivityVersion.version), 0)).where(
                AutomatedActivityVersion.activity_id == activity_id
            )
        )
        next_version = result.scalar_one() + 1

        version = AutomatedActivityVersion(
            activity_id=activity_id,
            version=next_version,
            source_code=data.get("source_code"),
            input_schema=data.get("input_schema"),
            output_schema=data.get("output_schema"),
            config_mutations=data.get("config_mutations"),
            rollback_mutations=data.get("rollback_mutations"),
            changelog=data.get("changelog"),
            runtime_config=data.get("runtime_config"),
        )
        self.db.add(version)
        await self.db.flush()
        return version

    async def publish_version(
        self, tenant_id: str, activity_id: str, version_id: str, published_by: str
    ) -> AutomatedActivityVersion:
        """Publish a version, making it immutable and available for use."""
        activity = await self._get_or_raise(tenant_id, activity_id)

        result = await self.db.execute(
            select(AutomatedActivityVersion).where(
                AutomatedActivityVersion.id == version_id,
                AutomatedActivityVersion.activity_id == activity_id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise ActivityServiceError("Version not found", "VERSION_NOT_FOUND")

        if version.published_at:
            raise ActivityServiceError("Version is already published", "ALREADY_PUBLISHED")

        version.published_at = datetime.now(UTC)
        version.published_by = published_by
        await self.db.flush()

        # Emit event
        from app.services.events.event_bus import emit_event_async

        emit_event_async("activity.version.published", {
            "activity_id": activity_id, "version_id": version_id,
            "version_number": version.version,
        }, tenant_id, "activity_service", published_by)

        return version

    async def get_version(
        self, activity_id: str, version_id: str
    ) -> AutomatedActivityVersion | None:
        """Get a specific version."""
        result = await self.db.execute(
            select(AutomatedActivityVersion).where(
                AutomatedActivityVersion.id == version_id,
                AutomatedActivityVersion.activity_id == activity_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_versions(
        self, activity_id: str
    ) -> list[AutomatedActivityVersion]:
        """List all versions of an activity."""
        result = await self.db.execute(
            select(AutomatedActivityVersion)
            .where(AutomatedActivityVersion.activity_id == activity_id)
            .order_by(AutomatedActivityVersion.version.desc())
        )
        return list(result.scalars().all())

    async def get_latest_published(
        self, activity_id: str
    ) -> AutomatedActivityVersion | None:
        """Get the latest published version."""
        result = await self.db.execute(
            select(AutomatedActivityVersion)
            .where(
                AutomatedActivityVersion.activity_id == activity_id,
                AutomatedActivityVersion.published_at.isnot(None),
            )
            .order_by(AutomatedActivityVersion.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Internal ───────────────────────────────────────

    async def _get_or_raise(self, tenant_id: str, activity_id: str) -> AutomatedActivity:
        activity = await self.get(tenant_id, activity_id)
        if not activity:
            raise ActivityServiceError("Activity not found", "NOT_FOUND")
        return activity
