/**
 * Overview: Dialog for assigning OS images to tenants via checkbox list with search filter.
 * Architecture: Feature dialog for OS image tenant assignment (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/shared/services/dialog.service, app/core/services/tenant.service
 * Concepts: Tenant assignment, multi-select, checkbox list with search
 */
import { Component, inject, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';
import { TenantService } from '@core/services/tenant.service';
import { Tenant } from '@core/models/tenant.model';

export interface TenantAssignmentDialogData {
  currentTenantIds: string[];
}

@Component({
  selector: 'nimbus-tenant-assignment-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog">
      <h2>Manage Tenant Availability</h2>
      <p class="subtitle">Select which tenants can see this image.</p>

      <div class="search-row">
        <input type="text" class="search-input" placeholder="Search tenants..."
          [ngModel]="searchTerm()" (ngModelChange)="searchTerm.set($event)" />
      </div>

      <div class="select-actions">
        <button class="link-btn" (click)="selectAll()">Select All</button>
        <button class="link-btn" (click)="selectNone()">Select None</button>
        <span class="count">{{ selectedCount() }} selected</span>
      </div>

      @if (loading()) {
        <div class="loading">Loading tenants...</div>
      } @else {
        <div class="tenant-list">
          @for (t of filteredTenants(); track t.id) {
            <label class="tenant-row">
              <input type="checkbox" [checked]="isSelected(t.id)" (change)="toggle(t.id)" />
              <span class="tenant-info">
                <span class="tenant-name">{{ t.name }}</span>
                <span class="tenant-slug">{{ t.name }}</span>
              </span>
            </label>
          }
          @if (filteredTenants().length === 0) {
            <div class="empty">No tenants match your search.</div>
          }
        </div>
      }

      <div class="actions">
        <button class="btn btn-cancel" (click)="onCancel()">Cancel</button>
        <button class="btn btn-primary" (click)="onSave()">Save</button>
      </div>
    </div>
  `,
  styles: [`
    .dialog { padding: 1.5rem; min-width: 420px; max-width: 520px; }
    h2 { margin: 0 0 0.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .subtitle { margin: 0 0 1rem; font-size: 0.8125rem; color: #64748b; }

    .search-row { margin-bottom: 0.75rem; }
    .search-input {
      width: 100%; box-sizing: border-box; padding: 0.4375rem 0.75rem;
      border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.8125rem;
      font-family: inherit; color: #374151; background: #fff; outline: none;
    }
    .search-input:focus { border-color: #3b82f6; }

    .select-actions {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;
      font-size: 0.75rem;
    }
    .link-btn {
      background: none; border: none; cursor: pointer; color: #3b82f6;
      font-size: 0.75rem; font-family: inherit; padding: 0;
    }
    .link-btn:hover { text-decoration: underline; }
    .count { color: #94a3b8; margin-left: auto; }

    .tenant-list {
      max-height: 320px; overflow-y: auto; border: 1px solid #e2e8f0;
      border-radius: 6px; margin-bottom: 1rem;
    }
    .tenant-row {
      display: flex; align-items: center; gap: 0.625rem; padding: 0.5rem 0.75rem;
      border-bottom: 1px solid #f1f5f9; cursor: pointer; transition: background 0.1s;
    }
    .tenant-row:last-child { border-bottom: none; }
    .tenant-row:hover { background: #f8fafc; }
    .tenant-row input[type="checkbox"] { accent-color: #3b82f6; }
    .tenant-info { display: flex; flex-direction: column; }
    .tenant-name { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .tenant-slug { font-size: 0.6875rem; color: #94a3b8; }

    .loading, .empty { padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem; }

    .actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem; transition: background 0.15s; }
    .btn-cancel { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
  `],
})
export class TenantAssignmentDialogComponent implements OnInit {
  private dialogData = inject<TenantAssignmentDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);
  private tenantService = inject(TenantService);

  loading = signal(true);
  allTenants = signal<Tenant[]>([]);
  selectedIds = signal<Set<string>>(new Set());
  searchTerm = signal('');

  filteredTenants = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    const tenants = this.allTenants();
    if (!term) return tenants;
    return tenants.filter(
      (t) =>
        t.name.toLowerCase().includes(term) ||
        (t.description || '').toLowerCase().includes(term),
    );
  });

  selectedCount = computed(() => this.selectedIds().size);

  ngOnInit(): void {
    const data = this.dialogData;
    if (data?.currentTenantIds) {
      this.selectedIds.set(new Set(data.currentTenantIds));
    }

    this.tenantService.listTenants(0, 500).subscribe({
      next: (tenants) => {
        this.allTenants.set(tenants);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  isSelected(id: string): boolean {
    return this.selectedIds().has(id);
  }

  toggle(id: string): void {
    const current = new Set(this.selectedIds());
    if (current.has(id)) {
      current.delete(id);
    } else {
      current.add(id);
    }
    this.selectedIds.set(current);
  }

  selectAll(): void {
    this.selectedIds.set(new Set(this.allTenants().map((t) => t.id)));
  }

  selectNone(): void {
    this.selectedIds.set(new Set());
  }

  onSave(): void {
    this.dialogService.close(Array.from(this.selectedIds()));
  }

  onCancel(): void {
    this.dialogService.close(undefined);
  }
}
