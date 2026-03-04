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
            semantic_activity_type_id=data.get("semantic_activity_type_id"),
            semantic_type_id=data.get("semantic_type_id"),
            provider_id=data.get("provider_id"),
            operation_kind=OperationKind(data["operation_kind"]) if data.get("operation_kind") else OperationKind.UPDATE,
            implementation_type=ImplementationType(data["implementation_type"]) if data.get("implementation_type") else ImplementationType.PYTHON_SCRIPT,
            idempotent=data.get("idempotent", False),
            timeout_seconds=data.get("timeout_seconds", 300),
            is_component_activity=data.get("is_component_activity", False),
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
        operation_kind: str | None = None,
        provider_id: str | None = None,
        search: str | None = None,
        component_id: str | None = None,
        is_component_activity: bool | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[AutomatedActivity]:
        """List activities with optional filters."""
        query = select(AutomatedActivity).where(
            or_(
                AutomatedActivity.tenant_id == tenant_id,
                AutomatedActivity.tenant_id.is_(None),
            ),
            AutomatedActivity.deleted_at.is_(None),
        )

        if operation_kind:
            query = query.where(AutomatedActivity.operation_kind == OperationKind(operation_kind))
        if provider_id:
            query = query.where(AutomatedActivity.provider_id == provider_id)
        if component_id:
            query = query.where(AutomatedActivity.component_id == component_id)
        if is_component_activity is not None:
            query = query.where(AutomatedActivity.is_component_activity == is_component_activity)
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

        for field in ("name", "description", "semantic_activity_type_id",
                       "semantic_type_id", "provider_id", "idempotent", "timeout_seconds"):
            if field in data:
                setattr(activity, field, data[field])

        if "operation_kind" in data:
            activity.operation_kind = OperationKind(data["operation_kind"])
        if "implementation_type" in data:
            activity.implementation_type = ImplementationType(data["implementation_type"])
        if "slug" in data:
            activity.slug = data["slug"]

        activity.updated_at = datetime.now(UTC)
        await self.db.flush()
        return activity

    async def delete(self, tenant_id: str, activity_id: str) -> bool:
        """Soft-delete an activity."""
        activity = await self._get_or_raise(tenant_id, activity_id)
        if activity.is_mandatory:
            raise ActivityServiceError(
                "Cannot delete mandatory activities (deploy, decommission, upgrade)",
                "MANDATORY_ACTIVITY",
            )
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
            resolver_bindings=data.get("resolver_bindings"),
        )
        self.db.add(version)
        await self.db.flush()

        # Bump component version if activity is linked to a component
        if activity.component_id:
            await self._bump_component_version(activity.component_id)

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

    # ── Upgrade from Library ─────────────────────────────

    async def check_upgrade_available(
        self, tenant_id: str, activity_id: str
    ) -> dict[str, int] | None:
        """Check if an upgrade is available from the library activity.

        Returns {library_version, forked_at_version} if upgrade exists, else None.
        """
        activity = await self._get_or_raise(tenant_id, activity_id)
        if not activity.template_activity_id:
            return None

        library_latest = await self.get_latest_published(str(activity.template_activity_id))
        if not library_latest:
            return None

        forked_at = activity.forked_at_version or 0
        if library_latest.version > forked_at:
            return {
                "library_version": library_latest.version,
                "forked_at_version": forked_at,
            }
        return None

    async def upgrade_from_library(
        self, tenant_id: str, activity_id: str
    ) -> AutomatedActivity:
        """Upgrade a forked activity to the latest library version.

        Creates a new version on the fork with library code/schemas and updates forked_at_version.
        """
        activity = await self._get_or_raise(tenant_id, activity_id)
        if not activity.template_activity_id:
            raise ActivityServiceError(
                "Activity is not a fork — no template_activity_id", "NOT_A_FORK"
            )

        library_latest = await self.get_latest_published(str(activity.template_activity_id))
        if not library_latest:
            raise ActivityServiceError(
                "No published version found on the library activity", "NO_LIBRARY_VERSION"
            )

        forked_at = activity.forked_at_version or 0
        if library_latest.version <= forked_at:
            raise ActivityServiceError(
                f"Already at latest library version (v{forked_at})", "ALREADY_CURRENT"
            )

        # Create a new version on the fork with library code
        result = await self.db.execute(
            select(func.coalesce(func.max(AutomatedActivityVersion.version), 0)).where(
                AutomatedActivityVersion.activity_id == activity_id
            )
        )
        next_version = result.scalar_one() + 1

        new_version = AutomatedActivityVersion(
            activity_id=activity_id,
            version=next_version,
            source_code=library_latest.source_code,
            input_schema=library_latest.input_schema,
            output_schema=library_latest.output_schema,
            config_mutations=library_latest.config_mutations,
            rollback_mutations=library_latest.rollback_mutations,
            changelog=f"Upgraded from library v{library_latest.version}",
            runtime_config=library_latest.runtime_config,
            resolver_bindings=library_latest.resolver_bindings,
        )
        self.db.add(new_version)

        activity.forked_at_version = library_latest.version
        activity.updated_at = datetime.now(UTC)
        await self.db.flush()

        # Bump component version if linked
        if activity.component_id:
            await self._bump_component_version(activity.component_id)

        return activity

    async def _bump_component_version(self, component_id) -> None:
        """Increment the version number on the linked component."""
        from app.models.component import Component

        result = await self.db.execute(
            select(Component).where(Component.id == component_id)
        )
        comp = result.scalar_one_or_none()
        if comp:
            comp.version = comp.version + 1
            await self.db.flush()

    # ── Internal ───────────────────────────────────────

    async def _get_or_raise(self, tenant_id: str, activity_id: str) -> AutomatedActivity:
        activity = await self.get(tenant_id, activity_id)
        if not activity:
            raise ActivityServiceError("Activity not found", "NOT_FOUND")
        return activity
