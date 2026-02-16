"""
Overview: Resolver setup — registers all built-in resolver handlers on startup.
Architecture: Resolver initialization (Section 11)
Dependencies: app.services.resolver.registry, app.services.resolver.*_resolver
Concepts: Called during app startup to populate the global resolver registry with built-in handlers.
"""

from __future__ import annotations

from app.services.resolver.registry import get_resolver_registry
from app.services.resolver.ipam_resolver import IPAMResolver
from app.services.resolver.naming_resolver import NamingResolver
from app.services.resolver.image_resolver import ImageCatalogResolver


def setup_resolvers() -> None:
    """Register all built-in resolver handlers."""
    registry = get_resolver_registry()
    registry.register("ipam", IPAMResolver())
    registry.register("naming", NamingResolver())
    registry.register("image_catalog", ImageCatalogResolver())
