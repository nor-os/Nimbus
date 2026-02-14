/**
 * Overview: Tenant-facing read-only view of the service catalog pinned to the current tenant.
 *     Displays published service offerings with customer-facing prices, grouped by category,
 *     along with service groups. No internal cost rates, markups, or provider data exposed.
 * Architecture: Feature component for tenant service catalog view (Section 8)
 * Dependencies: @angular/core, @angular/common, rxjs, app/core/services/catalog.service,
 *     app/core/services/tenant-context.service, app/shared/components/layout/layout.component
 * Concepts: Tenant catalog pin, effective pricing, service offerings, service groups,
 *     customer-facing catalog, read-only view
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
import { forkJoin, of } from 'rxjs';
import { CatalogService } from '@core/services/catalog.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import {
  EffectivePrice,
  ServiceCatalog,
  ServiceCatalogItem,
  ServiceGroup,
  ServiceOffering,
  TenantCatalogPin,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

/** Enriched offering with its effective price for display. */
interface CatalogOffering {
  offering: ServiceOffering;
  price: EffectivePrice | null;
}

/** Offerings grouped by category for display. */
interface CategoryGroup {
  category: string;
  offerings: CatalogOffering[];
}

/** Service group enriched with resolved offering details. */
interface CatalogGroup {
  group: ServiceGroup;
  offerings: CatalogOffering[];
}

