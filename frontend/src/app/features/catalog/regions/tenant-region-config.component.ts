/**
 * Overview: Tenant region configuration — manage per-tenant delivery region acceptance
 *     overrides including compliance enforcement flags.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms,
 *     app/core/services/delivery.service, app/shared/services/toast.service,
 *     app/shared/services/confirm.service
 * Concepts: Tenant region acceptance, compliance enforcement, delivery region overrides
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
import { FormsModule } from '@angular/forms';
import { DeliveryService } from '@core/services/delivery.service';
import {
  TenantRegionAcceptance,
  TenantRegionAcceptanceCreateInput,
  DeliveryRegion,
  RegionAcceptanceType,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-tenant-region-config',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="trc-page">
        <!-- Page header -->
        <div class="page-header">
          <div>
            <h1>Tenant Region Configuration</h1>
            <p class="page-description">
              Configure which delivery regions are available for the current tenant.
            </p>
          </div>
        </div>

        @if (loading()) {
          <div class="loading">Loading acceptances...</div>
        }

        @if (!loading()) {
          <!-- Acceptances table -->
          <div class="card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Region</th>
                  <th>Acceptance Type</th>
                  <th>Compliance Enforced?</th>
                  <th>Reason</th>
                  <th class="col-actions">Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (acc of acceptances(); track acc.id) {
                  <tr>
                    <td class="cell-region">
                      {{ regionDisplayName(acc.deliveryRegionId) }}
                    </td>
                    <td>
                      <span
                        class="badge"
                        [class.badge-preferred]="acc.acceptanceType === 'preferred'"
                        [class.badge-accepted]="acc.acceptanceType === 'accepted'"
                        [class.badge-blocked]="acc.acceptanceType === 'blocked'"
                      >
                        {{ acc.acceptanceType }}
                      </span>
                    </td>
                    <td>
                      @if (acc.isComplianceEnforced) {
                        <span class="compliance-badge compliance-yes">Yes</span>
                      } @else {
                        <span class="compliance-badge compliance-no">No</span>
                      }
                    </td>
                    <td class="cell-reason">{{ acc.reason || '--' }}</td>
                    <td class="col-actions">
                      <button
                        class="btn btn-remove btn-sm"
                        *nimbusHasPermission="'catalog:compliance:manage'"
                        (click)="deleteAcceptance(acc)"
                        title="Delete override"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="5" class="empty-row">
                      No tenant region overrides configured.
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Add override form -->
          <div
            class="card add-form-card"
            *nimbusHasPermission="'catalog:compliance:manage'"
          >
            <h3>Add Override</h3>
            <div class="add-row">
              <div class="form-group">
                <label for="overrideRegion">Region *</label>
                <nimbus-searchable-select [(ngModel)]="newRegionId" [options]="regionOptions()" placeholder="Select region..." />
              </div>

              <div class="form-group">
                <label for="overrideType">Acceptance Type *</label>
                <select
                  id="overrideType"
                  class="form-input form-select"
                  [(ngModel)]="newAcceptanceType"
                >
                  <option value="">-- Select --</option>
                  <option value="preferred">Preferred</option>
                  <option value="accepted">Accepted</option>
                  <option value="blocked">Blocked</option>
                </select>
              </div>

              <div class="form-group form-group-checkbox">
                <label class="checkbox-label">
                  <input
                    type="checkbox"
                    [(ngModel)]="newComplianceEnforced"
                  />
                  <span>Compliance Enforced</span>
                </label>
              </div>

              <div class="form-group form-group-wide">
                <label for="overrideReason">Reason</label>
                <input
                  id="overrideReason"
                  class="form-input"
                  [(ngModel)]="newReason"
                  placeholder="Optional reason"
                />
              </div>

              <div class="form-group form-group-action">
                <label>&nbsp;</label>
                <button
                  class="btn btn-primary btn-sm"
                  [disabled]="!newRegionId || !newAcceptanceType || adding()"
                  (click)="addOverride()"
                >
                  {{ adding() ? 'Adding...' : 'Add' }}
                </button>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .trc-page { padding: 0; }

    /* ── Page header ──────────────────────────────────────────────── */
    .page-header {
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .page-description {
      margin: 0.375rem 0 0; font-size: 0.875rem; color: #64748b;
    }

    /* ── Loading ───────────────────────────────────────────────────── */
    .loading {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* ── Card ──────────────────────────────────────────────────────── */
    .card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1.5rem; overflow: hidden;
    }

    /* ── Data table ────────────────────────────────────────────────── */
    .data-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .data-table thead th {
      background: #f8fafc; padding: 0.625rem 1rem; text-align: left;
      font-weight: 600; color: #64748b; font-size: 0.6875rem;
      text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 1px solid #e2e8f0;
    }
    .data-table tbody td {
      padding: 0.625rem 1rem; color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .data-table tbody tr:hover { background: #f8fafc; }
    .data-table tbody tr:last-child td { border-bottom: none; }

    .col-actions { width: 90px; text-align: right; }
    .cell-region { font-weight: 500; color: #1e293b; }
    .cell-reason {
      max-width: 220px; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap; color: #64748b;
    }
    .empty-row {
      text-align: center; color: #94a3b8; padding: 2rem 1rem !important;
    }

    /* ── Add override form ─────────────────────────────────────────── */
    .add-form-card {
      padding: 1.25rem; overflow: visible;
    }
    .add-form-card h3 {
      margin: 0 0 0.75rem; font-size: 0.875rem; font-weight: 600; color: #1e293b;
    }
    .add-row {
      display: flex; gap: 0.75rem; align-items: flex-end; flex-wrap: wrap;
    }

    /* ── Form elements ─────────────────────────────────────────────── */
    .form-group { display: flex; flex-direction: column; min-width: 160px; }
    .form-group-wide { flex: 1; min-width: 180px; }
    .form-group-action { min-width: auto; }
    .form-group-checkbox {
      min-width: auto; justify-content: flex-end; padding-bottom: 0.25rem;
    }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .form-select { cursor: pointer; }
    .form-select option { background: #fff; color: #1e293b; }

    .checkbox-label {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.8125rem; font-weight: 500; color: #374151;
      cursor: pointer; white-space: nowrap;
    }
    .checkbox-label input[type="checkbox"] {
      cursor: pointer; width: 16px; height: 16px;
      accent-color: #3b82f6;
    }

    /* ── Badges ────────────────────────────────────────────────────── */
    .badge {
      display: inline-block; padding: 0.125rem 0.5rem;
      border-radius: 9999px; font-size: 0.6875rem; font-weight: 600;
      text-transform: capitalize;
    }
    .badge-preferred { background: #dbeafe; color: #2563eb; }
    .badge-accepted { background: #dcfce7; color: #16a34a; }
    .badge-blocked { background: #fee2e2; color: #dc2626; }

    .compliance-badge {
      display: inline-block; padding: 0.125rem 0.5rem;
      border-radius: 9999px; font-size: 0.6875rem; font-weight: 600;
    }
    .compliance-yes { background: #dcfce7; color: #16a34a; }
    .compliance-no { background: #f1f5f9; color: #94a3b8; }

    /* ── Buttons ───────────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      border: none;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.25rem;
    }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-remove {
      background: #fff; color: #dc2626; border: 1px solid #fecaca;
    }
    .btn-remove:hover:not(:disabled) { background: #fef2f2; }
  `],
})
export class TenantRegionConfigComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);

  // ── State signals ─────────────────────────────────────────────────
  loading = signal(false);
  adding = signal(false);
  acceptances = signal<TenantRegionAcceptance[]>([]);
  regions = signal<DeliveryRegion[]>([]);

  regionOptions = computed(() => this.regions().map(r => ({ value: r.id, label: r.displayName })));

  // ── Add override form state ───────────────────────────────────────
  newRegionId = '';
  newAcceptanceType: RegionAcceptanceType | '' = '';
  newComplianceEnforced = false;
  newReason = '';

  // ── Region lookup map ─────────────────────────────────────────────
  private regionMap = new Map<string, DeliveryRegion>();

  ngOnInit(): void {
    this.loadRegions();
    this.loadAcceptances();
  }

  // ── Add override ──────────────────────────────────────────────────

  addOverride(): void {
    if (!this.newRegionId || !this.newAcceptanceType) return;

    this.adding.set(true);
    const input: TenantRegionAcceptanceCreateInput = {
      deliveryRegionId: this.newRegionId,
      acceptanceType: this.newAcceptanceType as RegionAcceptanceType,
      reason: this.newReason.trim() || null,
      isComplianceEnforced: this.newComplianceEnforced,
    };

    this.deliveryService.setTenantAcceptance(input).subscribe({
      next: () => {
        this.adding.set(false);
        this.toastService.success('Region override added');
        this.resetForm();
        this.loadAcceptances();
      },
      error: (err) => {
        this.adding.set(false);
        this.toastService.error(err.message || 'Failed to add override');
      },
    });
  }

  // ── Delete acceptance ─────────────────────────────────────────────

  async deleteAcceptance(acc: TenantRegionAcceptance): Promise<void> {
    const regionName = this.regionDisplayName(acc.deliveryRegionId);
    const confirmed = await this.confirmService.confirm({
      title: 'Delete Override',
      message: `Remove the "${acc.acceptanceType}" override for ${regionName}?`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;

    this.deliveryService.deleteTenantAcceptance(acc.id).subscribe({
      next: () => {
        this.toastService.success('Override deleted');
        this.loadAcceptances();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete override');
      },
    });
  }

  // ── Region display name lookup ────────────────────────────────────

  regionDisplayName(regionId: string): string {
    return this.regionMap.get(regionId)?.displayName || regionId;
  }

  // ── Private helpers ───────────────────────────────────────────────

  private loadAcceptances(): void {
    this.loading.set(true);
    this.deliveryService.listTenantAcceptances().subscribe({
      next: (list) => {
        this.acceptances.set(list);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load acceptances');
      },
    });
  }

  private loadRegions(): void {
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (result) => {
        this.regions.set(result.items);
        this.regionMap.clear();
        for (const r of result.items) {
          this.regionMap.set(r.id, r);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load regions');
      },
    });
  }

  private resetForm(): void {
    this.newRegionId = '';
    this.newAcceptanceType = '';
    this.newComplianceEnforced = false;
    this.newReason = '';
  }
}
