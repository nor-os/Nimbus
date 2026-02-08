"""
Overview: REST API endpoints for user management and tenant membership within tenant context.
Architecture: User CRUD + tenant membership endpoints (Section 7.1)
Dependencies: fastapi, app.services.user, app.schemas.user, app.api.deps
Concepts: User management, tenant-scoped users, tenant membership, pagination
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_not_impersonating
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserDetailResponse,
    UserGroupInfo,
    UserListResponse,
    UserResponse,
    UserRoleInfo,
    UserUpdate,
)
from app.services.user.service import UserError, UserService

router = APIRouter(prefix="/tenants/{tenant_id}/users", tags=["users"])


def _get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)


@router.get("", response_model=UserListResponse)
async def list_users(
    tenant_id: str,
    offset: int = 0,
    limit: int = 50,
    search: str | None = None,
    current_user: User = Depends(require_permission("users:user:list")),
    service: UserService = Depends(_get_user_service),
) -> UserListResponse:
    """List users in a tenant with optional search."""
    users, total = await service.list_users(tenant_id, offset, limit, search)
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{user_id}", response_model=UserDetailResponse)
async def get_user(
    tenant_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:user:read")),
    service: UserService = Depends(_get_user_service),
    db: AsyncSession = Depends(get_db),
) -> UserDetailResponse:
    """Get user detail with roles, groups, and permissions."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.models.group import Group
    from app.models.role import Role
    from app.models.user_group import UserGroup
    from app.models.user_role import UserRole

    user = await service.get_user(user_id, tenant_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "USER_NOT_FOUND",
                    "message": "User not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Load roles
    role_result = await db.execute(
        select(UserRole, Role.name)
        .join(Role, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id, UserRole.tenant_id == tenant_id)
    )
    roles = [
        UserRoleInfo(
            id=ur.id,
            role_id=ur.role_id,
            role_name=role_name,
            tenant_id=ur.tenant_id,
            compartment_id=ur.compartment_id,
            granted_at=ur.granted_at,
            expires_at=ur.expires_at,
        )
        for ur, role_name in role_result.all()
    ]

    # Load groups
    group_result = await db.execute(
        select(UserGroup, Group.name)
        .join(Group, Group.id == UserGroup.group_id)
        .where(UserGroup.user_id == user_id, Group.deleted_at.is_(None))
    )
    groups = [
        UserGroupInfo(id=ug.id, group_id=ug.group_id, group_name=group_name)
        for ug, group_name in group_result.all()
    ]

    return UserDetailResponse(
        **UserResponse.model_validate(user).model_dump(),
        roles=roles,
        groups=groups,
    )


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    tenant_id: str,
    body: UserCreate,
    request: Request,
    current_user: User = Depends(require_permission("users:user:create")),
    service: UserService = Depends(_get_user_service),
) -> UserResponse:
    """Create a new user in a tenant."""
    try:
        user = await service.create_user(
            tenant_id=tenant_id,
            email=body.email,
            password=body.password,
            display_name=body.display_name,
            role_ids=[str(rid) for rid in body.role_ids],
            group_ids=[str(gid) for gid in body.group_ids],
            identity_provider_id=str(body.identity_provider_id) if body.identity_provider_id else None,
            external_id=body.external_id,
        )
        return UserResponse.model_validate(user)
    except UserError as e:
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


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    tenant_id: str,
    user_id: str,
    body: UserUpdate,
    request: Request,
    current_user: User = Depends(require_permission("users:user:update")),
    service: UserService = Depends(_get_user_service),
) -> UserResponse:
    """Update a user's attributes."""
    try:
        user = await service.update_user(
            user_id=user_id,
            tenant_id=tenant_id,
            display_name=body.display_name,
            is_active=body.is_active,
        )
        return UserResponse.model_validate(user)
    except UserError as e:
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


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_user(
    tenant_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_not_impersonating),
    _perm: User = Depends(require_permission("users:user:delete")),
    service: UserService = Depends(_get_user_service),
) -> None:
    """Deactivate (soft-delete) a user."""
    try:
        await service.deactivate_user(user_id, tenant_id)
    except UserError as e:
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


@router.post("/{user_id}/tenant-membership", status_code=status.HTTP_201_CREATED)
async def add_user_to_tenant(
    tenant_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:user:create")),
    service: UserService = Depends(_get_user_service),
) -> dict:
    """Add an existing user to this tenant."""
    try:
        await service.assign_user_to_tenant(user_id, tenant_id)
        return {"user_id": user_id, "tenant_id": tenant_id}
    except UserError as e:
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


@router.delete("/{user_id}/tenant-membership", status_code=status.HTTP_204_NO_CONTENT)
async def remove_user_from_tenant(
    tenant_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:user:delete")),
    service: UserService = Depends(_get_user_service),
) -> None:
    """Remove a user from this tenant."""
    try:
        await service.remove_user_from_tenant(user_id, tenant_id)
    except UserError as e:
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
