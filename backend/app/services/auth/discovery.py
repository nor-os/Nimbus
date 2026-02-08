"""
Overview: Discovery service resolving email domains to tenants and their available auth providers.
Architecture: Login discovery logic for email-first auth flow (Section 5.1)
Dependencies: sqlalchemy, app.models
Concepts: Domain-based tenant discovery, IdP provider listing, slug-based login
"""

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_mapping import DomainMapping
from app.models.identity_provider import IdPType, IdentityProvider
from app.models.tenant import Tenant


@dataclass
class SSOProviderInfo:
    id: str
    name: str
    idp_type: str


@dataclass
class DiscoveryResult:
    found: bool
    tenant_id: str | None = None
    tenant_name: str | None = None
    tenant_slug: str | None = None
    has_local_auth: bool = False
    sso_providers: list[SSOProviderInfo] = field(default_factory=list)


@dataclass
class TenantLoginInfo:
    tenant_id: str
    tenant_name: str
    slug: str
    has_local_auth: bool
    sso_providers: list[SSOProviderInfo]


class DiscoveryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def discover(self, email: str) -> DiscoveryResult:
        """Given an email, find the tenant and available auth providers via domain mapping."""
        parts = email.rsplit("@", 1)
        if len(parts) != 2:
            return DiscoveryResult(found=False)

        domain = parts[1].lower()
        mapping = await self._lookup_domain(domain)
        if not mapping:
            return DiscoveryResult(found=False)

        tenant = await self._get_tenant(mapping.tenant_id)
        if not tenant:
            return DiscoveryResult(found=False)

        providers = await self._get_enabled_providers(mapping.tenant_id)
        has_local = any(p.idp_type == IdPType.LOCAL for p in providers)
        sso_providers = [
            SSOProviderInfo(id=str(p.id), name=p.name, idp_type=p.idp_type.value)
            for p in providers
            if p.idp_type != IdPType.LOCAL
        ]

        return DiscoveryResult(
            found=True,
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            tenant_slug=tenant.slug,
            has_local_auth=has_local,
            sso_providers=sso_providers,
        )

    async def get_tenant_by_slug(self, slug: str) -> TenantLoginInfo | None:
        """Get tenant login info by slug (for /login/:slug route)."""
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.slug == slug.lower(),
                Tenant.deleted_at.is_(None),
            )
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            return None

        providers = await self._get_enabled_providers(tenant.id)
        has_local = any(p.idp_type == IdPType.LOCAL for p in providers)
        sso_providers = [
            SSOProviderInfo(id=str(p.id), name=p.name, idp_type=p.idp_type.value)
            for p in providers
            if p.idp_type != IdPType.LOCAL
        ]

        return TenantLoginInfo(
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            slug=tenant.slug or slug,
            has_local_auth=has_local,
            sso_providers=sso_providers,
        )

    async def _lookup_domain(self, domain: str) -> DomainMapping | None:
        result = await self.db.execute(
            select(DomainMapping).where(DomainMapping.domain == domain)
        )
        return result.scalar_one_or_none()

    async def _get_tenant(self, tenant_id) -> Tenant | None:
        result = await self.db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def _get_enabled_providers(self, tenant_id) -> list[IdentityProvider]:
        result = await self.db.execute(
            select(IdentityProvider).where(
                IdentityProvider.tenant_id == tenant_id,
                IdentityProvider.is_enabled.is_(True),
                IdentityProvider.deleted_at.is_(None),
            )
        )
        return list(result.scalars().all())
