"""
Overview: Identity provider CRUD service with claim mapping management.
Architecture: Service layer for IdP configuration (Section 3.1, 5.1)
Dependencies: sqlalchemy, app.models
Concepts: Identity providers, claim mappings, SSO configuration
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity_provider import IdPType, IdentityProvider
from app.models.idp_claim_mapping import IdPClaimMapping
from app.models.role import Role
from app.models.user_group import UserGroup
from app.models.user_role import UserRole


class IdentityProviderError(Exception):
    def __init__(self, message: str, code: str = "IDP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class IdentityProviderService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_providers(self, tenant_id: str) -> list[IdentityProvider]:
        """List all identity providers for a tenant."""
        result = await self.db.execute(
            select(IdentityProvider)
            .where(
                IdentityProvider.tenant_id == tenant_id,
                IdentityProvider.deleted_at.is_(None),
            )
            .order_by(IdentityProvider.created_at)
        )
        return list(result.scalars().all())

    async def get_provider(self, provider_id: str, tenant_id: str) -> IdentityProvider | None:
        """Get a single identity provider."""
        result = await self.db.execute(
            select(IdentityProvider).where(
                IdentityProvider.id == provider_id,
                IdentityProvider.tenant_id == tenant_id,
                IdentityProvider.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_provider(
        self,
        tenant_id: str,
        name: str,
        idp_type: str,
        is_enabled: bool = True,
        is_default: bool = False,
        config: dict | None = None,
    ) -> IdentityProvider:
        """Create a new identity provider."""
        # Enforce one LOCAL provider per tenant
        if IdPType(idp_type) == IdPType.LOCAL:
            existing = await self.db.execute(
                select(IdentityProvider).where(
                    IdentityProvider.tenant_id == tenant_id,
                    IdentityProvider.idp_type == IdPType.LOCAL,
                    IdentityProvider.deleted_at.is_(None),
                )
            )
            if existing.scalar_one_or_none():
                raise IdentityProviderError(
                    "A local authentication provider already exists for this tenant",
                    "DUPLICATE_LOCAL_IDP",
                )

        if is_default:
            await self._clear_default(tenant_id)

        provider = IdentityProvider(
            tenant_id=tenant_id,
            name=name,
            idp_type=IdPType(idp_type),
            is_enabled=is_enabled,
            is_default=is_default,
            config=config,
        )
        self.db.add(provider)
        await self.db.flush()
        return provider

    async def update_provider(
        self,
        provider_id: str,
        tenant_id: str,
        name: str | None = None,
        is_enabled: bool | None = None,
        is_default: bool | None = None,
        config: dict | None = None,
    ) -> IdentityProvider:
        """Update an identity provider."""
        provider = await self.get_provider(provider_id, tenant_id)
        if not provider:
            raise IdentityProviderError("Identity provider not found", "IDP_NOT_FOUND")

        if name is not None:
            provider.name = name
        if is_enabled is not None:
            provider.is_enabled = is_enabled
        if is_default is not None:
            if is_default:
                await self._clear_default(tenant_id)
            provider.is_default = is_default
        if config is not None:
            provider.config = config

        await self.db.flush()
        return provider

    async def delete_provider(self, provider_id: str, tenant_id: str) -> None:
        """Soft-delete an identity provider."""
        from datetime import UTC, datetime

        provider = await self.get_provider(provider_id, tenant_id)
        if not provider:
            raise IdentityProviderError("Identity provider not found", "IDP_NOT_FOUND")

        provider.deleted_at = datetime.now(UTC)
        await self.db.flush()

    async def get_enabled_providers(self, tenant_id: str) -> list[IdentityProvider]:
        """Get only enabled SSO providers for a tenant (for login page)."""
        result = await self.db.execute(
            select(IdentityProvider).where(
                IdentityProvider.tenant_id == tenant_id,
                IdentityProvider.is_enabled.is_(True),
                IdentityProvider.deleted_at.is_(None),
                IdentityProvider.idp_type != IdPType.LOCAL,
            )
        )
        return list(result.scalars().all())

    # ── Claim Mappings ───────────────────────────────────────────────

    async def list_claim_mappings(self, provider_id: str) -> list[IdPClaimMapping]:
        """List claim mappings for an identity provider."""
        result = await self.db.execute(
            select(IdPClaimMapping)
            .where(IdPClaimMapping.identity_provider_id == provider_id)
            .order_by(IdPClaimMapping.priority.desc())
        )
        return list(result.scalars().all())

    async def create_claim_mapping(
        self,
        provider_id: str,
        claim_name: str,
        claim_value: str,
        role_id: str,
        group_id: str | None = None,
        priority: int = 0,
    ) -> IdPClaimMapping:
        """Create a claim-to-role mapping."""
        mapping = IdPClaimMapping(
            identity_provider_id=provider_id,
            claim_name=claim_name,
            claim_value=claim_value,
            role_id=role_id,
            group_id=group_id,
            priority=priority,
        )
        self.db.add(mapping)
        await self.db.flush()
        return mapping

    async def update_claim_mapping(
        self,
        mapping_id: str,
        **kwargs,
    ) -> IdPClaimMapping:
        """Update a claim mapping."""
        result = await self.db.execute(
            select(IdPClaimMapping).where(IdPClaimMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise IdentityProviderError("Claim mapping not found", "MAPPING_NOT_FOUND")

        for key, value in kwargs.items():
            if value is not None and hasattr(mapping, key):
                setattr(mapping, key, value)

        await self.db.flush()
        return mapping

    async def delete_claim_mapping(self, mapping_id: str) -> None:
        """Delete a claim mapping."""
        result = await self.db.execute(
            select(IdPClaimMapping).where(IdPClaimMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if not mapping:
            raise IdentityProviderError("Claim mapping not found", "MAPPING_NOT_FOUND")

        await self.db.delete(mapping)
        await self.db.flush()

    async def apply_claim_mappings(
        self,
        provider_id: str,
        tenant_id: str,
        user_id: str,
        claims: dict,
    ) -> None:
        """Apply claim mappings to assign roles/groups after SSO login."""
        mappings = await self.list_claim_mappings(provider_id)

        for mapping in mappings:
            claim_value = claims.get(mapping.claim_name)
            if claim_value is None:
                continue

            # Handle both single values and lists
            values = claim_value if isinstance(claim_value, list) else [claim_value]
            if mapping.claim_value not in values:
                continue

            # Assign role
            existing_role = await self.db.execute(
                select(UserRole).where(
                    UserRole.user_id == user_id,
                    UserRole.role_id == mapping.role_id,
                    UserRole.tenant_id == tenant_id,
                )
            )
            if not existing_role.scalar_one_or_none():
                self.db.add(
                    UserRole(user_id=user_id, role_id=mapping.role_id, tenant_id=tenant_id)
                )

            # Assign group
            if mapping.group_id:
                existing_group = await self.db.execute(
                    select(UserGroup).where(
                        UserGroup.user_id == user_id,
                        UserGroup.group_id == mapping.group_id,
                    )
                )
                if not existing_group.scalar_one_or_none():
                    self.db.add(UserGroup(user_id=user_id, group_id=mapping.group_id))

        await self.db.flush()

    # ── Private helpers ──────────────────────────────────────────────

    async def _clear_default(self, tenant_id: str) -> None:
        """Clear the default flag on all providers for a tenant."""
        result = await self.db.execute(
            select(IdentityProvider).where(
                IdentityProvider.tenant_id == tenant_id,
                IdentityProvider.is_default.is_(True),
                IdentityProvider.deleted_at.is_(None),
            )
        )
        for provider in result.scalars().all():
            provider.is_default = False
