"""
Overview: FastAPI dependency injection for auth, database, tenant context, and request context.
Architecture: Dependency layer between endpoints and services (Section 3.1)
Dependencies: fastapi, app.db.session, app.services.auth, app.core.tenant_context
Concepts: Dependency injection, authentication context, tenant context, permission checking
"""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.services.auth.service import AuthError, AuthService

_bearer_scheme = HTTPBearer()


async def get_auth_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(db)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate the bearer token and return the authenticated user."""
    auth_service = AuthService(db)
    try:
        payload = await auth_service.validate_token(credentials.credentials)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    from sqlalchemy import select

    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()

    if not user or not user.is_active or user.is_deleted:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "USER_INVALID",
                    "message": "User not found or disabled",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Store JTI and user_id on request for logout and actor tracking
    request.state.jti = payload["jti"]
    request.state.user_id = str(user.id)

    # Store impersonation context if present
    impersonating = payload.get("impersonating")
    if impersonating:
        request.state.impersonating = impersonating
    else:
        request.state.impersonating = None

    return user


def get_current_tenant_id(request: Request) -> str:
    """Extract the current tenant ID from request state (set by TenantContextMiddleware)."""
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "NO_TENANT_CONTEXT",
                    "message": "No tenant context — include current_tenant_id in JWT",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return tenant_id


def get_real_actor_id(request: Request) -> str:
    """Return the original user ID if impersonating, else current user's ID."""
    impersonating = getattr(request.state, "impersonating", None)
    if impersonating:
        return impersonating["original_user"]
    # Fall back to the sub claim stored by get_current_user
    return getattr(request.state, "user_id", "")


async def require_not_impersonating(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    """Block dangerous operations during impersonation."""
    if getattr(request.state, "impersonating", None):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "IMPERSONATION_BLOCKED",
                    "message": "This operation is not allowed during impersonation",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return current_user


async def require_provider_level(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Require provider-level access. Uses PermissionEngine for real RBAC checks."""
    tenant_id = getattr(request.state, "current_tenant_id", None)
    if not tenant_id:
        # No tenant context — allow if authenticated (backward compat for setup flow)
        return current_user

    from app.services.permission.engine import PermissionEngine

    engine = PermissionEngine(db)
    allowed, _ = await engine.check_permission(
        str(current_user.id), "*:*:*", tenant_id
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PROVIDER_ACCESS_REQUIRED",
                    "message": "Provider-level access required",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return current_user
