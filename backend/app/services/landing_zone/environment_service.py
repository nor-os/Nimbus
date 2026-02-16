"""
Overview: Environment service — template CRUD, tenant environment lifecycle management.
Architecture: Landing zone service layer (Section 6)
Dependencies: sqlalchemy, app.models.environment
Concepts: Environment templates, tenant environments, lifecycle (PLANNED→ACTIVE→DECOMMISSIONED)
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.environment import EnvironmentStatus, EnvironmentTemplate, TenantEnvironment


class EnvironmentService:

    # ── Templates ──────────────────────────────────────────────────────

    async def create_template(self, db: AsyncSession, *, provider_id: uuid.UUID,
                              name: str, display_name: str, description: str | None = None,
                              icon: str | None = None, color: str | None = None,
                              default_tags: dict | None = None, default_policies: dict | None = None,
                              sort_order: int = 0) -> EnvironmentTemplate:
        template = EnvironmentTemplate(
            provider_id=provider_id, name=name, display_name=display_name,
            description=description, icon=icon, color=color,
            default_tags=default_tags, default_policies=default_policies,
            sort_order=sort_order, is_system=False,
        )
        db.add(template)
        await db.flush()
        await db.refresh(template)
        return template

    async def get_template(self, db: AsyncSession, template_id: uuid.UUID) -> EnvironmentTemplate | None:
        result = await db.execute(
            select(EnvironmentTemplate)
            .where(EnvironmentTemplate.id == template_id, EnvironmentTemplate.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_templates(self, db: AsyncSession, provider_id: uuid.UUID | None = None,
                             offset: int | None = None, limit: int | None = None) -> list[EnvironmentTemplate]:
        stmt = select(EnvironmentTemplate).where(EnvironmentTemplate.deleted_at.is_(None))
        if provider_id:
            stmt = stmt.where(EnvironmentTemplate.provider_id == provider_id)
        stmt = stmt.order_by(EnvironmentTemplate.sort_order)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def delete_template(self, db: AsyncSession, template_id: uuid.UUID) -> None:
        template = await self.get_template(db, template_id)
        if not template:
            raise ValueError(f"Template {template_id} not found")
        if template.is_system:
            raise ValueError("Cannot delete system templates")
        template.deleted_at = datetime.now(timezone.utc)
        await db.flush()

    # ── Tenant Environments ───────────────────────────────────────────

    async def _resolve_landing_zone_id(
        self, db: AsyncSession, tenant_id: uuid.UUID, landing_zone_id: uuid.UUID | None
    ) -> uuid.UUID:
        """Auto-resolve the landing zone for a tenant if not explicitly provided."""
        if landing_zone_id:
            return landing_zone_id

        from app.services.cloud.backend_service import CloudBackendService
        from app.services.landing_zone.zone_service import LandingZoneService

        backend_svc = CloudBackendService(db)
        backend = await backend_svc.get_tenant_backend(tenant_id)
        if not backend:
            raise ValueError(
                "No cloud backend configured for this tenant. "
                "Set up a cloud backend first."
            )

        zone_svc = LandingZoneService()
        zones = await zone_svc.list_by_backend(db, backend.id)
        if not zones:
            raise ValueError(
                "Initialize the landing zone on your cloud backend first."
            )
        return zones[0].id

    async def create_environment(self, db: AsyncSession, *, tenant_id: uuid.UUID,
                                 landing_zone_id: uuid.UUID | None = None, name: str, display_name: str,
                                 created_by: uuid.UUID, template_id: uuid.UUID | None = None,
                                 description: str | None = None,
                                 root_compartment_id: uuid.UUID | None = None,
                                 tags: dict | None = None, policies: dict | None = None,
                                 settings: dict | None = None,
                                 network_config: dict | None = None,
                                 iam_config: dict | None = None,
                                 security_config: dict | None = None,
                                 monitoring_config: dict | None = None) -> TenantEnvironment:
        # Auto-resolve landing zone if not provided
        resolved_lz_id = await self._resolve_landing_zone_id(db, tenant_id, landing_zone_id)
        landing_zone_id = resolved_lz_id

        # Merge template defaults if template specified
        merged_tags = {}
        merged_policies = {}
        if template_id:
            template = await self.get_template(db, template_id)
            if template:
                merged_tags = dict(template.default_tags or {})
                merged_policies = dict(template.default_policies or {})
        if tags:
            merged_tags.update(tags)
        if policies:
            merged_policies.update(policies)

        env = TenantEnvironment(
            tenant_id=tenant_id, landing_zone_id=landing_zone_id, template_id=template_id,
            name=name, display_name=display_name, description=description,
            status=EnvironmentStatus.PLANNED, root_compartment_id=root_compartment_id,
            tags=merged_tags, policies=merged_policies, settings=settings,
            network_config=network_config, iam_config=iam_config,
            security_config=security_config, monitoring_config=monitoring_config,
            created_by=created_by,
        )
        db.add(env)
        await db.flush()
        await db.refresh(env)
        return env

    async def get_environment(self, db: AsyncSession, env_id: uuid.UUID) -> TenantEnvironment | None:
        result = await db.execute(
            select(TenantEnvironment)
            .where(TenantEnvironment.id == env_id, TenantEnvironment.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def list_environments(self, db: AsyncSession, tenant_id: uuid.UUID,
                                landing_zone_id: uuid.UUID | None = None,
                                status: str | None = None,
                                offset: int | None = None,
                                limit: int | None = None) -> list[TenantEnvironment]:
        stmt = select(TenantEnvironment).where(
            TenantEnvironment.tenant_id == tenant_id,
            TenantEnvironment.deleted_at.is_(None),
        )
        if landing_zone_id:
            stmt = stmt.where(TenantEnvironment.landing_zone_id == landing_zone_id)
        if status:
            stmt = stmt.where(TenantEnvironment.status == EnvironmentStatus(status))
        stmt = stmt.order_by(TenantEnvironment.created_at)
        if offset is not None:
            stmt = stmt.offset(offset)
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def update_environment(self, db: AsyncSession, env_id: uuid.UUID, **kwargs) -> TenantEnvironment:
        env = await self.get_environment(db, env_id)
        if not env:
            raise ValueError(f"Environment {env_id} not found")
        for key, value in kwargs.items():
            if hasattr(env, key) and key not in ("id", "tenant_id", "landing_zone_id", "created_at", "created_by"):
                setattr(env, key, value)
        await db.flush()
        await db.refresh(env)
        return env

    async def transition_status(self, db: AsyncSession, env_id: uuid.UUID,
                                new_status: EnvironmentStatus) -> TenantEnvironment:
        env = await self.get_environment(db, env_id)
        if not env:
            raise ValueError(f"Environment {env_id} not found")

        valid_transitions = {
            EnvironmentStatus.PLANNED: {EnvironmentStatus.PROVISIONING, EnvironmentStatus.ACTIVE},
            EnvironmentStatus.PROVISIONING: {EnvironmentStatus.ACTIVE, EnvironmentStatus.PLANNED},
            EnvironmentStatus.ACTIVE: {EnvironmentStatus.SUSPENDED, EnvironmentStatus.DECOMMISSIONING},
            EnvironmentStatus.SUSPENDED: {EnvironmentStatus.ACTIVE, EnvironmentStatus.DECOMMISSIONING},
            EnvironmentStatus.DECOMMISSIONING: {EnvironmentStatus.DECOMMISSIONED},
        }

        allowed = valid_transitions.get(env.status, set())
        if new_status not in allowed:
            raise ValueError(f"Cannot transition from {env.status.value} to {new_status.value}")

        env.status = new_status
        await db.flush()
        await db.refresh(env)
        return env

    async def decommission(self, db: AsyncSession, env_id: uuid.UUID) -> TenantEnvironment:
        return await self.transition_status(db, env_id, EnvironmentStatus.DECOMMISSIONING)
