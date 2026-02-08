"""
Overview: REST API endpoints for role management and assignment.
Architecture: Role CRUD and assignment endpoints (Section 7.1)
Dependencies: fastapi, app.services.permission.role_service, app.schemas.permission, app.api.deps
Concepts: RBAC, role management, role assignment
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_not_impersonating
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.permission import (
    PermissionResponse,
    RoleAssignRequest,
    RoleCreate,
    RoleDetailResponse,
    RoleResponse,
    RoleUnassignRequest,
    RoleUpdate,
)
from app.services.permission.role_service import RoleError, RoleService

router = APIRouter(prefix="/tenants/{tenant_id}/roles", tags=["roles"])


def _get_role_service(db: AsyncSession = Depends(get_db)) -> RoleService:
    return RoleService(db)


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    tenant_id: str,
    current_user: User = Depends(require_permission("users:role:list")),
    service: RoleService = Depends(_get_role_service),
) -> list[RoleResponse]:
    """List roles for a tenant (including system roles)."""
    roles = await service.list_roles(tenant_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.get("/{role_id}", response_model=RoleDetailResponse)
async def get_role(
    tenant_id: str,
    role_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:role:read")),
    service: RoleService = Depends(_get_role_service),
) -> RoleDetailResponse:
    """Get role detail with permissions."""
    role = await service.get_role(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "ROLE_NOT_FOUND",
                    "message": "Role not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    permissions = await service.get_role_permissions(role_id)
    return RoleDetailResponse(
        **RoleResponse.model_validate(role).model_dump(),
        permissions=[PermissionResponse.model_validate(p) for p in permissions],
    )


@router.post("", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    tenant_id: str,
    body: RoleCreate,
    request: Request,
    current_user: User = Depends(require_permission("users:role:create")),
    service: RoleService = Depends(_get_role_service),
) -> RoleResponse:
    """Create a custom role."""
    try:
        role = await service.create_role(
            tenant_id=tenant_id,
            name=body.name,
            description=body.description,
            scope=body.scope or "tenant",
            parent_role_id=str(body.parent_role_id) if body.parent_role_id else None,
            permission_ids=[str(pid) for pid in body.permission_ids],
            max_level=body.max_level,
        )
        return RoleResponse.model_validate(role)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    tenant_id: str,
    role_id: str,
    body: RoleUpdate,
    request: Request,
    current_user: User = Depends(require_not_impersonating),
    _perm: User = Depends(require_permission("users:role:update")),
    service: RoleService = Depends(_get_role_service),
) -> RoleResponse:
    """Update a custom role."""
    try:
        role = await service.update_role(
            role_id=role_id,
            name=body.name,
            description=body.description,
            permission_ids=[str(pid) for pid in body.permission_ids] if body.permission_ids else None,
            max_level=body.max_level,
        )
        return RoleResponse.model_validate(role)
    except RoleError as e:
        code = status.HTTP_404_NOT_FOUND if e.code == "ROLE_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=code,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    tenant_id: str,
    role_id: str,
    request: Request,
    current_user: User = Depends(require_not_impersonating),
    _perm: User = Depends(require_permission("users:role:delete")),
    service: RoleService = Depends(_get_role_service),
) -> None:
    """Soft-delete a custom role."""
    try:
        await service.delete_role(role_id)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/assign", status_code=status.HTTP_201_CREATED)
async def assign_role(
    tenant_id: str,
    body: RoleAssignRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:role:assign")),
    service: RoleService = Depends(_get_role_service),
) -> dict:
    """Assign a role to a user."""
    try:
        ur = await service.assign_role(
            user_id=str(body.user_id),
            role_id=str(body.role_id),
            tenant_id=tenant_id,
            compartment_id=str(body.compartment_id) if body.compartment_id else None,
            granted_by=str(current_user.id),
            expires_at=body.expires_at,
        )
        return {"id": str(ur.id), "user_id": str(ur.user_id), "role_id": str(ur.role_id)}
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/unassign", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_role(
    tenant_id: str,
    body: RoleUnassignRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:role:assign")),
    service: RoleService = Depends(_get_role_service),
) -> None:
    """Remove a role assignment from a user."""
    try:
        await service.unassign_role(str(body.user_id), str(body.role_id), tenant_id)
    except RoleError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


