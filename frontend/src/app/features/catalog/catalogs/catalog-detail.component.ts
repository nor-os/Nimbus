/**
 * Overview: Service catalog detail -- view and manage a single service catalog including
 *     version history, lifecycle actions, catalog items, and tenant assignments with diff view.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/catalog.service,
 *     app/core/services/tenant.service
 * Concepts: Catalog versioning, publish/archive lifecycle, item management, tenant assignments
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { CatalogService } from '@core/services/catalog.service';
import { TenantService } from '@core/services/tenant.service';
import {
  CatalogDiff,
  CatalogDiffItem,
  ServiceCatalog,
  ServiceCatalogItem,
  ServiceOffering,
  ServiceGroup,
  TenantCatalogAssignment,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

interface TenantInfo {
  id: string;
  name: string;
}

@Component({
  selector: 'nimbus-catalog-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="catalog-detail-page">
        @if (loading()) {
          <div class="loading">Loading catalog...</div>
        }

        @if (!loading() && !catalog()) {
          <div class="empty-state">
            Catalog not found.
            <a routerLink="/catalog/catalogs" class="back-link">Back to list</a>
          </div>
        }

        @if (catalog(); as cat) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <a routerLink="/catalog/catalogs" class="back-link">&larr; Back</a>
              <h1>{{ cat.name }}</h1>
              <div class="header-badges">
                <span class="badge badge-version">{{ cat.versionLabel }}</span>
                <span
                  class="badge"
                  [class.badge-draft]="cat.status === 'draft'"
                  [class.badge-published]="cat.status === 'published'"
                  [class.badge-archived]="cat.status === 'archived'"
                >
                  {{ cat.status }}
                </span>
              </div>
            </div>
          </div>

          @if (cat.description) {
            <p class="catalog-description">{{ cat.description }}</p>
          }

          <div class="meta-row">
            <span class="meta-item">
              Created: {{ cat.createdAt | date: 'medium' }}
            </span>
          </div>

          <!-- Actions section -->
          <div class="actions-section">
            <div class="section-title">Actions</div>
            <div class="actions-row">
              @if (cat.status === 'draft') {
                <button
                  *nimbusHasPermission="'catalog:catalog:manage'"
                  class="btn btn-sm btn-success"
                  (click)="publishCatalog()"
                >
                  Publish
                </button>
              }
              @if (cat.status === 'published') {
                <button
                  *nimbusHasPermission="'catalog:catalog:manage'"
                  class="btn btn-sm btn-secondary"
                  (click)="archiveCatalog()"
                >
                  Archive
                </button>
              }
              <button
                *nimbusHasPermission="'catalog:catalog:manage'"
                class="btn btn-sm btn-secondary"
                (click)="showVersionForm()"
              >
                New Version
              </button>
              <button
                *nimbusHasPermission="'catalog:catalog:manage'"
                class="btn btn-sm btn-secondary"
                (click)="showCloneForm()"
              >
                Clone for Tenant
              </button>
            </div>

            <!-- New version inline form -->
            @if (versionFormVisible()) {
              <div class="inline-form">
                <span class="inline-label">Create new version from {{ cat.versionLabel }}:</span>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="createVersion('minor')"
                >
                  Minor bump
                </button>
                <button
                  class="btn btn-sm btn-secondary"
                  (click)="createVersion('major')"
                >
                  Major bump
                </button>
                <button class="btn btn-sm btn-secondary" (click)="versionFormVisible.set(false)">Cancel</button>
              </div>
            }

            <!-- Clone for tenant inline form -->
            @if (cloneFormVisible()) {
              <div class="inline-form">
                <select
                  class="form-input clone-field"
                  [(ngModel)]="cloneTenantId"
                >
                  <option value="">Select target tenant...</option>
                  @for (tenant of tenants(); track tenant.id) {
                    <option [value]="tenant.id">{{ tenant.name }}</option>
                  }
                </select>
                <button
                  class="btn btn-sm btn-primary"
                  (click)="cloneForTenant()"
                  [disabled]="!cloneTenantId"
                >
                  Clone
                </button>
                <button class="btn btn-sm btn-secondary" (click)="cloneFormVisible.set(false)">Cancel</button>
              </div>
            }
          </div>

          <!-- Version history sidebar -->
          @if (versions().length > 1) {
            <div class="version-section">
              <div class="section-title">Version History</div>
              <div class="version-list">
                @for (ver of versions(); track ver.id) {
                  <div
                    class="version-item"
                    [class.version-active]="ver.id === cat.id"
                    (click)="switchToVersion(ver.id)"
                  >
                    <span class="version-label">{{ ver.versionLabel }}</span>
                    <span
                      class="badge badge-sm"
                      [class.badge-draft]="ver.status === 'draft'"
                      [class.badge-published]="ver.status === 'published'"
                      [class.badge-archived]="ver.status === 'archived'"
                    >
                      {{ ver.status }}
                    </span>
                    <span class="version-date">{{ ver.createdAt | date: 'shortDate' }}</span>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Items management -->
          <div class="items-section">
            <div class="items-header">
              <span class="section-title">Catalog Items ({{ cat.items.length }})</span>
              <button
                *nimbusHasPermission="'catalog:catalog:manage'"
                class="btn-link"
                (click)="showAddItemForm()"
              >
                + Add Item
              </button>
            </div>

            <!-- Add item form -->
            @if (addingItem()) {
              <div class="add-item-form">
                <select class="form-input item-field" [(ngModel)]="newItemType">
                  <option value="offering">Service</option>
                  <option value="group">Service Group</option>
                </select>
                @if (newItemType === 'offering') {
                  <select class="form-input item-field" [(ngModel)]="newItemOfferingId">
                    <option value="">Select offering...</option>
                    @for (offering of offerings(); track offering.id) {
                      <option [value]="offering.id">{{ offering.name }}</option>
                    }
                  </select>
                }
                @if (newItemType === 'group') {
                  <select class="form-input item-field" [(ngModel)]="newItemGroupId">
                    <option value="">Select group...</option>
                    @for (group of groups(); track group.id) {
                      <option [value]="group.id">{{ group.displayName || group.name }}</option>
                    }
                  </select>
                }
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
                  [disabled]="!isAddItemValid()"
                >
                  Add
                </button>
                <button class="btn btn-sm btn-secondary" (click)="addingItem.set(false)">Cancel</button>
              </div>
            }

            @if (cat.items && cat.items.length > 0) {
              <table class="items-table">
                <thead>
                  <tr>
                    <th>Type</th>
                    <th>Name</th>
                    <th>Sort Order</th>
                    <th class="th-actions">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  @for (item of cat.items; track item.id) {
                    <tr>
                      <td>
                        <span class="badge" [class.badge-offering]="item.serviceOfferingId" [class.badge-group]="item.serviceGroupId">
                          {{ item.serviceOfferingId ? 'Service' : 'Group' }}
                        </span>
                      </td>
                      <td>{{ itemName(item) }}</td>
                      <td>{{ item.sortOrder }}</td>
                      <td class="td-actions">
                        <button
                          *nimbusHasPermission="'catalog:catalog:manage'"
                          class="btn-icon btn-danger"
                          title="Remove item"
                          (click)="removeItem(item)"
                        >
                          &times;
                        </button>
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            } @else {
              <div class="no-items">No items in this catalog.</div>
            }
          </div>

          <!-- Tenant Assignments -->
          <div class="assignment-section">
            <div class="section-title">Tenant Assignments</div>

            @if (assignments().length > 0) {
              <table class="items-table">
                <thead>
                  <tr>
                    <th>Tenant</th>
                    <th>Type</th>
                    <th>Customized</th>
                    <th>Changes</th>
                    <th class="th-actions">Open</th>
                  </tr>
                </thead>
                <tbody>
                  @for (a of assignments(); track a.tenantId + a.assignmentType) {
                    <tr
                      class="assignment-row"
                      [class.assignment-active]="selectedAssignment()?.tenantId === a.tenantId && selectedAssignment()?.assignmentType === a.assignmentType"
                      (click)="selectAssignment(a)"
                    >
                      <td>{{ tenantNameForId(a.tenantId) || a.tenantId.substring(0, 8) + '...' }}</td>
                      <td>
                        @if (a.assignmentType === 'pin') {
                          <span class="badge badge-pin">Pinned</span>
                        } @else {
                          <span class="badge badge-clone">Custom Copy</span>
                        }
                      </td>
                      <td>
                        @if (a.assignmentType === 'clone') {
                          @if (a.isCustomized) {
                            <span class="badge badge-warning">Modified</span>
                          } @else {
                            <span class="badge badge-published">Identical</span>
                          }
                        } @else {
                          <span class="text-muted">\u2014</span>
                        }
                      </td>
                      <td>
                        @if (a.assignmentType === 'clone') {
                          <span class="diff-add" [class.diff-zero]="a.additions === 0">+{{ a.additions }}</span>
                          <span class="diff-sep">/</span>
                          <span class="diff-del" [class.diff-zero]="a.deletions === 0">-{{ a.deletions }}</span>
                        } @else {
                          <span class="text-muted">\u2014</span>
                        }
                      </td>
                      <td class="td-actions">
                        @if (a.assignmentType === 'clone' && a.cloneCatalogId) {
                          <a
                            class="btn-link"
                            [routerLink]="['/catalog', 'catalogs', a.cloneCatalogId]"
                            title="Open tenant catalog"
                            (click)="$event.stopPropagation()"
                          >
                            Open
                          </a>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>

              <!-- Diff panel -->
              @if (selectedAssignment(); as sel) {
                <div class="diff-panel">
                  <div class="diff-panel-header">
                    <span class="diff-panel-title">
                      {{ tenantNameForId(sel.tenantId) || 'Tenant' }} &mdash;
                      @if (sel.assignmentType === 'pin') {
                        Uses catalog as-is (pinned)
                      } @else {
                        Custom Copy Diff
                      }
                    </span>
                    <button class="btn-icon" (click)="closeAssignment()" title="Close">&times;</button>
                  </div>

                  @if (sel.assignmentType === 'pin') {
                    <div class="diff-panel-body">
                      <div class="diff-info">This tenant uses the catalog as-is via a pin. No customizations.</div>
                    </div>
                  }

                  @if (sel.assignmentType === 'clone') {
                    <div class="diff-panel-body">
                      @if (diffLoading()) {
                        <div class="loading">Loading diff...</div>
                      }

                      @if (!diffLoading() && diff(); as d) {
                        @if (d.additions.length > 0) {
                          <div class="diff-group diff-group-add">
                            <div class="diff-group-title">Additions ({{ d.additions.length }})</div>
                            @for (item of d.additions; track item.id) {
                              <div class="diff-item">+ {{ diffItemName(item) }}</div>
                            }
                          </div>
                        }

                        @if (d.deletions.length > 0) {
                          <div class="diff-group diff-group-del">
                            <div class="diff-group-title">Removals ({{ d.deletions.length }})</div>
                            @for (item of d.deletions; track item.id) {
                              <div class="diff-item">- {{ diffItemName(item) }}</div>
                            }
                          </div>
                        }

                        @if (d.additions.length === 0 && d.deletions.length === 0) {
                          <div class="diff-info">No differences. The clone is identical to the source.</div>
                        }

                        @if (sel.cloneCatalogId) {
                          <div class="diff-actions">
                            <a
                              class="btn btn-sm btn-primary"
                              [routerLink]="['/catalog', 'catalogs', sel.cloneCatalogId]"
                            >
                              Edit Tenant Catalog
                            </a>
                          </div>
                        }
                      }
                    </div>
                  }
                </div>
              }
            } @else {
              <div class="no-items">No tenants assigned to this catalog.</div>
            }
            <div class="pin-hint">Pin catalogs from tenant settings. Clone using the action above.</div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .catalog-detail-page { padding: 0; max-width: 960px; }

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
    .catalog-description {
      font-size: 0.875rem; color: #64748b; margin: 0 0 1rem; line-height: 1.5;
    }

    .meta-row {
      display: flex; gap: 1.5rem; margin-bottom: 1.5rem; flex-wrap: wrap;
    }
    .meta-item {
      font-size: 0.8125rem; color: #64748b; white-space: nowrap;
    }

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
      display: flex; gap: 0.5rem; align-items: center; margin-top: 0.75rem;
      padding: 0.75rem; background: #eff6ff; border-radius: 6px;
      border: 1px solid #dbeafe; flex-wrap: wrap;
    }
    .inline-label { font-size: 0.8125rem; color: #374151; font-weight: 500; }
    .clone-field { min-width: 200px; max-width: 300px; }

    /* -- Version history ---------------------------------------------- */
    .version-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .version-list { display: flex; flex-direction: column; gap: 0.25rem; }
    .version-item {
      display: flex; align-items: center; gap: 0.75rem; cursor: pointer;
      padding: 0.5rem 0.75rem; border-radius: 6px;
      font-size: 0.8125rem; color: #374151; transition: background 0.15s;
    }
    .version-item:hover { background: #f8fafc; }
    .version-active { background: #eff6ff; font-weight: 600; }
    .version-label { font-weight: 500; min-width: 60px; }
    .version-date { color: #94a3b8; font-size: 0.75rem; margin-left: auto; }

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
    .item-field { flex: 2; min-width: 180px; }
    .item-field-sm { flex: 1; min-width: 60px; max-width: 80px; }

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

    .no-items { color: #64748b; font-size: 0.8125rem; padding: 0.5rem 0; }

    /* -- Assignment section -------------------------------------------- */
    .assignment-section {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1rem;
    }
    .assignment-row { cursor: pointer; transition: background 0.15s; }
    .assignment-row:hover { background: #f8fafc; }
    .assignment-active { background: #eff6ff !important; }

    .text-muted { color: #94a3b8; font-size: 0.8125rem; }

    .diff-add { color: #16a34a; font-weight: 600; font-size: 0.8125rem; }
    .diff-del { color: #dc2626; font-weight: 600; font-size: 0.8125rem; }
    .diff-sep { color: #94a3b8; margin: 0 0.125rem; font-size: 0.8125rem; }
    .diff-zero { opacity: 0.4; }

    .pin-hint {
      margin-top: 0.75rem; font-size: 0.75rem; color: #94a3b8; font-style: italic;
    }

    /* -- Diff panel --------------------------------------------------- */
    .diff-panel {
      margin-top: 0.75rem; border: 1px solid #e2e8f0; border-radius: 8px;
      overflow: hidden;
    }
    .diff-panel-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 1rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .diff-panel-title { font-size: 0.8125rem; font-weight: 600; color: #1e293b; }
    .diff-panel-body { padding: 0.75rem 1rem; }

    .diff-info { color: #64748b; font-size: 0.8125rem; font-style: italic; }

    .diff-group { padding: 0.5rem 0.75rem; border-radius: 6px; margin-bottom: 0.5rem; }
    .diff-group-add { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .diff-group-del { background: #fef2f2; border: 1px solid #fecaca; }
    .diff-group-title {
      font-size: 0.75rem; font-weight: 600; margin-bottom: 0.375rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .diff-group-add .diff-group-title { color: #166534; }
    .diff-group-del .diff-group-title { color: #991b1b; }
    .diff-item { font-size: 0.8125rem; padding: 0.125rem 0; }
    .diff-group-add .diff-item { color: #15803d; }
    .diff-group-del .diff-item { color: #dc2626; }

    .diff-actions { margin-top: 0.75rem; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-sm { font-size: 0.625rem; padding: 0.0625rem 0.375rem; }
    .badge-version { background: #dbeafe; color: #1d4ed8; }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .badge-offering { background: #ede9fe; color: #6d28d9; }
    .badge-group { background: #fce7f3; color: #be185d; }
    .badge-pin { background: #dbeafe; color: #1d4ed8; }
    .badge-clone { background: #ede9fe; color: #6d28d9; }
    .badge-warning { background: #fef3c7; color: #92400e; }

    /* -- Form inputs -------------------------------------------------- */
    .form-input {
      padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }

    /* -- Buttons ------------------------------------------------------ */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none; text-decoration: none;
      display: inline-block;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-success { background: #16a34a; color: #fff; }
    .btn-success:hover { background: #15803d; }
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
export class CatalogDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private catalogService = inject(CatalogService);
  private tenantService = inject(TenantService);
  private toastService = inject(ToastService);

  catalog = signal<ServiceCatalog | null>(null);
  versions = signal<ServiceCatalog[]>([]);
  assignments = signal<TenantCatalogAssignment[]>([]);
  selectedAssignment = signal<TenantCatalogAssignment | null>(null);
  diff = signal<CatalogDiff | null>(null);
  diffLoading = signal(false);
  offerings = signal<ServiceOffering[]>([]);
  groups = signal<ServiceGroup[]>([]);
  tenants = signal<TenantInfo[]>([]);
  loading = signal(false);

  // Action form state
  versionFormVisible = signal(false);
  cloneFormVisible = signal(false);
  addingItem = signal(false);

  // Clone form
  cloneTenantId = '';

  // Add item form
  newItemType: 'offering' | 'group' = 'offering';
  newItemOfferingId = '';
  newItemGroupId = '';
  newItemSortOrder = 0;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadCatalog(id);
      this.loadTenants();
      this.loadOfferings();
      this.loadGroups();
    }
  }

  loadCatalog(id: string): void {
    this.loading.set(true);
    this.catalogService.getCatalog(id).subscribe({
      next: (cat) => {
        this.catalog.set(cat);
        this.loading.set(false);
        if (cat?.groupId) {
          this.loadVersions(cat.groupId);
        }
        this.loadAssignments();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load catalog');
        this.loading.set(false);
      },
    });
  }

  private loadVersions(groupId: string): void {
    this.catalogService.listCatalogVersions(groupId).subscribe({
      next: (versions) => this.versions.set(versions),
      error: () => { /* silent */ },
    });
  }

  private loadAssignments(): void {
    const catalogId = this.catalog()?.id;
    if (!catalogId) return;
    this.catalogService.getTenantAssignments(catalogId).subscribe({
      next: (assignments) => this.assignments.set(assignments),
      error: () => { /* silent */ },
    });
  }

  private loadTenants(): void {
    this.tenantService.listTenants(0, 500).subscribe({
      next: (list) => this.tenants.set(list.map((t) => ({ id: t.id, name: t.name }))),
    });
  }

  private loadOfferings(): void {
    this.catalogService.listOfferings({ limit: 500 }).subscribe({
      next: (response) => this.offerings.set(response.items),
    });
  }

  private loadGroups(): void {
    this.catalogService.listGroups(0, 500).subscribe({
      next: (response) => this.groups.set(response.items),
    });
  }

  // -- Lifecycle actions ----------------------------------------------

  publishCatalog(): void {
    const cat = this.catalog();
    if (!cat) return;

    this.catalogService.publishCatalog(cat.id).subscribe({
      next: (updated) => {
        this.catalog.set(updated);
        this.updateVersionInList(updated);
        this.toastService.success(`${cat.name} ${updated.versionLabel} published`);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to publish catalog');
      },
    });
  }

  archiveCatalog(): void {
    const cat = this.catalog();
    if (!cat) return;

    this.catalogService.archiveCatalog(cat.id).subscribe({
      next: (updated) => {
        this.catalog.set(updated);
        this.updateVersionInList(updated);
        this.toastService.success(`${cat.name} ${updated.versionLabel} archived`);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to archive catalog');
      },
    });
  }

  // -- Versioning -----------------------------------------------------

  showVersionForm(): void {
    this.versionFormVisible.set(true);
    this.cloneFormVisible.set(false);
  }

  createVersion(bump: 'minor' | 'major'): void {
    const cat = this.catalog();
    if (!cat) return;

    this.catalogService.createCatalogVersion(cat.id, bump).subscribe({
      next: (created) => {
        this.versions.update((v) => [...v, created]);
        this.toastService.success(`Version ${created.versionLabel} created (draft)`);
        this.versionFormVisible.set(false);
        // Navigate to the new version
        this.router.navigate(['/catalog', 'catalogs', created.id]);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create version');
      },
    });
  }

  switchToVersion(versionId: string): void {
    this.router.navigate(['/catalog', 'catalogs', versionId]);
    this.loadCatalog(versionId);
  }

  // -- Clone ----------------------------------------------------------

  showCloneForm(): void {
    this.cloneFormVisible.set(true);
    this.versionFormVisible.set(false);
    this.cloneTenantId = '';
  }

  cloneForTenant(): void {
    const cat = this.catalog();
    if (!cat || !this.cloneTenantId) return;

    this.catalogService.cloneCatalogForTenant(cat.id, this.cloneTenantId).subscribe({
      next: (cloned) => {
        this.toastService.success(`Catalog cloned as "${cloned.name}"`);
        this.cloneFormVisible.set(false);
        this.cloneTenantId = '';
        this.router.navigate(['/catalog', 'catalogs', cloned.id]);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to clone catalog');
      },
    });
  }

  // -- Tenant Assignments ---------------------------------------------

  selectAssignment(a: TenantCatalogAssignment): void {
    this.selectedAssignment.set(a);
    this.diff.set(null);
    if (a.assignmentType === 'clone' && a.cloneCatalogId) {
      this.diffLoading.set(true);
      this.catalogService.getCatalogDiff(a.catalogId, a.cloneCatalogId).subscribe({
        next: (d) => {
          this.diff.set(d);
          this.diffLoading.set(false);
        },
        error: () => {
          this.diffLoading.set(false);
        },
      });
    }
  }

  closeAssignment(): void {
    this.selectedAssignment.set(null);
    this.diff.set(null);
  }

  diffItemName(item: CatalogDiffItem): string {
    if (item.serviceOfferingId) {
      const offering = this.offerings().find((o) => o.id === item.serviceOfferingId);
      return offering ? offering.name : item.serviceOfferingId.substring(0, 8) + '...';
    }
    if (item.serviceGroupId) {
      const group = this.groups().find((g) => g.id === item.serviceGroupId);
      return group ? (group.displayName || group.name) : item.serviceGroupId.substring(0, 8) + '...';
    }
    return '\u2014';
  }

  // -- Item management ------------------------------------------------

  showAddItemForm(): void {
    this.addingItem.set(true);
    this.newItemType = 'offering';
    this.newItemOfferingId = '';
    this.newItemGroupId = '';
    this.newItemSortOrder = 0;
  }

  isAddItemValid(): boolean {
    if (this.newItemType === 'offering') {
      return !!this.newItemOfferingId;
    }
    return !!this.newItemGroupId;
  }

  addItem(): void {
    const cat = this.catalog();
    if (!cat) return;

    const offeringId = this.newItemType === 'offering' ? this.newItemOfferingId : undefined;
    const groupId = this.newItemType === 'group' ? this.newItemGroupId : undefined;

    this.catalogService.addCatalogItem(
      cat.id,
      offeringId,
      groupId,
      this.newItemSortOrder || undefined,
    ).subscribe({
      next: (item: ServiceCatalogItem) => {
        this.catalog.update((c) =>
          c ? { ...c, items: [...(c.items || []), item] } : c,
        );
        this.toastService.success('Item added to catalog');
        this.addingItem.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to add item');
      },
    });
  }

  removeItem(item: ServiceCatalogItem): void {
    this.catalogService.removeCatalogItem(item.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.catalog.update((c) =>
            c ? { ...c, items: c.items.filter((i) => i.id !== item.id) } : c,
          );
          this.toastService.success('Item removed from catalog');
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to remove item');
      },
    });
  }

  itemName(item: ServiceCatalogItem): string {
    if (item.serviceOfferingId) {
      const offering = this.offerings().find((o) => o.id === item.serviceOfferingId);
      return offering ? offering.name : item.serviceOfferingId.substring(0, 8) + '...';
    }
    if (item.serviceGroupId) {
      const group = this.groups().find((g) => g.id === item.serviceGroupId);
      return group ? (group.displayName || group.name) : item.serviceGroupId.substring(0, 8) + '...';
    }
    return '\u2014';
  }

  tenantNameForId(tenantId: string): string {
    const tenant = this.tenants().find((t) => t.id === tenantId);
    return tenant ? tenant.name : '';
  }

  // -- Private helpers ------------------------------------------------

  private updateVersionInList(updated: ServiceCatalog): void {
    this.versions.update((list) =>
      list.map((v) => {
        if (v.id === updated.id) return updated;
        // Archive previously published version in same group
        if (v.groupId === updated.groupId && v.status === 'published' && updated.status === 'published') {
          return { ...v, status: 'archived' };
        }
        return v;
      }),
    );
  }
}
