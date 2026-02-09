"""
Overview: Mapping engine — resolves provider resources to semantic types. Providers call this
    engine rather than implementing mapping logic individually.
Architecture: Core mapping resolution layer between providers and the semantic model (Section 5)
Dependencies: app.services.semantic.registry, app.services.semantic.data_classes
Concepts: Resolution strategy: exact match → pattern match → unmapped. The engine loads
    mappings from the registry and converts raw ProviderResource objects into SemanticResource
    objects with the correct type and normalized attributes.
"""

from __future__ import annotations

import logging
import re

from app.services.semantic.data_classes import (
    ProviderResource,
    SemanticResource,
)
from app.services.semantic.registry import (
    PROVIDER_RESOURCE_TYPES,
    TYPE_MAPPINGS,
    ProviderResourceTypeDef,
    SemanticTypeDef,
    TypeMappingDef,
    get_provider_resource_types,
    get_type,
    get_type_mappings_for_provider,
)

logger = logging.getLogger(__name__)

# The fallback type name for unmapped resources
UNMAPPED_TYPE = "UnmappedResource"


class MappingEngine:
    """Resolves provider-specific resources to semantic types."""

    def __init__(self) -> None:
        # Build lookup index: (provider_name, api_type) -> TypeMappingDef
        self._exact_index: dict[tuple[str, str], TypeMappingDef] = {}
        for mapping in TYPE_MAPPINGS:
            key = (mapping.provider_name.lower(), mapping.api_type.lower())
            self._exact_index[key] = mapping

    def resolve(
        self, provider_name: str, provider_resource_type: str
    ) -> SemanticTypeDef | None:
        """Resolve a provider resource type to a semantic type definition.

        Strategy: exact match → pattern match → None.
        """
        # Exact match
        mapping = self._exact_match(provider_name, provider_resource_type)
        if mapping:
            return get_type(mapping.semantic_type_name)

        # Pattern match (partial string matching for provider resource types)
        mapping = self._pattern_match(provider_name, provider_resource_type)
        if mapping:
            return get_type(mapping.semantic_type_name)

        return None

    def map_resource(self, provider_resource: ProviderResource) -> SemanticResource:
        """Convert a raw ProviderResource into a SemanticResource.

        If no mapping exists, returns a SemanticResource with type=UnmappedResource.
        """
        type_def = self.resolve(
            provider_resource.provider_name, provider_resource.resource_type
        )

        if type_def is None:
            logger.info(
                "No semantic mapping for %s/%s — marking as unmapped",
                provider_resource.provider_name,
                provider_resource.resource_type,
            )
            return SemanticResource(
                semantic_type=UNMAPPED_TYPE,
                provider_resource_id=provider_resource.resource_id,
                attributes=provider_resource.raw_attributes,
            )

        # Extract and normalize attributes based on the type's property schema
        attributes = self._extract_attributes(type_def, provider_resource.raw_attributes)

        return SemanticResource(
            semantic_type=type_def.name,
            provider_resource_id=provider_resource.resource_id,
            attributes=attributes,
        )

    def get_provider_resource_types(
        self, provider_name: str
    ) -> list[ProviderResourceTypeDef]:
        """Get all resource type definitions for a given provider."""
        return get_provider_resource_types(provider_name)

    def get_mappings_for_provider(self, provider_name: str) -> list[TypeMappingDef]:
        """Get all type mappings for a given provider."""
        return get_type_mappings_for_provider(provider_name)

    def _exact_match(
        self, provider_name: str, provider_resource_type: str
    ) -> TypeMappingDef | None:
        """Try an exact case-insensitive match."""
        key = (provider_name.lower(), provider_resource_type.lower())
        return self._exact_index.get(key)

    def _pattern_match(
        self, provider_name: str, provider_resource_type: str
    ) -> TypeMappingDef | None:
        """Try partial matching on the provider resource type.

        Checks if any registered mapping's resource type is a substring of the
        given resource type (or vice versa).
        """
        provider_lower = provider_name.lower()
        resource_lower = provider_resource_type.lower()

        for mapping in TYPE_MAPPINGS:
            if mapping.provider_name.lower() != provider_lower:
                continue
            registered = mapping.api_type.lower()
            if registered in resource_lower or resource_lower in registered:
                return mapping

        return None

    @staticmethod
    def _extract_attributes(
        type_def: SemanticTypeDef, raw_attributes: dict
    ) -> dict:
        """Extract attributes from raw data based on the type's property schema.

        For each property in the type definition, look for a matching key in
        raw_attributes (exact or snake_case match). Include raw attributes that
        don't match any property under an 'extra' key.
        """
        result: dict = {}
        matched_keys: set[str] = set()

        for prop in type_def.properties:
            # Try exact match first, then snake_case variations
            candidates = [
                prop.name,
                prop.name.lower(),
                _to_snake_case(prop.name),
            ]
            for candidate in candidates:
                if candidate in raw_attributes:
                    result[prop.name] = raw_attributes[candidate]
                    matched_keys.add(candidate)
                    break
            else:
                # Property not found in raw attributes — use default if available
                if prop.default_value is not None:
                    result[prop.name] = prop.default_value

        # Collect unmatched raw attributes
        extra = {k: v for k, v in raw_attributes.items() if k not in matched_keys}
        if extra:
            result["_extra"] = extra

        return result


def _to_snake_case(name: str) -> str:
    """Convert camelCase or PascalCase to snake_case."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()
