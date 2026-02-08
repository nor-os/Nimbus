"""
Overview: SAML authentication service for SSO flows.
Architecture: SAML integration with JIT user provisioning (Section 5.1)
Dependencies: app.services.identity.service, app.services.user.service, app.services.auth.jwt
Concepts: SAML, SSO, assertion consumer, JIT provisioning
"""

import base64
import secrets
import uuid
from datetime import UTC, datetime
from urllib.parse import urlencode
from xml.etree import ElementTree

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.identity_provider import IdentityProvider
from app.services.auth.jwt import create_access_token, create_refresh_token
from app.services.identity.service import IdentityProviderService
from app.services.user.service import UserService

settings = get_settings()


class SAMLError(Exception):
    def __init__(self, message: str, code: str = "SAML_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class SAMLService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def create_authn_request(
        self, provider: IdentityProvider, relay_state: str | None = None
    ) -> tuple[str, str]:
        """Create a SAML AuthnRequest and return (redirect_url, request_id)."""
        config = provider.config or {}
        sso_url = config.get("sso_url")
        entity_id = settings.saml_entity_id

        if not sso_url:
            raise SAMLError("SAML provider misconfigured: missing sso_url", "SAML_CONFIG_ERROR")

        request_id = f"_nimbus_{uuid.uuid4().hex}"

        # Build minimal SAML AuthnRequest XML
        saml_request = (
            f'<samlp:AuthnRequest xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol" '
            f'xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion" '
            f'ID="{request_id}" '
            f'Version="2.0" '
            f'IssueInstant="{datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}" '
            f'AssertionConsumerServiceURL="{settings.saml_acs_url}" '
            f'Destination="{sso_url}">'
            f'<saml:Issuer>{entity_id}</saml:Issuer>'
            f'<samlp:NameIDPolicy Format="{config.get("name_id_format", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress")}" '
            f'AllowCreate="true"/>'
            f'</samlp:AuthnRequest>'
        )

        encoded = base64.b64encode(saml_request.encode()).decode()
        params = {"SAMLRequest": encoded}
        if relay_state:
            params["RelayState"] = relay_state

        redirect_url = f"{sso_url}?{urlencode(params)}"
        return redirect_url, request_id

    def process_assertion(
        self, provider: IdentityProvider, saml_response: str
    ) -> dict:
        """Process a SAML Response and extract user attributes."""
        try:
            decoded = base64.b64decode(saml_response)
            root = ElementTree.fromstring(decoded)
        except Exception as e:
            raise SAMLError(f"Invalid SAML response: {e}", "SAML_INVALID_RESPONSE")

        # Extract attributes from SAML assertion
        ns = {
            "saml": "urn:oasis:names:tc:SAML:2.0:assertion",
            "samlp": "urn:oasis:names:tc:SAML:2.0:protocol",
        }

        # Check status
        status_elem = root.find(".//samlp:Status/samlp:StatusCode", ns)
        if status_elem is not None:
            status_value = status_elem.get("Value", "")
            if "Success" not in status_value:
                raise SAMLError("SAML authentication failed", "SAML_AUTH_FAILED")

        # Extract NameID (typically email)
        name_id = root.find(".//saml:Assertion/saml:Subject/saml:NameID", ns)
        attributes: dict = {}
        if name_id is not None and name_id.text:
            attributes["email"] = name_id.text

        # Extract attribute statements
        for attr in root.findall(".//saml:Assertion/saml:AttributeStatement/saml:Attribute", ns):
            attr_name = attr.get("Name", "")
            values = [v.text for v in attr.findall("saml:AttributeValue", ns) if v.text]
            if values:
                attributes[attr_name] = values[0] if len(values) == 1 else values

        if "email" not in attributes:
            raise SAMLError("No email in SAML assertion", "SAML_NO_EMAIL")

        return attributes

    async def process_sso_login(
        self,
        provider: IdentityProvider,
        tenant_id: str,
        attributes: dict,
    ) -> dict:
        """Process SAML SSO login: JIT provision user, apply claim mappings, return tokens."""
        email = attributes.get("email")
        if not email:
            raise SAMLError("Email not provided in SAML assertion", "SAML_NO_EMAIL")

        external_id = attributes.get("sub", email)
        display_name = attributes.get("displayName") or attributes.get("name")

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
            claims=attributes,
        )

        # Create tokens
        from sqlalchemy import select

        from app.models.user_tenant import UserTenant

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
