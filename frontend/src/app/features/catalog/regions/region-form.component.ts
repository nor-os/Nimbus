/**
 * Overview: Delivery region create/edit form with parent region selection, timezone,
 *     country code, and sort order fields.
 * Architecture: Catalog feature component for delivery region CRUD (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, @angular/common,
 *     app/core/services/delivery.service, app/shared/services/toast.service
 * Concepts: Delivery region CRUD, create vs edit mode from route param, parent region
 *     dropdown, readonly fields in edit mode
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
import { ActivatedRoute, Router } from '@angular/router';
import { DeliveryService } from '@core/services/delivery.service';
import {
  DeliveryRegion,
  DeliveryRegionCreateInput,
  DeliveryRegionUpdateInput,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { TIMEZONE_OPTIONS, COUNTRY_CODE_OPTIONS } from '@shared/data/geo-options';

@Component({
  selector: 'nimbus-region-form',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="region-form-page">
        <div class="page-header">
          <h1>{{ isEditMode() ? 'Edit Region' : 'Create Region' }}</h1>
        </div>

        @if (loading()) {
          <div class="loading">Loading...</div>
        }

        @if (!loading()) {
          <form class="form" (ngSubmit)="onSubmit()">
            <!-- Name -->
            <div class="form-group">
              <label for="name">Name *</label>
              <input
                id="name"
                type="text"
                class="form-input"
                [(ngModel)]="formData.name"
                name="name"
                required
                placeholder="Region name (e.g. us-east)"
                [readonly]="isEditMode()"
                [class.readonly]="isEditMode()"
              />
              @if (isEditMode()) {
                <span class="form-hint">Name cannot be changed after creation.</span>
              }
            </div>

            <!-- Display Name -->
            <div class="form-group">
              <label for="displayName">Display Name *</label>
              <input
                id="displayName"
                type="text"
                class="form-input"
                [(ngModel)]="formData.displayName"
                name="displayName"
                required
                placeholder="Human-readable name (e.g. US East)"
              />
            </div>

            <!-- Code -->
            <div class="form-group">
              <label for="code">Code *</label>
              <input
                id="code"
                type="text"
                class="form-input"
                [(ngModel)]="formData.code"
                name="code"
                required
                placeholder="Short code (e.g. USE)"
                [readonly]="isEditMode()"
                [class.readonly]="isEditMode()"
              />
              @if (isEditMode()) {
                <span class="form-hint">Code cannot be changed after creation.</span>
              }
            </div>

            <!-- Parent Region -->
            <div class="form-group">
              <label for="parentRegionId">Parent Region</label>
              <nimbus-searchable-select [(ngModel)]="formData.parentRegionId" name="parentRegionId" [options]="parentOptions()" placeholder="None (top-level region)" [allowClear]="true" />
              <span class="form-hint">
                Optionally nest this region under a parent for hierarchical organization.
              </span>
            </div>

            <!-- Timezone -->
            <div class="form-group">
              <label for="timezone">Timezone</label>
              <nimbus-searchable-select
                [(ngModel)]="formData.timezone"
                name="timezone"
                [options]="timezoneOptions"
                placeholder="Select timezone..."
                [allowClear]="true"
              />
            </div>

            <!-- Country Code -->
            <div class="form-group">
              <label for="countryCode">Country Code</label>
              <nimbus-searchable-select
                [(ngModel)]="formData.countryCode"
                name="countryCode"
                [options]="countryCodeOptions"
                placeholder="Select country..."
                [allowClear]="true"
              />
              <span class="form-hint">ISO 3166-1 alpha-2 country code.</span>
            </div>

            <!-- Sort Order -->
            <div class="form-group">
              <label for="sortOrder">Sort Order</label>
              <input
                id="sortOrder"
                type="number"
                class="form-input"
                [(ngModel)]="formData.sortOrder"
                name="sortOrder"
                min="0"
                placeholder="0"
              />
              <span class="form-hint">Lower values appear first in listings.</span>
            </div>

            <!-- Active toggle (edit mode only) -->
            @if (isEditMode()) {
              <div class="form-group">
                <label class="toggle-label">
                  <input
                    type="checkbox"
                    [(ngModel)]="formData.isActive"
                    name="isActive"
                  />
                  <span>{{ formData.isActive ? 'Active' : 'Inactive' }}</span>
                </label>
              </div>
            }

            <!-- Error message -->
            @if (errorMessage()) {
              <div class="form-error">{{ errorMessage() }}</div>
            }

            <!-- Actions -->
            <div class="form-actions">
              <button
                type="submit"
                class="btn btn-primary"
                [disabled]="!isFormValid() || submitting()"
              >
                {{ submitting() ? 'Saving...' : (isEditMode() ? 'Update' : 'Create') }}
              </button>
              <button type="button" class="btn btn-secondary" (click)="cancel()">Cancel</button>
            </div>
          </form>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .region-form-page { padding: 0; max-width: 680px; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    .form {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1.25rem; }
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
    .form-input.readonly {
      background: #f8fafc; color: #64748b; cursor: not-allowed;
    }
    .form-select { cursor: pointer; }
    .form-hint {
      display: block; font-size: 0.6875rem; color: #64748b; margin-top: 0.25rem;
    }

    .toggle-label {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.8125rem; color: #374151; cursor: pointer;
    }
    .toggle-label input[type="checkbox"] { cursor: pointer; }

    .form-error {
      background: #fef2f2; color: #dc2626; padding: 0.75rem 1rem;
      border-radius: 6px; margin-bottom: 1rem; font-size: 0.8125rem;
      border: 1px solid #fecaca;
    }

    .form-actions { display: flex; gap: 0.75rem; margin-top: 1.5rem; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1.5rem;
      transition: background 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
  `],
})
export class RegionFormComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  timezoneOptions = TIMEZONE_OPTIONS;
  countryCodeOptions = COUNTRY_CODE_OPTIONS;

  isEditMode = signal(false);
  loading = signal(false);
  submitting = signal(false);
  errorMessage = signal('');
  allRegions = signal<DeliveryRegion[]>([]);
  availableParents = signal<DeliveryRegion[]>([]);

  parentOptions = computed(() => this.availableParents().map(r => ({ value: r.id, label: r.displayName + ' (' + r.code + ')' })));

  formData = {
    name: '',
    displayName: '',
    code: '',
    parentRegionId: null as string | null,
    timezone: '',
    countryCode: '',
    sortOrder: 0,
    isActive: true,
  };

  private regionId: string | null = null;

  ngOnInit(): void {
    this.regionId = this.route.snapshot.paramMap.get('id') ?? null;
    this.isEditMode.set(!!this.regionId);

    this.loadParentRegions();

    if (this.regionId) {
      this.loading.set(true);
      this.loadExistingRegion(this.regionId);
    }
  }

  isFormValid(): boolean {
    return !!(
      this.formData.name.trim() &&
      this.formData.displayName.trim() &&
      this.formData.code.trim()
    );
  }

  onSubmit(): void {
    if (!this.isFormValid()) return;

    this.submitting.set(true);
    this.errorMessage.set('');

    if (this.isEditMode() && this.regionId) {
      this.submitUpdate(this.regionId);
    } else {
      this.submitCreate();
    }
  }

  cancel(): void {
    this.router.navigate(['/catalog', 'regions']);
  }

  // ── Private helpers ─────────────────────────────────────────────

  private submitCreate(): void {
    const input: DeliveryRegionCreateInput = {
      name: this.formData.name.trim(),
      displayName: this.formData.displayName.trim(),
      code: this.formData.code.trim(),
      parentRegionId: this.formData.parentRegionId || null,
      timezone: this.formData.timezone.trim() || null,
      countryCode: this.formData.countryCode.trim() || null,
      sortOrder: this.formData.sortOrder,
    };

    this.deliveryService.createRegion(input).subscribe({
      next: (region) => {
        this.toastService.success(`"${region.displayName}" created`);
        this.router.navigate(['/catalog', 'regions']);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to create delivery region';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private submitUpdate(id: string): void {
    const input: DeliveryRegionUpdateInput = {
      displayName: this.formData.displayName.trim() || null,
      timezone: this.formData.timezone.trim() || null,
      countryCode: this.formData.countryCode.trim() || null,
      isActive: this.formData.isActive,
      sortOrder: this.formData.sortOrder,
    };

    this.deliveryService.updateRegion(id, input).subscribe({
      next: (region) => {
        this.toastService.success(`"${region.displayName}" updated`);
        this.router.navigate(['/catalog', 'regions']);
      },
      error: (err) => {
        this.submitting.set(false);
        const msg = err.message || 'Failed to update delivery region';
        this.errorMessage.set(msg);
        this.toastService.error(msg);
      },
    });
  }

  private loadParentRegions(): void {
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (response) => {
        this.allRegions.set(response.items);
        this.updateAvailableParents();
      },
      error: () => {
        // Non-critical — parent dropdown will just be empty
      },
    });
  }

  private loadExistingRegion(id: string): void {
    this.deliveryService.getRegion(id).subscribe({
      next: (region) => {
        if (!region) {
          this.loading.set(false);
          this.toastService.error('Delivery region not found');
          this.router.navigate(['/catalog', 'regions']);
          return;
        }

        this.formData.name = region.name;
        this.formData.displayName = region.displayName;
        this.formData.code = region.code;
        this.formData.parentRegionId = region.parentRegionId;
        this.formData.timezone = region.timezone || '';
        this.formData.countryCode = region.countryCode || '';
        this.formData.sortOrder = region.sortOrder;
        this.formData.isActive = region.isActive;

        this.updateAvailableParents();
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
        this.toastService.error('Failed to load delivery region');
        this.router.navigate(['/catalog', 'regions']);
      },
    });
  }

  private updateAvailableParents(): void {
    const regions = this.allRegions();
    // In edit mode, exclude self from parent options to prevent circular reference
    const filtered = this.regionId
      ? regions.filter((r) => r.id !== this.regionId)
      : regions;
    this.availableParents.set(filtered);
  }
}
