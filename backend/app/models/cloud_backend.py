"""
Overview: Cloud backend models — configured connections to cloud/infrastructure providers.
    Each backend references a SemanticProvider as its platform type and stores encrypted credentials.
Architecture: Tenant-scoped models with IAM mapping support (Section 11)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: CloudBackend = a configured connection instance (e.g. "Prod AWS us-east-1").
    SemanticProvider = the abstract platform type (e.g. "AWS"). Multiple backends can reference
    the same provider. IAM mappings link Nimbus roles to cloud-specific identities per backend.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CloudBackend(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A configured cloud backend connection referencing a SemanticProvider."""

    __tablename__ = "cloud_backends"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("semantic_providers.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="active"
    )
    credentials_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )
    credentials_schema_version: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="1"
    )
    scope_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    endpoint_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    last_connectivity_check: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_connectivity_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )
    last_connectivity_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    provider: Mapped["SemanticProvider"] = relationship(lazy="joined")  # noqa: F821
    regions: Mapped[list["BackendRegion"]] = relationship(
        back_populates="backend", lazy="selectin"
    )
    iam_mappings: Mapped[list["CloudBackendIAMMapping"]] = relationship(
        back_populates="backend", lazy="selectin"
    )

    __table_args__ = (
        # Partial unique index (tenant_id, name) WHERE deleted_at IS NULL
        # is created in migration 035 via raw SQL
        # Partial unique index on tenant_id WHERE deleted_at IS NULL (1:1 tenant→backend)
        # is created in migration 063 via raw SQL
        Index("ix_cloud_backends_tenant", "tenant_id"),
        Index("ix_cloud_backends_provider", "provider_id"),
        Index("ix_cloud_backends_status", "status"),
    )


class BackendRegion(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """An activated/configured region on a cloud backend."""

    __tablename__ = "backend_regions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    backend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_backends.id"), nullable=False
    )
    region_identifier: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    provider_region_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )
    availability_zones: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    settings: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    backend: Mapped["CloudBackend"] = relationship(
        back_populates="regions", lazy="joined"
    )

    __table_args__ = (
        # Partial unique index (backend_id, region_identifier) WHERE deleted_at IS NULL
        # created in migration 080 via raw SQL
        Index("ix_backend_regions_tenant", "tenant_id"),
        Index("ix_backend_regions_backend", "backend_id"),
    )


class CloudBackendIAMMapping(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Maps a Nimbus role to a cloud-specific identity for a backend."""

    __tablename__ = "cloud_backend_iam_mappings"

    backend_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cloud_backends.id"), nullable=False, index=True
    )
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False, index=True
    )
    cloud_identity: Mapped[dict] = mapped_column(JSONB, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    backend: Mapped["CloudBackend"] = relationship(
        back_populates="iam_mappings", lazy="joined"
    )
    role: Mapped["Role"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        # Partial unique index (backend_id, role_id) WHERE deleted_at IS NULL
        # is created in migration 035 via raw SQL
        Index("ix_cloud_iam_backend", "backend_id"),
        Index("ix_cloud_iam_role", "role_id"),
    )
