"""
Overview: GraphQL queries for currency settings — provider/tenant currency, exchange rates
    (global + tenant overrides), and currency conversion.
Architecture: GraphQL query resolvers for currency management (Section 7.2)
Dependencies: strawberry, app.services.currency.currency_service
Concepts: Read-only currency queries with permission checks, global + tenant override lookup
"""

import uuid
from datetime import date
from decimal import Decimal

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.currency import (
    CurrencyConversionResultType,
    CurrencyExchangeRateType,
    ProviderCurrencyType,
    TenantCurrencyType,
)


def _rate_to_type(r) -> CurrencyExchangeRateType:
    return CurrencyExchangeRateType(
        id=r.id,
        tenant_id=r.tenant_id,
        source_currency=r.source_currency,
        target_currency=r.target_currency,
        rate=r.rate,
        effective_from=r.effective_from,
        effective_to=r.effective_to,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


async def _get_session(info: Info):
    """Get shared DB session from NimbusContext, falling back to new session."""
    ctx = info.context
    if hasattr(ctx, "session"):
        return await ctx.session()
    from app.db.session import async_session_factory
    return async_session_factory()


@strawberry.type
class CurrencyQuery:
    @strawberry.field
    async def provider_currency(
        self, info: Info, provider_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> ProviderCurrencyType:
        await check_graphql_permission(info, "settings:currency:read", str(tenant_id))
        from app.services.currency.currency_service import CurrencyService

        db = await _get_session(info)
        service = CurrencyService(db)
        currency = await service.get_provider_currency(str(provider_id))
        return ProviderCurrencyType(
            provider_id=provider_id,
            default_currency=currency,
        )

    @strawberry.field
    async def tenant_currency(
        self, info: Info, tenant_id: uuid.UUID
    ) -> TenantCurrencyType:
        await check_graphql_permission(info, "settings:currency:read", str(tenant_id))
        from app.services.currency.currency_service import CurrencyService

        db = await _get_session(info)
        service = CurrencyService(db)
        invoice_currency, effective = await service.get_tenant_effective_currency(str(tenant_id))
        return TenantCurrencyType(
            tenant_id=tenant_id,
            invoice_currency=invoice_currency,
            effective_currency=effective,
        )

    @strawberry.field
    async def exchange_rates(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        include_global: bool = True,
        source_currency: str | None = None,
        target_currency: str | None = None,
    ) -> list[CurrencyExchangeRateType]:
        await check_graphql_permission(info, "settings:exchange_rate:read", str(tenant_id))
        from app.services.currency.currency_service import CurrencyService

        db = await _get_session(info)
        service = CurrencyService(db)
        if include_global:
            rates = await service.list_exchange_rates(
                str(tenant_id), source_currency, target_currency
            )
        else:
            rates = await service.list_tenant_overrides(str(tenant_id))
        return [_rate_to_type(r) for r in rates]

    @strawberry.field
    async def convert_currency(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        amount: Decimal,
        source_currency: str,
        target_currency: str,
        as_of: date | None = None,
    ) -> CurrencyConversionResultType:
        await check_graphql_permission(info, "settings:exchange_rate:read", str(tenant_id))
        from app.services.currency.currency_service import CurrencyService

        effective_date = as_of or date.today()
        db = await _get_session(info)
        service = CurrencyService(db)
        converted, rate = await service.convert_amount(
            amount, source_currency, target_currency, str(tenant_id), as_of
        )
        return CurrencyConversionResultType(
            source_currency=source_currency.upper(),
            target_currency=target_currency.upper(),
            source_amount=amount,
            converted_amount=converted,
            rate=rate,
            as_of=effective_date,
        )
