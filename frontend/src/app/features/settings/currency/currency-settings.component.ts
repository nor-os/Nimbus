/**
 * Overview: Currency settings page — manage provider default currency and exchange rates.
 * Architecture: Settings feature component (Section 4)
 * Dependencies: @angular/core, @angular/common, @angular/forms,
 *     app/core/services/currency.service, app/core/services/tenant-context.service
 * Concepts: Multi-currency, exchange rates, provider-scoped billing, ISO 4217
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import {
  CurrencyService,
  ExchangeRate,
  ProviderCurrency,
} from '@core/services/currency.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { TenantService } from '@core/services/tenant.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const COMMON_CURRENCIES = [
  'EUR', 'USD', 'GBP', 'CHF', 'JPY', 'CNY', 'AUD', 'CAD',
  'SEK', 'NOK', 'DKK', 'PLN', 'CZK', 'HUF', 'RON', 'BGN',
  'BRL', 'INR', 'KRW', 'MXN', 'SGD', 'HKD', 'NZD', 'ZAR',
];

@Component({
  selector: 'nimbus-currency-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  template: `
    <nimbus-layout>
      <div class="currency-page">
        <h1>Currency & Exchange Rates</h1>

        <!-- ── Provider Default Currency ────────────────────── -->
        <div class="section">
          <h2>Provider Default Currency</h2>
          <p class="section-hint">
            The base currency for all pricing. Tenants inherit this unless they set a custom invoice currency.
          </p>

          <div class="currency-form">
            <select
              class="form-input currency-select"
              [(ngModel)]="selectedCurrency"
              [disabled]="!canManage()"
            >
              @for (c of currencies; track c) {
                <option [value]="c">{{ c }}</option>
              }
            </select>
            <button
              *nimbusHasPermission="'settings:currency:manage'"
              class="btn btn-primary"
              (click)="saveProviderCurrency()"
              [disabled]="savingCurrency() || selectedCurrency === currentCurrency()"
            >
              {{ savingCurrency() ? 'Saving...' : 'Save' }}
            </button>
          </div>
        </div>

        <!-- ── Exchange Rates ───────────────────────────────── -->
        <div class="section">
          <div class="section-header">
            <h2>Exchange Rates</h2>
            <span class="section-count">{{ rates().length }}</span>
            <button
              *nimbusHasPermission="'settings:exchange_rate:manage'"
              class="btn btn-primary btn-sm"
              (click)="showAddForm()"
            >
              + Add Rate
            </button>
          </div>
          <p class="section-hint">
            Define conversion rates between currencies. Each provider manages its own rates.
          </p>

          <!-- Filter -->
          <div class="filter-row">
            <select class="form-input filter-select" [(ngModel)]="filterSource" (ngModelChange)="loadRates()">
              <option value="">All sources</option>
              @for (c of currencies; track c) {
                <option [value]="c">{{ c }}</option>
              }
            </select>
            <select class="form-input filter-select" [(ngModel)]="filterTarget" (ngModelChange)="loadRates()">
              <option value="">All targets</option>
              @for (c of currencies; track c) {
                <option [value]="c">{{ c }}</option>
              }
            </select>
          </div>

          <!-- Add form -->
          @if (addingRate()) {
            <div class="form-card">
              <h3 class="form-title">New Exchange Rate</h3>
              <div class="form-row">
                <div class="form-group third">
                  <label class="form-label">Source Currency *</label>
                  <select class="form-input" [(ngModel)]="newRate.sourceCurrency">
                    @for (c of currencies; track c) {
                      <option [value]="c">{{ c }}</option>
                    }
                  </select>
                </div>
                <div class="form-group third">
                  <label class="form-label">Target Currency *</label>
                  <select class="form-input" [(ngModel)]="newRate.targetCurrency">
                    @for (c of currencies; track c) {
                      <option [value]="c">{{ c }}</option>
                    }
                  </select>
                </div>
                <div class="form-group third">
                  <label class="form-label">Rate *</label>
                  <input
                    class="form-input"
                    type="number"
                    [(ngModel)]="newRate.rate"
                    min="0.00000001"
                    step="0.0001"
                    placeholder="1.00000000"
                  />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group half">
                  <label class="form-label">Effective From *</label>
                  <input class="form-input" type="date" [(ngModel)]="newRate.effectiveFrom" />
                </div>
                <div class="form-group half">
                  <label class="form-label">Effective To</label>
                  <input class="form-input" type="date" [(ngModel)]="newRate.effectiveTo" />
                </div>
              </div>
              <div class="form-actions">
                <button class="btn btn-secondary" (click)="cancelAdd()">Cancel</button>
                <button
                  class="btn btn-primary"
                  (click)="createRate()"
                  [disabled]="!isNewRateValid()"
                >Create</button>
              </div>
            </div>
          }

          <!-- Edit form -->
          @if (editingRate()) {
            <div class="form-card">
              <h3 class="form-title">
                Edit Rate: {{ editData.sourceCurrency }} &rarr; {{ editData.targetCurrency }}
              </h3>
              <div class="form-row">
                <div class="form-group third">
                  <label class="form-label">Rate *</label>
                  <input
                    class="form-input"
                    type="number"
                    [(ngModel)]="editData.rate"
                    min="0.00000001"
                    step="0.0001"
                  />
                </div>
                <div class="form-group third">
                  <label class="form-label">Effective From *</label>
                  <input class="form-input" type="date" [(ngModel)]="editData.effectiveFrom" />
                </div>
                <div class="form-group third">
                  <label class="form-label">Effective To</label>
                  <input class="form-input" type="date" [(ngModel)]="editData.effectiveTo" />
                </div>
              </div>
              <div class="form-actions">
                <button class="btn btn-secondary" (click)="cancelEdit()">Cancel</button>
                <button
                  class="btn btn-primary"
                  (click)="saveEdit()"
                  [disabled]="editData.rate <= 0 || !editData.effectiveFrom"
                >Save</button>
              </div>
            </div>
          }

          <!-- Rates table -->
          @if (rates().length > 0) {
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Source</th>
                    <th>Target</th>
                    <th>Rate</th>
                    <th>Effective From</th>
                    <th>Effective To</th>
                    <th>Updated</th>
                    <th class="th-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (rate of rates(); track rate.id) {
                    <tr>
                      <td><span class="currency-badge">{{ rate.sourceCurrency }}</span></td>
                      <td><span class="currency-badge">{{ rate.targetCurrency }}</span></td>
                      <td class="mono">{{ rate.rate | number: '1.2-8' }}</td>
                      <td>{{ rate.effectiveFrom | date: 'mediumDate' }}</td>
                      <td>
                        @if (rate.effectiveTo) {
                          {{ rate.effectiveTo | date: 'mediumDate' }}
                        } @else {
                          <span class="text-muted">No end date</span>
                        }
                      </td>
                      <td class="text-muted">{{ rate.updatedAt | date: 'medium' }}</td>
                      <td class="td-actions">
                        <button
                          *nimbusHasPermission="'settings:exchange_rate:manage'"
                          class="btn-icon"
                          (click)="startEdit(rate)"
                          title="Edit"
                        >&#9998;</button>
                        <button
                          *nimbusHasPermission="'settings:exchange_rate:manage'"
                          class="btn-icon-del"
                          (click)="deleteRate(rate)"
                          title="Delete"
                        >&#10005;</button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          } @else if (!addingRate()) {
            <div class="empty-hint">No exchange rates configured yet.</div>
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .currency-page { padding: 0; }
    h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 1.25rem; }
    .section { margin-bottom: 2rem; }
    .section h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin-bottom: 0.75rem; }
    .section-hint { font-size: 0.8125rem; color: #64748b; margin: -0.25rem 0 1rem; }
    .section-header {
      display: flex; align-items: center; gap: 0.5rem;
      margin-bottom: 0.75rem; padding-bottom: 0.5rem;
      border-bottom: 1px solid #f1f5f9;
    }
    .section-header h2 { margin: 0; }
    .section-count {
      background: #f1f5f9; color: #64748b; padding: 0.125rem 0.5rem;
      border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .section-header .btn { margin-left: auto; }

    .currency-form { display: flex; gap: 0.5rem; align-items: center; max-width: 320px; }
    .currency-select { width: 160px; }

    .filter-row { display: flex; gap: 0.5rem; margin-bottom: 1rem; }
    .filter-select { width: 160px; }

    /* ── Forms ──────────────────────────────────────────────── */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem;
    }
    .form-title {
      font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem;
      padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;
    }
    .form-group { margin-bottom: 1rem; }
    .form-label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-group.third { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }

    /* ── Table ──────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .data-table th, .data-table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .data-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .data-table tbody tr:hover { background: #f8fafc; }
    .th-actions, .td-actions { width: 80px; text-align: right; }
    .td-actions { display: flex; gap: 0.25rem; justify-content: flex-end; }

    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
      color: #374151;
    }
    .text-muted { color: #94a3b8; font-size: 0.8125rem; }
    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 0.5rem 0; }

    .currency-badge {
      display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px;
      background: #eff6ff; color: #3b82f6; font-size: 0.75rem; font-weight: 600;
      letter-spacing: 0.05em;
    }

    /* ── Buttons ────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; transition: background 0.15s;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover:not(:disabled) { background: #f8fafc; }
    .btn-icon {
      padding: 0.2rem 0.4rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; cursor: pointer; font-size: 0.75rem; color: #3b82f6;
    }
    .btn-icon:hover { background: #eff6ff; border-color: #bfdbfe; }
    .btn-icon-del {
      padding: 0.2rem 0.4rem; border: 1px solid #e2e8f0; border-radius: 4px;
      background: #fff; cursor: pointer; font-size: 0.75rem; color: #dc2626;
    }
    .btn-icon-del:hover { background: #fef2f2; border-color: #fecaca; }
  `],
})
export class CurrencySettingsComponent implements OnInit {
  private currencyService = inject(CurrencyService);
  private tenantContext = inject(TenantContextService);
  private tenantService = inject(TenantService);
  private toastService = inject(ToastService);

  currencies = COMMON_CURRENCIES;
  currentCurrency = signal('EUR');
  selectedCurrency = 'EUR';
  savingCurrency = signal(false);

  rates = signal<ExchangeRate[]>([]);
  addingRate = signal(false);
  editingRate = signal(false);
  editingRateId = '';

  filterSource = '';
  filterTarget = '';

  canManage = computed(() => true); // Permission-gated by route guard + directives

  newRate = {
    sourceCurrency: 'EUR',
    targetCurrency: 'USD',
    rate: 1,
    effectiveFrom: '',
    effectiveTo: '',
  };

  editData = {
    sourceCurrency: '',
    targetCurrency: '',
    rate: 0,
    effectiveFrom: '',
    effectiveTo: '',
  };

  private providerId = '';

  ngOnInit(): void {
    const tenantId = this.tenantContext.currentTenantId();
    if (tenantId) {
      this.tenantService.getTenant(tenantId).subscribe({
        next: (tenant) => {
          this.providerId = tenant.provider_id;
          this.loadProviderCurrency();
          this.loadRates();
        },
      });
    }
  }

  // ── Provider Currency ─────────────────────────────────────────────

  saveProviderCurrency(): void {
    this.savingCurrency.set(true);
    this.currencyService.updateProviderCurrency(this.providerId, this.selectedCurrency).subscribe({
      next: (result) => {
        this.currentCurrency.set(result.defaultCurrency);
        this.savingCurrency.set(false);
        this.toastService.success('Provider currency updated');
      },
      error: (err) => {
        this.savingCurrency.set(false);
        this.toastService.error(err.message || 'Failed to update currency');
      },
    });
  }

  // ── Exchange Rates ────────────────────────────────────────────────

  loadRates(): void {
    this.currencyService
      .listExchangeRates(this.providerId, this.filterSource || undefined, this.filterTarget || undefined)
      .subscribe({
        next: (rates) => this.rates.set(rates),
        error: () => this.rates.set([]),
      });
  }

  showAddForm(): void {
    this.cancelEdit();
    this.newRate = {
      sourceCurrency: this.currentCurrency(),
      targetCurrency: this.currentCurrency() === 'USD' ? 'EUR' : 'USD',
      rate: 1,
      effectiveFrom: new Date().toISOString().split('T')[0],
      effectiveTo: '',
    };
    this.addingRate.set(true);
  }

  cancelAdd(): void {
    this.addingRate.set(false);
  }

  isNewRateValid(): boolean {
    return (
      this.newRate.sourceCurrency !== this.newRate.targetCurrency &&
      this.newRate.rate > 0 &&
      !!this.newRate.effectiveFrom
    );
  }

  createRate(): void {
    this.currencyService
      .createExchangeRate(this.providerId, {
        sourceCurrency: this.newRate.sourceCurrency,
        targetCurrency: this.newRate.targetCurrency,
        rate: this.newRate.rate,
        effectiveFrom: this.newRate.effectiveFrom,
        effectiveTo: this.newRate.effectiveTo || null,
      })
      .subscribe({
        next: (created) => {
          this.rates.update((list) => [created, ...list]);
          this.addingRate.set(false);
          this.toastService.success('Exchange rate created');
        },
        error: (err) => this.toastService.error(err.message || 'Failed to create rate'),
      });
  }

  startEdit(rate: ExchangeRate): void {
    this.cancelAdd();
    this.editingRateId = rate.id;
    this.editData = {
      sourceCurrency: rate.sourceCurrency,
      targetCurrency: rate.targetCurrency,
      rate: rate.rate,
      effectiveFrom: rate.effectiveFrom,
      effectiveTo: rate.effectiveTo ?? '',
    };
    this.editingRate.set(true);
  }

  cancelEdit(): void {
    this.editingRate.set(false);
    this.editingRateId = '';
  }

  saveEdit(): void {
    this.currencyService
      .updateExchangeRate(this.providerId, this.editingRateId, {
        rate: this.editData.rate,
        effectiveFrom: this.editData.effectiveFrom,
        effectiveTo: this.editData.effectiveTo || null,
      })
      .subscribe({
        next: (updated) => {
          this.rates.update((list) =>
            list.map((r) => (r.id === updated.id ? updated : r)),
          );
          this.cancelEdit();
          this.toastService.success('Exchange rate updated');
        },
        error: (err) => this.toastService.error(err.message || 'Failed to update rate'),
      });
  }

  deleteRate(rate: ExchangeRate): void {
    this.currencyService.deleteExchangeRate(this.providerId, rate.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.rates.update((list) => list.filter((r) => r.id !== rate.id));
          this.toastService.success('Exchange rate deleted');
        }
      },
      error: (err) => this.toastService.error(err.message || 'Failed to delete rate'),
    });
  }

  // ── Private ───────────────────────────────────────────────────────

  private loadProviderCurrency(): void {
    this.currencyService.getProviderCurrency(this.providerId).subscribe({
      next: (result) => {
        this.currentCurrency.set(result.defaultCurrency);
        this.selectedCurrency = result.defaultCurrency;
      },
    });
  }
}
