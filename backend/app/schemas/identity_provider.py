"""
Overview: Pydantic schemas for identity provider configuration and claim mappings.
Architecture: Request/response validation for IdP endpoints (Section 7.1)
Dependencies: pydantic
Concepts: Identity providers, OIDC, SAML, claim mappings, SSO configuration
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class OIDCConfigSchema(BaseModel):
    client_id: str
    client_secret: str
    issuer_url: str
    authorization_endpoint: str | None = None
    token_endpoint: str | None = None
    userinfo_endpoint: str | None = None
    scopes: list[str] = Field(default_factory=lambda: ["openid", "profile", "email"])


class SAMLConfigSchema(BaseModel):
    entity_id: str
    sso_url: str
    slo_url: str | None = None
    certificate: str
    name_id_format: str = "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress"
    sign_requests: bool = False


class IdentityProviderCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    idp_type: str = Field(..., pattern="^(local|oidc|saml)$")
    is_enabled: bool = True
    is_default: bool = False
    config: dict | None = None


class IdentityProviderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    is_enabled: bool | None = None
    is_default: bool | None = None
    config: dict | None = None


class IdentityProviderResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    name: str
    idp_type: str
    is_enabled: bool
    is_default: bool
    config: dict | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ClaimMappingCreate(BaseModel):
    claim_name: str = Field(..., min_length=1, max_length=255)
    claim_value: str = Field(..., min_length=1, max_length=255)
    role_id: uuid.UUID
    group_id: uuid.UUID | None = None
    priority: int = 0


class ClaimMappingUpdate(BaseModel):
    claim_name: str | None = Field(None, min_length=1, max_length=255)
    claim_value: str | None = Field(None, min_length=1, max_length=255)
    role_id: uuid.UUID | None = None
    group_id: uuid.UUID | None = None
    priority: int | None = None


class ClaimMappingResponse(BaseModel):
    id: uuid.UUID
    identity_provider_id: uuid.UUID
    claim_name: str
    claim_value: str
    role_id: uuid.UUID
    group_id: uuid.UUID | None
    priority: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SSOProviderInfo(BaseModel):
    """Public-facing SSO provider info for the login page."""

    id: uuid.UUID
    name: str
    idp_type: str
