"""
Overview: REST API endpoints for authentication (login, logout, refresh, sessions, tenant switching).
Architecture: Auth endpoints using REST (Section 7.1)
Dependencies: fastapi, app.services.auth, app.schemas.auth, app.api.deps
Concepts: Authentication, JWT token lifecycle, session management, tenant context
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_auth_service, get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import (
    DiscoverRequest,
    DiscoverResponse,
    LoginRequest,
    RefreshRequest,
    SessionResponse,
    SSOProviderInfoSchema,
    SwitchTenantRequest,
    TenantLoginInfoResponse,
    TokenResponse,
    UserResponse,
    UserTenantResponse,
)
from app.services.auth.service import AuthError, AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate with email and password."""
    try:
        result = await auth_service.login(
            email=body.email,
            password=body.password,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return TokenResponse(**result)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/discover", response_model=DiscoverResponse)
async def discover(
    body: DiscoverRequest,
    db: AsyncSession = Depends(get_db),
) -> DiscoverResponse:
    """Discover tenant and available auth providers for an email address (public)."""
    from app.services.auth.discovery import DiscoveryService

    service = DiscoveryService(db)
    result = await service.discover(body.email)
    return DiscoverResponse(
        found=result.found,
        tenant_id=result.tenant_id,
        tenant_name=result.tenant_name,
        tenant_slug=result.tenant_slug,
        has_local_auth=result.has_local_auth,
        sso_providers=[
            SSOProviderInfoSchema(id=p.id, name=p.name, idp_type=p.idp_type)
            for p in result.sso_providers
        ],
    )


@router.get("/login-info/{slug}", response_model=TenantLoginInfoResponse)
async def login_info(
    slug: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TenantLoginInfoResponse:
    """Get tenant login info by slug (public, for /login/:slug route)."""
    from app.services.auth.discovery import DiscoveryService

    service = DiscoveryService(db)
    info = await service.get_tenant_by_slug(slug)
    if not info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "error": {
                    "code": "TENANT_NOT_FOUND",
                    "message": "No tenant found with that slug",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )
    return TenantLoginInfoResponse(
        tenant_id=info.tenant_id,
        tenant_name=info.tenant_name,
        slug=info.slug,
        has_local_auth=info.has_local_auth,
        sso_providers=[
            SSOProviderInfoSchema(id=p.id, name=p.name, idp_type=p.idp_type)
            for p in info.sso_providers
        ],
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Refresh access token using a valid refresh token."""
    try:
        result = await auth_service.refresh(body.refresh_token)
        return TokenResponse(**result)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Revoke the current session."""
    await auth_service.logout(request.state.jti)


@router.get("/me")
async def me(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Get the current authenticated user, including impersonation info if applicable."""
    user_data = UserResponse.model_validate(current_user).model_dump()
    impersonating = getattr(request.state, "impersonating", None)
    if impersonating:
        user_data["impersonation"] = {
            "is_impersonating": True,
            "original_user_id": impersonating.get("original_user"),
            "original_tenant_id": impersonating.get("original_tenant"),
            "session_id": impersonating.get("session_id"),
            "started_at": impersonating.get("started_at"),
            "expires_at": impersonating.get("expires_at"),
        }
    return user_data


@router.get("/sessions", response_model=list[SessionResponse])
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> list[SessionResponse]:
    """List all active sessions for the current user."""
    sessions = await auth_service.get_active_sessions(str(current_user.id))
    current_jti = request.state.jti
    return [
        SessionResponse(
            id=s.id,
            ip_address=s.ip_address,
            user_agent=s.user_agent,
            created_at=s.created_at,
            expires_at=s.expires_at,
            is_current=s.token_jti == current_jti,
        )
        for s in sessions
    ]


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> None:
    """Revoke a specific session."""
    await auth_service.revoke_session(session_id, str(current_user.id))


@router.post("/switch-tenant", response_model=TokenResponse)
async def switch_tenant(
    body: SwitchTenantRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Switch the active tenant and get new tokens."""
    try:
        result = await auth_service.switch_tenant(current_user, str(body.tenant_id))
        return TokenResponse(**result)
    except AuthError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )


@router.get("/sso/{tenant_id}/providers", response_model=list["SSOProviderInfo"])
async def list_sso_providers(
    tenant_id: str,
    db: AsyncSession = Depends(get_db),
) -> list:
    """List available SSO providers for a tenant (public, for login page)."""
    from app.schemas.identity_provider import SSOProviderInfo
    from app.services.identity.service import IdentityProviderService

    service = IdentityProviderService(db)
    providers = await service.get_enabled_providers(tenant_id)
    return [
        SSOProviderInfo(id=p.id, name=p.name, idp_type=p.idp_type.value)
        for p in providers
    ]


@router.get("/sso/{tenant_id}/oidc/authorize")
async def oidc_authorize(
    tenant_id: str,
    provider_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate OIDC authorization flow."""
    import secrets

    from app.services.identity.oidc import OIDCError, OIDCService
    from app.services.identity.service import IdentityProviderService

    idp_service = IdentityProviderService(db)
    provider = await idp_service.get_provider(provider_id, tenant_id)
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

    try:
        oidc_service = OIDCService(db)
        state = f"{tenant_id}:{provider_id}:{secrets.token_urlsafe(32)}"
        nonce = secrets.token_urlsafe(32)
        url = oidc_service.get_authorization_url(provider, state, nonce)
        return {"authorization_url": url, "state": state}
    except OIDCError as e:
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


@router.get("/sso/oidc/callback")
async def oidc_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Handle OIDC callback with authorization code."""
    from app.services.identity.oidc import OIDCError, OIDCService
    from app.services.identity.service import IdentityProviderService

    # Parse state to extract tenant_id and provider_id
    parts = state.split(":", 2)
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_STATE",
                    "message": "Invalid state parameter",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    tenant_id, provider_id = parts[0], parts[1]

    idp_service = IdentityProviderService(db)
    provider = await idp_service.get_provider(provider_id, tenant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "IDP_NOT_FOUND",
                    "message": "Identity provider not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    try:
        oidc_service = OIDCService(db)
        user_info = await oidc_service.handle_callback(provider, code, state)
        result = await oidc_service.process_sso_login(provider, tenant_id, user_info)
        return TokenResponse(**result)
    except OIDCError as e:
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


@router.get("/sso/{tenant_id}/saml/login")
async def saml_login(
    tenant_id: str,
    provider_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Initiate SAML authentication flow."""
    from app.services.identity.saml import SAMLError, SAMLService
    from app.services.identity.service import IdentityProviderService

    idp_service = IdentityProviderService(db)
    provider = await idp_service.get_provider(provider_id, tenant_id)
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

    try:
        saml_service = SAMLService(db)
        relay_state = f"{tenant_id}:{provider_id}"
        redirect_url, request_id = saml_service.create_authn_request(provider, relay_state)
        return {"redirect_url": redirect_url, "request_id": request_id}
    except SAMLError as e:
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


@router.post("/sso/saml/acs")
async def saml_acs(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """SAML Assertion Consumer Service endpoint."""
    from app.services.identity.saml import SAMLError, SAMLService
    from app.services.identity.service import IdentityProviderService

    form_data = await request.form()
    saml_response = form_data.get("SAMLResponse")
    relay_state = form_data.get("RelayState", "")

    if not saml_response:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SAML_NO_RESPONSE",
                    "message": "Missing SAMLResponse",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    # Parse relay state
    parts = str(relay_state).split(":", 1)
    if len(parts) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_RELAY_STATE",
                    "message": "Invalid relay state",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    tenant_id, provider_id = parts[0], parts[1]

    idp_service = IdentityProviderService(db)
    provider = await idp_service.get_provider(provider_id, tenant_id)
    if not provider:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "IDP_NOT_FOUND",
                    "message": "Identity provider not found",
                    "trace_id": getattr(request.state, "trace_id", None),
                }
            },
        )

    try:
        saml_service = SAMLService(db)
        attributes = saml_service.process_assertion(provider, str(saml_response))
        result = await saml_service.process_sso_login(provider, tenant_id, attributes)
        return TokenResponse(**result)
    except SAMLError as e:
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


@router.get("/tenants", response_model=list[UserTenantResponse])
async def list_user_tenants(
    current_user: User = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
) -> list[UserTenantResponse]:
    """List all tenants the current user has access to (explicit + descendant tenants)."""
    from sqlalchemy import select, text
    from sqlalchemy.orm import selectinload

    from app.models.tenant import Tenant
    from app.models.user_tenant import UserTenant

    # 1. Get explicit tenant associations
    ut_result = await db.execute(
        select(UserTenant)
        .where(UserTenant.user_id == current_user.id)
        .options(selectinload(UserTenant.tenant))
    )
    user_tenants = ut_result.scalars().all()
    explicit_ids = {str(ut.tenant_id) for ut in user_tenants}

    response = [
        UserTenantResponse(
            tenant_id=ut.tenant_id,
            tenant_name=ut.tenant.name,
            parent_id=ut.tenant.parent_id,
            is_default=ut.is_default,
            is_root=ut.tenant.is_root,
            level=ut.tenant.level,
            joined_at=ut.joined_at,
        )
        for ut in user_tenants
    ]

    # 2. Find descendant tenants via recursive CTE
    if explicit_ids:
        desc_result = await db.execute(
            text("""
                WITH RECURSIVE descendants AS (
                    SELECT t.id
                    FROM tenants t
                    JOIN user_tenants ut ON t.parent_id = ut.tenant_id
                    WHERE ut.user_id = :user_id AND t.deleted_at IS NULL
                    UNION
                    SELECT t.id
                    FROM tenants t
                    JOIN descendants d ON t.parent_id = d.id
                    WHERE t.deleted_at IS NULL
                )
                SELECT id FROM descendants
            """),
            {"user_id": str(current_user.id)},
        )
        descendant_ids = [str(row[0]) for row in desc_result.all()]
        descendant_ids = [did for did in descendant_ids if did not in explicit_ids]

        if descendant_ids:
            t_result = await db.execute(
                select(Tenant).where(
                    Tenant.id.in_(descendant_ids),
                    Tenant.deleted_at.is_(None),
                )
            )
            for t in t_result.scalars().all():
                response.append(
                    UserTenantResponse(
                        tenant_id=t.id,
                        tenant_name=t.name,
                        parent_id=t.parent_id,
                        is_default=False,
                        is_root=t.is_root,
                        level=t.level,
                        joined_at=t.created_at,
                    )
                )

    return response
