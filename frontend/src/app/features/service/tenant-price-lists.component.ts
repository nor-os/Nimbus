/**
 * Overview: Tenant-facing read-only view of price lists pinned to the current tenant.
 *     Displays published price lists with their items (service name, price, currency,
 *     coverage model) without exposing internal data such as markups or cost rates.
 * Architecture: Service feature component, customer-facing (Section 8)
 * Dependencies: @angular/core, @angular/common, app/core/services/catalog.service,
 *     app/core/services/tenant-context.service, app/shared/components/layout/layout.component
 * Concepts: Tenant price list pins, read-only pricing view, customer-facing portal,
 *     offering name resolution via offerings map
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { CatalogService } from '@core/services/catalog.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import {
  TenantPriceListPin,
  PriceList,
  PriceListItem,
  ServiceOffering,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-tenant-price-lists',
  standalone: true,
  imports: [CommonModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="tenant-price-lists-page">
        <div class="page-header">
          <h1>Price Lists</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading price lists...</div>
        }

        @if (!loading() && priceListCards().length === 0) {
          <div class="empty-state">
            No price lists have been assigned to your organization.
          </div>
        }

        @for (card of priceListCards(); track card.pin.id) {
          <div class="price-list-card">
            <div class="card-header">
              <div class="card-title-row">
                <span class="card-name">{{ card.priceList.name }}</span>
                <span class="badge badge-version">{{ card.priceList.versionLabel }}</span>
                <span class="badge" [class]="'badge-status-' + card.priceList.status">
                  {{ card.priceList.status }}
                </span>
              </div>
              <div class="card-meta"></div>
            </div>

            <div class="items-section">
              @if (card.priceList.items.length > 0) {
                <table class="items-table">
                  <thead>
                    <tr>
                      <th>Service / SKU</th>
                      <th>Price per Unit</th>
                      <th>Currency</th>
                      <th>Coverage</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of card.priceList.items; track item.id) {
                      <tr>
                        <td>{{ resolveItemName(item) }}</td>
                        <td class="mono">{{ item.pricePerUnit | number: '1.2-2' }}</td>
                        <td>{{ item.currency }}</td>
                        <td>{{ formatCoverage(item.coverageModel) }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              } @else {
                <div class="no-items">No items in this price list.</div>
              }
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .tenant-price-lists-page { padding: 0; max-width: 960px; }

    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.875rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }

    /* -- Price list cards --------------------------------------------------- */
    .price-list-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1rem; overflow: hidden;
    }
    .card-header {
      padding: 1rem 1.25rem; border-bottom: 1px solid #f1f5f9;
    }
    .card-title-row {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.375rem;
    }
    .card-name {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b;
    }
    .card-meta {
      display: flex; gap: 1rem; font-size: 0.75rem; color: #64748b;
    }
    .meta-item { white-space: nowrap; }
    .meta-muted { color: #94a3b8; font-style: italic; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-version { background: #dbeafe; color: #1d4ed8; }
    .badge-status-draft { background: #fef3c7; color: #92400e; }
    .badge-status-published { background: #dcfce7; color: #166534; }
    .badge-status-archived { background: #f1f5f9; color: #64748b; }

    /* -- Items table -------------------------------------------------------- */
    .items-section { padding: 0.75rem 1.25rem 1rem; }
    .items-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .items-table th, .items-table td {
      padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
      color: #374151;
    }
    .items-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .items-table tbody tr:hover { background: #f8fafc; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .no-items {
      color: #64748b; font-size: 0.8125rem; padding: 0.5rem 0;
    }
  `],
})
export class TenantPriceListsComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private tenantContext = inject(TenantContextService);

  /** Raw pins returned from the API. */
  pins = signal<TenantPriceListPin[]>([]);

  /** All offerings loaded for name resolution. */
  offerings = signal<ServiceOffering[]>([]);

  /** Map from offering ID to offering name for fast lookups. */
  offeringsMap = computed<Map<string, string>>(() => {
    const map = new Map<string, string>();
    for (const offering of this.offerings()) {
      map.set(offering.id, offering.name);
    }
    return map;
  });

  loading = signal(true);

  /** Derived list of cards — each pin with its nested price list (non-null only). */
  priceListCards = computed(() => {
    return this.pins()
      .filter((pin): pin is TenantPriceListPin & { priceList: PriceList } => pin.priceList != null)
      .map((pin) => ({
        pin,
        priceList: pin.priceList,
      }));
  });

  ngOnInit(): void {
    this.loadPins();
    this.loadOfferings();
  }

  /** Resolve a display name for a price list item. */
  resolveItemName(item: PriceListItem): string {
    if (item.serviceOfferingId) {
      const name = this.offeringsMap().get(item.serviceOfferingId);
      return name ?? item.serviceOfferingId.substring(0, 8) + '...';
    }
    if (item.providerSkuId) {
      return item.providerSkuId.substring(0, 8) + '...';
    }
    if (item.activityDefinitionId) {
      return item.activityDefinitionId.substring(0, 8) + '...';
    }
    return 'Unknown';
  }

  /** Format a coverage model string for display. */
  formatCoverage(model: string | null): string {
    if (!model) return '\u2014';
    const labels: Record<string, string> = {
      business_hours: 'Business Hours',
      extended: 'Extended',
      '24x7': '24x7',
    };
    return labels[model] || model;
  }

  // -- Private loaders -------------------------------------------------------

  private loadPins(): void {
    const tenantId = this.tenantContext.currentTenantId();
    if (!tenantId) {
      this.loading.set(false);
      return;
    }

    this.catalogService.listTenantPins(tenantId).subscribe({
      next: (pins) => {
        this.pins.set(pins);
        this.loading.set(false);
      },
      error: () => {
        this.pins.set([]);
        this.loading.set(false);
      },
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });
  }
}
