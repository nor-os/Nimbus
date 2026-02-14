/**
 * Overview: Service group detail page — view and manage a single service group including
 *     lifecycle actions (publish/archive/clone), inline name/description editing for drafts,
 *     and item management (add/remove offerings).
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/common, @angular/forms,
 *     app/core/services/catalog.service, app/core/services/tenant.service
 * Concepts: Service group lifecycle (draft/published/archived), clone-only immutability,
 *     offering item management, permission-gated actions
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
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CatalogService } from '@core/services/catalog.service';
import { TenantService } from '@core/services/tenant.service';
import { ServiceGroup, ServiceOffering } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface TenantInfo {
  id: string;
  name: string;
}

@Component({
  selector: 'nimbus-group-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="group-detail-page">
        @if (loading()) {
          <div class="loading">Loading group...</div>
        }

        @if (!loading() && !group()) {
          <div class="empty-state">
            Group not found.
            <a routerLink="/catalog/groups" class="back-link">Back to list</a>
          </div>
        }

        @if (group(); as g) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <a routerLink="/catalog/groups" class="back-link">&larr; Back</a>
              <h1>{{ g.displayName || g.name }}</h1>
              <div class="header-badges">
                <span
                  class="badge"
                  [class.badge-draft]="g.status === 'draft'"
                  [class.badge-published]="g.status === 'published'"
                  [class.badge-archived]="g.status === 'archived'"
                >
                  {{ g.status | titlecase }}
                </span>
                <span class="badge badge-count">{{ g.items.length }} items</span>
              </div>
            </div>
          </div>

          <!-- Info row -->
          <div class="meta-row">
            @if (g.name !== g.displayName && g.displayName) {
              <span class="meta-item">Slug: <strong>{{ g.name }}</strong></span>
            }
            @if (g.description) {
              <span class="meta-item">{{ g.description }}</span>
            }
            <span class="meta-item">Created: {{ g.createdAt | date: 'medium' }}</span>
            <span class="meta-item">Updated: {{ g.updatedAt | date: 'medium' }}</span>
          </div>

          <!-- Actions section -->
          <div class="actions-section">
            <div class="section-title">Actions</div>
            <div class="actions-row">
              @if (g.status === 'draft') {
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn btn-sm btn-success"
                  (click)="publishGroup()"
                  [disabled]="actionInProgress()"
                >
                  {{ actionInProgress() ? 'Publishing...' : 'Publish' }}
                </button>
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn btn-sm btn-secondary"
                  (click)="toggleEditing()"
                >
                  {{ editing() ? 'Cancel Edit' : 'Edit' }}
                </button>
              }
              @if (g.status === 'published') {
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn btn-sm btn-warning"
                  (click)="archiveGroup()"
                  [disabled]="actionInProgress()"
                >
                  {{ actionInProgress() ? 'Archiving...' : 'Archive' }}
                </button>
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn btn-sm btn-secondary"
                  (click)="toggleCloneForm()"
                >
                  Clone
                </button>
              }
              @if (g.status === 'archived') {
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn btn-sm btn-secondary"
                  (click)="toggleCloneForm()"
                >
                  Clone
                </button>
              }
            </div>

            <!-- Inline edit form (draft only) -->
            @if (editing()) {
              <div class="inline-form">
                <div class="edit-fields">
                  <div class="edit-field">
                    <label class="edit-label">Name</label>
                    <input
                      class="form-input"
                      [(ngModel)]="editName"
                      placeholder="Group name (slug)"
                    />
                  </div>
                  <div class="edit-field">
                    <label class="edit-label">Display Name</label>
                    <input
                      class="form-input"
                      [(ngModel)]="editDisplayName"
                      placeholder="Display name"
                    />
                  </div>
                  <div class="edit-field">
                    <label class="edit-label">Description</label>
                    <textarea
                      class="form-input form-textarea"
                      [(ngModel)]="editDescription"
                      placeholder="Description"
                      rows="2"
                    ></textarea>
                  </div>
                </div>
                <div class="edit-actions">
                  <button
                    class="btn btn-sm btn-primary"
                    (click)="saveEdit()"
                    [disabled]="!editName.trim()"
                  >
                    Save
                  </button>
                  <button class="btn btn-sm btn-secondary" (click)="editing.set(false)">Cancel</button>
                </div>
              </div>
            }

            <!-- Clone form -->
            @if (cloning()) {
              <div class="inline-form">
                <span class="inline-label">Clone as new draft:</span>
                <select class="form-input clone-field" [(ngModel)]="cloneTenantId">
                  <option value="">Same tenant</option>
                  @for (tenant of tenants(); track tenant.id) {
                    <option [value]="tenant.id">{{ tenant.name }}</option>
                  }
                </select>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="cloneGroup()"
                  [disabled]="actionInProgress()"
                >
                  {{ actionInProgress() ? 'Cloning...' : 'Clone' }}
                </button>
                <button class="btn btn-sm btn-secondary" (click)="cloning.set(false)">Cancel</button>
              </div>
            }
          </div>

          <!-- Items section -->
          <div class="items-section">
            <div class="items-header">
              <span class="section-title">Offerings ({{ g.items.length }})</span>
              @if (g.status === 'draft') {
                <button
                  *nimbusHasPermission="'catalog:group:manage'"
                  class="btn-link"
                  (click)="addingItem.set(!addingItem())"
                >
                  {{ addingItem() ? 'Cancel' : '+ Add Offering' }}
                </button>
              }
            </div>

            <!-- Add item form (draft only) -->
            @if (addingItem() && g.status === 'draft') {
              <div class="add-item-form">
                <select class="form-input item-field" [(ngModel)]="newOfferingId">
                  <option value="">Select offering...</option>
                  @for (offering of availableOfferings(); track offering.id) {
                    <option [value]="offering.id">{{ offering.name }}</option>
                  }
                </select>
                <label class="checkbox-label">
                  <input type="checkbox" [(ngModel)]="newItemRequired" />
                  Required
                </label>
                <input
                  class="form-input item-field-sm"
                  type="number"
                  [(ngModel)]="newItemSortOrder"
                  placeholder="Sort"
                  min="0"
                />
                <button
                  class="btn btn-sm btn-primary"
                  (click)="addItem()"
                  [disabled]="!newOfferingId"
                >
                  Add
                </button>
              </div>
            }

            @if (g.items.length > 0) {
              <table class="items-table">
                <thead>
                  <tr>
                    <th>Offering</th>
                    <th>Required</th>
                    <th>Sort Order</th>
                    <th>Added</th>
                    @if (g.status === 'draft') {
                      <th class="th-actions">Actions</th>
                    }
                  </tr>
                </thead>
                <tbody>
                  @for (item of g.items; track item.id) {
                    <tr>
                      <td class="name-cell">{{ offeringName(item.serviceOfferingId) }}</td>
                      <td>
                        <span class="badge" [class.badge-yes]="item.isRequired" [class.badge-no]="!item.isRequired">
                          {{ item.isRequired ? 'Yes' : 'No' }}
                        </span>
                      </td>
                      <td class="mono">{{ item.sortOrder }}</td>
                      <td>{{ item.createdAt | date: 'medium' }}</td>
                      @if (g.status === 'draft') {
                        <td class="td-actions">
                          <button
                            *nimbusHasPermission="'catalog:group:manage'"
                            class="btn-icon btn-danger"
                            title="Remove"
                            (click)="removeItem(item.id)"
                          >
                            &times;
                          </button>
                        </td>
                      }
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <div class="no-items">No offerings in this group.</div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .group-detail-page { padding: 0; max-width: 960px; }

    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Header ------------------------------------------------------- */
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 0.5rem;
    }
    .header-left { display: flex; flex-direction: column; gap: 0.25rem; }
    .back-link {
      font-size: 0.8125rem; color: #3b82f6; text-decoration: none;
      margin-bottom: 0.25rem; display: inline-block;
    }
    .back-link:hover { text-decoration: underline; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-badges { display: flex; gap: 0.5rem; margin-top: 0.25rem; }

    .meta-row {
      display: flex; gap: 1.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;
    }
    .meta-item {
      font-size: 0.8125rem; color: #64748b; white-space: nowrap;
    }
    .meta-item strong { color: #374151; }

    /* -- Sections ----------------------------------------------------- */
    .section-title {
      font-size: 0.875rem; font-weight: 600; color: #1e293b;
      margin-bottom: 0.75rem;
    }

    /* -- Actions ------------------------------------------------------ */
    .actions-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .actions-row { display: flex; gap: 0.5rem; flex-wrap: wrap; }
    .inline-form {
      display: flex; gap: 0.5rem; align-items: flex-start; margin-top: 0.75rem;
      padding: 0.75rem; background: #eff6ff; border-radius: 6px;
      border: 1px solid #dbeafe; flex-wrap: wrap;
    }
    .inline-label { font-size: 0.8125rem; color: #374151; font-weight: 500; padding-top: 0.5rem; }
    .clone-field { min-width: 200px; max-width: 300px; }

    /* -- Edit form ---------------------------------------------------- */
    .edit-fields { display: flex; flex-direction: column; gap: 0.75rem; width: 100%; }
    .edit-field { display: flex; flex-direction: column; gap: 0.25rem; }
    .edit-label { font-size: 0.75rem; font-weight: 600; color: #374151; }
    .edit-actions { display: flex; gap: 0.5rem; width: 100%; margin-top: 0.25rem; }
    .form-textarea { resize: vertical; min-height: 40px; }

    /* -- Items section ------------------------------------------------ */
    .items-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .items-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.75rem;
    }
    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; font-weight: 500;
      padding: 0; text-decoration: none;
    }
    .btn-link:hover { text-decoration: underline; }

    .add-item-form {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 0.75rem;
      flex-wrap: wrap;
    }
    .item-field { flex: 2; min-width: 200px; }
    .item-field-sm { flex: 0; min-width: 60px; max-width: 80px; }
    .checkbox-label {
      display: flex; align-items: center; gap: 0.25rem; font-size: 0.8125rem;
      color: #374151; cursor: pointer; white-space: nowrap;
    }

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
    .th-actions, .td-actions { width: 60px; text-align: right; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }

    .no-items { color: #64748b; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .badge-count { background: #dbeafe; color: #1d4ed8; }
    .badge-yes { background: #dcfce7; color: #16a34a; }
    .badge-no { background: #f1f5f9; color: #64748b; }

    /* -- Form inputs -------------------------------------------------- */
    .form-input {
      padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s; width: 100%;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }

    /* -- Buttons ------------------------------------------------------ */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-success { background: #16a34a; color: #fff; }
    .btn-success:hover { background: #15803d; }
    .btn-success:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-warning { background: #f59e0b; color: #fff; }
    .btn-warning:hover { background: #d97706; }
    .btn-warning:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }

    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
      transition: background 0.15s, color 0.15s;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class GroupDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private toastService = inject(ToastService);

  group = signal<ServiceGroup | null>(null);
  offerings = signal<ServiceOffering[]>([]);
  tenants = signal<TenantInfo[]>([]);
  loading = signal(false);
  actionInProgress = signal(false);

  // Edit state (draft only)
  editing = signal(false);
  editName = '';
  editDisplayName = '';
  editDescription = '';

  // Clone state
  cloning = signal(false);
  cloneTenantId = '';

  // Add item state
  addingItem = signal(false);
  newOfferingId = '';
  newItemRequired = false;
  newItemSortOrder = 0;

  // Offering name lookup map
  private offeringMap = signal<Map<string, string>>(new Map());

  availableOfferings = computed(() => {
    const g = this.group();
    if (!g) return this.offerings();
    const existingIds = new Set(g.items.map((i) => i.serviceOfferingId));
    return this.offerings().filter((o) => !existingIds.has(o.id));
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadGroup(id);
      this.loadOfferings();
      this.loadTenants();
    }
  }

  // -- Data loading ---------------------------------------------------

  private loadGroup(id: string): void {
    this.loading.set(true);
    this.catalogService.getGroup(id).subscribe({
      next: (g) => {
        this.group.set(g);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load group');
        this.loading.set(false);
      },
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => {
        this.offerings.set(response.items);
        const m = new Map<string, string>();
        for (const o of response.items) {
          m.set(o.id, o.name);
        }
        this.offeringMap.set(m);
      },
    });
  }

  private loadTenants(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (list) => this.tenants.set(list.map((t) => ({ id: t.id, name: t.name }))),
    });
  }

  offeringName(id: string): string {
    return this.offeringMap().get(id) || id.substring(0, 8) + '...';
  }

  // -- Lifecycle actions -----------------------------------------------

  publishGroup(): void {
    const g = this.group();
    if (!g) return;
    this.actionInProgress.set(true);
    this.catalogService.publishGroup(g.id).subscribe({
      next: (updated) => {
        this.group.set(updated);
        this.actionInProgress.set(false);
        this.editing.set(false);
        this.toastService.success(`"${updated.displayName || updated.name}" published`);
      },
      error: (err) => {
        this.actionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to publish group');
      },
    });
  }

  archiveGroup(): void {
    const g = this.group();
    if (!g) return;
    this.actionInProgress.set(true);
    this.catalogService.archiveGroup(g.id).subscribe({
      next: (updated) => {
        this.group.set(updated);
        this.actionInProgress.set(false);
        this.toastService.success(`"${updated.displayName || updated.name}" archived`);
      },
      error: (err) => {
        this.actionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to archive group');
      },
    });
  }

  toggleCloneForm(): void {
    this.cloning.set(!this.cloning());
    this.cloneTenantId = '';
  }

  cloneGroup(): void {
    const g = this.group();
    if (!g) return;
    this.actionInProgress.set(true);
    this.catalogService.cloneGroup(g.id, this.cloneTenantId || undefined).subscribe({
      next: (cloned) => {
        this.actionInProgress.set(false);
        this.cloning.set(false);
        this.toastService.success(`Cloned as "${cloned.displayName || cloned.name}"`);
        this.router.navigate(['/catalog', 'groups', cloned.id]);
      },
      error: (err) => {
        this.actionInProgress.set(false);
        this.toastService.error(err.message || 'Failed to clone group');
      },
    });
  }

  // -- Editing (draft only) -------------------------------------------

  toggleEditing(): void {
    const g = this.group();
    if (!g) return;
    if (this.editing()) {
      this.editing.set(false);
    } else {
      this.editName = g.name;
      this.editDisplayName = g.displayName || '';
      this.editDescription = g.description || '';
      this.editing.set(true);
    }
  }

  saveEdit(): void {
    const g = this.group();
    if (!g) return;
    this.catalogService.updateGroup(g.id, {
      name: this.editName.trim(),
      displayName: this.editDisplayName.trim() || null,
      description: this.editDescription.trim() || null,
    }).subscribe({
      next: (updated) => {
        this.group.set(updated);
        this.editing.set(false);
        this.toastService.success('Group updated');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to update group');
      },
    });
  }

  // -- Item management (draft only) ------------------------------------

  addItem(): void {
    const g = this.group();
    if (!g || !this.newOfferingId) return;
    this.catalogService.addGroupItem(
      g.id,
      this.newOfferingId,
      this.newItemRequired || undefined,
      this.newItemSortOrder || undefined,
    ).subscribe({
      next: (item) => {
        this.group.update((grp) =>
          grp ? { ...grp, items: [...grp.items, item] } : grp,
        );
        this.newOfferingId = '';
        this.newItemRequired = false;
        this.newItemSortOrder = 0;
        this.toastService.success('Offering added to group');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to add offering');
      },
    });
  }

  removeItem(itemId: string): void {
    this.catalogService.removeGroupItem(itemId).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.group.update((grp) =>
            grp ? { ...grp, items: grp.items.filter((i) => i.id !== itemId) } : grp,
          );
          this.toastService.success('Offering removed from group');
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to remove offering');
      },
    });
  }
}
