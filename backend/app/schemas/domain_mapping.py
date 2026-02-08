"""
Overview: Pydantic schemas for domain mapping requests and responses.
Architecture: Request/response validation for domain mapping endpoints (Section 7.1)
Dependencies: pydantic
Concepts: Domain mappings, email domain routing, tenant discovery
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DomainMappingCreate(BaseModel):
    domain: str = Field(..., min_length=3, max_length=255)
    identity_provider_id: uuid.UUID | None = None


class DomainMappingResponse(BaseModel):
    id: uuid.UUID
    domain: str
    tenant_id: uuid.UUID
    identity_provider_id: uuid.UUID | None
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
