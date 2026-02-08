"""
Overview: Temporal activities for tenant purge workflow.
Architecture: Tenant lifecycle cleanup activities (Section 9)
Dependencies: temporalio, app.services.tenant.purge_service
Concepts: Temporal activities, tenant purge, data retention
"""

from dataclasses import dataclass

from temporalio import activity


@dataclass
class PurgeResult:
    tenant_id: str
    success: bool
    error: str | None = None


@activity.defn
async def find_purgeable_tenants() -> list[str]:
    """Find all tenants eligible for permanent deletion."""
    from app.db.session import async_session_factory
    from app.services.tenant.purge_service import PurgeService

    async with async_session_factory() as db:
        service = PurgeService(db)
        tenant_ids = await service.find_purgeable_tenants()
        activity.logger.info(f"Found {len(tenant_ids)} purgeable tenants")
        return tenant_ids


@activity.defn
async def purge_single_tenant(tenant_id: str) -> PurgeResult:
    """Purge a single tenant (idempotent)."""
    from app.db.session import async_session_factory
    from app.services.tenant.purge_service import PurgeService

    try:
        async with async_session_factory() as db:
            service = PurgeService(db)
            await service.purge_tenant(tenant_id)
            await db.commit()
            activity.logger.info(f"Purged tenant {tenant_id}")
            return PurgeResult(tenant_id=tenant_id, success=True)
    except Exception as e:
        activity.logger.error(f"Failed to purge tenant {tenant_id}: {e}")
        return PurgeResult(tenant_id=tenant_id, success=False, error=str(e))
