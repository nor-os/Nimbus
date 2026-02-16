/**
 * Overview: Currency management GraphQL service — queries and mutations for provider/tenant
 *     currency settings and exchange rates with global defaults + tenant overrides.
 * Architecture: Core service layer for currency management (Section 4)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Multi-currency, exchange rates, global defaults + tenant overrides
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';

// ── Interfaces ────────────────────────────────────────────────────────

export interface ProviderCurrency {
  providerId: string;
  defaultCurrency: string;
}

export interface TenantCurrency {
  tenantId: string;
  invoiceCurrency: string | null;
  effectiveCurrency: string;
}

export interface ExchangeRate {
  id: string;
  tenantId: string | null;
  sourceCurrency: string;
  targetCurrency: string;
  rate: number;
  effectiveFrom: string;
  effectiveTo: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CurrencyConversionResult {
  sourceCurrency: string;
  targetCurrency: string;
  sourceAmount: number;
  convertedAmount: number;
  rate: number;
  asOf: string;
}

export interface ExchangeRateCreateInput {
  sourceCurrency: string;
  targetCurrency: string;
  rate: number;
  effectiveFrom: string;
  effectiveTo?: string | null;
  tenantId?: string | null;
}

export interface ExchangeRateUpdateInput {
  rate?: number;
  effectiveFrom?: string;
  effectiveTo?: string | null;
}

// ── Field constants ───────────────────────────────────────────────────

const RATE_FIELDS = `
  id tenantId sourceCurrency targetCurrency rate
  effectiveFrom effectiveTo createdAt updatedAt
`;

@Injectable({ providedIn: 'root' })
export class CurrencyService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Provider Currency ─────────────────────────────────────────────

  getProviderCurrency(providerId: string): Observable<ProviderCurrency> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ providerCurrency: ProviderCurrency }>(`
      query ProviderCurrency($providerId: UUID!, $tenantId: UUID!) {
        providerCurrency(providerId: $providerId, tenantId: $tenantId) {
          providerId defaultCurrency
        }
      }
    `, { providerId, tenantId }).pipe(map((d) => d.providerCurrency));
  }

  updateProviderCurrency(providerId: string, currency: string): Observable<ProviderCurrency> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateProviderCurrency: ProviderCurrency }>(`
      mutation UpdateProviderCurrency($providerId: UUID!, $tenantId: UUID!, $currency: String!) {
        updateProviderCurrency(providerId: $providerId, tenantId: $tenantId, currency: $currency) {
          providerId defaultCurrency
        }
      }
    `, { providerId, tenantId, currency }).pipe(map((d) => d.updateProviderCurrency));
  }

  // ── Tenant Currency ───────────────────────────────────────────────

  getTenantCurrency(tenantId: string): Observable<TenantCurrency> {
    return this.gql<{ tenantCurrency: TenantCurrency }>(`
      query TenantCurrency($tenantId: UUID!) {
        tenantCurrency(tenantId: $tenantId) {
          tenantId invoiceCurrency effectiveCurrency
        }
      }
    `, { tenantId }).pipe(map((d) => d.tenantCurrency));
  }

  updateTenantInvoiceCurrency(tenantId: string, currency: string | null): Observable<TenantCurrency> {
    return this.gql<{ updateTenantInvoiceCurrency: TenantCurrency }>(`
      mutation UpdateTenantInvoiceCurrency($tenantId: UUID!, $currency: String) {
        updateTenantInvoiceCurrency(tenantId: $tenantId, currency: $currency) {
          tenantId invoiceCurrency effectiveCurrency
        }
      }
    `, { tenantId, currency }).pipe(map((d) => d.updateTenantInvoiceCurrency));
  }

  // ── Exchange Rates ────────────────────────────────────────────────

  listExchangeRates(
    sourceCurrency?: string,
    targetCurrency?: string,
  ): Observable<ExchangeRate[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ exchangeRates: ExchangeRate[] }>(`
      query ExchangeRates(
        $tenantId: UUID!,
        $sourceCurrency: String, $targetCurrency: String
      ) {
        exchangeRates(
          tenantId: $tenantId,
          sourceCurrency: $sourceCurrency, targetCurrency: $targetCurrency
        ) { ${RATE_FIELDS} }
      }
    `, { tenantId, sourceCurrency, targetCurrency }).pipe(
      map((d) => d.exchangeRates),
    );
  }

  listTenantOverrides(tenantId: string): Observable<ExchangeRate[]> {
    return this.gql<{ exchangeRates: ExchangeRate[] }>(`
      query TenantOverrideRates($tenantId: UUID!) {
        exchangeRates(tenantId: $tenantId, includeGlobal: false) {
          ${RATE_FIELDS}
        }
      }
    `, { tenantId }).pipe(map((d) => d.exchangeRates));
  }

  createExchangeRate(input: ExchangeRateCreateInput): Observable<ExchangeRate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createExchangeRate: ExchangeRate }>(`
      mutation CreateExchangeRate($tenantId: UUID!, $input: ExchangeRateCreateInput!) {
        createExchangeRate(tenantId: $tenantId, input: $input) {
          ${RATE_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(map((d) => d.createExchangeRate));
  }

  updateExchangeRate(
    rateId: string,
    input: ExchangeRateUpdateInput,
  ): Observable<ExchangeRate> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateExchangeRate: ExchangeRate }>(`
      mutation UpdateExchangeRate(
        $tenantId: UUID!, $rateId: UUID!, $input: ExchangeRateUpdateInput!
      ) {
        updateExchangeRate(tenantId: $tenantId, rateId: $rateId, input: $input) {
          ${RATE_FIELDS}
        }
      }
    `, { tenantId, rateId, input }).pipe(map((d) => d.updateExchangeRate));
  }

  deleteExchangeRate(rateId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteExchangeRate: boolean }>(`
      mutation DeleteExchangeRate($tenantId: UUID!, $rateId: UUID!) {
        deleteExchangeRate(tenantId: $tenantId, rateId: $rateId)
      }
    `, { tenantId, rateId }).pipe(map((d) => d.deleteExchangeRate));
  }

  // ── Conversion ────────────────────────────────────────────────────

  convertCurrency(
    amount: number,
    sourceCurrency: string,
    targetCurrency: string,
    asOf?: string,
  ): Observable<CurrencyConversionResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ convertCurrency: CurrencyConversionResult }>(`
      query ConvertCurrency(
        $tenantId: UUID!,
        $amount: Decimal!, $sourceCurrency: String!, $targetCurrency: String!, $asOf: Date
      ) {
        convertCurrency(
          tenantId: $tenantId,
          amount: $amount, sourceCurrency: $sourceCurrency, targetCurrency: $targetCurrency, asOf: $asOf
        ) {
          sourceCurrency targetCurrency sourceAmount convertedAmount rate asOf
        }
      }
    `, { tenantId, amount, sourceCurrency, targetCurrency, asOf }).pipe(
      map((d) => d.convertCurrency),
    );
  }

  // ── GraphQL helper ────────────────────────────────────────────────

  private gql<T>(
    query: string,
    variables: Record<string, unknown> = {},
  ): Observable<T> {
    return this.api
      .post<{ data: T; errors?: Array<{ message: string }> }>(this.gqlUrl, {
        query,
        variables,
      })
      .pipe(
        map((response) => {
          if (response.errors?.length) {
            throw new Error(response.errors[0].message);
          }
          return response.data;
        }),
      );
  }
}
