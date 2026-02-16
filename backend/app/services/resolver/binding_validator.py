"""
Overview: Resolver binding validator — validates component bindings and suggests compatible resolvers.
Architecture: Validation service for resolver-component binding (Section 11)
Dependencies: sqlalchemy, app.models.resolver, app.models.component
Concepts: Schema-matched binding validation. Matches resolver output_schema field types to
    component input field types. Suggests compatible resolvers for a given field type and provider.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.resolver import Resolver, ResolverProviderCompatibility


class ResolverBindingValidator:

    async def suggest_resolvers_for_field(
        self,
        db: AsyncSession,
        field_type: str,
        provider_id: uuid.UUID | None = None,
    ) -> list[dict]:
        """Suggest resolvers whose output_schema contains fields matching the given type.

        Args:
            db: Database session.
            field_type: The JSON Schema type of the field (e.g., 'string', 'object', 'integer').
            provider_id: Optional provider filter.

        Returns:
            List of dicts with resolver info and matching output fields.
        """
        stmt = select(Resolver).where(Resolver.deleted_at.is_(None))

        if provider_id:
            stmt = stmt.join(
                ResolverProviderCompatibility,
                ResolverProviderCompatibility.resolver_id == Resolver.id,
            ).where(
                ResolverProviderCompatibility.provider_id == provider_id,
            )

        result = await db.execute(stmt)
        resolvers = list(result.scalars().all())

        suggestions = []
        for r in resolvers:
            output_schema = r.output_schema or {}
            properties = output_schema.get("properties", {})

            matching_fields = []
            for fname, fdef in properties.items():
                ftype = fdef.get("type", "")
                if ftype == field_type or field_type == "object":
                    matching_fields.append(fname)

            if matching_fields:
                suggestions.append({
                    "resolver_id": str(r.id),
                    "resolver_type": r.resolver_type,
                    "display_name": r.display_name,
                    "matching_fields": matching_fields,
                })

        return suggestions

    async def validate_bindings(
        self,
        db: AsyncSession,
        component_id: uuid.UUID,
    ) -> list[str]:
        """Validate resolver bindings on a component.

        Returns list of warning strings (non-blocking).
        """
        from app.models.component import Component

        result = await db.execute(
            select(Component).where(
                Component.id == component_id,
                Component.deleted_at.is_(None),
            )
        )
        component = result.scalar_one_or_none()
        if not component:
            return [f"Component {component_id} not found"]

        warnings: list[str] = []
        bindings = component.resolver_bindings or {}
        input_schema = component.input_schema or {}
        input_properties = input_schema.get("properties", {})

        # Load all resolvers for lookup
        resolver_result = await db.execute(
            select(Resolver).where(Resolver.deleted_at.is_(None))
        )
        resolvers_by_type = {r.resolver_type: r for r in resolver_result.scalars().all()}

        for param_name, binding in bindings.items():
            resolver_type = binding.get("resolver_type")
            if not resolver_type:
                warnings.append(f"Binding for '{param_name}' has no resolver_type")
                continue

            resolver = resolvers_by_type.get(resolver_type)
            if not resolver:
                warnings.append(f"Resolver type '{resolver_type}' not found for binding '{param_name}'")
                continue

            # Check provider compatibility
            if component.provider_id:
                compat_result = await db.execute(
                    select(ResolverProviderCompatibility).where(
                        ResolverProviderCompatibility.resolver_id == resolver.id,
                        ResolverProviderCompatibility.provider_id == component.provider_id,
                    )
                )
                if not compat_result.scalar_one_or_none():
                    warnings.append(
                        f"Resolver '{resolver_type}' is not compatible with component's provider"
                    )

            # Check that the target field exists in input_schema
            target = binding.get("target", param_name)
            if isinstance(target, str) and target not in input_properties:
                warnings.append(
                    f"Target field '{target}' not found in component input schema"
                )

        return warnings
