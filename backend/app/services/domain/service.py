"""
Overview: Domain mapping CRUD service for managing email domain-to-tenant associations.
Architecture: Service layer for domain discovery configuration (Section 5.1)
Dependencies: sqlalchemy, app.models
Concepts: Domain mapping, tenant routing, email domain verification
"""

import re

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.domain_mapping import DomainMapping


class DomainMappingError(Exception):
    def __init__(self, message: str, code: str = "DOMAIN_MAPPING_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# Simple regex for domain validation (no protocol, no path)
_DOMAIN_RE = re.compile(
    r"^(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(\.[a-zA-Z0-9-]{1,63})*\.[a-zA-Z]{2,}$"
)


class DomainMappingService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_mappings(self, tenant_id: str) -> list[DomainMapping]:
        """List all domain mappings for a tenant."""
        result = await self.db.execute(
            select(DomainMapping)
            .where(DomainMapping.tenant_id == tenant_id)
            .order_by(DomainMapping.created_at)
        )
        return list(result.scalars().all())

    async def create_mapping(
        self,
        tenant_id: str,
        domain: str,
        identity_provider_id: str | None = None,
    ) -> DomainMapping:
        """Create a domain mapping. Domain must be unique across all tenants."""
        domain = domain.strip().lower()

        if not _DOMAIN_RE.match(domain):
            raise DomainMappingError(
                f"Invalid domain format: {domain}",
                "INVALID_DOMAIN",
            )

        mapping = DomainMapping(
            tenant_id=tenant_id,
            domain=domain,
            identity_provider_id=identity_provider_id,
        )
        self.db.add(mapping)
        try:
            await self.db.flush()
        except IntegrityError:
            await self.db.rollback()
            raise DomainMappingError(
                f"Domain '{domain}' is already mapped to a tenant",
                "DOMAIN_ALREADY_MAPPED",
            )
        return mapping

    async def delete_mapping(self, mapping_id: str, tenant_id: str) -> None:
        """Delete a domain mapping (hard delete — no audit trail needed for mappings)."""
        result = await self.db.execute(
            select(DomainMapping).where(
                DomainMapping.id == mapping_id,
                DomainMapping.tenant_id == tenant_id,
            )
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise DomainMappingError(
                "Domain mapping not found",
                "DOMAIN_MAPPING_NOT_FOUND",
            )
        await self.db.delete(mapping)
        await self.db.flush()

    async def verify_mapping(self, mapping_id: str, tenant_id: str) -> DomainMapping:
        """Mark a domain mapping as verified (future: DNS TXT verification)."""
        result = await self.db.execute(
            select(DomainMapping).where(
                DomainMapping.id == mapping_id,
                DomainMapping.tenant_id == tenant_id,
            )
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise DomainMappingError(
                "Domain mapping not found",
                "DOMAIN_MAPPING_NOT_FOUND",
            )
        mapping.is_verified = True
        await self.db.flush()
        return mapping
