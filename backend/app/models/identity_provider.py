"""
Overview: Identity provider model for tenant-level SSO configuration.
Architecture: Identity provider entity for OIDC/SAML/local auth (Section 5.1)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Identity providers, SSO, OIDC, SAML, multi-tenancy
"""

import enum
import uuid

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class IdPType(str, enum.Enum):
    LOCAL = "local"
    OIDC = "oidc"
    SAML = "saml"


class IdentityProvider(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "identity_providers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    idp_type: Mapped[IdPType] = mapped_column(
        Enum(
            IdPType,
            name="idp_type_enum",
            create_constraint=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    claim_mappings: Mapped[list["IdPClaimMapping"]] = relationship(  # noqa: F821
        back_populates="identity_provider", cascade="all, delete-orphan"
    )
