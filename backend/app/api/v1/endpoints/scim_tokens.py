"""
Overview: REST API endpoints for SCIM token management.
Architecture: SCIM token CRUD endpoints (Section 7.1)
Dependencies: fastapi, app.services.scim.token_service, app.api.deps
Concepts: SCIM tokens, bearer token management
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.scim import SCIMTokenCreate, SCIMTokenCreateResponse, SCIMTokenResponse
from app.services.scim.token_service import SCIMTokenError, SCIMTokenService

router = APIRouter(prefix="/tenants/{tenant_id}/scim-tokens", tags=["scim-tokens"])


def _get_token_service(db: AsyncSession = Depends(get_db)) -> SCIMTokenService:
    return SCIMTokenService(db)


@router.get("", response_model=list[SCIMTokenResponse])
async def list_tokens(
    tenant_id: str,
    current_user: User = Depends(require_permission("settings:scim:manage")),
    service: SCIMTokenService = Depends(_get_token_service),
) -> list[SCIMTokenResponse]:
    """List SCIM tokens for a tenant."""
    tokens = await service.list_tokens(tenant_id)
    return [SCIMTokenResponse.model_validate(t) for t in tokens]


@router.post("", response_model=SCIMTokenCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_token(
    tenant_id: str,
    body: SCIMTokenCreate,
    current_user: User = Depends(require_permission("settings:scim:manage")),
    service: SCIMTokenService = Depends(_get_token_service),
) -> SCIMTokenCreateResponse:
    """Create a new SCIM token. The raw token is only shown once."""
    token, raw_token = await service.create_token(
        tenant_id=tenant_id,
        created_by=str(current_user.id),
        description=body.description,
        expires_in_days=body.expires_in_days,
    )
    return SCIMTokenCreateResponse(
        **SCIMTokenResponse.model_validate(token).model_dump(),
        token=raw_token,
    )


@router.delete("/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    tenant_id: str,
    token_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:scim:manage")),
    service: SCIMTokenService = Depends(_get_token_service),
) -> None:
    """Revoke a SCIM token."""
    try:
        await service.revoke_token(token_id, tenant_id)
    except SCIMTokenError as e:
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
