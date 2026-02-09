"""
Overview: CI class and attribute definition models — defines the schema for configuration items.
Architecture: CMDB class hierarchy with optional semantic type linkage (Section 8)
Dependencies: sqlalchemy, app.db.base, app.models.base
Concepts: CI classes can be system-seeded (from semantic types) or custom. Each class has a JSON
    schema for validating CI attributes. Classes support single inheritance via parent_class_id.
    Attribute definitions extend the schema with custom per-class fields.
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CIClass(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """A CI class definition — system-seeded or custom."""

    __tablename__ = "ci_classes"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_class_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=True, index=True
    )
    semantic_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("semantic_resource_types.id"),
        nullable=True,
    )
    schema: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_system: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="true"
    )

    parent_class: Mapped["CIClass | None"] = relationship(
        "CIClass",
        remote_side="CIClass.id",
        foreign_keys=[parent_class_id],
        lazy="joined",
    )
    children: Mapped[list["CIClass"]] = relationship(
        "CIClass",
        back_populates="parent_class",
        foreign_keys=[parent_class_id],
        lazy="selectin",
    )
    attribute_definitions: Mapped[list["CIAttributeDefinition"]] = relationship(
        back_populates="ci_class",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "name", name="uq_ci_class_tenant_name"),
    )


class CIAttributeDefinition(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    """Custom attribute definition for a CI class."""

    __tablename__ = "ci_attribute_definitions"

    ci_class_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ci_classes.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    data_type: Mapped[str] = mapped_column(String(50), nullable=False)
    is_required: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    default_value: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    validation_rules: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sort_order: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )

    ci_class: Mapped["CIClass"] = relationship(
        back_populates="attribute_definitions",
    )

    __table_args__ = (
        UniqueConstraint(
            "ci_class_id", "name", name="uq_ci_attr_def_class_name"
        ),
    )
