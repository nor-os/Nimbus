/**
 * Overview: Audit log explorer with taxonomy filter tree, context menus, active filter bar, and trace view.
 * Architecture: Feature component for audit log browsing (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/audit.service
 * Concepts: Audit logging, taxonomy filtering, context menus, trace visualization
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditService } from '@core/services/audit.service';
import { PermissionCheckService } from '@core/services/permission-check.service';
import {
  AuditLog,
  AuditSearchParams,
  SavedQuery,
  AuditPriority,
  TaxonomyResponse,
} from '@shared/models/audit.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';
import { FilterTreePopoverComponent, TreeNode } from '@shared/components/filter-tree-popover/filter-tree-popover.component';
import { ActiveFiltersBarComponent, ActiveFilter } from '@shared/components/active-filters-bar/active-filters-bar.component';
import { ContextMenuService, ContextMenuItem } from '@shared/services/context-menu.service';
import { AuditDetailComponent } from '../audit-detail/audit-detail.component';
import { TraceViewComponent } from '../trace-view/trace-view.component';

@Component({
  selector: 'nimbus-audit-explorer',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LayoutComponent,
    AuditDetailComponent,
    FilterTreePopoverComponent,
    ActiveFiltersBarComponent,
    TraceViewComponent,
  ],
  template: `
    <nimbus-layout>
      <div class="audit-page">
        <div class="page-header">
          <h1>Audit Log</h1>
          <div class="header-actions">
            <button class="btn btn-secondary" (click)="exportLogs('json')">Export JSON</button>
            <button class="btn btn-secondary" (click)="exportLogs('csv')">Export CSV</button>
          </div>
        </div>

        <!-- Filter bar -->
        <div class="filter-bar">
          <input
            type="text"
            [(ngModel)]="searchText"
            (ngModelChange)="onSearchChange()"
            placeholder="Search..."
            class="search-input"
          />
          <nimbus-filter-tree-popover
            [items]="taxonomyTree()"
            [selected]="selectedEventTypes()"
            label="Event Type"
            (selectionChange)="onEventTypesChange($event)"
          />
          <select [(ngModel)]="filterPriority" (ngModelChange)="onFilterChange()" class="filter-select">
            <option value="">All Priorities</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARN">WARN</option>
            <option value="ERR">ERR</option>
            <option value="CRITICAL">CRITICAL</option>
          </select>
          <input
            type="date"
            [(ngModel)]="filterDateFrom"
            (ngModelChange)="onFilterChange()"
            class="filter-input"
          />
          <input
            type="date"
            [(ngModel)]="filterDateTo"
            (ngModelChange)="onFilterChange()"
            class="filter-input"
          />
          <button class="btn btn-sm" (click)="clearFilters()">Clear</button>
        </div>

        <!-- Active filters bar -->
        <nimbus-active-filters-bar
          [filters]="activeFilters()"
          (removeFilter)="removeFilter($event)"
          (clearAll)="clearFilters()"
        />

        <!-- Saved queries -->
        @if (savedQueries().length > 0) {
          <div class="saved-queries">
            <span class="sq-label">Saved:</span>
            @for (sq of savedQueries(); track sq.id) {
              <button class="sq-chip" (click)="applySavedQuery(sq)">{{ sq.name }}</button>
            }
          </div>
        }

        <!-- Trace view overlay -->
        @if (traceViewId()) {
          <div class="trace-overlay">
            <div class="trace-overlay-header">
              <span>Trace View</span>
              <button class="close-btn" (click)="traceViewId.set(null)">&times;</button>
            </div>
            <nimbus-trace-view [traceId]="traceViewId()!" />
          </div>
        }

        <div class="content-area" [class.with-detail]="selectedLog()">
          <!-- Results table -->
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>Event</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>Priority</th>
                  <th>Trace</th>
                </tr>
              </thead>
              <tbody>
                @for (log of logs(); track log.id) {
                  <tr
                    [class.selected]="selectedLog()?.id === log.id"
                    (click)="selectLog(log)"
                  >
                    <td class="mono" (contextmenu)="onCellContext($event, log, 'timestamp')">
                      {{ log.created_at | date: 'short' }}
                    </td>
                    <td (contextmenu)="onCellContext($event, log, 'event')">
                      @if (log.event_type) {
                        <span class="event-type-badge">{{ log.event_type }}</span>
                      } @else {
                        <span class="badge" [class]="'badge-' + log.action.toLowerCase()">{{ log.action }}</span>
                      }
                    </td>
                    <td (contextmenu)="onCellContext($event, log, 'actor')">
                      {{ log.actor_email || '\u2014' }}
                    </td>
                    <td class="resource-cell" (contextmenu)="onCellContext($event, log, 'resource')">
                      {{ log.resource_type || '' }}
                      @if (log.resource_name) {
                        <span class="resource-name">{{ log.resource_name }}</span>
                      }
                    </td>
                    <td (contextmenu)="onCellContext($event, log, 'priority')">
                      <span class="priority" [class]="'priority-' + log.priority.toLowerCase()">{{ log.priority }}</span>
                    </td>
                    <td class="mono trace-cell" (contextmenu)="onCellContext($event, log, 'trace')">
                      @if (log.trace_id) {
                        <span class="trace-link" (click)="showTrace(log.trace_id!); $event.stopPropagation()">
                          {{ log.trace_id.substring(0, 8) }}...
                        </span>
                      } @else {
                        \u2014
                      }
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="empty-state">No audit logs found</td>
                  </tr>
                }
              </tbody>
            </table>

            <div class="pagination">
              <button
                class="btn btn-sm"
                [disabled]="currentOffset() === 0"
                (click)="prevPage()"
              >Previous</button>
              <span class="page-info">
                {{ currentOffset() + 1 }}\u2013{{ currentOffset() + logs().length }}
                of {{ totalLogs() }}
              </span>
              <button
                class="btn btn-sm"
                [disabled]="currentOffset() + logs().length >= totalLogs()"
                (click)="nextPage()"
              >Next</button>
            </div>
          </div>

          <!-- Detail panel -->
          @if (selectedLog()) {
            <div class="detail-pane">
              <nimbus-audit-detail
                [entry]="selectedLog()"
                (closed)="selectedLog.set(null)"
                (traceClicked)="filterByTrace($event)"
                (showTraceClicked)="showTrace($event)"
              />
            </div>
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .audit-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-actions { display: flex; gap: 0.5rem; }
    .filter-bar {
      display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center;
      margin-bottom: 0.5rem; padding: 0.75rem; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .search-input {
      padding: 0.375rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 6px;
      width: 200px; font-size: 0.8125rem; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; }
    .filter-select, .filter-input {
      padding: 0.375rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; font-family: inherit; background: #fff;
    }
    .filter-select:focus, .filter-input:focus { border-color: #3b82f6; outline: none; }
    .filter-input { width: 130px; }
    .saved-queries {
      display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem;
    }
    .sq-label { font-size: 0.75rem; color: #64748b; font-weight: 500; }
    .sq-chip {
      padding: 0.25rem 0.5rem; border: 1px solid #dbeafe; border-radius: 12px;
      background: #eff6ff; color: #1d4ed8; font-size: 0.6875rem; font-weight: 500;
      cursor: pointer; font-family: inherit;
    }
    .sq-chip:hover { background: #dbeafe; }
    .trace-overlay {
      margin-bottom: 1rem; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    }
    .trace-overlay-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.5rem 0.75rem; background: #f8fafc; border-bottom: 1px solid #e2e8f0;
      font-size: 0.8125rem; font-weight: 600; color: #475569;
    }
    .close-btn {
      background: none; border: none; font-size: 1.125rem; color: #64748b;
      cursor: pointer; padding: 0 0.25rem;
    }
    .content-area { display: flex; gap: 1rem; }
    .content-area.with-detail .table-container { flex: 1; min-width: 0; }
    .detail-pane { width: 420px; flex-shrink: 0; }
    .table-container {
      flex: 1; overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td { padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr { cursor: pointer; transition: background 0.1s; }
    .table tbody tr:hover { background: #f8fafc; }
    .table tbody tr.selected { background: #eff6ff; }
    .mono { font-family: monospace; font-size: 0.75rem; }
    .event-type-badge {
      font-family: monospace; font-size: 0.6875rem; background: #f0fdf4;
      color: #16a34a; padding: 0.125rem 0.5rem; border-radius: 6px; font-weight: 500;
    }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      background: #f1f5f9; color: #475569;
    }
    .badge-create { background: #dcfce7; color: #16a34a; }
    .badge-update { background: #fef3c7; color: #d97706; }
    .badge-delete { background: #fef2f2; color: #dc2626; }
    .badge-login { background: #dbeafe; color: #2563eb; }
    .badge-logout { background: #e0e7ff; color: #4f46e5; }
    .badge-read { background: #f0fdf4; color: #15803d; }
    .badge-permission_change { background: #fae8ff; color: #a855f7; }
    .badge-system { background: #f1f5f9; color: #475569; }
    .badge-export { background: #ecfdf5; color: #059669; }
    .badge-archive { background: #f5f3ff; color: #7c3aed; }
    .badge-break_glass { background: #fef2f2; color: #dc2626; }
    .badge-impersonate { background: #fff7ed; color: #ea580c; }
    .badge-override { background: #fef2f2; color: #dc2626; }
    .priority { font-size: 0.6875rem; font-weight: 600; }
    .priority-debug { color: #94a3b8; }
    .priority-info { color: #3b82f6; }
    .priority-warn { color: #f59e0b; }
    .priority-err { color: #dc2626; }
    .priority-critical { color: #dc2626; font-weight: 800; }
    .resource-cell { max-width: 200px; }
    .resource-name { display: block; color: #64748b; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .trace-cell { white-space: nowrap; }
    .trace-link { color: #3b82f6; cursor: pointer; text-decoration: underline; }
    .trace-link:hover { color: #2563eb; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; padding: 0.75rem;
    }
    .page-info { color: #64748b; font-size: 0.8125rem; }
    .btn {
      padding: 0.5rem 1rem; border: none;
      border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-weight: 500; font-family: inherit; transition: all 0.15s;
    }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class AuditExplorerComponent implements OnInit {
  private auditService = inject(AuditService);
  private toastService = inject(ToastService);
  private contextMenu = inject(ContextMenuService);
  private permissions = inject(PermissionCheckService);

  logs = signal<AuditLog[]>([]);
  totalLogs = signal(0);
  currentOffset = signal(0);
  selectedLog = signal<AuditLog | null>(null);
  savedQueries = signal<SavedQuery[]>([]);
  traceViewId = signal<string | null>(null);

  searchText = '';
  filterPriority = '';
  filterDateFrom = '';
  filterDateTo = '';
  pageSize = 50;

  // Taxonomy
  private taxonomy = signal<TaxonomyResponse | null>(null);
  selectedEventTypes = signal<string[]>([]);

  taxonomyTree = computed<TreeNode[]>(() => {
    const tax = this.taxonomy();
    if (!tax) return [];
    return tax.categories.map(cat => ({
      key: cat.category,
      label: cat.label,
      children: cat.event_types.map(et => ({
        key: et.key,
        label: et.label,
      })),
    }));
  });

  activeFilters = computed<ActiveFilter[]>(() => {
    const filters: ActiveFilter[] = [];
    if (this.searchText.trim()) {
      filters.push({ key: 'full_text', label: 'Search', value: this.searchText, displayValue: this.searchText });
    }
    for (const et of this.selectedEventTypes()) {
      filters.push({ key: 'event_type', label: 'Event', value: et, displayValue: et });
    }
    if (this.filterPriority) {
      filters.push({ key: 'priority', label: 'Priority', value: this.filterPriority, displayValue: this.filterPriority });
    }
    if (this.filterDateFrom) {
      filters.push({ key: 'date_from', label: 'From', value: this.filterDateFrom, displayValue: this.filterDateFrom });
    }
    if (this.filterDateTo) {
      filters.push({ key: 'date_to', label: 'To', value: this.filterDateTo, displayValue: this.filterDateTo });
    }
    return filters;
  });

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadLogs();
    this.loadSavedQueries();
    this.loadTaxonomy();
  }

  onSearchChange(): void {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.currentOffset.set(0);
      this.loadLogs();
    }, 300);
  }

  onFilterChange(): void {
    this.currentOffset.set(0);
    this.loadLogs();
  }

  onEventTypesChange(types: string[]): void {
    this.selectedEventTypes.set(types);
    this.currentOffset.set(0);
    this.loadLogs();
  }

  clearFilters(): void {
    this.searchText = '';
    this.filterPriority = '';
    this.filterDateFrom = '';
    this.filterDateTo = '';
    this.selectedEventTypes.set([]);
    this.currentOffset.set(0);
    this.loadLogs();
  }

  removeFilter(filter: ActiveFilter): void {
    switch (filter.key) {
      case 'full_text':
        this.searchText = '';
        break;
      case 'event_type':
        this.selectedEventTypes.update(types => types.filter(t => t !== filter.value));
        break;
      case 'priority':
        this.filterPriority = '';
        break;
      case 'date_from':
        this.filterDateFrom = '';
        break;
      case 'date_to':
        this.filterDateTo = '';
        break;
    }
    this.currentOffset.set(0);
    this.loadLogs();
  }

  selectLog(log: AuditLog): void {
    this.selectedLog.set(this.selectedLog()?.id === log.id ? null : log);
  }

  filterByTrace(traceId: string): void {
    this.clearFilters();
    this.auditService.getLogsByTrace(traceId).subscribe({
      next: (logs) => {
        this.logs.set(logs);
        this.totalLogs.set(logs.length);
      },
    });
  }

  showTrace(traceId: string): void {
    this.traceViewId.set(traceId);
  }

  applySavedQuery(sq: SavedQuery): void {
    const p = sq.query_params as Record<string, unknown>;
    this.searchText = (p['full_text'] as string) || '';
    this.filterPriority = (p['priority'] as string) || '';
    this.filterDateFrom = (p['date_from'] as string) || '';
    this.filterDateTo = (p['date_to'] as string) || '';
    this.selectedEventTypes.set((p['event_types'] as string[]) || []);
    this.currentOffset.set(0);
    this.loadLogs();
  }

  exportLogs(format: 'json' | 'csv'): void {
    this.auditService.startExport({ format }).subscribe({
      next: (res) => {
        this.toastService.success(`Export started (ID: ${res.export_id.substring(0, 8)}...)`);
      },
      error: () => {
        this.toastService.error('Failed to start export');
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadLogs();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadLogs();
  }

  // ── Context Menus ─────────────────────────────────

  onCellContext(event: MouseEvent, log: AuditLog, column: string): void {
    const items = this.buildContextMenu(log, column);
    if (items.length > 0) {
      this.contextMenu.open(event, items);
    }
  }

  private buildContextMenu(log: AuditLog, column: string): ContextMenuItem[] {
    const items: ContextMenuItem[] = [];

    switch (column) {
      case 'actor':
        if (log.actor_email) {
          items.push({ label: `Filter by "${log.actor_email}"`, action: () => {
            this.searchText = log.actor_email!;
            this.currentOffset.set(0);
            this.loadLogs();
          }});
          items.push({ label: 'Copy actor', action: () => navigator.clipboard.writeText(log.actor_email!) });
        }
        break;

      case 'event':
        if (log.event_type) {
          items.push({ label: `Filter by "${log.event_type}"`, action: () => {
            this.selectedEventTypes.set([log.event_type!]);
            this.currentOffset.set(0);
            this.loadLogs();
          }});
          if (log.event_category) {
            items.push({ label: `Filter by category "${log.event_category}"`, action: () => {
              const tax = this.taxonomy();
              if (tax) {
                const cat = tax.categories.find(c => c.category === log.event_category);
                if (cat) {
                  this.selectedEventTypes.set(cat.event_types.map(et => et.key));
                  this.currentOffset.set(0);
                  this.loadLogs();
                }
              }
            }});
          }
          items.push({ label: 'Copy event type', action: () => navigator.clipboard.writeText(log.event_type!) });
        } else {
          items.push({ label: 'Copy action', action: () => navigator.clipboard.writeText(log.action) });
        }
        break;

      case 'trace':
        if (log.trace_id) {
          items.push({ label: 'Show full trace', action: () => this.showTrace(log.trace_id!) });
          items.push({ label: 'Filter by trace', action: () => this.filterByTrace(log.trace_id!) });
          items.push({ label: 'Copy trace ID', action: () => navigator.clipboard.writeText(log.trace_id!) });
        }
        break;

      case 'priority':
        items.push({ label: `Filter by "${log.priority}"`, action: () => {
          this.filterPriority = log.priority;
          this.currentOffset.set(0);
          this.loadLogs();
        }});
        break;

      case 'resource':
        if (log.resource_type) {
          items.push({ label: `Filter by type "${log.resource_type}"`, action: () => {
            this.searchText = log.resource_type!;
            this.currentOffset.set(0);
            this.loadLogs();
          }});
        }
        if (log.resource_id) {
          items.push({ label: 'Copy resource ID', action: () => navigator.clipboard.writeText(log.resource_id!) });
        }
        break;
    }

    return items;
  }

  // ── Private ───────────────────────────────────────

  private loadLogs(): void {
    const params: AuditSearchParams = {
      offset: this.currentOffset(),
      limit: this.pageSize,
    };
    if (this.searchText.trim()) params.full_text = this.searchText.trim();
    if (this.selectedEventTypes().length > 0) params.event_types = this.selectedEventTypes();
    if (this.filterPriority) params.priority = this.filterPriority as AuditPriority;
    if (this.filterDateFrom) params.date_from = new Date(this.filterDateFrom).toISOString();
    if (this.filterDateTo) params.date_to = new Date(this.filterDateTo).toISOString();

    this.auditService.searchLogs(params).subscribe({
      next: (res) => {
        this.logs.set(res.items);
        this.totalLogs.set(res.total);
      },
    });
  }

  private loadSavedQueries(): void {
    if (!this.permissions.hasPermission('audit:query:read')) {
      return;
    }
    this.auditService.listSavedQueries().subscribe({
      next: (queries) => this.savedQueries.set(queries),
      error: () => { /* Non-critical — saved queries are optional UI sugar */ },
    });
  }

  private loadTaxonomy(): void {
    this.auditService.getTaxonomy().subscribe({
      next: (tax) => this.taxonomy.set(tax),
    });
  }
}
