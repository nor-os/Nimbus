"""
Overview: Strawberry GraphQL types for policy library and resolution.
Architecture: GraphQL type definitions for governance policies (Section 7.2)
Dependencies: strawberry
Concepts: Policy library types, resolved policy types, input types for CRUD, enum mappings
"""

import uuid
from datetime import datetime
from enum import Enum

import strawberry
import strawberry.scalars


@strawberry.enum
class PolicyCategoryGQL(Enum):
    IAM = "IAM"
    NETWORK = "NETWORK"
    ENCRYPTION = "ENCRYPTION"
    TAGGING = "TAGGING"
    COST = "COST"


@strawberry.enum
class PolicySeverityGQL(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@strawberry.type
class PolicyLibraryEntryType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    name: str
    display_name: str
    description: str | None
    category: str
    statements: strawberry.scalars.JSON
    variables: strawberry.scalars.JSON | None
    severity: str
    is_system: bool
    tags: list[str] | None
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime


@strawberry.type
class ResolvedPolicyType:
    policy_id: str
    name: str
    source: str
    source_compartment_id: str | None
    statements: strawberry.scalars.JSON
    severity: str
    category: str
    can_suppress: bool


@strawberry.type
class PolicySummaryType:
    compartment_id: str
    direct_policies: int
    inherited_policies: int
    total_statements: int
    deny_count: int
    allow_count: int


@strawberry.input
class PolicyLibraryCreateInput:
    name: str
    display_name: str
    description: str | None = None
    category: str
    statements: strawberry.scalars.JSON
    variables: strawberry.scalars.JSON | None = None
    severity: str = "MEDIUM"
    tags: list[str] | None = None


@strawberry.input
class PolicyLibraryUpdateInput:
    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    statements: strawberry.scalars.JSON | None = None
    variables: strawberry.scalars.JSON | None = None
    severity: str | None = None
    tags: list[str] | None = None
