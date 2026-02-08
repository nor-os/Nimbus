"""
Overview: Claim-to-role mapping for identity provider SSO flows.
Architecture: IdP claim mapping for automatic role assignment (Section 5.1)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Claim mapping, SSO role assignment, identity providers
"""

import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class IdPClaimMapping(Base, IDMixin, TimestampMixin):
    __tablename__ = "idp_claim_mappings"

    identity_provider_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("identity_providers.id"), nullable=False, index=True
    )
    claim_name: Mapped[str] = mapped_column(String(255), nullable=False)
    claim_value: Mapped[str] = mapped_column(String(255), nullable=False)
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False
    )
    group_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id"), nullable=True
    )
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    identity_provider: Mapped["IdentityProvider"] = relationship(  # noqa: F821
        back_populates="claim_mappings"
    )
