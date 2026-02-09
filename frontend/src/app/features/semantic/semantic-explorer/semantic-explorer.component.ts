/**
 * Overview: Unified Semantic Explorer — tabbed view with Catalog, Providers, and Relationships,
 *     side detail panel, and full CRUD via dialogs.
 * Architecture: Feature component combining type catalog, provider hierarchy, and relationship management (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/semantic.service
 * Concepts: View toggle (Catalog/Providers/Relationships), provider drill-down, side detail panel,
 *     CRUD dialogs, is_system protection
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { SemanticService } from '@core/services/semantic.service';
import { PermissionCheckService } from '@core/services/permission-check.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';
import { DialogService } from '@shared/services/dialog.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import {
  SemanticCategoryWithTypes,
  SemanticResourceType,
  SemanticRelationshipKind,
  SemanticCategory,
  SemanticProvider,
  SemanticProviderResourceType,
  SemanticTypeMapping,
} from '@shared/models/semantic.model';
import { CategoryDialogComponent } from '../dialogs/category-dialog.component';
import { TypeDialogComponent, TypeDialogData } from '../dialogs/type-dialog.component';
import { ProviderDialogComponent } from '../dialogs/provider-dialog.component';
import { ProviderResourceTypeDialogComponent, PRTDialogData } from '../dialogs/provider-resource-type-dialog.component';
import { TypeMappingDialogComponent, TypeMappingDialogData } from '../dialogs/type-mapping-dialog.component';
import { RelationshipKindDialogComponent } from '../dialogs/relationship-kind-dialog.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';

type ViewMode = 'catalog' | 'providers' | 'relationships';

@Component({
  selector: 'nimbus-semantic-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  template: `
    <nimbus-layout>
    <div class="explorer">
      <!-- Header -->
      <div class="page-header">
        <div class="header-top">
          <h1>Semantic Explorer</h1>
          <div class="header-actions" *nimbusHasPermission="'semantic:type:manage'">
            @if (activeView() === 'catalog') {
              <button class="btn btn-sm btn-outline" (click)="openCategoryDialog()">+ Category</button>
              <button class="btn btn-sm btn-primary" (click)="openTypeDialog()">+ Type</button>
            }
            @if (activeView() === 'providers' && !selectedProvider()) {
              <button class="btn btn-sm btn-primary" (click)="openProviderDialog()">+ Provider</button>
            }
            @if (activeView() === 'providers' && selectedProvider()) {
              <button class="btn btn-sm btn-outline" (click)="openPRTDialog()">+ Resource Type</button>
              <button class="btn btn-sm btn-primary" (click)="openTypeMappingDialog()">+ Mapping</button>
            }
            @if (activeView() === 'relationships') {
              <button class="btn btn-sm btn-primary" (click)="openRelationshipKindDialog()">+ Relationship</button>
            }
          </div>
        </div>

        <!-- Stats bar -->
        <div class="stats-bar">
          <span class="stat">{{ typeCount() }} types</span>
          <span class="stat-sep">&middot;</span>
          <span class="stat">{{ categoryCount() }} categories</span>
          <span class="stat-sep">&middot;</span>
          <span class="stat">{{ providerCount() }} providers</span>
          <span class="stat-sep">&middot;</span>
          <span class="stat">{{ relationshipCount() }} relationships</span>
        </div>

        <!-- View toggle + filters -->
        <div class="toolbar">
          <div class="view-toggle">
            <button [class.active]="activeView() === 'catalog'" (click)="switchView('catalog')">Catalog</button>
            <button [class.active]="activeView() === 'providers'" (click)="switchView('providers')">Providers</button>
            <button [class.active]="activeView() === 'relationships'" (click)="switchView('relationships')">Relationships</button>
          </div>
          @if (activeView() === 'catalog') {
            <div class="filter-area">
              <input type="text" class="search-input" placeholder="Search types..." [ngModel]="searchTerm()" (ngModelChange)="searchTerm.set($event)" />
              <nimbus-searchable-select
                [ngModel]="categoryFilter()"
                (ngModelChange)="categoryFilter.set($event)"
                [options]="categoryOptions()"
                placeholder="All categories"
                [allowClear]="true"
              />
            </div>
          }
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading semantic data...</div>
      }

      <!-- Content area with optional side panel -->
      @if (!loading()) {
        <div class="content-area" [class.has-panel]="selectedType()">

          <!-- Main content -->
          <div class="main-content">

            <!-- CATALOG VIEW -->
            @if (activeView() === 'catalog') {
              @for (group of filteredGroups(); track group.category) {
                <div class="cat-section">
                  <div class="cat-header">
                    <span class="cat-name">{{ group.categoryLabel }}</span>
                    <span class="cat-count">{{ group.types.length }}</span>
                    <button class="icon-btn" *nimbusHasPermission="'semantic:type:manage'" title="Edit category" (click)="editCategory(group)">&#9998;</button>
                    @if (!group.isSystem) {
                      <button class="icon-btn danger" *nimbusHasPermission="'semantic:type:manage'" title="Delete category" (click)="deleteCategory(group)">&#10005;</button>
                    }
                  </div>
                  <div class="type-grid">
                    @for (t of group.types; track t.id) {
                      <div class="type-card" [class.selected]="selectedType()?.id === t.id" (click)="selectType(t)">
                        <div class="card-top">
                          <span class="card-name">{{ t.displayName }}</span>
                          @if (t.isAbstract) { <span class="badge abstract">Abstract</span> }
                          @if (t.isSystem) { <span class="badge system">System</span> }
                        </div>
                        @if (t.description) {
                          <p class="card-desc">{{ t.description }}</p>
                        }
                        <div class="card-meta">
                          <span>{{ t.mappings.length }} mappings</span>
                          @if (t.children.length) { <span>{{ t.children.length }} children</span> }
                        </div>
                        <div class="card-actions" *nimbusHasPermission="'semantic:type:manage'">
                          <button class="icon-btn" (click)="editType(t); $event.stopPropagation()" title="Edit">&#9998;</button>
                          @if (!t.isSystem) {
                            <button class="icon-btn danger" (click)="deleteType(t); $event.stopPropagation()" title="Delete">&#10005;</button>
                          }
                        </div>
                      </div>
                    }
                  </div>
                </div>
              }
              @if (filteredGroups().length === 0) {
                <div class="empty-state">No types match your filters.</div>
              }
            }

            <!-- PROVIDERS VIEW -->
            @if (activeView() === 'providers') {
              @if (!selectedProvider()) {
                <!-- Level 1: Provider cards -->
                <div class="provider-grid">
                  @for (p of providers(); track p.id) {
                    <div class="provider-card" (click)="selectProvider(p)">
                      <div class="provider-card-top">
                        <span class="provider-card-name">{{ p.displayName }}</span>
                        <span class="badge" [class]="'ptype-' + p.providerType">{{ p.providerType }}</span>
                        @if (p.isSystem) { <span class="badge system">System</span> }
                      </div>
                      @if (p.description) {
                        <p class="card-desc">{{ p.description }}</p>
                      }
                      <div class="card-meta">
                        <span>{{ p.resourceTypeCount }} resource types</span>
                      </div>
                      <div class="card-actions" *nimbusHasPermission="'semantic:provider:manage'">
                        <button class="icon-btn" (click)="editProvider(p); $event.stopPropagation()" title="Edit">&#9998;</button>
                        @if (!p.isSystem) {
                          <button class="icon-btn danger" (click)="deleteProvider(p); $event.stopPropagation()" title="Delete">&#10005;</button>
                        }
                      </div>
                    </div>
                  }
                </div>
                @if (providers().length === 0) {
                  <div class="empty-state">No providers found.</div>
                }
              } @else {
                <!-- Level 2: Resource types table for selected provider -->
                <div class="breadcrumb">
                  <button class="breadcrumb-link" (click)="selectedProvider.set(null)">Providers</button>
                  <span class="breadcrumb-sep">&#8250;</span>
                  <span class="breadcrumb-current">{{ selectedProvider()!.displayName }}</span>
                </div>
                <div class="table-wrapper">
                  <table>
                    <thead>
                      <tr>
                        <th>API Type</th>
                        <th>Display Name</th>
                        <th>Status</th>
                        <th>Semantic Type</th>
                        <th>System</th>
                        <th *nimbusHasPermission="'semantic:provider:manage'">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (prt of providerResourceTypes(); track prt.id) {
                        <tr>
                          <td class="mono">{{ prt.apiType }}</td>
                          <td>{{ prt.displayName }}</td>
                          <td>
                            <span class="badge" [class]="'status-' + prt.status">{{ prt.status }}</span>
                          </td>
                          <td>
                            @if (prt.semanticTypeName) {
                              <span class="badge category">{{ prt.semanticTypeName }}</span>
                            } @else {
                              <span class="muted">—</span>
                            }
                          </td>
                          <td>
                            @if (prt.isSystem) { <span class="badge system">System</span> }
                          </td>
                          <td *nimbusHasPermission="'semantic:provider:manage'">
                            <button class="icon-btn" (click)="editPRT(prt)" title="Edit">&#9998;</button>
                            @if (!prt.isSystem) {
                              <button class="icon-btn danger" (click)="deletePRT(prt)" title="Delete">&#10005;</button>
                            }
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
                @if (providerResourceTypes().length === 0) {
                  <div class="empty-state">No resource types for this provider.</div>
                }
              }
            }

            <!-- RELATIONSHIPS VIEW -->
            @if (activeView() === 'relationships') {
              <div class="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Name</th>
                      <th>Display Name</th>
                      <th>Inverse Name</th>
                      <th>Description</th>
                      <th>System</th>
                      <th *nimbusHasPermission="'semantic:type:manage'">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (kind of relationshipKinds(); track kind.id) {
                      <tr>
                        <td class="mono">{{ kind.name }}</td>
                        <td>{{ kind.displayName }}</td>
                        <td class="mono">{{ kind.inverseName }}</td>
                        <td class="muted">{{ kind.description || '—' }}</td>
                        <td>
                          @if (kind.isSystem) { <span class="badge system">System</span> }
                        </td>
                        <td *nimbusHasPermission="'semantic:type:manage'">
                          <button class="icon-btn" (click)="editRelationshipKind(kind)" title="Edit">&#9998;</button>
                          @if (!kind.isSystem) {
                            <button class="icon-btn danger" (click)="deleteRelationshipKind(kind)" title="Delete">&#10005;</button>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </div>

          <!-- Side detail panel -->
          @if (selectedType(); as t) {
            <div class="side-panel">
              <div class="panel-header">
                <h3>{{ t.displayName }}</h3>
                <button class="icon-btn" (click)="selectedType.set(null)" title="Close">&times;</button>
              </div>
              <div class="panel-badges">
                <span class="badge category">{{ t.category.displayName }}</span>
                @if (t.isAbstract) { <span class="badge abstract">Abstract</span> }
                @if (t.isSystem) { <span class="badge system">System</span> }
              </div>
              @if (t.description) { <p class="panel-desc">{{ t.description }}</p> }

              <div class="panel-actions" *nimbusHasPermission="'semantic:type:manage'">
                <button class="btn btn-sm btn-outline" (click)="editType(t)">Edit Type</button>
                @if (!t.isSystem) {
                  <button class="btn btn-sm btn-danger" (click)="deleteType(t)">Delete Type</button>
                }
              </div>

              <!-- Properties -->
              @if (t.propertiesSchema?.length) {
                <div class="panel-section">
                  <h4>Properties ({{ t.propertiesSchema!.length }})</h4>
                  <div class="props-table">
                    @for (prop of t.propertiesSchema; track prop.name) {
                      <div class="prop-row">
                        <span class="mono prop-name">{{ prop.name }}</span>
                        <span class="badge type-badge">{{ prop.data_type }}</span>
                        @if (prop.required) { <span class="required-dot">*</span> }
                      </div>
                    }
                  </div>
                </div>
              }

              <!-- Mappings -->
              @if (t.mappings.length) {
                <div class="panel-section">
                  <h4>Provider Mappings ({{ t.mappings.length }})</h4>
                  @for (m of t.mappings; track m.id) {
                    <div class="mapping-row">
                      <span class="provider-name">{{ m.providerName }}</span>
                      <span class="mono">{{ m.providerDisplayName || m.providerApiType }}</span>
                    </div>
                  }
                </div>
              }

              <!-- Hierarchy -->
              @if (t.parentTypeName || t.children.length) {
                <div class="panel-section">
                  <h4>Hierarchy</h4>
                  @if (t.parentTypeName) {
                    <div class="hier-item"><span class="muted">Parent:</span> <span class="mono">{{ t.parentTypeName }}</span></div>
                  }
                  @if (t.children.length) {
                    <div class="hier-item">
                      <span class="muted">Children:</span>
                      @for (child of t.children; track child.id) {
                        <span class="chip clickable" (click)="selectType(child)">{{ child.displayName }}</span>
                      }
                    </div>
                  }
                </div>
              }

              <!-- Allowed relationships -->
              @if (t.allowedRelationshipKinds?.length) {
                <div class="panel-section">
                  <h4>Allowed Relationships</h4>
                  <div class="chip-list">
                    @for (kind of t.allowedRelationshipKinds; track kind) {
                      <span class="chip">{{ kind }}</span>
                    }
                  </div>
                </div>
              }
            </div>
          }
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .explorer { padding: 1.5rem; }
    .page-header { margin-bottom: 1.25rem; }
    .header-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.375rem; }
    .header-top h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-actions { display: flex; gap: 0.5rem; }

    .stats-bar { display: flex; gap: 0.25rem; font-size: 0.8125rem; color: #64748b; margin-bottom: 0.75rem; }
    .stat-sep { color: #cbd5e1; }

    .toolbar { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }
    .view-toggle { display: inline-flex; border-radius: 6px; overflow: hidden; border: 1px solid #e2e8f0; }
    .view-toggle button {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500; padding: 0.4375rem 1rem;
      border: none; background: #f1f5f9; color: #64748b; cursor: pointer; transition: all 0.15s;
    }
    .view-toggle button + button { border-left: 1px solid #e2e8f0; }
    .view-toggle button.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .view-toggle button:hover:not(.active) { background: #e2e8f0; color: #374151; }

    .filter-area { display: flex; gap: 0.5rem; flex: 1; }
    .search-input, .filter-area select {
      padding: 0.4375rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit; color: #374151; background: #fff; outline: none;
    }
    .search-input { width: 240px; }
    .search-input:focus, .filter-area select:focus { border-color: #3b82f6; }

    .loading, .empty-state { padding: 3rem; text-align: center; color: #64748b; }

    /* Content layout with side panel */
    .content-area { display: flex; gap: 1.25rem; }
    .main-content { flex: 1; min-width: 0; }

    /* CATALOG */
    .cat-section { margin-bottom: 1.5rem; }
    .cat-header {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;
      padding-bottom: 0.375rem; border-bottom: 1px solid #e2e8f0;
    }
    .cat-name { font-weight: 600; color: #1d4ed8; font-size: 0.9375rem; }
    .cat-count { font-size: 0.75rem; color: #94a3b8; background: #f1f5f9; padding: 0.0625rem 0.5rem; border-radius: 999px; }

    .type-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 0.75rem; }
    .type-card, .provider-card {
      position: relative; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 0.875rem; cursor: pointer; transition: border-color 0.15s, box-shadow 0.15s;
    }
    .type-card:hover, .provider-card:hover { border-color: #3b82f6; box-shadow: 0 1px 4px rgba(59,130,246,0.1); }
    .type-card.selected { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.2); }
    .card-top, .provider-card-top { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem; }
    .card-name, .provider-card-name { font-weight: 600; font-size: 0.875rem; color: #1e293b; }
    .card-desc { font-size: 0.75rem; color: #64748b; margin: 0 0 0.375rem; line-height: 1.4; }
    .card-meta { font-size: 0.6875rem; color: #94a3b8; display: flex; gap: 0.75rem; }
    .card-actions {
      position: absolute; top: 0.5rem; right: 0.5rem; display: none; gap: 0.25rem;
    }
    .type-card:hover .card-actions, .provider-card:hover .card-actions { display: flex; }

    /* PROVIDERS */
    .provider-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 0.75rem; }

    .breadcrumb { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 1rem; font-size: 0.875rem; }
    .breadcrumb-link { background: none; border: none; color: #3b82f6; cursor: pointer; font-family: inherit; font-size: 0.875rem; padding: 0; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { color: #94a3b8; }
    .breadcrumb-current { font-weight: 600; color: #1e293b; }

    .badge.ptype-cloud { background: #dbeafe; color: #1d4ed8; }
    .badge.ptype-on_prem { background: #dcfce7; color: #16a34a; }
    .badge.ptype-saas { background: #f3e8ff; color: #7c3aed; }
    .badge.ptype-custom { background: #fef3c7; color: #92400e; }
    .badge.status-available { background: #dcfce7; color: #16a34a; }
    .badge.status-preview { background: #fef3c7; color: #92400e; }
    .badge.status-deprecated { background: #fef2f2; color: #dc2626; }

    /* Table */
    .table-wrapper {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    th {
      text-align: left; padding: 0.5rem 0.75rem; color: #64748b; font-weight: 600;
      font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em;
      border-bottom: 2px solid #e2e8f0; position: sticky; top: 0; background: #fff; z-index: 1;
    }
    td { padding: 0.5rem 0.75rem; color: #374151; border-bottom: 1px solid #f1f5f9; vertical-align: middle; }
    tr:hover td { background: #f8fafc; }

    /* Shared styles */
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.8125rem; }
    .muted { color: #94a3b8; }
    .badge {
      font-size: 0.625rem; padding: 0.0625rem 0.375rem; border-radius: 3px;
      text-transform: uppercase; font-weight: 600; letter-spacing: 0.03em; white-space: nowrap;
    }
    .badge.category { background: #dbeafe; color: #1d4ed8; }
    .badge.abstract { background: #f3e8ff; color: #7c3aed; }
    .badge.system { background: #f1f5f9; color: #64748b; }
    .badge.type-badge { background: #dcfce7; color: #16a34a; font-size: 0.5625rem; text-transform: lowercase; }

    .icon-btn {
      background: none; border: none; cursor: pointer; color: #94a3b8; font-size: 0.875rem;
      padding: 0.125rem 0.25rem; border-radius: 4px; transition: color 0.15s, background 0.15s;
    }
    .icon-btn:hover { color: #3b82f6; background: rgba(59,130,246,0.08); }
    .icon-btn.danger:hover { color: #dc2626; background: rgba(220,38,38,0.08); }

    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.4375rem 1rem; transition: all 0.15s; }
    .btn-sm { font-size: 0.75rem; padding: 0.375rem 0.875rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; border: none; }
    .btn-danger:hover { background: #b91c1c; }

    /* Side panel */
    .side-panel {
      width: 420px; min-width: 420px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.25rem; overflow-y: auto; max-height: calc(100vh - 240px);
    }
    .panel-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.375rem; }
    .panel-header h3 { margin: 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .panel-badges { display: flex; gap: 0.375rem; margin-bottom: 0.5rem; }
    .panel-desc { font-size: 0.8125rem; color: #64748b; margin: 0 0 0.75rem; line-height: 1.5; }
    .panel-actions { display: flex; gap: 0.5rem; margin-bottom: 1rem; padding-bottom: 0.75rem; border-bottom: 1px solid #f1f5f9; }
    .panel-section { margin-bottom: 1rem; }
    .panel-section h4 {
      font-size: 0.8125rem; font-weight: 600; color: #475569; margin: 0 0 0.5rem;
      padding-bottom: 0.25rem; border-bottom: 1px solid #f1f5f9;
    }
    .props-table { display: flex; flex-direction: column; gap: 0.25rem; }
    .prop-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; }
    .prop-name { min-width: 120px; }
    .required-dot { color: #dc2626; font-weight: 700; }
    .mapping-row { display: flex; align-items: center; gap: 0.5rem; font-size: 0.8125rem; padding: 0.25rem 0; }
    .provider-name { text-transform: capitalize; font-weight: 500; min-width: 70px; }
    .hier-item { display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; margin-bottom: 0.375rem; font-size: 0.8125rem; }
    .chip-list { display: flex; flex-wrap: wrap; gap: 0.375rem; }
    .chip {
      font-size: 0.6875rem; padding: 0.1875rem 0.5rem; background: #f1f5f9;
      border: 1px solid #e2e8f0; border-radius: 999px; color: #475569;
    }
    .chip.clickable { cursor: pointer; }
    .chip.clickable:hover { border-color: #3b82f6; color: #3b82f6; }
  `],
})
export class SemanticExplorerComponent implements OnInit {
  private semanticService = inject(SemanticService);
  private permissionCheck = inject(PermissionCheckService);
  private toast = inject(ToastService);
  private dialogService = inject(DialogService);
  private confirmService = inject(ConfirmService);

  activeView = signal<ViewMode>('catalog');
  loading = signal(true);
  categories = signal<SemanticCategoryWithTypes[]>([]);
  relationshipKinds = signal<SemanticRelationshipKind[]>([]);
  providers = signal<SemanticProvider[]>([]);
  providerResourceTypes = signal<SemanticProviderResourceType[]>([]);
  selectedProvider = signal<SemanticProvider | null>(null);
  searchTerm = signal('');
  categoryFilter = signal('');
  selectedType = signal<SemanticResourceType | null>(null);

  categoryOptions = computed(() => this.categories().map(c => ({ value: c.name, label: c.displayName })));

  // Stats
  typeCount = computed(() => this.categories().reduce((sum, c) => sum + c.types.length, 0));
  categoryCount = computed(() => this.categories().length);
  providerCount = computed(() => this.providers().length);
  relationshipCount = computed(() => this.relationshipKinds().length);

  // Filtered groups for catalog view
  filteredGroups = computed(() => {
    const cats = this.categories();
    const term = this.searchTerm().toLowerCase().trim();
    const catFilter = this.categoryFilter();

    return cats
      .filter((cat) => !catFilter || cat.name === catFilter)
      .map((cat) => ({
        category: cat.name,
        categoryLabel: cat.displayName,
        categoryId: cat.id,
        isSystem: cat.isSystem,
        types: cat.types.filter(
          (t) =>
            !term ||
            t.name.toLowerCase().includes(term) ||
            t.displayName.toLowerCase().includes(term) ||
            (t.description || '').toLowerCase().includes(term),
        ),
      }))
      .filter((g) => g.types.length > 0);
  });

  ngOnInit(): void {
    this.loadData();
  }

  switchView(view: ViewMode): void {
    this.activeView.set(view);
    this.selectedType.set(null);
    if (view === 'providers') {
      this.selectedProvider.set(null);
      this.loadProviders();
    }
  }

  selectType(t: SemanticResourceType): void {
    this.selectedType.set(t);
  }

  selectProvider(p: SemanticProvider): void {
    this.selectedProvider.set(p);
    this.loadProviderResourceTypes(p.id);
  }

  // -- Category CRUD ------------------------------------------------------

  async openCategoryDialog(category?: SemanticCategory): Promise<void> {
    const result = await this.dialogService.open<Record<string, unknown>>(
      CategoryDialogComponent,
      category ?? null,
    );
    if (!result) return;

    if (category) {
      this.semanticService.updateCategory(category.id, result as any).subscribe({
        next: () => { this.toast.success('Category updated'); this.loadData(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createCategory(result as any).subscribe({
        next: () => { this.toast.success('Category created'); this.loadData(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editCategory(group: { categoryId: string; categoryLabel: string; isSystem: boolean }): void {
    const cat = this.categories().find((c) => c.id === group.categoryId);
    if (cat) this.openCategoryDialog(cat);
  }

  async deleteCategory(group: { categoryId: string; categoryLabel: string; isSystem: boolean }): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Category',
      message: `Delete category "${group.categoryLabel}" and all its types?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteCategory(group.categoryId).subscribe({
      next: () => { this.toast.success('Category deleted'); this.loadData(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Type CRUD ----------------------------------------------------------

  async openTypeDialog(type?: SemanticResourceType): Promise<void> {
    const allTypes = this.categories().flatMap((c) => c.types);
    const data: TypeDialogData = {
      type: type ?? null,
      categories: this.categories(),
      types: allTypes,
      relationshipKinds: this.relationshipKinds(),
    };
    const result = await this.dialogService.open<Record<string, unknown>>(
      TypeDialogComponent,
      data,
    );
    if (!result) return;

    if (type) {
      this.semanticService.updateType(type.id, result as any).subscribe({
        next: (updated) => {
          this.toast.success('Type updated');
          if (updated) this.selectedType.set(updated);
          this.loadData();
        },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createType(result as any).subscribe({
        next: (created) => {
          this.toast.success('Type created');
          this.selectedType.set(created);
          this.loadData();
        },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editType(t: SemanticResourceType): void {
    this.openTypeDialog(t);
  }

  async deleteType(t: SemanticResourceType): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Type',
      message: `Delete type "${t.displayName}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteType(t.id).subscribe({
      next: () => {
        this.toast.success('Type deleted');
        if (this.selectedType()?.id === t.id) this.selectedType.set(null);
        this.loadData();
      },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Provider CRUD ------------------------------------------------------

  async openProviderDialog(provider?: SemanticProvider): Promise<void> {
    const result = await this.dialogService.open<Record<string, unknown>>(
      ProviderDialogComponent,
      provider ?? null,
    );
    if (!result) return;

    if (provider) {
      this.semanticService.updateProvider(provider.id, result as any).subscribe({
        next: () => { this.toast.success('Provider updated'); this.loadProviders(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createProvider(result as any).subscribe({
        next: () => { this.toast.success('Provider created'); this.loadProviders(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editProvider(p: SemanticProvider): void {
    this.openProviderDialog(p);
  }

  async deleteProvider(p: SemanticProvider): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Provider',
      message: `Delete provider "${p.displayName}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteProvider(p.id).subscribe({
      next: () => { this.toast.success('Provider deleted'); this.loadProviders(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Provider Resource Type CRUD ----------------------------------------

  async openPRTDialog(prt?: SemanticProviderResourceType): Promise<void> {
    const data: PRTDialogData = {
      prt: prt ?? null,
      providers: this.providers(),
      preselectedProviderId: this.selectedProvider()?.id,
    };
    const result = await this.dialogService.open<Record<string, unknown>>(
      ProviderResourceTypeDialogComponent,
      data,
    );
    if (!result) return;

    if (prt) {
      this.semanticService.updateProviderResourceType(prt.id, result as any).subscribe({
        next: () => {
          this.toast.success('Resource type updated');
          this.loadProviderResourceTypes(this.selectedProvider()!.id);
        },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createProviderResourceType(result as any).subscribe({
        next: () => {
          this.toast.success('Resource type created');
          this.loadProviderResourceTypes(this.selectedProvider()!.id);
          this.loadProviders();
        },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editPRT(prt: SemanticProviderResourceType): void {
    this.openPRTDialog(prt);
  }

  async deletePRT(prt: SemanticProviderResourceType): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Resource Type',
      message: `Delete resource type "${prt.displayName}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteProviderResourceType(prt.id).subscribe({
      next: () => {
        this.toast.success('Resource type deleted');
        this.loadProviderResourceTypes(this.selectedProvider()!.id);
        this.loadProviders();
      },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Type Mapping CRUD --------------------------------------------------

  async openTypeMappingDialog(): Promise<void> {
    const allTypes = this.categories().flatMap((c) => c.types);
    const data: TypeMappingDialogData = {
      mapping: null,
      providerResourceTypes: this.providerResourceTypes(),
      semanticTypes: allTypes,
    };
    const result = await this.dialogService.open<Record<string, unknown>>(
      TypeMappingDialogComponent,
      data,
    );
    if (!result) return;

    this.semanticService.createTypeMapping(result as any).subscribe({
      next: () => {
        this.toast.success('Mapping created');
        this.loadProviderResourceTypes(this.selectedProvider()!.id);
        this.loadData();
      },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Relationship kind CRUD ---------------------------------------------

  async openRelationshipKindDialog(kind?: SemanticRelationshipKind): Promise<void> {
    const result = await this.dialogService.open<Record<string, unknown>>(
      RelationshipKindDialogComponent,
      kind ?? null,
    );
    if (!result) return;

    if (kind) {
      this.semanticService.updateRelationshipKind(kind.id, result as any).subscribe({
        next: () => { this.toast.success('Relationship kind updated'); this.loadRelationshipKinds(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    } else {
      this.semanticService.createRelationshipKind(result as any).subscribe({
        next: () => { this.toast.success('Relationship kind created'); this.loadRelationshipKinds(); },
        error: (e: Error) => this.toast.error(e.message),
      });
    }
  }

  editRelationshipKind(kind: SemanticRelationshipKind): void {
    this.openRelationshipKindDialog(kind);
  }

  async deleteRelationshipKind(kind: SemanticRelationshipKind): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete Relationship Kind',
      message: `Delete relationship kind "${kind.displayName}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.semanticService.deleteRelationshipKind(kind.id).subscribe({
      next: () => { this.toast.success('Relationship kind deleted'); this.loadRelationshipKinds(); },
      error: (e: Error) => this.toast.error(e.message),
    });
  }

  // -- Data loading -------------------------------------------------------

  private loadData(): void {
    this.loading.set(true);
    this.semanticService.listCategories().subscribe({
      next: (categories) => {
        this.categories.set(categories);
        this.loading.set(false);
        // Refresh selected type if it still exists
        const sel = this.selectedType();
        if (sel) {
          const updated = categories.flatMap((c) => c.types).find((t) => t.id === sel.id);
          this.selectedType.set(updated ?? null);
        }
      },
      error: () => this.loading.set(false),
    });
    this.loadRelationshipKinds();
    this.loadProviders();
  }

  private loadRelationshipKinds(): void {
    this.semanticService.listRelationshipKinds().subscribe({
      next: (kinds) => this.relationshipKinds.set(kinds),
    });
  }

  private loadProviders(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => this.providers.set(providers),
    });
  }

  private loadProviderResourceTypes(providerId: string): void {
    this.semanticService.listProviderResourceTypes(providerId).subscribe({
      next: (prts) => this.providerResourceTypes.set(prts),
    });
  }
}
