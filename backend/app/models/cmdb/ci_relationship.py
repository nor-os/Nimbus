"""
Overview: CI relationship model — edges in the CMDB graph connecting configuration items.
Architecture: Directed edges with type classification and uniqueness constraints (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: Relationships link a source CI to a target CI with a typed edge. Each (source, target,
    type) triple is unique. Self-referencing edges are prevented by a check constraint.
"""

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CIRelationship(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A directed relationship between two CIs."""

    __tablename__ = "ci_relationships"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    source_ci_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration_items.id"),
        nullable=False,
        index=True,
    )
    target_ci_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("configuration_items.id"),
        nullable=False,
        index=True,
    )
    relationship_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("relationship_types.id"),
        nullable=False,
        index=True,
    )
    attributes: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    source_ci: Mapped["ConfigurationItem"] = relationship(  # noqa: F821
        foreign_keys=[source_ci_id], lazy="joined"
    )
    target_ci: Mapped["ConfigurationItem"] = relationship(  # noqa: F821
        foreign_keys=[target_ci_id], lazy="joined"
    )
    relationship_type: Mapped["RelationshipType"] = relationship(lazy="joined")  # noqa: F821

    __table_args__ = (
        UniqueConstraint(
            "source_ci_id", "target_ci_id", "relationship_type_id",
            name="uq_ci_relationship_src_tgt_type",
        ),
        CheckConstraint(
            "source_ci_id != target_ci_id",
            name="ck_ci_relationship_no_self_ref",
        ),
    )
