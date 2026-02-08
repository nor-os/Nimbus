"""
Overview: REST API endpoints for permission deny overrides management.
Architecture: Explicit deny override CRUD endpoints (Section 7.1)
Dependencies: fastapi, sqlalchemy, app.models, app.schemas.permission, app.api.deps
Concepts: Permission overrides, explicit deny, principal-scoped deny
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.group import Group
from app.models.permission import Permission
from app.models.permission_override import PermissionOverride
from app.models.role import Role
from app.models.user import User
from app.schemas.permission import (
    PermissionOverrideCreate,
    PermissionOverrideResponse,
)

router = APIRouter(prefix="/tenants/{tenant_id}/permission-overrides", tags=["permission-overrides"])


async def _resolve_principal_name(db: AsyncSession, principal_type: str, principal_id: str) -> str:
    """Resolve a principal ID to a display name."""
    if principal_type == "user":
        result = await db.execute(select(User.email).where(User.id == principal_id))
        row = result.first()
        return row[0] if row else str(principal_id)
    elif principal_type == "group":
        result = await db.execute(select(Group.name).where(Group.id == principal_id))
        row = result.first()
        return row[0] if row else str(principal_id)
    elif principal_type == "role":
        result = await db.execute(select(Role.name).where(Role.id == principal_id))
        row = result.first()
        return row[0] if row else str(principal_id)
    return str(principal_id)


@router.get("", response_model=list[PermissionOverrideResponse])
async def list_overrides(
    tenant_id: str,
    current_user: User = Depends(require_permission("permissions:abac:list")),
    db: AsyncSession = Depends(get_db),
) -> list[PermissionOverrideResponse]:
    """List all permission overrides for a tenant."""
    result = await db.execute(
        select(PermissionOverride, Permission)
        .join(Permission, Permission.id == PermissionOverride.permission_id)
        .where(PermissionOverride.tenant_id == tenant_id)
        .order_by(Permission.domain, Permission.resource, Permission.action)
    )

    responses = []
    for override, perm in result.all():
        principal_name = await _resolve_principal_name(
            db, override.principal_type, str(override.principal_id)
        )
        responses.append(
            PermissionOverrideResponse(
                id=override.id,
                tenant_id=override.tenant_id,
                permission_id=override.permission_id,
                permission_key=perm.key,
                principal_type=override.principal_type,
                principal_id=override.principal_id,
                principal_name=principal_name,
                effect=override.effect,
                reason=override.reason,
                created_at=override.created_at,
                updated_at=override.updated_at,
            )
        )
    return responses


@router.post("", response_model=PermissionOverrideResponse, status_code=status.HTTP_201_CREATED)
async def create_override(
    tenant_id: str,
    body: PermissionOverrideCreate,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:create")),
    db: AsyncSession = Depends(get_db),
) -> PermissionOverrideResponse:
    """Create a deny override for a permission."""
    # Verify permission exists
    perm_result = await db.execute(
        select(Permission).where(Permission.id == str(body.permission_id))
    )
    perm = perm_result.scalar_one_or_none()
    if not perm:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "PERMISSION_NOT_FOUND",
                    "message": "Permission not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Check for existing override
    existing = await db.execute(
        select(PermissionOverride).where(
            PermissionOverride.tenant_id == tenant_id,
            PermissionOverride.permission_id == str(body.permission_id),
            PermissionOverride.principal_type == body.principal_type,
            PermissionOverride.principal_id == str(body.principal_id),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": {
                    "code": "OVERRIDE_EXISTS",
                    "message": "A deny override already exists for this permission and principal",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    override = PermissionOverride(
        tenant_id=tenant_id,
        permission_id=str(body.permission_id),
        principal_type=body.principal_type,
        principal_id=str(body.principal_id),
        reason=body.reason,
        created_by=current_user.id,
    )
    db.add(override)
    await db.flush()

    principal_name = await _resolve_principal_name(
        db, override.principal_type, str(override.principal_id)
    )
    return PermissionOverrideResponse(
        id=override.id,
        tenant_id=override.tenant_id,
        permission_id=override.permission_id,
        permission_key=perm.key,
        principal_type=override.principal_type,
        principal_id=override.principal_id,
        principal_name=principal_name,
        effect=override.effect,
        reason=override.reason,
        created_at=override.created_at,
        updated_at=override.updated_at,
    )


@router.delete("/{override_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_override(
    tenant_id: str,
    override_id: str,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a permission deny override."""
    result = await db.execute(
        select(PermissionOverride).where(
            PermissionOverride.id == override_id,
            PermissionOverride.tenant_id == tenant_id,
        )
    )
    override = result.scalar_one_or_none()
    if not override:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "OVERRIDE_NOT_FOUND",
                    "message": "Permission override not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    await db.delete(override)
    await db.flush()
