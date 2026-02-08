"""
Overview: REST API endpoints for group management, membership, and role assignment.
Architecture: Group CRUD, user/group membership, and role endpoints (Section 7.1)
Dependencies: fastapi, app.services.permission.group_service, app.schemas.permission, app.api.deps
Concepts: RBAC, group management, flat groups with many-to-many nesting
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.permission import (
    GroupChildRequest,
    GroupCreate,
    GroupMemberRequest,
    GroupMembersResponse,
    GroupResponse,
    GroupRoleRequest,
    GroupUpdate,
    RoleResponse,
)
from app.schemas.user import UserResponse
from app.services.permission.group_service import GroupError, GroupService

router = APIRouter(prefix="/tenants/{tenant_id}/groups", tags=["groups"])


def _get_group_service(db: AsyncSession = Depends(get_db)) -> GroupService:
    return GroupService(db)


@router.get("", response_model=list[GroupResponse])
async def list_groups(
    tenant_id: str,
    current_user: User = Depends(require_permission("users:group:list")),
    service: GroupService = Depends(_get_group_service),
) -> list[GroupResponse]:
    """List all groups in a tenant."""
    groups = await service.list_groups(tenant_id)
    return [GroupResponse.model_validate(g) for g in groups]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    tenant_id: str,
    group_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:group:read")),
    service: GroupService = Depends(_get_group_service),
) -> GroupResponse:
    """Get a group by ID."""
    group = await service.get_group(group_id, tenant_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "GROUP_NOT_FOUND",
                    "message": "Group not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return GroupResponse.model_validate(group)


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    tenant_id: str,
    body: GroupCreate,
    request: Request,
    current_user: User = Depends(require_permission("users:group:create")),
    service: GroupService = Depends(_get_group_service),
) -> GroupResponse:
    """Create a new group."""
    try:
        group = await service.create_group(
            tenant_id=tenant_id,
            name=body.name,
            description=body.description,
        )
        return GroupResponse.model_validate(group)
    except GroupError as e:
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


@router.patch("/{group_id}", response_model=GroupResponse)
async def update_group(
    tenant_id: str,
    group_id: str,
    body: GroupUpdate,
    request: Request,
    current_user: User = Depends(require_permission("users:group:update")),
    service: GroupService = Depends(_get_group_service),
) -> GroupResponse:
    """Update a group."""
    try:
        group = await service.update_group(
            group_id=group_id,
            tenant_id=tenant_id,
            name=body.name,
            description=body.description,
        )
        return GroupResponse.model_validate(group)
    except GroupError as e:
        code = status.HTTP_404_NOT_FOUND if e.code == "GROUP_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
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


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    tenant_id: str,
    group_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:group:delete")),
    service: GroupService = Depends(_get_group_service),
) -> None:
    """Soft-delete a group."""
    try:
        await service.delete_group(group_id, tenant_id)
    except GroupError as e:
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


# ── User members ─────────────────────────────────────────────────────


@router.get("/{group_id}/members", response_model=GroupMembersResponse)
async def list_members(
    tenant_id: str,
    group_id: str,
    current_user: User = Depends(require_permission("users:group:read")),
    service: GroupService = Depends(_get_group_service),
) -> GroupMembersResponse:
    """List all members (users and child groups) of a group."""
    data = await service.get_group_members(group_id)
    return GroupMembersResponse(
        users=[UserResponse.model_validate(u) for u in data["users"]],
        groups=[GroupResponse.model_validate(g) for g in data["groups"]],
    )


@router.post("/{group_id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    tenant_id: str,
    group_id: str,
    body: GroupMemberRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:group:manage_members")),
    service: GroupService = Depends(_get_group_service),
) -> dict:
    """Add a user to a group."""
    try:
        ug = await service.add_member(group_id, str(body.user_id))
        return {"user_id": str(ug.user_id), "group_id": str(ug.group_id)}
    except GroupError as e:
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


@router.delete("/{group_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    tenant_id: str,
    group_id: str,
    user_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:group:manage_members")),
    service: GroupService = Depends(_get_group_service),
) -> None:
    """Remove a user from a group."""
    try:
        await service.remove_member(group_id, user_id)
    except GroupError as e:
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


# ── Group-in-group membership ────────────────────────────────────────


@router.post("/{group_id}/members/group", status_code=status.HTTP_201_CREATED)
async def add_child_group(
    tenant_id: str,
    group_id: str,
    body: GroupChildRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:group:manage_members")),
    service: GroupService = Depends(_get_group_service),
) -> dict:
    """Add a group as a member of this group."""
    try:
        membership = await service.add_child_group(group_id, str(body.group_id))
        return {
            "parent_group_id": str(membership.parent_group_id),
            "child_group_id": str(membership.child_group_id),
        }
    except GroupError as e:
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


@router.delete(
    "/{group_id}/members/group/{child_group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_child_group(
    tenant_id: str,
    group_id: str,
    child_group_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:group:manage_members")),
    service: GroupService = Depends(_get_group_service),
) -> None:
    """Remove a group from this group's members."""
    try:
        await service.remove_child_group(group_id, child_group_id)
    except GroupError as e:
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


@router.get("/{group_id}/member-of", response_model=list[GroupResponse])
async def get_member_of(
    tenant_id: str,
    group_id: str,
    current_user: User = Depends(require_permission("users:group:read")),
    service: GroupService = Depends(_get_group_service),
) -> list[GroupResponse]:
    """List groups this group is a member of (parent groups)."""
    parents = await service.get_parent_groups(group_id)
    return [GroupResponse.model_validate(g) for g in parents]


# ── Group roles ──────────────────────────────────────────────────────


@router.get("/{group_id}/roles", response_model=list[RoleResponse])
async def list_group_roles(
    tenant_id: str,
    group_id: str,
    current_user: User = Depends(require_permission("users:group:read")),
    service: GroupService = Depends(_get_group_service),
) -> list[RoleResponse]:
    """List roles assigned to a group."""
    roles = await service.get_group_roles(group_id)
    return [RoleResponse.model_validate(r) for r in roles]


@router.post("/{group_id}/roles", status_code=status.HTTP_201_CREATED)
async def assign_role_to_group(
    tenant_id: str,
    group_id: str,
    body: GroupRoleRequest,
    request: Request,
    current_user: User = Depends(require_permission("users:role:assign")),
    service: GroupService = Depends(_get_group_service),
) -> dict:
    """Assign a role to a group."""
    try:
        gr = await service.assign_role(group_id, str(body.role_id))
        return {"group_id": str(gr.group_id), "role_id": str(gr.role_id)}
    except GroupError as e:
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


@router.delete("/{group_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_role_from_group(
    tenant_id: str,
    group_id: str,
    role_id: str,
    request: Request,
    current_user: User = Depends(require_permission("users:role:assign")),
    service: GroupService = Depends(_get_group_service),
) -> None:
    """Remove a role from a group."""
    try:
        await service.unassign_role(group_id, role_id)
    except GroupError as e:
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
