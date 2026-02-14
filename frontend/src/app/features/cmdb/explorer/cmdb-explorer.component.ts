/**
 * CMDB Explorer Component
 *
 * Overview:
 *   Interactive drill-down explorer for CMDB configuration items organized by
 *   semantic category -> type -> CI class hierarchy. Supports compartment and
 *   backend scoping, text search, tag filtering, and lifecycle state filtering.
 *
 * Architecture:
 *   See docs/architecture.md -- CMDB Core (Phase 8), Semantic Layer (Phase 5)
 *
 * Dependencies:
 *   - CmdbService: CI queries, compartment tree, explorer summary
 *   - CloudBackendService: Backend list for scoping
 *   - LayoutComponent: Page wrapper with header/sidebar
 *
 * Concepts:
 *   - Drill-down: Category -> Type -> CIs with breadcrumb navigation
 *   - Scoping: Compartment and backend filters narrow all queries
 *   - Tags: JSONB key:value metadata on CIs, filterable via tag search
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
import { Router } from '@angular/router';
import { CmdbService } from '@core/services/cmdb.service';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';
import {
  ConfigurationItem,
  CompartmentNode,
  ExplorerSummary,
  ExplorerCategorySummary,
  ExplorerTypeSummary,
} from '@shared/models/cmdb.model';
import { CloudBackend } from '@shared/models/cloud-backend.model';

@Component({
  selector: 'nimbus-cmdb-explorer',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="explorer-page">
        <!-- Page header -->
        <div class="page-header">
          <h1>CMDB Explorer</h1>
          <div class="search-bar">
            <input
              type="text"
              class="search-input"
              placeholder="Search configuration items..."
              [ngModel]="searchQuery()"
              (ngModelChange)="onSearchChange($event)"
            />
            <div class="lifecycle-chips">
              @for (state of lifecycleStates; track state.value) {
                <button
                  class="chip"
                  [class.chip-active]="lifecycleFilter() === state.value"
                  (click)="setLifecycleFilter(state.value)"
                >
                  {{ state.label }}
                </button>
              }
            </div>
          </div>
        </div>

        <!-- Active filter pills -->
        @if (hasActiveFilters()) {
          <div class="active-filters">
            @if (selectedCompartmentId()) {
              <span class="filter-pill">
                Compartment: {{ selectedCompartmentName() }}
                <button class="pill-close" (click)="clearCompartmentFilter()">&times;</button>
              </span>
            }
            @if (selectedBackendId()) {
              <span class="filter-pill">
                Backend: {{ selectedBackendName() }}
                <button class="pill-close" (click)="clearBackendFilter()">&times;</button>
              </span>
            }
            @if (searchQuery()) {
              <span class="filter-pill">
                Search: {{ searchQuery() }}
                <button class="pill-close" (click)="clearSearch()">&times;</button>
              </span>
            }
            @if (lifecycleFilter()) {
              <span class="filter-pill">
                State: {{ lifecycleFilter() }}
                <button class="pill-close" (click)="setLifecycleFilter('')">&times;</button>
              </span>
            }
            @for (entry of tagFilterEntries(); track entry.key) {
              <span class="filter-pill">
                Tag: {{ entry.key }}={{ entry.value }}
                <button class="pill-close" (click)="removeTagFilter(entry.key)">&times;</button>
              </span>
            }
          </div>
        }

        <!-- Tag filter bar -->
        <div class="tag-filter-bar">
          <input
            type="text"
            class="tag-input"
            placeholder="Add tag filter (key:value)..."
            [ngModel]="tagInput()"
            (ngModelChange)="tagInput.set($event)"
            (keydown.enter)="addTagFilterFromInput()"
          />
          @if (tagInput()) {
            <button class="btn btn-sm btn-secondary" (click)="addTagFilterFromInput()">Add Tag</button>
          }
        </div>

        <div class="explorer-body">
          <!-- Left panel -->
          <div class="left-panel">
            <!-- Compartments section -->
            <div class="panel-section">
              <div class="section-header">
                <h3>Compartments</h3>
              </div>
              <div class="section-body">
                @if (compartmentTree().length === 0) {
                  <div class="empty-hint">No compartments</div>
                } @else {
                  @for (node of compartmentTree(); track node.id) {
                    <ng-container *ngTemplateOutlet="compartmentNodeTpl; context: { $implicit: node, depth: 0 }"></ng-container>
                  }
                }
              </div>
            </div>

            <!-- Backends section -->
            <div class="panel-section">
              <div class="section-header">
                <h3>Backends</h3>
              </div>
              <div class="section-body">
                @if (backends().length === 0) {
                  <div class="empty-hint">No backends</div>
                } @else {
                  @for (backend of backends(); track backend.id) {
                    <div
                      class="backend-item"
                      [class.selected]="selectedBackendId() === backend.id"
                      (click)="selectBackend(backend.id, backend.name)"
                    >
                      <span
                        class="status-dot"
                        [class.status-active]="backend.status === 'active'"
                        [class.status-error]="backend.status === 'error'"
                        [class.status-disabled]="backend.status === 'disabled'"
                      ></span>
                      <span class="backend-name">{{ backend.name }}</span>
                      <span class="backend-provider">{{ backend.providerDisplayName }}</span>
                    </div>
                  }
                }
              </div>
            </div>
          </div>

          <!-- Main content -->
          <div class="main-content">
            <!-- Breadcrumb -->
            <div class="breadcrumb">
              <button
                class="breadcrumb-item"
                [class.breadcrumb-active]="currentLevel() === 'categories'"
                (click)="drillBack('categories')"
              >
                All Categories
              </button>
              @if (selectedCategory()) {
                <span class="breadcrumb-sep">/</span>
                <button
                  class="breadcrumb-item"
                  [class.breadcrumb-active]="currentLevel() === 'types'"
                  (click)="drillBack('types')"
                >
                  {{ selectedCategory()!.categoryName }}
                </button>
              }
              @if (selectedType()) {
                <span class="breadcrumb-sep">/</span>
                <span class="breadcrumb-item breadcrumb-active">
                  {{ selectedType()!.ciClassName }}
                </span>
              }
            </div>

            @if (loading()) {
              <div class="loading">Loading...</div>
            }

            <!-- Level 0: Category cards -->
            @if (!loading() && currentLevel() === 'categories') {
              @if (summary()) {
                <div class="summary-bar">
                  <span class="summary-total">{{ summary()!.totalCis }} Configuration Items</span>
                </div>
                @if (summary()!.categories.length === 0) {
                  <div class="empty-state">No categories found. Create CI classes and semantic types first.</div>
                } @else {
                  <div class="card-grid">
                    @for (cat of summary()!.categories; track cat.categoryId ?? cat.categoryName) {
                      <div class="category-card" (click)="selectCategory(cat)">
                        <div class="card-header">
                          @if (cat.categoryIcon) {
                            <span class="card-icon">{{ cat.categoryIcon }}</span>
                          }
                          <h3 class="card-title">{{ cat.categoryName }}</h3>
                        </div>
                        <div class="card-stats">
                          <div class="stat">
                            <span class="stat-value">{{ cat.types.length }}</span>
                            <span class="stat-label">Types</span>
                          </div>
                          <div class="stat">
                            <span class="stat-value">{{ cat.totalCount }}</span>
                            <span class="stat-label">CIs</span>
                          </div>
                        </div>
                      </div>
                    }
                  </div>
                }
              }
            }

            <!-- Level 1: Types in selected category -->
            @if (!loading() && currentLevel() === 'types' && selectedCategory()) {
              @if (selectedCategory()!.types.length === 0) {
                <div class="empty-state">No types in this category.</div>
              } @else {
                <div class="type-list">
                  @for (type of selectedCategory()!.types; track type.ciClassId) {
                    <div class="type-row" (click)="selectType(type)">
                      <div class="type-info">
                        @if (type.ciClassIcon) {
                          <span class="type-icon">{{ type.ciClassIcon }}</span>
                        }
                        <div class="type-names">
                          <span class="type-class-name">{{ type.ciClassName }}</span>
                          @if (type.semanticTypeName) {
                            <span class="type-semantic-name">{{ type.semanticTypeName }}</span>
                          }
                        </div>
                      </div>
                      <div class="type-count">
                        <span class="count-value">{{ type.count }}</span>
                        <span class="count-label">CIs</span>
                      </div>
                    </div>
                  }
                </div>
              }
            }

            <!-- Level 2: CI table -->
            @if (!loading() && currentLevel() === 'cis') {
              <div class="ci-table-header">
                <span class="ci-total">{{ ciTotal() }} Configuration Items</span>
                <div class="ci-pagination">
                  <button
                    class="btn btn-sm btn-secondary"
                    [disabled]="ciOffset() === 0"
                    (click)="prevPage()"
                  >Previous</button>
                  <span class="page-info">
                    {{ ciOffset() + 1 }}--{{ Math.min(ciOffset() + ciLimit(), ciTotal()) }}
                    of {{ ciTotal() }}
                  </span>
                  <button
                    class="btn btn-sm btn-secondary"
                    [disabled]="ciOffset() + ciLimit() >= ciTotal()"
                    (click)="nextPage()"
                  >Next</button>
                </div>
              </div>

              @if (cis().length === 0) {
                <div class="empty-state">No configuration items found.</div>
              } @else {
                <div class="table-container">
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Class</th>
                        <th>Lifecycle State</th>
                        <th>Tags</th>
                        <th>Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (ci of cis(); track ci.id) {
                        <tr class="ci-row" (click)="navigateToCI(ci.id)">
                          <td class="ci-name">{{ ci.name }}</td>
                          <td>{{ ci.ciClassName }}</td>
                          <td>
                            <span
                              class="lifecycle-badge"
                              [class.lifecycle-active]="ci.lifecycleState === 'active'"
                              [class.lifecycle-planned]="ci.lifecycleState === 'planned'"
                              [class.lifecycle-maintenance]="ci.lifecycleState === 'maintenance'"
                              [class.lifecycle-retired]="ci.lifecycleState === 'retired'"
                            >
                              {{ ci.lifecycleState }}
                            </span>
                          </td>
                          <td class="ci-tags">
                            @if (ci.tags && objectKeys(ci.tags).length > 0) {
                              @for (key of objectKeys(ci.tags).slice(0, 3); track key) {
                                <span class="tag-pill">{{ key }}={{ ci.tags[key] }}</span>
                              }
                              @if (objectKeys(ci.tags).length > 3) {
                                <span class="tag-more">+{{ objectKeys(ci.tags).length - 3 }}</span>
                              }
                            } @else {
                              <span class="muted">--</span>
                            }
                          </td>
                          <td class="ci-updated">{{ formatDate(ci.updatedAt) }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            }
          </div>
        </div>
      </div>

      <!-- Compartment tree node template (recursive via ngTemplateOutlet) -->
      <ng-template #compartmentNodeTpl let-node let-depth="depth">
        <div
          class="compartment-item"
          [style.padding-left]="(depth * 1.25 + 0.75) + 'rem'"
          [class.selected]="selectedCompartmentId() === node.id"
          (click)="selectCompartment(node.id, node.name)"
        >
          @if (node.children && node.children.length > 0) {
            <button class="expand-btn" (click)="toggleCompartment($event, node.id)">
              {{ isCompartmentExpanded(node.id) ? '&#9662;' : '&#9656;' }}
            </button>
          } @else {
            <span class="expand-spacer"></span>
          }
          <span class="compartment-name">{{ node.name }}</span>
        </div>
        @if (node.children && node.children.length > 0 && isCompartmentExpanded(node.id)) {
          @for (child of node.children; track child.id) {
            <ng-container *ngTemplateOutlet="compartmentNodeTpl; context: { $implicit: child, depth: depth + 1 }"></ng-container>
          }
        }
      </ng-template>
    </nimbus-layout>
  `,
  styles: [`
    /* ── Page Layout ──────────────────────────────────────────────── */
    .explorer-page {
      display: flex;
      flex-direction: column;
      height: 100%;
      min-height: 0;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 1.5rem;
      margin-bottom: 1.5rem;
      flex-wrap: wrap;
    }
    .page-header h1 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 700;
      color: #1e293b;
    }

    /* ── Search Bar ───────────────────────────────────────────────── */
    .search-bar {
      display: flex;
      flex-direction: column;
      gap: 0.5rem;
      flex: 1;
      max-width: 600px;
    }
    .search-input {
      width: 100%;
      padding: 0.5rem 0.75rem;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-family: inherit;
      box-sizing: border-box;
      transition: border-color 0.15s;
    }
    .search-input:focus {
      border-color: #3b82f6;
      outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    .lifecycle-chips {
      display: flex;
      gap: 0.375rem;
      flex-wrap: wrap;
    }
    .chip {
      font-family: inherit;
      font-size: 0.6875rem;
      font-weight: 500;
      padding: 0.25rem 0.625rem;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      background: #fff;
      color: #64748b;
      cursor: pointer;
      transition: all 0.15s;
    }
    .chip:hover {
      background: #f1f5f9;
      border-color: #cbd5e1;
    }
    .chip-active {
      background: #eff6ff;
      border-color: #3b82f6;
      color: #2563eb;
    }

    /* ── Tag filter bar ───────────────────────────────────────────── */
    .tag-filter-bar {
      display: flex;
      gap: 0.5rem;
      align-items: center;
      margin-bottom: 0.75rem;
    }
    .tag-input {
      width: 240px;
      padding: 0.375rem 0.625rem;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.75rem;
      font-family: inherit;
      box-sizing: border-box;
    }
    .tag-input:focus {
      border-color: #3b82f6;
      outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
    }

    /* ── Active Filters ───────────────────────────────────────────── */
    .active-filters {
      display: flex;
      gap: 0.5rem;
      flex-wrap: wrap;
      margin-bottom: 0.75rem;
    }
    .filter-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.375rem;
      padding: 0.25rem 0.625rem;
      background: #eff6ff;
      color: #2563eb;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 500;
    }
    .pill-close {
      font-family: inherit;
      font-size: 0.8125rem;
      background: none;
      border: none;
      color: #2563eb;
      cursor: pointer;
      padding: 0;
      line-height: 1;
      font-weight: 600;
    }
    .pill-close:hover {
      color: #1d4ed8;
    }

    /* ── Explorer Body (3-panel) ──────────────────────────────────── */
    .explorer-body {
      display: flex;
      flex: 1;
      min-height: 0;
      gap: 0;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      background: #fff;
    }

    /* ── Left Panel ───────────────────────────────────────────────── */
    .left-panel {
      width: 280px;
      min-width: 280px;
      border-right: 1px solid #e2e8f0;
      background: #fff;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
    }

    .panel-section {
      border-bottom: 1px solid #e2e8f0;
    }
    .panel-section:last-child {
      border-bottom: none;
      flex: 1;
    }

    .section-header {
      padding: 0.75rem 1rem 0.5rem;
    }
    .section-header h3 {
      margin: 0;
      font-size: 0.6875rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #64748b;
    }

    .section-body {
      padding: 0 0 0.5rem;
    }

    .empty-hint {
      padding: 0.5rem 1rem;
      font-size: 0.75rem;
      color: #94a3b8;
    }

    /* ── Compartment Tree ─────────────────────────────────────────── */
    .compartment-item {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      padding: 0.375rem 0.75rem;
      cursor: pointer;
      font-size: 0.8125rem;
      color: #475569;
      transition: background 0.1s;
    }
    .compartment-item:hover {
      background: #f1f5f9;
    }
    .compartment-item.selected {
      background: #eff6ff;
      color: #2563eb;
      font-weight: 500;
    }

    .expand-btn {
      font-family: inherit;
      background: none;
      border: none;
      cursor: pointer;
      padding: 0;
      font-size: 0.625rem;
      color: #94a3b8;
      width: 1rem;
      text-align: center;
      flex-shrink: 0;
    }
    .expand-spacer {
      width: 1rem;
      flex-shrink: 0;
    }
    .compartment-name {
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    /* ── Backend List ─────────────────────────────────────────────── */
    .backend-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.4375rem 1rem;
      cursor: pointer;
      font-size: 0.8125rem;
      color: #475569;
      transition: background 0.1s;
    }
    .backend-item:hover {
      background: #f1f5f9;
    }
    .backend-item.selected {
      background: #eff6ff;
      color: #2563eb;
      font-weight: 500;
    }

    .status-dot {
      width: 8px;
      height: 8px;
      border-radius: 50%;
      flex-shrink: 0;
      background: #94a3b8;
    }
    .status-dot.status-active { background: #22c55e; }
    .status-dot.status-error { background: #ef4444; }
    .status-dot.status-disabled { background: #94a3b8; }

    .backend-name {
      flex: 1;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .backend-provider {
      font-size: 0.6875rem;
      color: #94a3b8;
      flex-shrink: 0;
    }

    /* ── Main Content ─────────────────────────────────────────────── */
    .main-content {
      flex: 1;
      padding: 1.5rem;
      overflow-y: auto;
      background: #fafbfc;
    }

    /* ── Breadcrumb ───────────────────────────────────────────────── */
    .breadcrumb {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      margin-bottom: 1.25rem;
    }
    .breadcrumb-item {
      font-family: inherit;
      font-size: 0.8125rem;
      font-weight: 500;
      background: none;
      border: none;
      padding: 0.25rem 0.375rem;
      border-radius: 4px;
      cursor: pointer;
      color: #3b82f6;
      transition: background 0.1s;
    }
    .breadcrumb-item:hover {
      background: #eff6ff;
    }
    .breadcrumb-active {
      color: #1e293b;
      cursor: default;
    }
    .breadcrumb-active:hover {
      background: none;
    }
    .breadcrumb-sep {
      color: #94a3b8;
      font-size: 0.8125rem;
    }

    .loading, .empty-state {
      padding: 3rem;
      text-align: center;
      color: #64748b;
      font-size: 0.875rem;
    }

    .summary-bar {
      margin-bottom: 1rem;
    }
    .summary-total {
      font-size: 0.8125rem;
      font-weight: 600;
      color: #64748b;
    }

    /* ── Category Cards (grid) ────────────────────────────────────── */
    .card-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 1rem;
    }
    @media (max-width: 1200px) {
      .card-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 900px) {
      .card-grid { grid-template-columns: 1fr; }
    }

    .category-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.25rem;
      cursor: pointer;
      transition: box-shadow 0.15s, border-color 0.15s;
    }
    .category-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
      border-color: #cbd5e1;
    }

    .card-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }
    .card-icon {
      font-size: 1.125rem;
      color: #3b82f6;
    }
    .card-title {
      margin: 0;
      font-size: 0.9375rem;
      font-weight: 600;
      color: #1e293b;
    }

    .card-stats {
      display: flex;
      gap: 2rem;
    }
    .stat {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }
    .stat-value {
      font-size: 1.25rem;
      font-weight: 700;
      color: #1e293b;
    }
    .stat-label {
      font-size: 0.6875rem;
      font-weight: 500;
      color: #64748b;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    /* ── Type List (Level 1) ──────────────────────────────────────── */
    .type-list {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .type-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.875rem 1.25rem;
      border-bottom: 1px solid #f1f5f9;
      cursor: pointer;
      transition: background 0.1s;
    }
    .type-row:last-child {
      border-bottom: none;
    }
    .type-row:hover {
      background: #f8fafc;
    }

    .type-info {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    .type-icon {
      font-size: 1rem;
      color: #3b82f6;
    }
    .type-names {
      display: flex;
      flex-direction: column;
      gap: 0.125rem;
    }
    .type-class-name {
      font-size: 0.875rem;
      font-weight: 500;
      color: #1e293b;
    }
    .type-semantic-name {
      font-size: 0.6875rem;
      color: #64748b;
    }

    .type-count {
      display: flex;
      align-items: center;
      gap: 0.375rem;
    }
    .count-value {
      font-size: 1rem;
      font-weight: 700;
      color: #1e293b;
    }
    .count-label {
      font-size: 0.6875rem;
      color: #64748b;
    }

    /* ── CI Table (Level 2) ───────────────────────────────────────── */
    .ci-table-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.75rem;
    }
    .ci-total {
      font-size: 0.8125rem;
      font-weight: 600;
      color: #64748b;
    }
    .ci-pagination {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    .page-info {
      font-size: 0.75rem;
      color: #64748b;
    }

    .table-container {
      overflow-x: auto;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #fff;
    }
    .table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.625rem 0.75rem;
      text-align: left;
      border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600;
      color: #64748b;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      background: #fafbfc;
    }
    .table tbody tr:last-child td {
      border-bottom: none;
    }
    .table tbody tr:nth-child(even) {
      background: #f8fafc;
    }
    .table tbody tr:hover {
      background: #f1f5f9;
    }

    .ci-row {
      cursor: pointer;
    }
    .ci-name {
      font-weight: 500;
      color: #1e293b;
    }
    .ci-updated {
      font-size: 0.75rem;
      color: #64748b;
    }

    .lifecycle-badge {
      display: inline-block;
      padding: 0.125rem 0.5rem;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: capitalize;
      background: #f1f5f9;
      color: #64748b;
    }
    .lifecycle-active { background: #dcfce7; color: #166534; }
    .lifecycle-planned { background: #dbeafe; color: #1d4ed8; }
    .lifecycle-maintenance { background: #fef3c7; color: #92400e; }
    .lifecycle-retired { background: #fef2f2; color: #dc2626; }

    .ci-tags {
      display: flex;
      gap: 0.25rem;
      flex-wrap: wrap;
      align-items: center;
    }
    .tag-pill {
      display: inline-block;
      padding: 0.0625rem 0.375rem;
      background: #f1f5f9;
      color: #475569;
      border-radius: 4px;
      font-size: 0.625rem;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .tag-more {
      font-size: 0.625rem;
      color: #94a3b8;
    }

    .muted {
      color: #94a3b8;
    }

    /* ── Buttons ──────────────────────────────────────────────────── */
    .btn {
      font-family: inherit;
      font-size: 0.8125rem;
      font-weight: 500;
      border-radius: 6px;
      cursor: pointer;
      padding: 0.5rem 1rem;
      transition: background 0.15s;
      border: none;
    }
    .btn-sm {
      font-size: 0.75rem;
      padding: 0.3125rem 0.625rem;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff;
      color: #374151;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class CmdbExplorerComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private cloudBackendService = inject(CloudBackendService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  // Expose Math to the template
  Math = Math;

  // ── Drill-down state ──────────────────────────────────────────────
  currentLevel = signal<'categories' | 'types' | 'cis'>('categories');
  selectedCategory = signal<ExplorerCategorySummary | null>(null);
  selectedType = signal<ExplorerTypeSummary | null>(null);

  // ── Filters ───────────────────────────────────────────────────────
  selectedCompartmentId = signal<string | null>(null);
  selectedCompartmentName = signal<string>('');
  selectedBackendId = signal<string | null>(null);
  selectedBackendName = signal<string>('');
  searchQuery = signal('');
  lifecycleFilter = signal<string>('');
  tagFilters = signal<Record<string, string>>({});
  tagInput = signal('');

  // ── Data ──────────────────────────────────────────────────────────
  summary = signal<ExplorerSummary | null>(null);
  compartmentTree = signal<CompartmentNode[]>([]);
  backends = signal<CloudBackend[]>([]);
  cis = signal<ConfigurationItem[]>([]);
  ciTotal = signal(0);
  ciOffset = signal(0);
  ciLimit = signal(25);

  // ── UI state ──────────────────────────────────────────────────────
  loading = signal(false);
  expandedCompartments = signal<Set<string>>(new Set());

  private searchDebounceTimer: ReturnType<typeof setTimeout> | null = null;

  lifecycleStates = [
    { label: 'All', value: '' },
    { label: 'Active', value: 'active' },
    { label: 'Planned', value: 'planned' },
    { label: 'Maintenance', value: 'maintenance' },
    { label: 'Retired', value: 'retired' },
  ];

  tagFilterEntries = computed(() => {
    const filters = this.tagFilters();
    return Object.entries(filters).map(([key, value]) => ({ key, value }));
  });

  hasActiveFilters = computed(() => {
    return !!(
      this.selectedCompartmentId() ||
      this.selectedBackendId() ||
      this.searchQuery() ||
      this.lifecycleFilter() ||
      Object.keys(this.tagFilters()).length > 0
    );
  });

  ngOnInit(): void {
    this.loadCompartments();
    this.loadBackends();
    this.loadSummary();
  }

  // ── Data Loading ──────────────────────────────────────────────────

  loadSummary(): void {
    this.loading.set(true);
    this.cmdbService.getExplorerSummary(
      this.selectedCompartmentId() ?? undefined,
      this.selectedBackendId() ?? undefined,
    ).subscribe({
      next: (summary) => {
        this.summary.set(summary);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load explorer summary');
      },
    });
  }

  private loadCompartments(): void {
    this.cmdbService.getCompartmentTree().subscribe({
      next: (tree) => this.compartmentTree.set(tree),
      error: () => this.toastService.error('Failed to load compartments'),
    });
  }

  private loadBackends(): void {
    this.cloudBackendService.listBackends().subscribe({
      next: (backends) => this.backends.set(backends),
      error: () => this.toastService.error('Failed to load backends'),
    });
  }

  loadCIs(): void {
    this.loading.set(true);
    const type = this.selectedType();
    this.cmdbService.listCIs({
      ciClassId: type?.ciClassId ?? undefined,
      compartmentId: this.selectedCompartmentId() ?? undefined,
      lifecycleState: this.lifecycleFilter() || undefined,
      search: this.searchQuery() || undefined,
      offset: this.ciOffset(),
      limit: this.ciLimit(),
    }).subscribe({
      next: (result) => {
        this.cis.set(result.items);
        this.ciTotal.set(result.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load configuration items');
      },
    });
  }

  // ── Drill-down Navigation ─────────────────────────────────────────

  selectCategory(cat: ExplorerCategorySummary): void {
    this.selectedCategory.set(cat);
    this.selectedType.set(null);
    this.currentLevel.set('types');
  }

  selectType(type: ExplorerTypeSummary): void {
    this.selectedType.set(type);
    this.currentLevel.set('cis');
    this.ciOffset.set(0);
    this.loadCIs();
  }

  drillBack(level: 'categories' | 'types'): void {
    if (level === 'categories') {
      this.selectedCategory.set(null);
      this.selectedType.set(null);
      this.currentLevel.set('categories');
      this.cis.set([]);
    } else if (level === 'types') {
      this.selectedType.set(null);
      this.currentLevel.set('types');
      this.cis.set([]);
    }
  }

  // ── Compartment Selection ─────────────────────────────────────────

  selectCompartment(id: string, name: string): void {
    if (this.selectedCompartmentId() === id) {
      this.clearCompartmentFilter();
      return;
    }
    this.selectedCompartmentId.set(id);
    this.selectedCompartmentName.set(name);
    this.resetToCategories();
    this.loadSummary();
  }

  clearCompartmentFilter(): void {
    this.selectedCompartmentId.set(null);
    this.selectedCompartmentName.set('');
    this.resetToCategories();
    this.loadSummary();
  }

  toggleCompartment(event: Event, id: string): void {
    event.stopPropagation();
    const current = this.expandedCompartments();
    const next = new Set(current);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    this.expandedCompartments.set(next);
  }

  isCompartmentExpanded(id: string): boolean {
    return this.expandedCompartments().has(id);
  }

  // ── Backend Selection ─────────────────────────────────────────────

  selectBackend(id: string, name: string): void {
    if (this.selectedBackendId() === id) {
      this.clearBackendFilter();
      return;
    }
    this.selectedBackendId.set(id);
    this.selectedBackendName.set(name);
    this.resetToCategories();
    this.loadSummary();
  }

  clearBackendFilter(): void {
    this.selectedBackendId.set(null);
    this.selectedBackendName.set('');
    this.resetToCategories();
    this.loadSummary();
  }

  // ── Search ────────────────────────────────────────────────────────

  onSearchChange(query: string): void {
    this.searchQuery.set(query);
    if (this.searchDebounceTimer) {
      clearTimeout(this.searchDebounceTimer);
    }
    this.searchDebounceTimer = setTimeout(() => {
      if (this.currentLevel() === 'cis') {
        this.ciOffset.set(0);
        this.loadCIs();
      }
    }, 300);
  }

  clearSearch(): void {
    this.searchQuery.set('');
    if (this.currentLevel() === 'cis') {
      this.ciOffset.set(0);
      this.loadCIs();
    }
  }

  // ── Lifecycle Filter ──────────────────────────────────────────────

  setLifecycleFilter(state: string): void {
    this.lifecycleFilter.set(state);
    if (this.currentLevel() === 'cis') {
      this.ciOffset.set(0);
      this.loadCIs();
    }
  }

  // ── Tag Filters ───────────────────────────────────────────────────

  addTagFilterFromInput(): void {
    const raw = this.tagInput().trim();
    if (!raw) return;
    const colonIdx = raw.indexOf(':');
    if (colonIdx <= 0) {
      this.toastService.error('Tag filter must be in key:value format');
      return;
    }
    const key = raw.substring(0, colonIdx).trim();
    const value = raw.substring(colonIdx + 1).trim();
    if (!key || !value) {
      this.toastService.error('Tag filter must have both key and value');
      return;
    }
    this.addTagFilter(key, value);
    this.tagInput.set('');
  }

  addTagFilter(key: string, value: string): void {
    const current = { ...this.tagFilters() };
    current[key] = value;
    this.tagFilters.set(current);
    if (this.currentLevel() === 'cis') {
      this.ciOffset.set(0);
      this.loadCIs();
    }
  }

  removeTagFilter(key: string): void {
    const current = { ...this.tagFilters() };
    delete current[key];
    this.tagFilters.set(current);
    if (this.currentLevel() === 'cis') {
      this.ciOffset.set(0);
      this.loadCIs();
    }
  }

  // ── Pagination ────────────────────────────────────────────────────

  nextPage(): void {
    if (this.ciOffset() + this.ciLimit() < this.ciTotal()) {
      this.ciOffset.set(this.ciOffset() + this.ciLimit());
      this.loadCIs();
    }
  }

  prevPage(): void {
    if (this.ciOffset() > 0) {
      this.ciOffset.set(Math.max(0, this.ciOffset() - this.ciLimit()));
      this.loadCIs();
    }
  }

  // ── Navigation ────────────────────────────────────────────────────

  navigateToCI(id: string): void {
    this.router.navigate(['/cmdb', id]);
  }

  // ── Helpers ───────────────────────────────────────────────────────

  objectKeys(obj: Record<string, unknown>): string[] {
    return Object.keys(obj);
  }

  formatDate(isoString: string): string {
    if (!isoString) return '--';
    const date = new Date(isoString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  }

  private resetToCategories(): void {
    this.selectedCategory.set(null);
    this.selectedType.set(null);
    this.currentLevel.set('categories');
    this.cis.set([]);
  }
}
