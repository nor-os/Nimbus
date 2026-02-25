"""
Overview: GraphQL mutations for policy library CRUD operations.
Architecture: Mutation resolvers for governance policies (Section 7.2)
Dependencies: strawberry, app.services.policy.*, app.api.graphql.auth
Concepts: Policy CRUD, statement validation, permission-gated management
"""

import logging
import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.queries.policy import _entry_to_type
from app.api.graphql.types.policy import (
    PolicyLibraryCreateInput,
    PolicyLibraryEntryType,
    PolicyLibraryUpdateInput,
)

logger = logging.getLogger(__name__)


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class PolicyMutation:

    @strawberry.mutation
    async def create_policy_library_entry(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        input: PolicyLibraryCreateInput,
    ) -> PolicyLibraryEntryType:
        """Create a new policy library entry."""
        user_id = await check_graphql_permission(
            info, "policy:library:manage", str(tenant_id)
        )

        from app.services.policy.policy_library_service import PolicyLibraryService

        db = await _get_session(info)
        svc = PolicyLibraryService(db)

        # Validate statements
        statements = input.statements if isinstance(input.statements, list) else []
        errors = PolicyLibraryService.validate_statements(statements)
        if errors:
            raise ValueError(f"Invalid statements: {'; '.join(errors)}")

        data = {
            "name": input.name,
            "display_name": input.display_name,
            "description": input.description,
            "category": input.category,
            "statements": statements,
            "variables": input.variables,
            "severity": input.severity,
            "tags": input.tags,
        }
        entry = await svc.create(str(tenant_id), str(user_id), data)
        await db.commit()
        return _entry_to_type(entry)

    @strawberry.mutation
    async def update_policy_library_entry(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
        input: PolicyLibraryUpdateInput,
    ) -> PolicyLibraryEntryType | None:
        """Update a policy library entry."""
        await check_graphql_permission(
            info, "policy:library:manage", str(tenant_id)
        )

        from app.services.policy.policy_library_service import PolicyLibraryService

        db = await _get_session(info)
        svc = PolicyLibraryService(db)

        data = {}
        if input.name is not None:
            data["name"] = input.name
        if input.display_name is not None:
            data["display_name"] = input.display_name
        if input.description is not None:
            data["description"] = input.description
        if input.category is not None:
            data["category"] = input.category
        if input.statements is not None:
            statements = input.statements if isinstance(input.statements, list) else []
            errors = PolicyLibraryService.validate_statements(statements)
            if errors:
                raise ValueError(f"Invalid statements: {'; '.join(errors)}")
            data["statements"] = statements
        if input.variables is not None:
            data["variables"] = input.variables
        if input.severity is not None:
            data["severity"] = input.severity
        if input.tags is not None:
            data["tags"] = input.tags

        entry = await svc.update(str(tenant_id), str(policy_id), data)
        await db.commit()
        return _entry_to_type(entry) if entry else None

    @strawberry.mutation
    async def delete_policy_library_entry(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        policy_id: uuid.UUID,
    ) -> bool:
        """Soft-delete a policy library entry."""
        await check_graphql_permission(
            info, "policy:library:manage", str(tenant_id)
        )

        from app.services.policy.policy_library_service import PolicyLibraryService

        db = await _get_session(info)
        svc = PolicyLibraryService(db)
        result = await svc.delete(str(tenant_id), str(policy_id))
        await db.commit()
        return result
