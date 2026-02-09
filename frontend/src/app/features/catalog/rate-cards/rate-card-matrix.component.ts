/**
 * Overview: Rate card matrix -- staff profile x delivery region hourly rate grid editor.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/forms, app/core/services/delivery.service
 * Concepts: Internal rate cards, staff profiles, delivery regions, hourly cost matrix
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
import { forkJoin } from 'rxjs';
import { DeliveryService } from '@core/services/delivery.service';
import {
  OrganizationalUnit,
  StaffProfile,
  DeliveryRegion,
  InternalRateCard,
  InternalRateCardCreateInput,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

/** Key for looking up a rate card in the matrix: "profileId::regionId" */
type CellKey = string;

interface CellEdit {
  profileId: string;
  regionId: string;
  hourlyCost: number;
  hourlySellRate: number | null;
  currency: string;
  isNew: boolean;
  rateCardId?: string;
}

@Component({
  selector: 'nimbus-rate-card-matrix',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="matrix-page">
        <div class="page-header">
          <h1>Rate Card Matrix</h1>
        </div>

        <div class="filters">
          <div class="filter-group">
            <label class="filter-label">Org Unit</label>
            <nimbus-searchable-select [(ngModel)]="filterOrgUnitId" [options]="orgUnitOptions()" placeholder="All units" (ngModelChange)="onFilterChange()" [allowClear]="true" />
          </div>
          <div class="filter-group">
            <label class="filter-label">Effective From</label>
            <input
              type="date"
              [(ngModel)]="filterEffectiveFrom"
              class="filter-input"
              (ngModelChange)="loadData()"
            />
          </div>
          <div class="filter-group">
            <label class="filter-label">Effective To</label>
            <input
              type="date"
              [(ngModel)]="filterEffectiveTo"
              class="filter-input"
              (ngModelChange)="loadData()"
            />
          </div>
          @if (filterEffectiveFrom || filterEffectiveTo || filterOrgUnitId) {
            <button class="btn btn-secondary btn-sm-filter" (click)="clearAllFilters()">
              Clear Filters
            </button>
          }
        </div>

        @if (loading()) {
          <div class="loading-state">Loading rate card data...</div>
        } @else {
          <div class="matrix-container">
            @if (filteredProfiles().length === 0) {
              <div class="empty-state">
                No staff profiles configured. Create staff profiles first.
              </div>
            } @else if (regions().length === 0) {
              <div class="empty-state">
                No delivery regions configured. Create delivery regions first.
              </div>
            } @else {
              <div class="table-container">
                <table class="matrix-table">
                  <thead>
                    <tr>
                      <th class="profile-header">Staff Profile</th>
                      @for (region of activeRegions(); track region.id) {
                        <th class="region-header" [title]="region.displayName + ' (' + region.code + ')'">
                          {{ region.displayName }}
                          <span class="region-code">{{ region.code }}</span>
                        </th>
                      }
                    </tr>
                  </thead>
                  <tbody>
                    @for (profile of filteredProfiles(); track profile.id) {
                      <tr>
                        <td class="profile-cell">
                          <span class="profile-name">{{ profile.displayName }}</span>
                          @if (profile.isSystem) {
                            <span class="badge badge-system">System</span>
                          }
                        </td>
                        @for (region of activeRegions(); track region.id) {
                          <td
                            class="rate-cell"
                            [class.rate-cell-empty]="!rateMap().get(getCellKey(profile.id, region.id))"
                            [class.rate-cell-editing]="isEditing(profile.id, region.id)"
                          >
                            @if (isEditing(profile.id, region.id)) {
                              <div class="edit-cell">
                                <div class="edit-row">
                                  <input
                                    type="number"
                                    [(ngModel)]="editingCell!.hourlyCost"
                                    class="cell-input"
                                    min="0"
                                    step="0.01"
                                    placeholder="Cost"
                                    (keyup.enter)="saveCell()"
                                    (keyup.escape)="cancelCellEdit()"
                                  />
                                  <input
                                    type="number"
                                    [(ngModel)]="editingCell!.hourlySellRate"
                                    class="cell-input"
                                    min="0"
                                    step="0.01"
                                    placeholder="Sell"
                                    (keyup.enter)="saveCell()"
                                    (keyup.escape)="cancelCellEdit()"
                                  />
                                  <input
                                    type="text"
                                    [(ngModel)]="editingCell!.currency"
                                    class="cell-input cell-input-currency"
                                    maxlength="3"
                                    placeholder="USD"
                                    (keyup.enter)="saveCell()"
                                    (keyup.escape)="cancelCellEdit()"
                                  />
                                </div>
                                <div class="edit-actions">
                                  <button class="cell-btn cell-btn-save" (click)="saveCell()">Save</button>
                                  <button class="cell-btn cell-btn-cancel" (click)="cancelCellEdit()">Cancel</button>
                                </div>
                              </div>
                            } @else if (getRateCard(profile.id, region.id)) {
                              <div
                                class="rate-display"
                                (click)="startCellEdit(profile.id, region.id, getRateCard(profile.id, region.id)!)"
                                title="Click to edit — Cost / Sell"
                              >
                                <span class="rate-value">{{ getRateCard(profile.id, region.id)!.hourlyCost | number:'1.2-2' }}</span>
                                @if (getRateCard(profile.id, region.id)!.hourlySellRate != null) {
                                  <span class="rate-sell">/{{ getRateCard(profile.id, region.id)!.hourlySellRate | number:'1.2-2' }}</span>
                                }
                                <span class="rate-currency">{{ getRateCard(profile.id, region.id)!.currency }}</span>
                              </div>
                            } @else {
                              <button
                                *nimbusHasPermission="'catalog:staff:manage'"
                                class="add-rate-btn"
                                (click)="startNewCell(profile.id, region.id)"
                                title="Add rate"
                              >
                                + Add
                              </button>
                            }
                          </td>
                        }
                      </tr>
                    }
                  </tbody>
                </table>
              </div>

              <div class="matrix-footer">
                <span class="footer-info">
                  {{ filteredProfiles().length }} profiles &times; {{ activeRegions().length }} regions
                  &middot; {{ totalRates() }} rates configured
                </span>
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .matrix-page { padding: 0; }

    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    /* ── Filters ───────────────────────────────────────────────────── */

    .filters {
      display: flex; gap: 1rem; align-items: flex-end; margin-bottom: 1.25rem;
      flex-wrap: wrap;
    }
    .filter-group { display: flex; flex-direction: column; }
    .filter-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem;
    }
    .filter-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b; font-family: inherit;
      min-width: 160px; transition: border-color 0.15s;
    }
    .filter-input:focus { border-color: #3b82f6; outline: none; }
    .btn-sm-filter {
      padding: 0.5rem 0.75rem; align-self: flex-end;
    }

    /* ── Loading / empty ───────────────────────────────────────────── */

    .loading-state {
      text-align: center; color: #64748b; padding: 3rem; font-size: 0.875rem;
    }
    .empty-state {
      text-align: center; color: #94a3b8; padding: 3rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      font-size: 0.875rem;
    }

    /* ── Matrix table ──────────────────────────────────────────────── */

    .matrix-container { }
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .matrix-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
      min-width: 600px;
    }
    .matrix-table th, .matrix-table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .matrix-table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap;
      border-bottom: 2px solid #e2e8f0;
    }

    .profile-header {
      position: sticky; left: 0; z-index: 2; background: #fff;
      min-width: 180px; border-right: 1px solid #e2e8f0;
    }
    .region-header { text-align: center; min-width: 120px; }
    .region-code {
      display: block; font-size: 0.625rem; font-weight: 400;
      color: #94a3b8; text-transform: none; letter-spacing: 0;
    }

    .profile-cell {
      position: sticky; left: 0; z-index: 1; background: #fff;
      border-right: 1px solid #e2e8f0; white-space: nowrap;
    }
    .matrix-table tbody tr:hover .profile-cell { background: #f8fafc; }
    .profile-name { font-weight: 500; color: #1e293b; }

    .badge {
      padding: 0.0625rem 0.375rem; border-radius: 10px; font-size: 0.625rem;
      font-weight: 600; margin-left: 0.375rem; vertical-align: middle;
    }
    .badge-system { background: #dbeafe; color: #2563eb; }

    .matrix-table tbody tr:hover { background: #f8fafc; }

    /* ── Rate cells ────────────────────────────────────────────────── */

    .rate-cell { text-align: center; min-width: 120px; vertical-align: middle; }
    .rate-cell-empty { background: #fafbfc; }
    .rate-cell-editing { background: #eff6ff; }

    .rate-display {
      cursor: pointer; padding: 0.25rem 0.375rem; border-radius: 4px;
      display: inline-flex; align-items: baseline; gap: 0.25rem;
      transition: background 0.15s;
    }
    .rate-display:hover { background: #f1f5f9; }
    .rate-value { font-weight: 600; color: #1e293b; font-size: 0.8125rem; }
    .rate-sell { font-size: 0.75rem; color: #16a34a; font-weight: 500; }
    .rate-currency { font-size: 0.6875rem; color: #94a3b8; font-weight: 400; }

    .add-rate-btn {
      border: 1px dashed #cbd5e1; background: none; color: #94a3b8;
      padding: 0.25rem 0.5rem; border-radius: 4px; font-size: 0.75rem;
      font-family: inherit; cursor: pointer; transition: all 0.15s;
    }
    .add-rate-btn:hover { border-color: #3b82f6; color: #3b82f6; background: #eff6ff; }

    /* ── Cell edit ──────────────────────────────────────────────────── */

    .edit-cell { display: flex; flex-direction: column; gap: 0.375rem; padding: 0.125rem; }
    .edit-row { display: flex; gap: 0.25rem; }
    .cell-input {
      padding: 0.3125rem 0.5rem; border: 1px solid #3b82f6; border-radius: 4px;
      font-size: 0.8125rem; font-family: inherit; background: #fff; color: #1e293b;
      width: 80px;
    }
    .cell-input:focus { outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.2); }
    .cell-input-currency { width: 48px; text-transform: uppercase; text-align: center; }
    .edit-actions { display: flex; gap: 0.25rem; justify-content: center; }
    .cell-btn {
      padding: 0.1875rem 0.5rem; border-radius: 3px; font-size: 0.6875rem;
      font-weight: 500; font-family: inherit; cursor: pointer; border: none;
      transition: background 0.15s;
    }
    .cell-btn-save { background: #3b82f6; color: #fff; }
    .cell-btn-save:hover { background: #2563eb; }
    .cell-btn-cancel { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }
    .cell-btn-cancel:hover { background: #e2e8f0; }

    /* ── Footer ────────────────────────────────────────────────────── */

    .matrix-footer {
      display: flex; justify-content: flex-end; margin-top: 0.75rem;
    }
    .footer-info { font-size: 0.75rem; color: #94a3b8; }

    /* ── Shared buttons ────────────────────────────────────────────── */

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      padding: 0.5rem 1rem; border: none;
    }
    .btn-secondary {
      background: #fff; color: #64748b; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; color: #1e293b; }
  `],
})
export class RateCardMatrixComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);

  profiles = signal<StaffProfile[]>([]);
  orgUnits = signal<OrganizationalUnit[]>([]);
  regions = signal<DeliveryRegion[]>([]);
  rateCards = signal<InternalRateCard[]>([]);
  loading = signal(false);

  orgUnitOptions = computed(() => this.orgUnits().map(ou => ({ value: ou.id, label: ou.displayName })));

  // Filters
  filterOrgUnitId = '';
  filterEffectiveFrom = '';
  filterEffectiveTo = '';

  /** Profiles filtered by org unit */
  filteredProfiles = computed(() => {
    const ouId = this.filterOrgUnitId;
    if (!ouId) return this.profiles();
    return this.profiles().filter((p) => p.orgUnitId === ouId);
  });

  // Cell editing state
  editingCell: CellEdit | null = null;
  private editingProfileId = signal<string | null>(null);
  private editingRegionId = signal<string | null>(null);

  /** Only show active regions in the matrix columns */
  activeRegions = computed(() =>
    this.regions()
      .filter((r) => r.isActive)
      .sort((a, b) => a.sortOrder - b.sortOrder),
  );

  /** Map of "profileId::regionId" -> InternalRateCard for O(1) cell lookups */
  rateMap = computed(() => {
    const map = new Map<CellKey, InternalRateCard>();
    const now = new Date().toISOString();
    for (const card of this.rateCards()) {
      // Apply date filters client-side
      if (this.filterEffectiveFrom && card.effectiveFrom < this.filterEffectiveFrom) continue;
      if (this.filterEffectiveTo && card.effectiveTo && card.effectiveTo > this.filterEffectiveTo) continue;

      const key = this.getCellKey(card.staffProfileId, card.deliveryRegionId);
      // Keep the latest effective card per cell
      const existing = map.get(key);
      if (!existing || card.effectiveFrom > existing.effectiveFrom) {
        map.set(key, card);
      }
    }
    return map;
  });

  totalRates = computed(() => this.rateMap().size);

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    forkJoin({
      profiles: this.deliveryService.listStaffProfiles(),
      orgUnits: this.deliveryService.listOrgUnits(),
      regions: this.deliveryService.listRegions(),
      rateCards: this.deliveryService.listRateCards(),
    }).subscribe({
      next: ({ profiles, orgUnits, regions, rateCards }) => {
        this.profiles.set(profiles);
        this.orgUnits.set(orgUnits);
        this.regions.set(regions.items);
        this.rateCards.set(rateCards);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load rate card data');
        this.loading.set(false);
      },
    });
  }

  onFilterChange(): void {
    // Org unit filter is client-side only, no reload needed
  }

  clearAllFilters(): void {
    this.filterOrgUnitId = '';
    this.filterEffectiveFrom = '';
    this.filterEffectiveTo = '';
    this.loadData();
  }

  getCellKey(profileId: string, regionId: string): CellKey {
    return `${profileId}::${regionId}`;
  }

  getRateCard(profileId: string, regionId: string): InternalRateCard | undefined {
    return this.rateMap().get(this.getCellKey(profileId, regionId));
  }

  isEditing(profileId: string, regionId: string): boolean {
    return this.editingProfileId() === profileId && this.editingRegionId() === regionId;
  }

  startCellEdit(profileId: string, regionId: string, rateCard: InternalRateCard): void {
    this.editingProfileId.set(profileId);
    this.editingRegionId.set(regionId);
    this.editingCell = {
      profileId,
      regionId,
      hourlyCost: rateCard.hourlyCost,
      hourlySellRate: rateCard.hourlySellRate,
      currency: rateCard.currency,
      isNew: false,
      rateCardId: rateCard.id,
    };
  }

  startNewCell(profileId: string, regionId: string): void {
    this.editingProfileId.set(profileId);
    this.editingRegionId.set(regionId);
    this.editingCell = {
      profileId,
      regionId,
      hourlyCost: 0,
      hourlySellRate: null,
      currency: 'USD',
      isNew: true,
    };
  }

  cancelCellEdit(): void {
    this.editingProfileId.set(null);
    this.editingRegionId.set(null);
    this.editingCell = null;
  }

  saveCell(): void {
    if (!this.editingCell) return;

    const cell = this.editingCell;
    const currency = (cell.currency || 'USD').toUpperCase();

    if (cell.hourlyCost < 0) {
      this.toastService.error('Hourly cost must be zero or positive');
      return;
    }

    if (cell.isNew) {
      const input: InternalRateCardCreateInput = {
        staffProfileId: cell.profileId,
        deliveryRegionId: cell.regionId,
        hourlyCost: cell.hourlyCost,
        hourlySellRate: cell.hourlySellRate,
        currency,
        effectiveFrom: this.filterEffectiveFrom || new Date().toISOString().split('T')[0],
        effectiveTo: this.filterEffectiveTo || undefined,
      };

      this.deliveryService.createRateCard(input).subscribe({
        next: () => {
          this.toastService.success('Rate card created');
          this.cancelCellEdit();
          this.loadData();
        },
        error: (err) => {
          this.toastService.error(err.message || 'Failed to create rate card');
        },
      });
    } else if (cell.rateCardId) {
      // Delete old then create new (service has no update method)
      this.deliveryService.deleteRateCard(cell.rateCardId).subscribe({
        next: () => {
          const input: InternalRateCardCreateInput = {
            staffProfileId: cell.profileId,
            deliveryRegionId: cell.regionId,
            hourlyCost: cell.hourlyCost,
            hourlySellRate: cell.hourlySellRate,
            currency,
            effectiveFrom: this.filterEffectiveFrom || new Date().toISOString().split('T')[0],
            effectiveTo: this.filterEffectiveTo || undefined,
          };
          this.deliveryService.createRateCard(input).subscribe({
            next: () => {
              this.toastService.success('Rate card updated');
              this.cancelCellEdit();
              this.loadData();
            },
            error: (err: Error) => {
              this.toastService.error(err.message || 'Failed to create replacement rate card');
            },
          });
        },
        error: (err: Error) => {
          this.toastService.error(err.message || 'Failed to update rate card');
        },
      });
    }
  }
}
