"""
Overview: Currency exchange rate model — global defaults (tenant_id NULL) or per-tenant overrides
    with date-range effective conversion rates.
Architecture: Currency management data model (Section 4)
Dependencies: sqlalchemy, app.models.base, app.db.base
Concepts: Multi-currency, exchange rates, global defaults + tenant overrides
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.base import IDMixin, SoftDeleteMixin, TimestampMixin


class CurrencyExchangeRate(Base, IDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "currency_exchange_rates"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=True, index=True
    )
    source_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    target_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)

    tenant: Mapped["Tenant | None"] = relationship()  # noqa: F821
