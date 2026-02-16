"""
Overview: Image catalog resolver — resolves abstract OS image choices to provider-specific references.
Architecture: Resolver implementation for image catalog (Section 11)
Dependencies: app.services.resolver.base, app.models.os_image
Concepts: Maps abstract OS image parameters (family, version, architecture) to concrete provider
    image references (AMI IDs, Azure URNs, Proxmox template names) via the OsImage catalog.
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.services.resolver.base import BaseResolver, ResolverContext

logger = logging.getLogger(__name__)


class ImageCatalogResolver(BaseResolver):
    """Resolves abstract OS image choices to provider-specific image references."""

    resolver_type = "image_catalog"

    async def resolve(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Resolve image parameters.

        Input params:
            os_family: str (e.g., 'ubuntu', 'windows', 'rhel')
            os_version: str (e.g., '22.04', '2022')
            architecture: str (default 'x86_64')

        Config:
            default_architecture: str (default 'x86_64')

        Returns:
            {image_id, image_reference, image_name}
        """
        from app.models.os_image import OsImage, OsImageProviderMapping

        db = context.db
        os_family = params.get("os_family")
        os_version = params.get("os_version")
        architecture = params.get(
            "architecture", config.get("default_architecture", "x86_64")
        )

        if not os_family:
            raise ValueError("Image catalog resolver requires 'os_family' parameter")

        # Find matching OS image
        stmt = (
            select(OsImage)
            .options(selectinload(OsImage.provider_mappings))
            .where(
                OsImage.deleted_at.is_(None),
                OsImage.os_family.ilike(os_family),
                OsImage.architecture == architecture,
            )
        )
        if os_version:
            stmt = stmt.where(OsImage.version == os_version)

        stmt = stmt.order_by(OsImage.sort_order, OsImage.version.desc())

        result = await db.execute(stmt)
        images = list(result.scalars().all())

        if not images:
            raise ValueError(
                f"No OS image found for family='{os_family}', version='{os_version}', arch='{architecture}'"
            )

        # Find the first image with a provider mapping for our provider
        for image in images:
            for mapping in (image.provider_mappings or []):
                if mapping.deleted_at is not None:
                    continue
                if context.provider_id and mapping.provider_id == context.provider_id:
                    return {
                        "image_id": str(image.id),
                        "image_reference": mapping.image_reference,
                        "image_name": image.display_name,
                    }

        # Fallback: return the first image even without provider mapping
        image = images[0]
        return {
            "image_id": str(image.id),
            "image_reference": "",
            "image_name": image.display_name,
        }

    async def release(
        self,
        allocation_ref: dict,
        config: dict,
        context: ResolverContext,
    ) -> bool:
        """Release an image reference — no-op since images are catalog lookups."""
        return True

    async def update(
        self,
        current: dict,
        new_params: dict,
        config: dict,
        context: ResolverContext,
    ) -> dict:
        """Update image selection — re-resolve with new params."""
        return await self.resolve(new_params, config, context)

    async def validate(
        self,
        params: dict,
        config: dict,
        context: ResolverContext,
    ) -> list[str]:
        """Validate image parameters — check os_family exists in catalog."""
        errors: list[str] = []
        os_family = params.get("os_family")
        if not os_family:
            errors.append("'os_family' parameter is required")
            return errors

        from app.models.os_image import OsImage

        db = context.db
        architecture = params.get(
            "architecture", config.get("default_architecture", "x86_64")
        )

        stmt = (
            select(OsImage.id)
            .where(
                OsImage.deleted_at.is_(None),
                OsImage.os_family.ilike(os_family),
                OsImage.architecture == architecture,
            )
            .limit(1)
        )
        os_version = params.get("os_version")
        if os_version:
            stmt = stmt.where(OsImage.version == os_version)

        result = await db.execute(stmt)
        if not result.scalar_one_or_none():
            errors.append(
                f"No OS image found for family='{os_family}', arch='{architecture}'"
                + (f", version='{os_version}'" if os_version else "")
            )

        return errors
