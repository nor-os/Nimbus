"""
Overview: Permission model for RBAC permission definitions.
Architecture: Permission entity with domain:resource:action[:subtype] format (Section 5.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: RBAC, permissions, domain-resource-action model
"""

from sqlalchemy import String, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class Permission(Base, IDMixin, TimestampMixin):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("domain", "resource", "action", "subtype", name="uq_permission_key"),
    )

    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    @property
    def key(self) -> str:
        """Return the permission key in domain:resource:action[:subtype] format."""
        parts = [self.domain, self.resource, self.action]
        if self.subtype:
            parts.append(self.subtype)
        return ":".join(parts)
