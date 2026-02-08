"""
Overview: OIDC authentication service using Authlib for SSO flows.
Architecture: OIDC integration with JIT user provisioning (Section 5.1)
Dependencies: authlib, app.services.identity.service, app.services.user.service, app.services.auth.jwt
Concepts: OIDC, SSO, authorization code flow, JIT provisioning
"""

import secrets
from urllib.parse import urlencode

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.identity_provider import IdentityProvider
from app.services.auth.jwt import create_access_token, create_refresh_token
from app.services.identity.service import IdentityProviderService
from app.services.user.service import UserService

settings = get_settings()


class OIDCError(Exception):
    def __init__(self, message: str, code: str = "OIDC_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class OIDCService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def get_authorization_url(
        self, provider: IdentityProvider, state: str, nonce: str
    ) -> str:
        """Build the OIDC authorization redirect URL."""
        config = provider.config or {}
        client_id = config.get("client_id")
        auth_endpoint = config.get("authorization_endpoint")
        scopes = config.get("scopes", ["openid", "profile", "email"])

        if not client_id or not auth_endpoint:
            raise OIDCError("OIDC provider misconfigured", "OIDC_CONFIG_ERROR")

        params = {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": settings.oidc_callback_url,
            "scope": " ".join(scopes),
            "state": state,
            "nonce": nonce,
        }
        return f"{auth_endpoint}?{urlencode(params)}"

    async def handle_callback(
        self, provider: IdentityProvider, code: str, state: str
    ) -> dict:
        """Exchange authorization code for tokens and retrieve user info."""
        import httpx

        config = provider.config or {}
        token_endpoint = config.get("token_endpoint")
        userinfo_endpoint = config.get("userinfo_endpoint")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")

        if not token_endpoint or not client_id or not client_secret:
            raise OIDCError("OIDC provider misconfigured", "OIDC_CONFIG_ERROR")

        # Exchange code for token
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": settings.oidc_callback_url,
                    "client_id": client_id,
                    "client_secret": client_secret,
                },
            )

            if token_response.status_code != 200:
                raise OIDCError("Failed to exchange authorization code", "OIDC_TOKEN_ERROR")

            token_data = token_response.json()

            # Get user info
            if userinfo_endpoint:
                userinfo_response = await client.get(
                    userinfo_endpoint,
                    headers={"Authorization": f"Bearer {token_data['access_token']}"},
                )
                if userinfo_response.status_code == 200:
                    return userinfo_response.json()

        raise OIDCError("Failed to retrieve user info", "OIDC_USERINFO_ERROR")

    async def process_sso_login(
        self,
        provider: IdentityProvider,
        tenant_id: str,
        user_info: dict,
    ) -> dict:
        """Process SSO login: JIT provision user, apply claim mappings, return tokens."""
        email = user_info.get("email")
        if not email:
            raise OIDCError("Email not provided by identity provider", "OIDC_NO_EMAIL")

        external_id = user_info.get("sub", email)
        display_name = user_info.get("name") or user_info.get("preferred_username")

        user_service = UserService(self.db)
        user, created = await user_service.get_or_create_sso_user(
            tenant_id=tenant_id,
            idp_id=str(provider.id),
            external_id=external_id,
            email=email,
            display_name=display_name,
        )

        # Apply claim mappings
        idp_service = IdentityProviderService(self.db)
        await idp_service.apply_claim_mappings(
            provider_id=str(provider.id),
            tenant_id=tenant_id,
            user_id=str(user.id),
            claims=user_info,
        )

        # Create tokens
        from app.models.user_tenant import UserTenant
        from sqlalchemy import select

        result = await self.db.execute(
            select(UserTenant.tenant_id).where(UserTenant.user_id == user.id)
        )
        tenant_ids = [str(row[0]) for row in result.all()]

        access_token, jti, expires_at = create_access_token(
            user_id=str(user.id),
            provider_id=str(user.provider_id),
            tenant_ids=tenant_ids,
            current_tenant_id=tenant_id,
        )
        refresh_token, refresh_expires_at = create_refresh_token(
            user_id=str(user.id),
            jti=jti,
        )

        # Create session
        from app.models.session import Session
        from app.services.auth.jwt import hash_refresh_token

        session = Session(
            user_id=user.id,
            token_jti=jti,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=refresh_expires_at,
        )
        self.db.add(session)
        await self.db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.jwt_access_token_expire_minutes * 60,
            "current_tenant_id": tenant_id,
        }
