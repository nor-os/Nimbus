/**
 * Overview: Unified Semantic Explorer — route-driven views for Catalog, Relationships, and Constraints,
 *     side detail panel, and full CRUD via dialogs.
 * Architecture: Feature component with route data-driven view selection (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router, app/core/services/semantic.service
 * Concepts: Route-driven views (Catalog/Relationships/Constraints), side detail panel,
 *     CRUD dialogs, is_system protection
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { SemanticService } from '@core/services/semantic.service';
import { CmdbService } from '@core/services/cmdb.service';
import { RelationshipType } from '@shared/models/cmdb.model';
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
} from '@shared/models/semantic.model';
import { CategoryDialogComponent } from '../dialogs/category-dialog.component';
import { TypeDialogComponent, TypeDialogData } from '../dialogs/type-dialog.component';
import { ProviderDialogComponent } from '../dialogs/provider-dialog.component';
import { RelationshipKindDialogComponent } from '../dialogs/relationship-kind-dialog.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';

type ViewMode = 'catalog' | 'relationships' | 'constraints';

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
          <h1>{{ pageTitle() }}</h1>
          <div class="header-actions" *nimbusHasPermission="'semantic:type:manage'">
            @if (activeView() === 'catalog') {
              <button class="btn btn-secondary" (click)="openCategoryDialog()">+ Category</button>
              <button class="btn btn-primary" (click)="openTypeDialog()">+ Type</button>
            }
            @if (activeView() === 'relationships') {
              <button class="btn btn-primary" (click)="openRelationshipKindDialog()">+ Relationship</button>
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

        <!-- Filters -->
        <div class="toolbar">
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

            <!-- CONSTRAINTS VIEW -->
            @if (activeView() === 'constraints') {
              <div class="constraints-section">
                <div class="constraints-toolbar">
                  <select class="domain-filter" [ngModel]="constraintDomainFilter()" (ngModelChange)="constraintDomainFilter.set($event)">
                    <option value="">All Domains</option>
                    <option value="infrastructure">Infrastructure</option>
                    <option value="operational">Operational</option>
                  </select>
                  <span class="toolbar-hint">Click cells to cycle: · → S → T → S+T → ·</span>
                </div>
                <div class="table-wrapper">
                  <table class="constraint-matrix">
                    <thead>
                      <tr>
                        <th class="sticky-col">Category</th>
                        @for (rt of filteredRelTypes(); track rt.id) {
                          <th class="rt-header">
                            <span class="rt-name">{{ rt.displayName }}</span>
                            <span class="rt-domain badge">{{ rt.domain }}</span>
                          </th>
                        }
                      </tr>
                    </thead>
                    <tbody>
                      @for (cat of constraintCategories(); track cat) {
                        <tr>
                          <td class="sticky-col cat-name">{{ cat }}</td>
                          @for (rt of filteredRelTypes(); track rt.id) {
                            <td class="cell editable"
                                [class.src]="isCategoryInConstraint(rt.sourceSemanticCategories, cat)"
                                [class.tgt]="isCategoryInConstraint(rt.targetSemanticCategories, cat)"
                                [class.both]="isCategoryInConstraint(rt.sourceSemanticCategories, cat) && isCategoryInConstraint(rt.targetSemanticCategories, cat)"
                                [class.saving]="isSavingConstraint(rt.id, cat)"
                                [title]="constraintCellTitle(rt, cat)"
                                (click)="cycleConstraint(rt, cat)"
                            >
                              @if (isSavingConstraint(rt.id, cat)) {
                                <span class="cell-icon saving-icon">⏳</span>
                              } @else if (isCategoryInConstraint(rt.sourceSemanticCategories, cat) && isCategoryInConstraint(rt.targetSemanticCategories, cat)) {
                                <span class="cell-icon">S+T</span>
                              } @else if (isCategoryInConstraint(rt.sourceSemanticCategories, cat)) {
                                <span class="cell-icon">S</span>
                              } @else if (isCategoryInConstraint(rt.targetSemanticCategories, cat)) {
                                <span class="cell-icon">T</span>
                              } @else {
                                <span class="cell-icon empty">&middot;</span>
                              }
                            </td>
                          }
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
                <div class="constraints-legend">
                  <span class="legend-item"><span class="legend-box src"></span> Source allowed</span>
                  <span class="legend-item"><span class="legend-box tgt"></span> Target allowed</span>
                  <span class="legend-item"><span class="legend-box both"></span> Both</span>
                  <span class="legend-item"><span class="legend-box empty-box"></span> No constraint</span>
                </div>
              </div>
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
                <button class="btn btn-secondary" (click)="editType(t)">Edit Type</button>
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
    .explorer { padding: 0; }
    .page-header { margin-bottom: 1.5rem; }
    .header-top { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.375rem; }
    .header-top h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-actions { display: flex; gap: 0.5rem; }

    .stats-bar { display: flex; gap: 0.25rem; font-size: 0.8125rem; color: #64748b; margin-bottom: 0.75rem; }
    .stat-sep { color: #cbd5e1; }

    .toolbar { display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; }

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

    .btn { font-family: inherit; font-size: 0.8125rem; font-weight: 500; border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem; border: none; transition: all 0.15s; }
    .btn-sm { font-size: 0.75rem; padding: 0.375rem 0.875rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; }
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

    /* Constraints view */
    .constraints-section { display: flex; flex-direction: column; gap: 1rem; }
    .constraints-toolbar { display: flex; gap: 0.75rem; align-items: center; }
    .domain-filter {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; color: #374151; background: #fff; outline: none; font-family: inherit;
    }
    .constraint-matrix { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .constraint-matrix th, .constraint-matrix td {
      border: 1px solid #e2e8f0; padding: 0.375rem 0.5rem; text-align: center;
    }
    .constraint-matrix th { background: #f8fafc; font-weight: 600; color: #374151; }
    .sticky-col { text-align: left; min-width: 120px; background: #fff; }
    .cat-name { font-weight: 500; color: #1e293b; }
    .rt-header { min-width: 100px; font-size: 0.75rem; }
    .rt-name { display: block; }
    .rt-domain { font-size: 0.625rem; }
    .cell { cursor: default; }
    .cell.editable { cursor: pointer; transition: background 0.15s, opacity 0.15s; }
    .cell.editable:hover { filter: brightness(0.95); }
    .cell.src { background: #dbeafe; }
    .cell.tgt { background: #fef3c7; }
    .cell.both { background: #d1fae5; }
    .cell.saving { opacity: 0.6; pointer-events: none; }
    .cell-icon { font-size: 0.75rem; font-weight: 600; }
    .cell-icon.empty { color: #cbd5e1; font-size: 1rem; }
    .cell-icon.saving-icon { font-size: 0.75rem; }
    .toolbar-hint { font-size: 0.75rem; color: #94a3b8; font-style: italic; }
    .constraints-legend {
      display: flex; gap: 1.25rem; align-items: center; font-size: 0.75rem; color: #64748b;
    }
    .legend-item { display: flex; align-items: center; gap: 0.375rem; }
    .legend-box {
      width: 14px; height: 14px; border-radius: 3px; border: 1px solid #e2e8f0;
    }
    .legend-box.src { background: #dbeafe; }
    .legend-box.tgt { background: #fef3c7; }
    .legend-box.both { background: #d1fae5; }
    .legend-box.empty-box { background: #fff; }

  `],
})
export class SemanticExplorerComponent implements OnInit {
  private semanticService = inject(SemanticService);
  private cmdbService = inject(CmdbService);
  private permissionCheck = inject(PermissionCheckService);
  private toast = inject(ToastService);
  private dialogService = inject(DialogService);
  private confirmService = inject(ConfirmService);
  private route = inject(ActivatedRoute);

  activeView = signal<ViewMode>('catalog');
  loading = signal(true);
  categories = signal<SemanticCategoryWithTypes[]>([]);
  relationshipKinds = signal<SemanticRelationshipKind[]>([]);
  providers = signal<SemanticProvider[]>([]);
  searchTerm = signal('');
  categoryFilter = signal('');
  selectedType = signal<SemanticResourceType | null>(null);
  // Constraints tab
  relationshipTypes = signal<RelationshipType[]>([]);
  constraintDomainFilter = signal<string>('');
  savingConstraints = signal<Set<string>>(new Set());

  private readonly viewTitles: Record<ViewMode, string> = {
    catalog: 'Semantic Catalog',
    relationships: 'Relationship Kinds',
    constraints: 'Constraints Matrix',
  };

  pageTitle = computed(() => this.viewTitles[this.activeView()] || 'Semantic Explorer');

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

  // Constraint computed properties
  filteredRelTypes = computed(() => {
    const domain = this.constraintDomainFilter();
    const types = this.relationshipTypes();
    if (!domain) return types;
    return types.filter((t) => t.domain === domain);
  });

  constraintCategories = computed(() => {
    const cats = this.categories().map((c) => c.name);
    return cats.sort();
  });

  ngOnInit(): void {
    const view = this.route.snapshot.data['view'] as ViewMode | undefined;
    if (view) {
      this.switchView(view);
    } else {
      this.switchView('catalog');
    }
  }

  switchView(view: ViewMode): void {
    this.activeView.set(view);
    this.selectedType.set(null);
    this.loadData();
    if (view === 'constraints') {
      this.loadRelationshipTypes();
    }
  }

  // -- Constraint helpers ---------------------------------------------------

  isCategoryInConstraint(constraintList: string[] | null, category: string): boolean {
    if (!constraintList) return false;
    return constraintList.includes(category);
  }

  constraintCellTitle(rt: RelationshipType, category: string): string {
    const parts: string[] = [];
    if (this.isCategoryInConstraint(rt.sourceSemanticCategories, category)) parts.push('Source');
    if (this.isCategoryInConstraint(rt.targetSemanticCategories, category)) parts.push('Target');
    return parts.length > 0 ? `${rt.displayName}: ${parts.join(' + ')} for ${category}` : `${rt.displayName}: No constraint for ${category}`;
  }

  isSavingConstraint(rtId: string, category: string): boolean {
    return this.savingConstraints().has(`${rtId}:${category}`);
  }

  cycleConstraint(rt: RelationshipType, category: string): void {
    const key = `${rt.id}:${category}`;
    if (this.savingConstraints().has(key)) return;

    const isSrc = this.isCategoryInConstraint(rt.sourceSemanticCategories, category);
    const isTgt = this.isCategoryInConstraint(rt.targetSemanticCategories, category);

    // Cycle: none → S → T → S+T → none
    let addSrc = false;
    let addTgt = false;
    if (!isSrc && !isTgt) {
      addSrc = true; addTgt = false;    // → S
    } else if (isSrc && !isTgt) {
      addSrc = false; addTgt = true;    // → T
    } else if (!isSrc && isTgt) {
      addSrc = true; addTgt = true;     // → S+T
    } else {
      addSrc = false; addTgt = false;   // → none
    }

    const newSrcCats = this.toggleCategory(rt.sourceSemanticCategories, category, addSrc);
    const newTgtCats = this.toggleCategory(rt.targetSemanticCategories, category, addTgt);

    // Mark saving
    const saving = new Set(this.savingConstraints());
    saving.add(key);
    this.savingConstraints.set(saving);

    this.cmdbService.updateRelationshipTypeConstraints(rt.id, {
      sourceSemanticCategories: newSrcCats.length > 0 ? newSrcCats : null,
      targetSemanticCategories: newTgtCats.length > 0 ? newTgtCats : null,
    }).subscribe({
      next: (updated) => {
        // Update the local relationship types array
        const types = this.relationshipTypes().map((t) =>
          t.id === updated.id ? updated : t,
        );
        this.relationshipTypes.set(types);
        this.removeSavingKey(key);
      },
      error: (e: Error) => {
        this.toast.error(e.message);
        this.removeSavingKey(key);
      },
    });
  }

  private toggleCategory(
    existing: string[] | null,
    category: string,
    include: boolean,
  ): string[] {
    const list = existing ? [...existing] : [];
    const idx = list.indexOf(category);
    if (include && idx === -1) {
      list.push(category);
    } else if (!include && idx !== -1) {
      list.splice(idx, 1);
    }
    return list;
  }

  private removeSavingKey(key: string): void {
    const saving = new Set(this.savingConstraints());
    saving.delete(key);
    this.savingConstraints.set(saving);
  }

  selectType(t: SemanticResourceType): void {
    this.selectedType.set(t);
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

  private loadRelationshipTypes(): void {
    this.cmdbService.listRelationshipTypes().subscribe({
      next: (types) => this.relationshipTypes.set(types),
    });
  }

}
