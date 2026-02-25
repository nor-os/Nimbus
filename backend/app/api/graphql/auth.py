"""
Overview: GraphQL authentication and permission checking utilities.
Architecture: GraphQL context helpers for permission enforcement (Section 5.2)
Dependencies: strawberry, app.services.auth.jwt, app.api.graphql.context
Concepts: GraphQL authentication, permission checking, per-request caching
"""

from jose.exceptions import ExpiredSignatureError, JWTError
from strawberry.types import Info

from app.services.auth.jwt import decode_token


async def check_graphql_permission(info: Info, permission_key: str, tenant_id: str) -> str:
    """Check permission for the authenticated user in GraphQL context.

    Returns the user_id if authorized. Raises PermissionError if not.
    Uses the shared NimbusContext session and permission cache to avoid
    redundant DB connections within the same request.
    """
    request = info.context.request
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise PermissionError("Not authenticated")

    token = auth_header[7:]
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise PermissionError("Token expired")
    except JWTError:
        raise PermissionError("Not authenticated")
    user_id = payload["sub"]

    # Fall back to JWT's current_tenant_id for provider-mode (no explicit tenant)
    effective_tenant_id = tenant_id or payload.get("current_tenant_id", "")

    # Use context's cached permission check if NimbusContext is available
    ctx = info.context
    if hasattr(ctx, "check_permission_cached"):
        allowed = await ctx.check_permission_cached(user_id, permission_key, effective_tenant_id)
    else:
        # Fallback for non-NimbusContext (e.g., tests)
        from app.db.session import async_session_factory
        from app.services.permission.engine import PermissionEngine

        async with async_session_factory() as db:
            engine = PermissionEngine(db)
            allowed, _source = await engine.check_permission(
                user_id, permission_key, effective_tenant_id
            )

    if not allowed:
        raise PermissionError(f"Missing permission: {permission_key}")

    return user_id
