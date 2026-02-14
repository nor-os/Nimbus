"""
Overview: Currency management service — CRUD for provider/tenant currency settings and
    exchange rates with date-range effective rate lookup and conversion.
Architecture: Service layer for currency management (Section 4)
Dependencies: sqlalchemy, app.models.provider, app.models.tenant, app.models.currency_exchange_rate
Concepts: Provider default currency, tenant invoice currency inheritance, exchange rate lookup
"""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency_exchange_rate import CurrencyExchangeRate
from app.models.provider import Provider
from app.models.tenant import Tenant

logger = logging.getLogger(__name__)


class CurrencyServiceError(Exception):
    def __init__(self, message: str, code: str = "CURRENCY_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class CurrencyService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ── Provider Currency ────────────────────────────────────────────

    async def get_provider_currency(self, provider_id: str) -> str:
        result = await self.db.execute(
            select(Provider.default_currency).where(
                Provider.id == provider_id,
                Provider.deleted_at.is_(None),
            )
        )
        currency = result.scalar_one_or_none()
        if currency is None:
            raise CurrencyServiceError("Provider not found", "NOT_FOUND")
        return currency

    async def update_provider_currency(self, provider_id: str, currency: str) -> Provider:
        currency = currency.upper().strip()
        if len(currency) != 3 or not currency.isalpha():
            raise CurrencyServiceError("Currency must be a 3-letter ISO 4217 code", "INVALID_CURRENCY")

        result = await self.db.execute(
            select(Provider).where(
                Provider.id == provider_id,
                Provider.deleted_at.is_(None),
            )
        )
        provider = result.scalar_one_or_none()
        if not provider:
            raise CurrencyServiceError("Provider not found", "NOT_FOUND")

        provider.default_currency = currency
        await self.db.flush()
        return provider

    # ── Tenant Currency ──────────────────────────────────────────────

    async def get_tenant_effective_currency(self, tenant_id: str) -> tuple[str | None, str]:
        """Returns (invoice_currency, effective_currency) where effective resolves inheritance."""
        result = await self.db.execute(
            select(Tenant.invoice_currency, Tenant.provider_id).where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        row = result.one_or_none()
        if row is None:
            raise CurrencyServiceError("Tenant not found", "NOT_FOUND")

        invoice_currency, provider_id = row
        if invoice_currency:
            return invoice_currency, invoice_currency

        # Inherit from provider
        provider_currency = await self.get_provider_currency(str(provider_id))
        return None, provider_currency

    async def update_tenant_currency(self, tenant_id: str, currency: str | None) -> Tenant:
        if currency is not None:
            currency = currency.upper().strip()
            if len(currency) != 3 or not currency.isalpha():
                raise CurrencyServiceError("Currency must be a 3-letter ISO 4217 code", "INVALID_CURRENCY")

        result = await self.db.execute(
            select(Tenant).where(
                Tenant.id == tenant_id,
                Tenant.deleted_at.is_(None),
            )
        )
        tenant = result.scalar_one_or_none()
        if not tenant:
            raise CurrencyServiceError("Tenant not found", "NOT_FOUND")

        tenant.invoice_currency = currency
        await self.db.flush()
        return tenant

    # ── Exchange Rates ───────────────────────────────────────────────

    async def list_exchange_rates(
        self,
        provider_id: str,
        source_currency: str | None = None,
        target_currency: str | None = None,
    ) -> list[CurrencyExchangeRate]:
        stmt = select(CurrencyExchangeRate).where(
            CurrencyExchangeRate.provider_id == provider_id,
            CurrencyExchangeRate.deleted_at.is_(None),
        )
        if source_currency:
            stmt = stmt.where(CurrencyExchangeRate.source_currency == source_currency.upper())
        if target_currency:
            stmt = stmt.where(CurrencyExchangeRate.target_currency == target_currency.upper())
        stmt = stmt.order_by(
            CurrencyExchangeRate.source_currency,
            CurrencyExchangeRate.target_currency,
            CurrencyExchangeRate.effective_from.desc(),
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_exchange_rate(
        self, provider_id: str, data: dict
    ) -> CurrencyExchangeRate:
        source = data["source_currency"].upper().strip()
        target = data["target_currency"].upper().strip()

        if source == target:
            raise CurrencyServiceError("Source and target currencies must differ", "SAME_CURRENCY")
        if len(source) != 3 or not source.isalpha():
            raise CurrencyServiceError("Source currency must be a 3-letter ISO 4217 code", "INVALID_CURRENCY")
        if len(target) != 3 or not target.isalpha():
            raise CurrencyServiceError("Target currency must be a 3-letter ISO 4217 code", "INVALID_CURRENCY")

        rate_value = Decimal(str(data["rate"]))
        if rate_value <= 0:
            raise CurrencyServiceError("Rate must be positive", "INVALID_RATE")

        rate = CurrencyExchangeRate(
            provider_id=provider_id,
            source_currency=source,
            target_currency=target,
            rate=rate_value,
            effective_from=data["effective_from"],
            effective_to=data.get("effective_to"),
        )
        self.db.add(rate)
        await self.db.flush()
        return rate

    async def update_exchange_rate(
        self, rate_id: str, provider_id: str, data: dict
    ) -> CurrencyExchangeRate:
        result = await self.db.execute(
            select(CurrencyExchangeRate).where(
                CurrencyExchangeRate.id == rate_id,
                CurrencyExchangeRate.provider_id == provider_id,
                CurrencyExchangeRate.deleted_at.is_(None),
            )
        )
        rate = result.scalar_one_or_none()
        if not rate:
            raise CurrencyServiceError("Exchange rate not found", "NOT_FOUND")

        if "rate" in data:
            rate_value = Decimal(str(data["rate"]))
            if rate_value <= 0:
                raise CurrencyServiceError("Rate must be positive", "INVALID_RATE")
            rate.rate = rate_value
        if "effective_from" in data:
            rate.effective_from = data["effective_from"]
        if "effective_to" in data:
            rate.effective_to = data["effective_to"]

        await self.db.flush()
        return rate

    async def delete_exchange_rate(self, rate_id: str, provider_id: str) -> bool:
        result = await self.db.execute(
            select(CurrencyExchangeRate).where(
                CurrencyExchangeRate.id == rate_id,
                CurrencyExchangeRate.provider_id == provider_id,
                CurrencyExchangeRate.deleted_at.is_(None),
            )
        )
        rate = result.scalar_one_or_none()
        if not rate:
            return False
        rate.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def get_effective_rate(
        self,
        provider_id: str,
        source_currency: str,
        target_currency: str,
        as_of: date | None = None,
    ) -> CurrencyExchangeRate | None:
        if as_of is None:
            as_of = date.today()

        source = source_currency.upper()
        target = target_currency.upper()

        stmt = (
            select(CurrencyExchangeRate)
            .where(
                CurrencyExchangeRate.provider_id == provider_id,
                CurrencyExchangeRate.source_currency == source,
                CurrencyExchangeRate.target_currency == target,
                CurrencyExchangeRate.effective_from <= as_of,
                CurrencyExchangeRate.deleted_at.is_(None),
            )
            .where(
                (CurrencyExchangeRate.effective_to.is_(None))
                | (CurrencyExchangeRate.effective_to >= as_of)
            )
            .order_by(CurrencyExchangeRate.effective_from.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def convert_amount(
        self,
        provider_id: str,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        as_of: date | None = None,
    ) -> tuple[Decimal, Decimal]:
        """Convert amount. Returns (converted_amount, rate_used)."""
        source = source_currency.upper()
        target = target_currency.upper()

        if source == target:
            return amount, Decimal("1")

        rate = await self.get_effective_rate(provider_id, source, target, as_of)
        if not rate:
            raise CurrencyServiceError(
                f"No exchange rate found for {source} -> {target}",
                "RATE_NOT_FOUND",
            )

        converted = amount * rate.rate
        return converted, rate.rate
