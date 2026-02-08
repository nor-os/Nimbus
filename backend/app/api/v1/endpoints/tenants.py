"""
Overview: REST API endpoints for tenant CRUD, hierarchy, stats, settings, and quotas.
Architecture: Tenant management endpoints (Section 7.1)
Dependencies: fastapi, app.services.tenant, app.schemas.tenant, app.api.deps
Concepts: Multi-tenancy, tenant lifecycle, quota management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user, require_not_impersonating
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.tenant import (
    QuotaResponse,
    QuotaUpdate,
    TenantCreate,
    TenantDetailResponse,
    TenantHierarchyResponse,
    TenantResponse,
    TenantSettingCreate,
    TenantSettingResponse,
    TenantStatsResponse,
    TenantUpdate,
)
from app.services.tenant.quota_service import QuotaExceededError, QuotaService
from app.services.tenant.service import TenantError, TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreate,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:create")),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Create a new tenant and associate the creating user with it."""
    from app.models.user_tenant import UserTenant

    service = TenantService(db)
    try:
        tenant = await service.create_tenant(
            name=body.name,
            provider_id=str(current_user.provider_id),
            parent_id=str(body.parent_id) if body.parent_id else None,
            contact_email=body.contact_email,
            billing_info=body.billing_info,
            description=body.description,
        )
        # Give the creating user access to the new tenant
        db.add(UserTenant(user_id=current_user.id, tenant_id=tenant.id))
        await db.flush()
        return TenantResponse.model_validate(tenant)
    except (TenantError, QuotaExceededError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": getattr(e, "code", "QUOTA_EXCEEDED"),
                    "message": str(e) if isinstance(e, QuotaExceededError) else e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    request: Request,
    offset: int = 0,
    limit: int = 50,
    parent_id: str | None = None,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> list[TenantResponse]:
    """List tenants for the current provider."""
    service = TenantService(db)
    tenants, _total = await service.list_tenants(
        provider_id=str(current_user.provider_id),
        offset=offset,
        limit=limit,
        parent_id=parent_id,
    )
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantDetailResponse)
async def get_tenant(
    tenant_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> TenantDetailResponse:
    """Get a tenant by ID with details."""
    service = TenantService(db)
    tenant = await service.get_tenant(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": "Tenant not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    stats = await service.get_tenant_stats(tenant_id)
    return TenantDetailResponse(
        **TenantResponse.model_validate(tenant).model_dump(),
        billing_info=tenant.billing_info,
        children_count=stats["total_children"],
        users_count=stats["total_users"],
    )


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: str,
    body: TenantUpdate,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Update a tenant."""
    service = TenantService(db)
    try:
        tenant = await service.update_tenant(
            tenant_id=tenant_id,
            **body.model_dump(exclude_unset=True),
        )
        return TenantResponse.model_validate(tenant)
    except TenantError as e:
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


@router.delete("/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tenant(
    tenant_id: str,
    request: Request,
    current_user: User = Depends(require_not_impersonating),
    _perm: User = Depends(require_permission("settings:tenant:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a tenant."""
    service = TenantService(db)
    try:
        await service.delete_tenant(tenant_id)
    except TenantError as e:
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


@router.get("/{tenant_id}/hierarchy", response_model=TenantHierarchyResponse)
async def get_tenant_hierarchy(
    tenant_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> TenantHierarchyResponse:
    """Get the tenant hierarchy tree."""
    service = TenantService(db)
    tenant = await service.get_tenant_hierarchy(tenant_id)
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": "Tenant not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return _build_hierarchy_response(tenant)


@router.get("/{tenant_id}/stats", response_model=TenantStatsResponse)
async def get_tenant_stats(
    tenant_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> TenantStatsResponse:
    """Get statistics for a tenant."""
    service = TenantService(db)
    try:
        stats = await service.get_tenant_stats(tenant_id)
        return TenantStatsResponse(
            tenant_id=stats["tenant_id"],
            name=stats["name"],
            total_users=stats["total_users"],
            total_compartments=stats["total_compartments"],
            total_children=stats["total_children"],
            quotas=[QuotaResponse.model_validate(q) for q in stats["quotas"]],
        )
    except TenantError as e:
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


@router.post("/{tenant_id}/settings", response_model=list[TenantSettingResponse])
async def update_settings(
    tenant_id: str,
    body: list[TenantSettingCreate],
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> list[TenantSettingResponse]:
    """Create or update tenant settings."""
    service = TenantService(db)
    try:
        settings = await service.update_settings(
            tenant_id, [s.model_dump() for s in body]
        )
        return [TenantSettingResponse.model_validate(s) for s in settings]
    except TenantError as e:
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


@router.patch("/{tenant_id}/quotas/{quota_type}", response_model=QuotaResponse)
async def update_quota(
    tenant_id: str,
    quota_type: str,
    body: QuotaUpdate,
    request: Request,
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> QuotaResponse:
    """Update a specific quota for a tenant."""
    service = QuotaService(db)
    quota = await service.update_quota(
        tenant_id=tenant_id,
        quota_type=quota_type,
        limit_value=body.limit_value,
        enforcement=body.enforcement,
    )
    if not quota:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "QUOTA_NOT_FOUND",
                    "message": f"Quota '{quota_type}' not found for tenant",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return QuotaResponse.model_validate(quota)


def _build_hierarchy_response(tenant) -> TenantHierarchyResponse:
    """Recursively build hierarchy response from tenant with loaded children."""
    children = [
        _build_hierarchy_response(child)
        for child in (tenant.children or [])
        if child.deleted_at is None
    ]
    return TenantHierarchyResponse(
        id=tenant.id,
        name=tenant.name,
        level=tenant.level,
        is_root=tenant.is_root,
        children=children,
    )
