"""
Overview: REST API endpoints for identity provider configuration and claim mappings.
Architecture: IdP CRUD endpoints (Section 7.1)
Dependencies: fastapi, app.services.identity, app.schemas.identity_provider, app.api.deps
Concepts: Identity providers, SSO configuration, claim mappings
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.permission_decorators import require_permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.identity_provider import (
    ClaimMappingCreate,
    ClaimMappingResponse,
    ClaimMappingUpdate,
    IdentityProviderCreate,
    IdentityProviderResponse,
    IdentityProviderUpdate,
)
from app.services.identity.service import IdentityProviderError, IdentityProviderService

router = APIRouter(prefix="/tenants/{tenant_id}/identity-providers", tags=["identity-providers"])


def _get_idp_service(db: AsyncSession = Depends(get_db)) -> IdentityProviderService:
    return IdentityProviderService(db)


@router.get("", response_model=list[IdentityProviderResponse])
async def list_providers(
    tenant_id: str,
    current_user: User = Depends(require_permission("settings:idp:list")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> list[IdentityProviderResponse]:
    """List identity providers for a tenant."""
    providers = await service.list_providers(tenant_id)
    return [IdentityProviderResponse.model_validate(p) for p in providers]


@router.get("/{provider_id}", response_model=IdentityProviderResponse)
async def get_provider(
    tenant_id: str,
    provider_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:read")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> IdentityProviderResponse:
    """Get an identity provider by ID."""
    provider = await service.get_provider(provider_id, tenant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "IDP_NOT_FOUND",
                    "message": "Identity provider not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return IdentityProviderResponse.model_validate(provider)


@router.post("", response_model=IdentityProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    tenant_id: str,
    body: IdentityProviderCreate,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:create")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> IdentityProviderResponse:
    """Create a new identity provider."""
    try:
        provider = await service.create_provider(
            tenant_id=tenant_id,
            name=body.name,
            idp_type=body.idp_type,
            is_enabled=body.is_enabled,
            is_default=body.is_default,
            config=body.config,
        )
        return IdentityProviderResponse.model_validate(provider)
    except IdentityProviderError as e:
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


@router.patch("/{provider_id}", response_model=IdentityProviderResponse)
async def update_provider(
    tenant_id: str,
    provider_id: str,
    body: IdentityProviderUpdate,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:update")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> IdentityProviderResponse:
    """Update an identity provider."""
    try:
        provider = await service.update_provider(
            provider_id=provider_id,
            tenant_id=tenant_id,
            name=body.name,
            is_enabled=body.is_enabled,
            is_default=body.is_default,
            config=body.config,
        )
        return IdentityProviderResponse.model_validate(provider)
    except IdentityProviderError as e:
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


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider(
    tenant_id: str,
    provider_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:delete")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> None:
    """Soft-delete an identity provider."""
    try:
        await service.delete_provider(provider_id, tenant_id)
    except IdentityProviderError as e:
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


# ── Claim Mappings ───────────────────────────────────────────────────


@router.get("/{provider_id}/claim-mappings", response_model=list[ClaimMappingResponse])
async def list_claim_mappings(
    tenant_id: str,
    provider_id: str,
    current_user: User = Depends(require_permission("settings:idp:read")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> list[ClaimMappingResponse]:
    """List claim mappings for an identity provider."""
    mappings = await service.list_claim_mappings(provider_id)
    return [ClaimMappingResponse.model_validate(m) for m in mappings]


@router.post(
    "/{provider_id}/claim-mappings",
    response_model=ClaimMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim_mapping(
    tenant_id: str,
    provider_id: str,
    body: ClaimMappingCreate,
    current_user: User = Depends(require_permission("settings:idp:update")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> ClaimMappingResponse:
    """Create a new claim-to-role mapping."""
    mapping = await service.create_claim_mapping(
        provider_id=provider_id,
        claim_name=body.claim_name,
        claim_value=body.claim_value,
        role_id=str(body.role_id),
        group_id=str(body.group_id) if body.group_id else None,
        priority=body.priority,
    )
    return ClaimMappingResponse.model_validate(mapping)


@router.patch(
    "/{provider_id}/claim-mappings/{mapping_id}",
    response_model=ClaimMappingResponse,
)
async def update_claim_mapping(
    tenant_id: str,
    provider_id: str,
    mapping_id: str,
    body: ClaimMappingUpdate,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:update")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> ClaimMappingResponse:
    """Update a claim mapping."""
    try:
        mapping = await service.update_claim_mapping(
            mapping_id=mapping_id,
            claim_name=body.claim_name,
            claim_value=body.claim_value,
            role_id=str(body.role_id) if body.role_id else None,
            group_id=str(body.group_id) if body.group_id else None,
            priority=body.priority,
        )
        return ClaimMappingResponse.model_validate(mapping)
    except IdentityProviderError as e:
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


@router.delete(
    "/{provider_id}/claim-mappings/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_claim_mapping(
    tenant_id: str,
    provider_id: str,
    mapping_id: str,
    request: Request,
    current_user: User = Depends(require_permission("settings:idp:update")),
    service: IdentityProviderService = Depends(_get_idp_service),
) -> None:
    """Delete a claim mapping."""
    try:
        await service.delete_claim_mapping(mapping_id)
    except IdentityProviderError as e:
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
