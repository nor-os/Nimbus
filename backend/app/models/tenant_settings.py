"""
Overview: Tenant-scoped key-value settings model.
Architecture: Tenant configuration storage (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Multi-tenancy, tenant configuration
"""

import uuid

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class TenantSettings(Base, IDMixin, TimestampMixin):
    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(50), nullable=False, default="string")

    tenant: Mapped["Tenant"] = relationship(back_populates="settings")  # noqa: F821
