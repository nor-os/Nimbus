"""
Overview: GraphQL mutations for currency management — update provider/tenant currency,
    CRUD exchange rates.
Architecture: GraphQL mutation resolvers for currency management (Section 7.2)
Dependencies: strawberry, app.services.currency.currency_service
Concepts: Currency settings mutations with permission enforcement
"""

import uuid

import strawberry
from strawberry.types import Info

from app.api.graphql.auth import check_graphql_permission
from app.api.graphql.types.currency import (
    CurrencyExchangeRateType,
    ExchangeRateCreateInput,
    ExchangeRateUpdateInput,
    ProviderCurrencyType,
    TenantCurrencyType,
)


def _rate_to_type(r) -> CurrencyExchangeRateType:
    return CurrencyExchangeRateType(
        id=r.id,
        provider_id=r.provider_id,
        source_currency=r.source_currency,
        target_currency=r.target_currency,
        rate=r.rate,
        effective_from=r.effective_from,
        effective_to=r.effective_to,
        created_at=r.created_at,
        updated_at=r.updated_at,
    )


@strawberry.type
class CurrencyMutation:
    @strawberry.mutation
    async def update_provider_currency(
        self,
        info: Info,
        provider_id: uuid.UUID,
        tenant_id: uuid.UUID,
        currency: str,
    ) -> ProviderCurrencyType:
        await check_graphql_permission(info, "settings:currency:manage", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.currency.currency_service import CurrencyService

        async with async_session_factory() as db:
            service = CurrencyService(db)
            provider = await service.update_provider_currency(str(provider_id), currency)
            await db.commit()
            return ProviderCurrencyType(
                provider_id=provider.id,
                default_currency=provider.default_currency,
            )

    @strawberry.mutation
    async def update_tenant_invoice_currency(
        self,
        info: Info,
        tenant_id: uuid.UUID,
        currency: str | None = None,
    ) -> TenantCurrencyType:
        await check_graphql_permission(info, "settings:currency:manage", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.currency.currency_service import CurrencyService

        async with async_session_factory() as db:
            service = CurrencyService(db)
            await service.update_tenant_currency(str(tenant_id), currency)
            invoice_currency, effective = await service.get_tenant_effective_currency(str(tenant_id))
            await db.commit()
            return TenantCurrencyType(
                tenant_id=tenant_id,
                invoice_currency=invoice_currency,
                effective_currency=effective,
            )

    @strawberry.mutation
    async def create_exchange_rate(
        self,
        info: Info,
        provider_id: uuid.UUID,
        tenant_id: uuid.UUID,
        input: ExchangeRateCreateInput,
    ) -> CurrencyExchangeRateType:
        await check_graphql_permission(info, "settings:exchange_rate:manage", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.currency.currency_service import CurrencyService

        async with async_session_factory() as db:
            service = CurrencyService(db)
            rate = await service.create_exchange_rate(str(provider_id), {
                "source_currency": input.source_currency,
                "target_currency": input.target_currency,
                "rate": input.rate,
                "effective_from": input.effective_from,
                "effective_to": input.effective_to,
            })
            await db.commit()
            return _rate_to_type(rate)

    @strawberry.mutation
    async def update_exchange_rate(
        self,
        info: Info,
        provider_id: uuid.UUID,
        tenant_id: uuid.UUID,
        rate_id: uuid.UUID,
        input: ExchangeRateUpdateInput,
    ) -> CurrencyExchangeRateType:
        await check_graphql_permission(info, "settings:exchange_rate:manage", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.currency.currency_service import CurrencyService

        data = {}
        if input.rate is not None:
            data["rate"] = input.rate
        if input.effective_from is not None:
            data["effective_from"] = input.effective_from
        if input.effective_to is not strawberry.UNSET:
            data["effective_to"] = input.effective_to

        async with async_session_factory() as db:
            service = CurrencyService(db)
            rate = await service.update_exchange_rate(str(rate_id), str(provider_id), data)
            await db.commit()
            return _rate_to_type(rate)

    @strawberry.mutation
    async def delete_exchange_rate(
        self,
        info: Info,
        provider_id: uuid.UUID,
        tenant_id: uuid.UUID,
        rate_id: uuid.UUID,
    ) -> bool:
        await check_graphql_permission(info, "settings:exchange_rate:manage", str(tenant_id))
        from app.db.session import async_session_factory
        from app.services.currency.currency_service import CurrencyService

        async with async_session_factory() as db:
            service = CurrencyService(db)
            result = await service.delete_exchange_rate(str(rate_id), str(provider_id))
            await db.commit()
            return result
