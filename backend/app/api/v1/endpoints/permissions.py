"""
Overview: REST API endpoints for permission checking and effective permissions.
Architecture: Permission query endpoints (Section 7.1)
Dependencies: fastapi, app.services.permission, app.schemas.permission, app.api.deps
Concepts: Permission checking, effective permissions, permission simulation
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_tenant_id
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.permission import Permission
from app.models.user import User
from app.schemas.permission import (
    EffectivePermissionResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    PermissionResponse,
    PermissionSimulateRequest,
    PermissionSimulateResponse,
)
from app.services.permission.engine import PermissionEngine

router = APIRouter(tags=["permissions"])


@router.get("/tenants/{tenant_id}/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    tenant_id: str,
    current_user: User = Depends(require_permission("users:role:read")),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionResponse]:
    """List all permission definitions."""
    result = await db.execute(select(Permission).order_by(Permission.domain, Permission.resource, Permission.action))
    permissions = result.scalars().all()
    return [
        PermissionResponse(
            id=p.id,
            domain=p.domain,
            resource=p.resource,
            action=p.action,
            subtype=p.subtype,
            description=p.description,
            is_system=p.is_system,
            key=p.key,
        )
        for p in permissions
    ]


@router.post("/permissions/check", response_model=PermissionCheckResponse)
async def check_permission(
    body: PermissionCheckRequest,
    request: Request,
    current_user: User = Depends(require_permission("permissions:permission:check")),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PermissionCheckResponse:
    """Check if the current user has a specific permission."""
    engine = PermissionEngine(db)
    allowed, source = await engine.check_permission(
        user_id=str(current_user.id),
        permission_key=body.permission_key,
        tenant_id=tenant_id,
        resource=body.resource,
        context=body.context,
    )
    return PermissionCheckResponse(
        allowed=allowed, permission_key=body.permission_key, source=source
    )


@router.get("/permissions/me", response_model=list[EffectivePermissionResponse])
async def my_permissions(
    current_user: User = Depends(get_current_user),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[EffectivePermissionResponse]:
    """Get the current user's effective permissions."""
    engine = PermissionEngine(db)
    effective = await engine.get_effective_permissions(str(current_user.id), tenant_id)
    return [
        EffectivePermissionResponse(
            permission_key=ep.permission_key,
            source=ep.source,
            role_name=ep.role_name,
            group_name=ep.group_name,
            source_tenant_id=ep.source_tenant_id,
            source_tenant_name=ep.source_tenant_name,
            is_inherited=ep.is_inherited,
            is_denied=ep.is_denied,
            deny_source=ep.deny_source,
        )
        for ep in effective
    ]


@router.get("/permissions/users/{user_id}", response_model=list[EffectivePermissionResponse])
async def user_permissions(
    user_id: str,
    current_user: User = Depends(require_permission("users:user:read")),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> list[EffectivePermissionResponse]:
    """Get a specific user's effective permissions."""
    engine = PermissionEngine(db)
    effective = await engine.get_effective_permissions(user_id, tenant_id)
    return [
        EffectivePermissionResponse(
            permission_key=ep.permission_key,
            source=ep.source,
            role_name=ep.role_name,
            group_name=ep.group_name,
            source_tenant_id=ep.source_tenant_id,
            source_tenant_name=ep.source_tenant_name,
            is_inherited=ep.is_inherited,
            is_denied=ep.is_denied,
            deny_source=ep.deny_source,
        )
        for ep in effective
    ]


@router.post("/permissions/simulate", response_model=PermissionSimulateResponse)
async def simulate_permission(
    body: PermissionSimulateRequest,
    request: Request,
    current_user: User = Depends(require_permission("permissions:permission:simulate")),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),
) -> PermissionSimulateResponse:
    """Simulate a permission check for a given user."""
    engine = PermissionEngine(db)
    allowed, source = await engine.check_permission(
        user_id=str(body.user_id),
        permission_key=body.permission_key,
        tenant_id=tenant_id,
        resource=body.resource,
        context=body.context,
    )
    return PermissionSimulateResponse(
        allowed=allowed,
        permission_key=body.permission_key,
        source=source,
        evaluation_steps=[
            f"Checked RBAC for user {body.user_id}",
            f"Checked ABAC policies for tenant {tenant_id}",
            f"Result: {'allowed' if allowed else 'denied'} via {source or 'no match'}",
        ],
    )
