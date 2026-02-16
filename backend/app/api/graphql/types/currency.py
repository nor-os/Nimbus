"""
Overview: Strawberry GraphQL types for currency management — exchange rates with global defaults
    + tenant overrides, conversion results, provider/tenant currency info, and input types.
Architecture: GraphQL type definitions for currency (Section 7.2)
Dependencies: strawberry
Concepts: Multi-currency, exchange rates, ISO 4217, global + tenant overrides
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

import strawberry


@strawberry.type
class CurrencyExchangeRateType:
    id: uuid.UUID
    tenant_id: uuid.UUID | None
    source_currency: str
    target_currency: str
    rate: Decimal
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime


@strawberry.type
class CurrencyConversionResultType:
    source_currency: str
    target_currency: str
    source_amount: Decimal
    converted_amount: Decimal
    rate: Decimal
    as_of: date


@strawberry.type
class ProviderCurrencyType:
    provider_id: uuid.UUID
    default_currency: str


@strawberry.type
class TenantCurrencyType:
    tenant_id: uuid.UUID
    invoice_currency: str | None
    effective_currency: str


@strawberry.input
class ExchangeRateCreateInput:
    source_currency: str
    target_currency: str
    rate: Decimal
    effective_from: date
    effective_to: date | None = None
    tenant_id: uuid.UUID | None = None


@strawberry.input
class ExchangeRateUpdateInput:
    rate: Decimal | None = None
    effective_from: date | None = None
    effective_to: date | None = strawberry.UNSET
