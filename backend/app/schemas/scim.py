"""
Overview: Pydantic schemas for SCIM v2 protocol endpoints.
Architecture: SCIM protocol schemas per RFC 7644 (Section 7.1)
Dependencies: pydantic
Concepts: SCIM, provisioning, user/group lifecycle, SCIM protocol
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# ── SCIM Core schemas ────────────────────────────────────────────────


class SCIMName(BaseModel):
    formatted: str | None = None
    familyName: str | None = None
    givenName: str | None = None


class SCIMEmail(BaseModel):
    value: str
    type: str = "work"
    primary: bool = True


class SCIMGroup(BaseModel):
    value: str
    display: str | None = None
    ref: str | None = Field(None, alias="$ref")


class SCIMMeta(BaseModel):
    resourceType: str
    created: datetime | None = None
    lastModified: datetime | None = None
    location: str | None = None


class SCIMUserResource(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:User"]
    )
    id: str | None = None
    userName: str
    name: SCIMName | None = None
    displayName: str | None = None
    active: bool = True
    emails: list[SCIMEmail] = Field(default_factory=list)
    groups: list[SCIMGroup] = Field(default_factory=list)
    meta: SCIMMeta | None = None


class SCIMGroupMember(BaseModel):
    value: str
    display: str | None = None
    ref: str | None = Field(None, alias="$ref")


class SCIMGroupResource(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:schemas:core:2.0:Group"]
    )
    id: str | None = None
    displayName: str
    members: list[SCIMGroupMember] = Field(default_factory=list)
    meta: SCIMMeta | None = None


class SCIMListResponse(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    )
    totalResults: int
    startIndex: int = 1
    itemsPerPage: int = 100
    Resources: list[dict] = Field(default_factory=list)


class SCIMPatchOperation(BaseModel):
    op: str = Field(..., pattern="^(add|remove|replace)$")
    path: str | None = None
    value: object | None = None


class SCIMPatchRequest(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:PatchOp"]
    )
    Operations: list[SCIMPatchOperation]


class SCIMError(BaseModel):
    schemas: list[str] = Field(
        default_factory=lambda: ["urn:ietf:params:scim:api:messages:2.0:Error"]
    )
    detail: str
    status: str
    scimType: str | None = None


# ── SCIM Token management schemas ────────────────────────────────────


class SCIMTokenCreate(BaseModel):
    description: str | None = None
    expires_in_days: int | None = Field(None, ge=1, le=365)


class SCIMTokenResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    description: str | None
    is_active: bool
    expires_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SCIMTokenCreateResponse(SCIMTokenResponse):
    """Returned only on creation — includes the raw token once."""

    token: str
