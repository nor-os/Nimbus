"""
Overview: REST API endpoints for ABAC policy management.
Architecture: ABAC policy CRUD and validation endpoints (Section 7.1)
Dependencies: fastapi, app.services.permission.abac_service, app.schemas.permission, app.api.deps
Concepts: ABAC, policy management, expression validation
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.permission import (
    ABACPolicyCreate,
    ABACPolicyResponse,
    ABACPolicyUpdate,
    ABACValidateRequest,
    ABACValidateResponse,
)
from app.services.permission.abac_service import ABACError, ABACService

router = APIRouter(prefix="/tenants/{tenant_id}/abac-policies", tags=["abac-policies"])


def _get_abac_service(db: AsyncSession = Depends(get_db)) -> ABACService:
    return ABACService(db)


@router.get("", response_model=list[ABACPolicyResponse])
async def list_policies(
    tenant_id: str,
    current_user: User = Depends(require_permission("permissions:abac:list")),
    service: ABACService = Depends(_get_abac_service),
) -> list[ABACPolicyResponse]:
    """List all ABAC policies for a tenant."""
    policies = await service.list_policies(tenant_id)
    return [ABACPolicyResponse.model_validate(p) for p in policies]


@router.get("/{policy_id}", response_model=ABACPolicyResponse)
async def get_policy(
    tenant_id: str,
    policy_id: str,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:list")),
    service: ABACService = Depends(_get_abac_service),
) -> ABACPolicyResponse:
    """Get an ABAC policy by ID."""
    policy = await service.get_policy(policy_id, tenant_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "POLICY_NOT_FOUND",
                    "message": "ABAC policy not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return ABACPolicyResponse.model_validate(policy)


@router.post("", response_model=ABACPolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    tenant_id: str,
    body: ABACPolicyCreate,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:create")),
    service: ABACService = Depends(_get_abac_service),
) -> ABACPolicyResponse:
    """Create a new ABAC policy."""
    try:
        policy = await service.create_policy(
            tenant_id=tenant_id,
            name=body.name,
            expression=body.expression,
            effect=body.effect,
            priority=body.priority,
            is_enabled=body.is_enabled,
            target_permission_id=str(body.target_permission_id) if body.target_permission_id else None,
        )
        return ABACPolicyResponse.model_validate(policy)
    except ABACError as e:
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


@router.patch("/{policy_id}", response_model=ABACPolicyResponse)
async def update_policy(
    tenant_id: str,
    policy_id: str,
    body: ABACPolicyUpdate,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:update")),
    service: ABACService = Depends(_get_abac_service),
) -> ABACPolicyResponse:
    """Update an ABAC policy."""
    try:
        policy = await service.update_policy(
            policy_id=policy_id,
            tenant_id=tenant_id,
            name=body.name,
            expression=body.expression,
            effect=body.effect,
            priority=body.priority,
            is_enabled=body.is_enabled,
            target_permission_id=str(body.target_permission_id) if body.target_permission_id else None,
        )
        return ABACPolicyResponse.model_validate(policy)
    except ABACError as e:
        code = status.HTTP_404_NOT_FOUND if e.code == "POLICY_NOT_FOUND" else status.HTTP_400_BAD_REQUEST
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


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    tenant_id: str,
    policy_id: str,
    request: Request,
    current_user: User = Depends(require_permission("permissions:abac:delete")),
    service: ABACService = Depends(_get_abac_service),
) -> None:
    """Delete an ABAC policy."""
    try:
        await service.delete_policy(policy_id, tenant_id)
    except ABACError as e:
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


@router.post("/validate", response_model=ABACValidateResponse)
async def validate_expression(
    tenant_id: str,
    body: ABACValidateRequest,
    current_user: User = Depends(require_permission("permissions:abac:list")),
) -> ABACValidateResponse:
    """Validate an ABAC expression without saving it."""
    error = ABACService.validate_expression(body.expression)
    return ABACValidateResponse(valid=error is None, error=error)
