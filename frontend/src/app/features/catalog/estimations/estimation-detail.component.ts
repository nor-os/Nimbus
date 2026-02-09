/**
 * Overview: Estimation detail — read-only view with approval workflow actions.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/delivery.service
 * Concepts: Service estimation detail, approval workflow, profitability summary
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { DeliveryService } from '@core/services/delivery.service';
import { CatalogService } from '@core/services/catalog.service';
import { TenantService } from '@core/services/tenant.service';
import {
  ServiceEstimation,
  DeliveryRegion,
  StaffProfile,
} from '@shared/models/delivery.model';
import { ServiceOffering } from '@shared/models/cmdb.model';
import { Tenant } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

const COVERAGE_LABELS: Record<string, string> = {
  business_hours: 'Business Hours',
  extended: 'Extended',
  '24x7': '24x7',
};

@Component({
  selector: 'nimbus-estimation-detail',
  standalone: true,
  imports: [CommonModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="detail-page">
        @if (loading()) {
          <div class="loading">Loading estimation...</div>
        }

        @if (!loading() && estimation()) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <h1>Estimation</h1>
              <span class="estimation-id">{{ estimation()!.id.substring(0, 8) }}...</span>
              <span
                class="badge"
                [class.badge-draft]="estimation()!.status === 'draft'"
                [class.badge-submitted]="estimation()!.status === 'submitted'"
                [class.badge-approved]="estimation()!.status === 'approved'"
                [class.badge-rejected]="estimation()!.status === 'rejected'"
              >
                {{ estimation()!.status | titlecase }}
              </span>
            </div>
            <div class="header-actions">
              @if (estimation()!.status === 'draft') {
                <a
                  *nimbusHasPermission="'catalog:estimation:manage'"
                  class="btn btn-outline"
                  (click)="goToEdit()"
                >
                  Edit
                </a>
              }
              @if (estimation()!.status === 'submitted') {
                <button
                  *nimbusHasPermission="'catalog:estimation:approve'"
                  class="btn btn-approve"
                  (click)="approve()"
                  [disabled]="actionInProgress()"
                >
                  {{ actionInProgress() ? 'Processing...' : 'Approve' }}
                </button>
                <button
                  *nimbusHasPermission="'catalog:estimation:approve'"
                  class="btn btn-reject"
                  (click)="reject()"
                  [disabled]="actionInProgress()"
                >
                  {{ actionInProgress() ? 'Processing...' : 'Reject' }}
                </button>
              }
            </div>
          </div>

          <span class="created-label">Created {{ estimation()!.createdAt | date: 'medium' }}</span>
          @if (estimation()!.approvedBy) {
            <span class="approved-label">
              Approved by {{ estimation()!.approvedBy }} on {{ estimation()!.approvedAt | date: 'medium' }}
            </span>
          }

          <!-- Details card -->
          <div class="details-card">
            <h2 class="section-title">Details</h2>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="detail-label">Client</span>
                <span class="detail-value">{{ clientName() }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Service</span>
                <span class="detail-value">{{ serviceName() }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Region</span>
                <span class="detail-value">{{ regionName() }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Coverage</span>
                <span class="detail-value">{{ coverageLabel() }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Quantity</span>
                <span class="detail-value">{{ estimation()!.quantity }}</span>
              </div>
              <div class="detail-item">
                <span class="detail-label">Sell Price / Unit</span>
                <span class="detail-value mono">
                  {{ estimation()!.sellPricePerUnit | number: '1.2-2' }}
                  {{ estimation()!.sellCurrency }}
                </span>
              </div>
            </div>
          </div>

          <!-- Line items table -->
          <div class="details-card">
            <h2 class="section-title">Line Items</h2>
            @if (estimation()!.lineItems.length > 0) {
              <div class="table-container">
                <table class="table">
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Staff Profile</th>
                      <th>Region</th>
                      <th class="th-right">Est. Hours</th>
                      <th class="th-right">Hourly Rate</th>
                      <th class="th-right">Line Cost</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (item of estimation()!.lineItems; track item.id) {
                      <tr>
                        <td class="name-cell">{{ item.name }}</td>
                        <td>{{ staffProfileName(item.staffProfileId) }}</td>
                        <td>{{ regionNameById(item.deliveryRegionId) }}</td>
                        <td class="td-right mono">{{ item.estimatedHours | number: '1.1-1' }}</td>
                        <td class="td-right mono">
                          {{ item.hourlyRate | number: '1.2-2' }} {{ item.rateCurrency }}
                        </td>
                        <td class="td-right mono">{{ item.lineCost | number: '1.2-2' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="empty-lines">No line items</div>
            }
          </div>

          <!-- Summary -->
          <div class="summary-card">
            <h2 class="section-title">Profitability Summary</h2>
            <div class="summary-grid">
              <div class="summary-item">
                <span class="summary-label">Total Cost</span>
                <span class="summary-value mono">
                  @if (estimation()!.totalEstimatedCost != null) {
                    {{ estimation()!.totalEstimatedCost | number: '1.2-2' }}
                  } @else {
                    &mdash;
                  }
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Total Sell</span>
                <span class="summary-value mono">
                  @if (estimation()!.totalSellPrice != null) {
                    {{ estimation()!.totalSellPrice | number: '1.2-2' }}
                  } @else {
                    &mdash;
                  }
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Margin</span>
                <span
                  class="summary-value mono"
                  [class.margin-positive]="(estimation()!.marginAmount ?? 0) >= 0"
                  [class.margin-negative]="(estimation()!.marginAmount ?? 0) < 0"
                >
                  @if (estimation()!.marginAmount != null) {
                    {{ estimation()!.marginAmount | number: '1.2-2' }}
                  } @else {
                    &mdash;
                  }
                </span>
              </div>
              <div class="summary-item">
                <span class="summary-label">Margin %</span>
                <span
                  class="summary-value"
                  [class.margin-positive]="(estimation()!.marginPercent ?? 0) >= 0"
                  [class.margin-negative]="(estimation()!.marginPercent ?? 0) < 0"
                >
                  @if (estimation()!.marginPercent != null) {
                    {{ estimation()!.marginPercent | number: '1.1-1' }}%
                  } @else {
                    &mdash;
                  }
                </span>
              </div>
            </div>
          </div>

          <!-- Back link -->
          <div class="back-row">
            <button class="btn btn-secondary" (click)="goBack()">Back to Estimations</button>
          </div>
        }

        @if (!loading() && !estimation()) {
          <div class="empty-state">Estimation not found.</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .detail-page { padding: 0; max-width: 1100px; }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* ── Header ────────────────────────────────────────────────────── */
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .header-left {
      display: flex; align-items: center; gap: 0.75rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .estimation-id {
      font-size: 0.8125rem; color: #64748b;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .header-actions { display: flex; gap: 0.5rem; }

    .created-label {
      display: block; font-size: 0.8125rem; color: #64748b; margin-bottom: 0.25rem;
    }
    .approved-label {
      display: block; font-size: 0.8125rem; color: #16a34a; margin-bottom: 1rem;
    }

    /* ── Badges ────────────────────────────────────────────────────── */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-submitted { background: #dbeafe; color: #1d4ed8; }
    .badge-approved { background: #dcfce7; color: #16a34a; }
    .badge-rejected { background: #fee2e2; color: #dc2626; }

    /* ── Details card ──────────────────────────────────────────────── */
    .details-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.25rem; margin-top: 1rem;
    }
    .section-title {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b;
      margin: 0 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .detail-grid {
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.25rem;
    }
    .detail-item { display: flex; flex-direction: column; gap: 0.25rem; }
    .detail-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .detail-value { font-size: 0.875rem; color: #1e293b; font-weight: 500; }

    /* ── Table ──────────────────────────────────────────────────────── */
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .th-right, .td-right { text-align: right; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
    }
    .empty-lines {
      text-align: center; color: #94a3b8; padding: 1.5rem; font-size: 0.8125rem;
    }

    /* ── Summary ───────────────────────────────────────────────────── */
    .summary-card {
      background: #f8fafc; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem; margin-bottom: 1.25rem;
    }
    .summary-card .section-title { border-bottom: 1px solid #e2e8f0; }
    .summary-grid {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 1.5rem;
    }
    .summary-item { display: flex; flex-direction: column; gap: 0.25rem; }
    .summary-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .summary-value { font-size: 1.25rem; font-weight: 700; color: #1e293b; }
    .margin-positive { color: #16a34a; }
    .margin-negative { color: #dc2626; }

    /* ── Buttons ────────────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem;
      transition: background 0.15s; border: none;
    }
    .btn-outline {
      background: #fff; color: #3b82f6; border: 1px solid #3b82f6;
      text-decoration: none; cursor: pointer;
    }
    .btn-outline:hover { background: #eff6ff; }
    .btn-approve { background: #16a34a; color: #fff; }
    .btn-approve:hover { background: #15803d; }
    .btn-approve:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-reject { background: #dc2626; color: #fff; }
    .btn-reject:hover { background: #b91c1c; }
    .btn-reject:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #475569; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }

    .back-row {
      margin-bottom: 2rem;
    }
  `],
})
export class EstimationDetailComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  estimation = signal<ServiceEstimation | null>(null);
  loading = signal(false);
  actionInProgress = signal(false);

  // Lookup data
  private clientMap = signal<Map<string, string>>(new Map());
  private serviceMap = signal<Map<string, string>>(new Map());
  private regionMap = signal<Map<string, string>>(new Map());
  private staffMap = signal<Map<string, string>>(new Map());

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id) {
      this.router.navigate(['/catalog', 'estimations']);
      return;
    }

    this.loading.set(true);
    this.loadLookups();
    this.loadEstimation(id);
  }

  approve(): void {
    const est = this.estimation();
    if (!est) return;

    this.actionInProgress.set(true);
    this.deliveryService.approveEstimation(est.id).subscribe({
      next: (updated) => {
        this.estimation.set(updated);
        this.actionInProgress.set(false);
        this.toastService.success('Estimation approved');
      },
      error: (err) => {
        this.actionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to approve estimation');
      },
    });
  }

  reject(): void {
    const est = this.estimation();
    if (!est) return;

    this.actionInProgress.set(true);
    this.deliveryService.rejectEstimation(est.id).subscribe({
      next: (updated) => {
        this.estimation.set(updated);
        this.actionInProgress.set(false);
        this.toastService.success('Estimation rejected');
      },
      error: (err) => {
        this.actionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to reject estimation');
      },
    });
  }

  goToEdit(): void {
    const est = this.estimation();
    if (est) {
      this.router.navigate(['/catalog', 'estimations', est.id, 'edit']);
    }
  }

  goBack(): void {
    this.router.navigate(['/catalog', 'estimations']);
  }

  clientName(): string {
    const est = this.estimation();
    if (!est) return '\u2014';
    return this.clientMap().get(est.clientTenantId) || est.clientTenantId.substring(0, 8) + '...';
  }

  serviceName(): string {
    const est = this.estimation();
    if (!est) return '\u2014';
    return this.serviceMap().get(est.serviceOfferingId) || est.serviceOfferingId.substring(0, 8) + '...';
  }

  regionName(): string {
    const est = this.estimation();
    if (!est || !est.deliveryRegionId) return '\u2014';
    return this.regionMap().get(est.deliveryRegionId) || est.deliveryRegionId.substring(0, 8) + '...';
  }

  coverageLabel(): string {
    const est = this.estimation();
    if (!est || !est.coverageModel) return '\u2014';
    return COVERAGE_LABELS[est.coverageModel] || est.coverageModel;
  }

  staffProfileName(id: string): string {
    return this.staffMap().get(id) || id.substring(0, 8) + '...';
  }

  regionNameById(id: string): string {
    return this.regionMap().get(id) || id.substring(0, 8) + '...';
  }

  // ── Private helpers ─────────────────────────────────────────────

  private loadEstimation(id: string): void {
    this.deliveryService.getEstimation(id).subscribe({
      next: (estimation) => {
        if (!estimation) {
          this.loading.set(false);
          this.toastService.error('Estimation not found');
          this.router.navigate(['/catalog', 'estimations']);
          return;
        }
        this.estimation.set(estimation);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load estimation');
        this.router.navigate(['/catalog', 'estimations']);
      },
    });
  }

  private loadLookups(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (tenants) => {
        const map = new Map<string, string>();
        tenants.forEach((t) => map.set(t.id, t.name));
        this.clientMap.set(map);
      },
    });

    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => {
        const map = new Map<string, string>();
        response.items.forEach((o) => map.set(o.id, o.name));
        this.serviceMap.set(map);
      },
    });

    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (response) => {
        const map = new Map<string, string>();
        response.items.forEach((r) => map.set(r.id, r.displayName));
        this.regionMap.set(map);
      },
    });

    this.deliveryService.listStaffProfiles().subscribe({
      next: (profiles) => {
        const map = new Map<string, string>();
        profiles.forEach((p) => map.set(p.id, p.displayName));
        this.staffMap.set(map);
      },
    });
  }
}
