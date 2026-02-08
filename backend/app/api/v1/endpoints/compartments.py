"""
Overview: REST API endpoints for compartment CRUD and tree operations.
Architecture: Compartment management endpoints (Section 7.1)
Dependencies: fastapi, app.services.tenant.compartment_service, app.schemas.compartment
Concepts: Compartments, resource organization, tenant-scoped hierarchy
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_tenant_id, get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.compartment import (
    CompartmentCreate,
    CompartmentResponse,
    CompartmentTreeResponse,
    CompartmentUpdate,
)
from app.services.tenant.compartment_service import CompartmentError, CompartmentService

router = APIRouter(prefix="/compartments", tags=["compartments"])


@router.post("", response_model=CompartmentResponse, status_code=status.HTTP_201_CREATED)
async def create_compartment(
    body: CompartmentCreate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> CompartmentResponse:
    """Create a new compartment in the current tenant."""
    service = CompartmentService(db)
    try:
        compartment = await service.create_compartment(
            tenant_id=tenant_id,
            name=body.name,
            parent_id=str(body.parent_id) if body.parent_id else None,
            description=body.description,
        )
        return CompartmentResponse.model_validate(compartment)
    except CompartmentError as e:
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


@router.get("", response_model=list[CompartmentResponse])
async def list_compartments(
    request: Request,
    parent_id: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> list[CompartmentResponse]:
    """List compartments in the current tenant."""
    service = CompartmentService(db)
    compartments = await service.list_compartments(tenant_id, parent_id)
    return [CompartmentResponse.model_validate(c) for c in compartments]


@router.get("/tree", response_model=list[CompartmentTreeResponse])
async def get_compartment_tree(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> list[CompartmentTreeResponse]:
    """Get the full compartment tree for the current tenant."""
    service = CompartmentService(db)
    tree = await service.get_compartment_tree(tenant_id)
    return [CompartmentTreeResponse(**node) for node in tree]


@router.get("/{compartment_id}", response_model=CompartmentResponse)
async def get_compartment(
    compartment_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:read")),
    db: AsyncSession = Depends(get_db),
) -> CompartmentResponse:
    """Get a compartment by ID."""
    service = CompartmentService(db)
    compartment = await service.get_compartment(compartment_id, tenant_id)
    if not compartment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "COMPARTMENT_NOT_FOUND",
                    "message": "Compartment not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return CompartmentResponse.model_validate(compartment)


@router.patch("/{compartment_id}", response_model=CompartmentResponse)
async def update_compartment(
    compartment_id: str,
    body: CompartmentUpdate,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> CompartmentResponse:
    """Update a compartment."""
    service = CompartmentService(db)
    try:
        compartment = await service.update_compartment(
            compartment_id=compartment_id,
            tenant_id=tenant_id,
            name=body.name,
            parent_id=str(body.parent_id) if body.parent_id else None,
            description=body.description,
        )
        return CompartmentResponse.model_validate(compartment)
    except CompartmentError as e:
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


@router.delete("/{compartment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_compartment(
    compartment_id: str,
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    current_user: User = Depends(require_permission("settings:tenant:update")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a compartment."""
    service = CompartmentService(db)
    try:
        await service.delete_compartment(compartment_id, tenant_id)
    except CompartmentError as e:
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
