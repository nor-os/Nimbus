"""
Overview: Domain mapping model linking email domains to tenants and identity providers.
Architecture: Login discovery data model (Section 5.1)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Domain discovery, email-based tenant routing, SSO provider selection
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class DomainMapping(Base, IDMixin, TimestampMixin):
    __tablename__ = "domain_mappings"

    domain: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    identity_provider_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_providers.id"), nullable=True
    )
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    tenant: Mapped["Tenant"] = relationship(back_populates="domain_mappings")  # noqa: F821
    identity_provider: Mapped["IdentityProvider | None"] = relationship()  # noqa: F821