@Component({
  selector: 'nimbus-tenant-catalog',
  standalone: true,
  imports: [CommonModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="catalog-page">
        <!-- Page header -->
        <div class="page-header">
          <div class="page-title-row">
            <h1>Service Catalog</h1>
            @if (catalog()) {
              <span class="badge badge-version">
                v{{ catalog()!.versionMajor }}.{{ catalog()!.versionMinor }}
              </span>
              <span class="badge" [class]="'badge-status-' + catalog()!.status">
                {{ catalog()!.status }}
              </span>
            }
          </div>
          @if (catalog()) {
            <div class="catalog-meta">
              <span class="meta-name">{{ catalog()!.name }}</span>
              @if (catalog()!.description) {
                <span class="meta-sep">&mdash;</span>
                <span class="meta-desc">{{ catalog()!.description }}</span>
              }
            </div>
          }
        </div>

        <!-- Loading state -->
        @if (loading()) {
          <div class="loading">Loading service catalog...</div>
        }

        <!-- No catalog pinned -->
        @if (!loading() && !catalog()) {
          <div class="empty-state">
            <div class="empty-icon">&#x1F4CB;</div>
            <h2 class="empty-title">No Service Catalog Available</h2>
            <p class="empty-text">
              No service catalog has been assigned to your organization.
              Please contact your service provider for access.
            </p>
          </div>
        }

        <!-- Catalog content -->
        @if (!loading() && catalog()) {
          <!-- Category-grouped offerings -->
          @if (categoryGroups().length > 0) {
            @for (group of categoryGroups(); track group.category) {
              <section class="category-section">
                <h2 class="category-heading">{{ group.category }}</h2>
                <div class="offerings-grid">
                  @for (item of group.offerings; track item.offering.id) {
                    <div class="offering-card">
                      <div class="offering-header">
                        <span class="offering-name">{{ item.offering.name }}</span>
                        <span class="badge" [class]="'badge-status-' + item.offering.status">
                          {{ item.offering.status }}
                        </span>
                      </div>
                      @if (item.offering.description) {
                        <p class="offering-desc">{{ item.offering.description }}</p>
                      }
                      <div class="offering-details">
                        <div class="detail-row">
                          <span class="detail-label">Type</span>
                          <span class="detail-value">{{ formatServiceType(item.offering.serviceType) }}</span>
                        </div>
                        <div class="detail-row">
                          <span class="detail-label">Unit</span>
                          <span class="detail-value">{{ formatMeasuringUnit(item.offering.measuringUnit) }}</span>
                        </div>
                        @if (item.offering.defaultCoverageModel) {
                          <div class="detail-row">
                            <span class="detail-label">Coverage</span>
                            <span class="detail-value">{{ formatCoverage(item.offering.defaultCoverageModel) }}</span>
                          </div>
                        }
                        @if (item.offering.baseFee != null && item.offering.baseFee > 0) {
                          <div class="detail-row">
                            <span class="detail-label">Base Fee</span>
                            <span class="detail-value mono">
                              {{ item.offering.baseFee | number: '1.2-2' }}
                              @if (item.offering.feePeriod) {
                                <span class="fee-period">/ {{ item.offering.feePeriod }}</span>
                              }
                            </span>
                          </div>
                        }
                      </div>
                      <!-- Price section -->
                      <div class="offering-price-section">
                        @if (item.price) {
                          <div class="price-display">
                            <span class="price-amount">
                              {{ item.price.currency }} {{ item.price.pricePerUnit | number: '1.2-2' }}
                            </span>
                            <span class="price-unit">
                              per {{ formatMeasuringUnit(item.price.measuringUnit) }}
                            </span>
                          </div>
                          @if (item.price.coverageModel) {
                            <span class="price-coverage">
                              {{ formatCoverage(item.price.coverageModel) }}
                            </span>
                          }
                        } @else {
                          <span class="price-unavailable">Price on request</span>
                        }
                      </div>
                    </div>
                  }
                </div>
              </section>
            }
          }

          <!-- Service groups -->
          @if (catalogGroups().length > 0) {
            <section class="groups-section">
              <h2 class="section-heading">Service Bundles</h2>
              @for (cg of catalogGroups(); track cg.group.id) {
                <div class="group-card">
                  <div class="group-header">
                    <span class="group-name">{{ cg.group.displayName || cg.group.name }}</span>
                    @if (cg.group.description) {
                      <span class="group-desc">{{ cg.group.description }}</span>
                    }
                  </div>
                  <div class="group-offerings">
                    @for (item of cg.offerings; track item.offering.id) {
                      <div class="group-offering-row">
                        <div class="group-offering-info">
                          <span class="group-offering-name">{{ item.offering.name }}</span>
                          @if (item.offering.description) {
                            <span class="group-offering-desc">{{ item.offering.description }}</span>
                          }
                        </div>
                        <div class="group-offering-price">
                          @if (item.price) {
                            <span class="price-amount-sm">
                              {{ item.price.currency }} {{ item.price.pricePerUnit | number: '1.2-2' }}
                            </span>
                            <span class="price-unit-sm">
                              / {{ formatMeasuringUnit(item.price.measuringUnit) }}
                            </span>
                          } @else {
                            <span class="price-unavailable-sm">Price on request</span>
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }
            </section>
          }

          <!-- No offerings in catalog -->
          @if (categoryGroups().length === 0 && catalogGroups().length === 0) {
            <div class="empty-state">
              <p class="empty-text">
                This catalog does not contain any service offerings yet.
              </p>
            </div>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .catalog-page { padding: 0; max-width: 1080px; }

    /* -- Page header -------------------------------------------------------- */
    .page-header { margin-bottom: 2rem; }
    .page-title-row {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;
    }
    .page-title-row h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .catalog-meta {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.875rem; color: #475569; margin-bottom: 0.25rem;
    }
    .meta-name { font-weight: 600; }
    .meta-sep { color: #94a3b8; }
    .meta-desc { color: #64748b; }
    .catalog-dates {
      display: flex; gap: 0.5rem; font-size: 0.8125rem; color: #64748b;
    }
    .date-label { white-space: nowrap; }

    /* -- Badges ------------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; white-space: nowrap;
    }
    .badge-version { background: #e0e7ff; color: #3730a3; }
    .badge-status-draft { background: #fef3c7; color: #92400e; }
    .badge-status-published { background: #dcfce7; color: #166534; }
    .badge-status-archived { background: #f1f5f9; color: #64748b; }

    /* -- Loading & empty states --------------------------------------------- */
    .loading {
      padding: 3rem; text-align: center; color: #64748b; font-size: 0.875rem;
    }
    .empty-state {
      padding: 4rem 2rem; text-align: center;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 12px;
    }
    .empty-icon { font-size: 2.5rem; margin-bottom: 1rem; }
    .empty-title {
      font-size: 1.125rem; font-weight: 600; color: #1e293b; margin: 0 0 0.5rem;
    }
    .empty-text {
      font-size: 0.875rem; color: #64748b; margin: 0;
      max-width: 400px; margin-left: auto; margin-right: auto;
      line-height: 1.5;
    }

    /* -- Category sections -------------------------------------------------- */
    .category-section { margin-bottom: 2rem; }
    .category-heading {
      font-size: 1.125rem; font-weight: 600; color: #1e293b;
      margin: 0 0 1rem; padding-bottom: 0.5rem;
      border-bottom: 2px solid #e2e8f0;
    }
    .section-heading {
      font-size: 1.125rem; font-weight: 600; color: #1e293b;
      margin: 0 0 1rem; padding-bottom: 0.5rem;
      border-bottom: 2px solid #e2e8f0;
    }

    /* -- Offering cards grid ------------------------------------------------ */
    .offerings-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
      gap: 1rem;
    }
    .offering-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; display: flex; flex-direction: column;
      transition: box-shadow 0.15s;
    }
    .offering-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }
    .offering-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      gap: 0.5rem; margin-bottom: 0.5rem;
    }
    .offering-name {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b; line-height: 1.3;
    }
    .offering-desc {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 0.75rem;
      line-height: 1.5;
    }

    /* -- Offering details --------------------------------------------------- */
    .offering-details {
      display: flex; flex-direction: column; gap: 0.375rem;
      margin-bottom: 1rem; flex: 1;
    }
    .detail-row {
      display: flex; justify-content: space-between; align-items: center;
      font-size: 0.8125rem;
    }
    .detail-label { color: #64748b; font-weight: 500; }
    .detail-value { color: #374151; font-weight: 500; }
    .fee-period { color: #64748b; font-weight: 400; font-size: 0.75rem; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8125rem;
    }

    /* -- Price display ------------------------------------------------------ */
    .offering-price-section {
      border-top: 1px solid #f1f5f9; padding-top: 0.75rem;
      display: flex; align-items: baseline; gap: 0.5rem; flex-wrap: wrap;
    }
    .price-display {
      display: flex; align-items: baseline; gap: 0.375rem;
    }
    .price-amount {
      font-size: 1.125rem; font-weight: 700; color: #1e293b;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .price-unit { font-size: 0.75rem; color: #64748b; }
    .price-coverage {
      font-size: 0.6875rem; color: #475569; background: #f1f5f9;
      padding: 0.125rem 0.5rem; border-radius: 12px;
    }
    .price-unavailable {
      font-size: 0.8125rem; color: #94a3b8; font-style: italic;
    }

    /* -- Service groups ----------------------------------------------------- */
    .groups-section { margin-bottom: 2rem; }
    .group-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1rem; overflow: hidden;
    }
    .group-header {
      padding: 1rem 1.25rem; border-bottom: 1px solid #f1f5f9;
      display: flex; flex-direction: column; gap: 0.25rem;
    }
    .group-name {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b;
    }
    .group-desc {
      font-size: 0.8125rem; color: #64748b;
    }
    .group-offerings { padding: 0; }
    .group-offering-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 1.25rem;
      border-bottom: 1px solid #f8fafc;
    }
    .group-offering-row:last-child { border-bottom: none; }
    .group-offering-row:hover { background: #f8fafc; }
    .group-offering-info {
      display: flex; flex-direction: column; gap: 0.125rem;
    }
    .group-offering-name {
      font-size: 0.875rem; font-weight: 500; color: #1e293b;
    }
    .group-offering-desc {
      font-size: 0.75rem; color: #64748b;
    }
    .group-offering-price {
      display: flex; align-items: baseline; gap: 0.25rem;
      white-space: nowrap;
    }
    .price-amount-sm {
      font-size: 0.9375rem; font-weight: 700; color: #1e293b;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .price-unit-sm { font-size: 0.6875rem; color: #64748b; }
    .price-unavailable-sm {
      font-size: 0.75rem; color: #94a3b8; font-style: italic;
    }
  `],
})
export class TenantCatalogComponent implements OnInit {
  private catalogService = inject(CatalogService);
  private tenantContext = inject(TenantContextService);

  // -- State signals ----------------------------------------------------------

  loading = signal(true);
  catalog = signal<ServiceCatalog | null>(null);
  offerings = signal<CatalogOffering[]>([]);
  groups = signal<CatalogGroup[]>([]);

  // -- Computed views ---------------------------------------------------------

  /** Offerings grouped by category for display. */
  categoryGroups = computed<CategoryGroup[]>(() => {
    const items = this.offerings();
    const categoryMap = new Map<string, CatalogOffering[]>();
    for (const item of items) {
      const cat = item.offering.category || 'General';
      if (!categoryMap.has(cat)) {
        categoryMap.set(cat, []);
      }
      categoryMap.get(cat)!.push(item);
    }
    return Array.from(categoryMap.entries())
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([category, catOfferings]) => ({ category, offerings: catOfferings }));
  });

  /** Enriched service groups. */
  catalogGroups = computed<CatalogGroup[]>(() => this.groups());

  // -- Lifecycle --------------------------------------------------------------

  ngOnInit(): void {
    this.loadCatalog();
  }

  // -- Display helpers --------------------------------------------------------

  formatServiceType(type: string): string {
    const map: Record<string, string> = {
      resource: 'Resource',
      labor: 'Labor',
    };
    return map[type] || type;
  }

  formatMeasuringUnit(unit: string): string {
    const map: Record<string, string> = {
      hour: 'Hour',
      day: 'Day',
      month: 'Month',
      gb: 'GB',
      request: 'Request',
      user: 'User',
      instance: 'Instance',
    };
    return map[unit] || unit;
  }

  formatCoverage(model: string | null): string {
    if (!model) return '';
    const map: Record<string, string> = {
      business_hours: 'Business Hours',
      extended: 'Extended',
      '24x7': '24x7',
    };
    return map[model] || model;
  }

  // -- Private data loading ---------------------------------------------------

  /**
   * Main loading flow:
   * 1. Load catalog pins for the current tenant
   * 2. Find the first pinned catalog
   * 3. Load the full catalog
   * 4. Resolve offering IDs to full ServiceOffering objects
   * 5. Load effective prices for each offering
   * 6. Resolve service group items
   */
  private loadCatalog(): void {
    this.loading.set(true);

    this.catalogService.listCatalogPins().subscribe({
      next: (pins: TenantCatalogPin[]) => {
        if (pins.length === 0) {
          this.loading.set(false);
          return;
        }

        // Use the first pinned catalog (with embedded catalog if available)
        const pin = pins[0];
        if (pin.catalog) {
          this.catalog.set(pin.catalog);
          this.resolveCatalogContents(pin.catalog);
        } else {
          // Fallback: load catalog by ID
          this.catalogService.getCatalog(pin.catalogId).subscribe({
            next: (cat) => {
              if (cat) {
                this.catalog.set(cat);
                this.resolveCatalogContents(cat);
              } else {
                this.loading.set(false);
              }
            },
            error: () => this.loading.set(false),
          });
        }
      },
      error: () => this.loading.set(false),
    });
  }

  /**
   * Given a loaded catalog, resolves its items into offerings and groups.
   * Catalog items reference either a serviceOfferingId or a serviceGroupId.
   */
  private resolveCatalogContents(catalog: ServiceCatalog): void {
    const offeringItemIds = catalog.items
      .filter((i: ServiceCatalogItem) => !!i.serviceOfferingId)
      .map((i: ServiceCatalogItem) => i.serviceOfferingId!);

    const groupItemIds = catalog.items
      .filter((i: ServiceCatalogItem) => !!i.serviceGroupId)
      .map((i: ServiceCatalogItem) => i.serviceGroupId!);

    // Load all offerings referenced in the catalog
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (offeringList) => {
        const allOfferings = offeringList.items;

        // Filter to only offerings referenced in the catalog
        const catalogOfferings = allOfferings.filter(
          (o) => offeringItemIds.includes(o.id),
        );

        // Load effective prices for each offering
        this.loadEffectivePrices(catalogOfferings);

        // Load service groups
        if (groupItemIds.length > 0) {
          this.loadGroups(groupItemIds, allOfferings);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  /**
   * Loads effective prices for all catalog offerings and builds the
   * enriched CatalogOffering array.
   */
  private loadEffectivePrices(catalogOfferings: ServiceOffering[]): void {
    if (catalogOfferings.length === 0) {
      this.offerings.set([]);
      this.loading.set(false);
      return;
    }

    const priceRequests = catalogOfferings.map((offering) =>
      this.catalogService.getEffectivePrice(offering.id),
    );

    forkJoin(priceRequests.length > 0 ? priceRequests : [of(null)]).subscribe({
      next: (prices) => {
        const enriched: CatalogOffering[] = catalogOfferings.map(
          (offering, idx) => ({
            offering,
            price: prices[idx] || null,
          }),
        );
        this.offerings.set(enriched);
        this.loading.set(false);
      },
      error: () => {
        // Even if prices fail, still show offerings without prices
        const enriched: CatalogOffering[] = catalogOfferings.map(
          (offering) => ({
            offering,
            price: null,
          }),
        );
        this.offerings.set(enriched);
        this.loading.set(false);
      },
    });
  }

  /**
   * Loads service groups and enriches them with offering details and prices.
   */
  private loadGroups(
    groupIds: string[],
    allOfferings: ServiceOffering[],
  ): void {
    const groupRequests = groupIds.map((gid) =>
      this.catalogService.getGroup(gid),
    );

    forkJoin(groupRequests).subscribe({
      next: (loadedGroups) => {
        const enrichedGroups: CatalogGroup[] = [];

        for (const group of loadedGroups) {
          if (!group) continue;

          const memberOfferingIds = group.items.map((gi) => gi.serviceOfferingId);
          const memberOfferings = allOfferings.filter((o) =>
            memberOfferingIds.includes(o.id),
          );

          // Fetch effective prices for group member offerings
          if (memberOfferings.length > 0) {
            const priceReqs = memberOfferings.map((o) =>
              this.catalogService.getEffectivePrice(o.id),
            );

            forkJoin(priceReqs).subscribe({
              next: (prices) => {
                const members: CatalogOffering[] = memberOfferings.map(
                  (offering, idx) => ({
                    offering,
                    price: prices[idx] || null,
                  }),
                );

                // Sort members by the sort order defined in the group items
                members.sort((a, b) => {
                  const aOrder = group.items.find(
                    (gi) => gi.serviceOfferingId === a.offering.id,
                  )?.sortOrder ?? 0;
                  const bOrder = group.items.find(
                    (gi) => gi.serviceOfferingId === b.offering.id,
                  )?.sortOrder ?? 0;
                  return aOrder - bOrder;
                });

                enrichedGroups.push({ group, offerings: members });
                this.groups.set([...enrichedGroups]);
              },
            });
          } else {
            enrichedGroups.push({ group, offerings: [] });
            this.groups.set([...enrichedGroups]);
          }
        }
      },
    });
  }
}
