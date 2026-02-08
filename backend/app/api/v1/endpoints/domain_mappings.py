"""
Overview: REST endpoints for managing email domain-to-tenant mappings.
Architecture: Domain mapping CRUD endpoints (Section 7.1)
Dependencies: fastapi, app.services.domain, app.schemas.domain_mapping, app.api.deps
Concepts: Domain mapping management, tenant-scoped configuration
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.domain_mapping import DomainMappingCreate, DomainMappingResponse
from app.services.domain.service import DomainMappingError, DomainMappingService

router = APIRouter(prefix="/tenants/{tenant_id}/domain-mappings", tags=["domain-mappings"])


@router.get("", response_model=list[DomainMappingResponse])
async def list_domain_mappings(
    tenant_id: str,
    current_user: User = Depends(require_permission("settings:idp:read")),
    db: AsyncSession = Depends(get_db),
) -> list[DomainMappingResponse]:
    """List all domain mappings for a tenant."""
    service = DomainMappingService(db)
    mappings = await service.list_mappings(tenant_id)
    return [DomainMappingResponse.model_validate(m) for m in mappings]


@router.post("", response_model=DomainMappingResponse, status_code=status.HTTP_201_CREATED)
async def create_domain_mapping(
    tenant_id: str,
    body: DomainMappingCreate,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:create")),
    db: AsyncSession = Depends(get_db),
) -> DomainMappingResponse:
    """Create a new domain mapping for a tenant."""
    service = DomainMappingService(db)
    try:
        mapping = await service.create_mapping(
            tenant_id=tenant_id,
            domain=body.domain,
            identity_provider_id=str(body.identity_provider_id) if body.identity_provider_id else None,
        )
        await db.commit()
        return DomainMappingResponse.model_validate(mapping)
    except DomainMappingError as e:
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


@router.delete("/{mapping_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_domain_mapping(
    tenant_id: str,
    mapping_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:delete")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a domain mapping."""
    service = DomainMappingService(db)
    try:
        await service.delete_mapping(mapping_id, tenant_id)
        await db.commit()
    except DomainMappingError as e:
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
