"""
Overview: Permission decorators for endpoint-level access control.
Architecture: Decorator-based permission checking (Section 5.2)
Dependencies: fastapi, app.services.permission.engine
Concepts: Permission decorators, RBAC enforcement, endpoint protection
"""

from functools import wraps

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.services.permission.engine import PermissionEngine


def require_permission(permission_key: str):
    """FastAPI dependency that checks a single permission."""

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
        tenant_id: str = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        engine = PermissionEngine(db)
        allowed, source = await engine.check_permission(
            str(current_user.id), permission_key, tenant_id
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": f"Missing permission: {permission_key}",
                        "trace_id": getattr(request.state, "trace_id", None),
                    }
                },
            )
        return current_user

    return _check


def require_any_permission(*permission_keys: str):
    """FastAPI dependency that checks if user has any of the given permissions."""

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
        tenant_id: str = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        engine = PermissionEngine(db)
        for key in permission_keys:
            allowed, _ = await engine.check_permission(
                str(current_user.id), key, tenant_id
            )
            if allowed:
                return current_user

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": f"Missing any of: {', '.join(permission_keys)}",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    return _check


def require_all_permissions(*permission_keys: str):
    """FastAPI dependency that checks if user has all of the given permissions."""

    async def _check(
        request: Request,
        current_user: User = Depends(get_current_user),
        tenant_id: str = Depends(get_current_tenant_id),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        engine = PermissionEngine(db)
        missing = []
        for key in permission_keys:
            allowed, _ = await engine.check_permission(
                str(current_user.id), key, tenant_id
            )
            if not allowed:
                missing.append(key)

        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "PERMISSION_DENIED",
                        "message": f"Missing permissions: {', '.join(missing)}",
                        "trace_id": getattr(request.state, "trace_id", None),
                    }
                },
            )
        return current_user

    return _check
