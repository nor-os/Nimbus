"""
Overview: Pydantic schemas for CMDB — CI classes, configuration items, relationships, snapshots.
Architecture: Validation schemas for CMDB data operations (Section 8)
Dependencies: pydantic
Concepts: Request/response schemas for CI CRUD, class management, relationship management,
    and snapshot versioning.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class LifecycleState(StrEnum):
    PLANNED = "planned"
    ACTIVE = "active"
    MAINTENANCE = "maintenance"
    RETIRED = "retired"
    DELETED = "deleted"


LIFECYCLE_TRANSITIONS: dict[str, list[str]] = {
    "planned": ["active", "deleted"],
    "active": ["maintenance", "retired", "deleted"],
    "maintenance": ["active", "retired", "deleted"],
    "retired": ["deleted"],
}


class CIClassResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str
    parent_class_id: uuid.UUID | None
    semantic_type_id: uuid.UUID | None
    schema_def: dict | None = None
    icon: str | None
    is_system: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CIClassCreate(BaseModel):
    name: str
    display_name: str
    parent_class_id: uuid.UUID | None = None
    schema_def: dict | None = None
    icon: str | None = None


class CIResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    ci_class_id: uuid.UUID
    compartment_id: uuid.UUID | None
    name: str
    description: str | None
    lifecycle_state: str
    attributes: dict
    tags: dict
    cloud_resource_id: str | None
    pulumi_urn: str | None
    created_at: datetime
    updated_at: datetime


class CICreate(BaseModel):
    ci_class_id: uuid.UUID
    compartment_id: uuid.UUID | None = None
    name: str
    description: str | None = None
    lifecycle_state: str = "planned"
    attributes: dict | None = None
    tags: dict | None = None
    cloud_resource_id: str | None = None
    pulumi_urn: str | None = None


class CIUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    attributes: dict | None = None
    tags: dict | None = None
    cloud_resource_id: str | None = None
    pulumi_urn: str | None = None


class RelationshipTypeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    name: str
    display_name: str
    inverse_name: str
    description: str | None
    source_class_ids: list | None
    target_class_ids: list | None
    is_system: bool
    created_at: datetime
    updated_at: datetime


class CIRelationshipResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    tenant_id: uuid.UUID
    source_ci_id: uuid.UUID
    target_ci_id: uuid.UUID
    relationship_type_id: uuid.UUID
    attributes: dict | None
    created_at: datetime
    updated_at: datetime


class CISnapshotResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    ci_id: uuid.UUID
    tenant_id: uuid.UUID
    version_number: int
    snapshot_data: dict
    changed_by: uuid.UUID | None
    changed_at: datetime
    change_reason: str | None
    change_type: str


class CIFilter(BaseModel):
    ci_class_id: uuid.UUID | None = None
    compartment_id: uuid.UUID | None = None
    lifecycle_state: str | None = None
    tags: dict | None = None
    search: str | None = None
