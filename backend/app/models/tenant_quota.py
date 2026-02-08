"""
Overview: Tenant quota model with hard/soft enforcement for resource limits.
Architecture: Quota management (Section 4.2)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Multi-tenancy, resource quotas, enforcement policies
"""

import enum
import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, TimestampMixin


class QuotaType(str, enum.Enum):
    MAX_USERS = "max_users"
    MAX_COMPARTMENTS = "max_compartments"
    MAX_RESOURCES = "max_resources"
    MAX_STORAGE_GB = "max_storage_gb"
    MAX_CHILD_TENANTS = "max_child_tenants"


class QuotaEnforcement(str, enum.Enum):
    HARD = "hard"
    SOFT = "soft"


class TenantQuota(Base, IDMixin, TimestampMixin):
    __tablename__ = "tenant_quotas"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, index=True
    )
    quota_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    current_usage: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    enforcement: Mapped[str] = mapped_column(
        String(10), nullable=False, default=QuotaEnforcement.HARD.value
    )

    tenant: Mapped["Tenant"] = relationship(back_populates="quotas")  # noqa: F821
