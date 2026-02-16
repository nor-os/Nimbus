"""
Overview: Provider model representing the top-level organization.
Architecture: Root of the tenant hierarchy (Section 4.1, 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Multi-tenancy, provider hierarchy
"""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class Provider(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "providers"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    default_currency: Mapped[str] = mapped_column(String(3), nullable=False, server_default="EUR")

    users: Mapped[list["User"]] = relationship(back_populates="provider")  # noqa: F821
    tenants: Mapped[list["Tenant"]] = relationship(back_populates="provider")  # noqa: F821
