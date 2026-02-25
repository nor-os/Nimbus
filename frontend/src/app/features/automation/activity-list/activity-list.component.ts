/**
 * Overview: Activity list — browsable catalog of automated activities with scope-aware tabs.
 * Architecture: Feature component for activity catalog (Section 11.5)
 * Dependencies: @angular/core, @angular/router, AutomatedActivityService
 * Concepts: Activity catalog, scope filtering (COMPONENT vs WORKFLOW), search/filter, permission-gated actions
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
import { AutomatedActivityService } from '@core/services/automated-activity.service';
import { AutomatedActivity, OperationKind, ImplementationType, ActivityScope } from '@shared/models/automated-activity.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';

@Component({
  selector: 'nimbus-activity-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1>{{ pageTitle() }}</h1>
            <p class="page-subtitle">{{ pageSubtitle() }}</p>
          </div>
          <div class="header-actions" *nimbusHasPermission="'automation:activity:create'">
            <button class="btn btn-primary" (click)="createActivity()">+ New Activity</button>
          </div>
        </div>

        <!-- Scope tabs -->
        @if (isComponentMode()) {
          <div class="scope-tabs">
            <button class="scope-tab" [class.active]="subTab() === 'day2'" (click)="subTab.set('day2'); loadActivities()">
              Day-2 Operations
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'deployment'" (click)="subTab.set('deployment'); loadActivities()">
              Deployment
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'all'" (click)="subTab.set('all'); loadActivities()">
              All
            </button>
          </div>
        }
        @if (!isComponentMode()) {
          <div class="scope-tabs">
            <button class="scope-tab" [class.active]="subTab() === 'all'" (click)="subTab.set('all'); loadActivities()">
              All
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'component'" (click)="subTab.set('component'); loadActivities()">
              Component
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'workflow'" (click)="subTab.set('workflow'); loadActivities()">
              Workflow
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'builtin'" (click)="subTab.set('builtin'); loadActivities()">
              Builtin
            </button>
            <button class="scope-tab" [class.active]="subTab() === 'custom'" (click)="subTab.set('custom'); loadActivities()">
              Custom
            </button>
          </div>
        }

        <!-- Filters -->
        <div class="filter-bar">
          <div class="search-box">
            <input
              type="text"
              placeholder="Search activities..."
              [ngModel]="search()"
              (ngModelChange)="search.set($event); loadActivities()"
            />
          </div>
          <select [ngModel]="categoryFilter()" (ngModelChange)="categoryFilter.set($event); loadActivities()">
            <option value="">All Categories</option>
            <option value="compute">Compute</option>
            <option value="storage">Storage</option>
            <option value="network">Network</option>
            <option value="security">Security</option>
            <option value="backup">Backup</option>
            <option value="monitoring">Monitoring</option>
            <option value="notification">Notification</option>
            <option value="integration">Integration</option>
            <option value="observability">Observability</option>
          </select>
          <select [ngModel]="operationKindFilter()" (ngModelChange)="operationKindFilter.set($event); loadActivities()">
            <option value="">All Operations</option>
            <option value="CREATE">Create</option>
            <option value="READ">Read</option>
            <option value="UPDATE">Update</option>
            <option value="DELETE">Delete</option>
            <option value="REMEDIATE">Remediate</option>
            <option value="VALIDATE">Validate</option>
            <option value="BACKUP">Backup</option>
            <option value="RESTORE">Restore</option>
          </select>
        </div>

        <!-- Table -->
        @if (loading()) {
          <div class="loading-state">Loading activities...</div>
        }

        @if (!loading() && filteredActivities().length === 0) {
          <div class="empty-state">
            <p>No activities found.</p>
            <p class="empty-hint">
              @if (isComponentMode()) {
                Component activities are infrastructure operations bound to deployed resources.
              } @else {
                Create workflow activities for general-purpose automation building blocks.
              }
            </p>
          </div>
        }

        @if (!loading() && filteredActivities().length > 0) {
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Operation</th>
                  <th>Type</th>
                  <th>Scope</th>
                  <th>Idempotent</th>
                  <th>Kind</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                @for (activity of filteredActivities(); track activity.id) {
                  <tr class="clickable-row" (click)="openActivity(activity.id)">
                    <td>
                      <div class="activity-name">{{ activity.name }}</div>
                      <div class="activity-slug">{{ activity.slug }}</div>
                    </td>
                    <td><span class="badge badge-category">{{ activity.category || '—' }}</span></td>
                    <td><span class="badge badge-operation">{{ formatOperationKind(activity.operationKind) }}</span></td>
                    <td><span class="badge badge-type">{{ formatImplType(activity.implementationType) }}</span></td>
                    <td>
                      <span class="badge" [class]="activity.scope === 'COMPONENT' ? 'badge-component' : 'badge-workflow'">
                        {{ activity.scope === 'COMPONENT' ? 'Component' : 'Workflow' }}
                      </span>
                    </td>
                    <td>{{ activity.idempotent ? 'Yes' : 'No' }}</td>
                    <td>
                      @if (activity.isSystem) {
                        <span class="badge badge-system">System</span>
                      } @else {
                        <span class="badge badge-custom">Custom</span>
                      }
                    </td>
                    <td>{{ activity.updatedAt | date:'short' }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 24px;
    }
    .page-header h1 { font-size: 24px; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 14px; color: #64748b; margin: 4px 0 0; }
    .header-actions { display: flex; gap: 8px; }

    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500;
      cursor: pointer; border: 1px solid transparent; transition: all 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }

    .scope-tabs {
      display: flex; gap: 0; margin-bottom: 16px;
      border-bottom: 2px solid #e2e8f0;
    }
    .scope-tab {
      padding: 8px 20px; font-size: 14px; font-weight: 500; color: #64748b;
      background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; transition: all 0.15s;
    }
    .scope-tab:hover { color: #334155; }
    .scope-tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .filter-bar {
      display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap;
    }
    .search-box { flex: 1; min-width: 200px; }
    .search-box input {
      width: 100%; padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 14px; background: #fff; color: #1e293b;
    }
    .search-box input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.15); }
    .filter-bar select {
      padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 14px; background: #fff; color: #1e293b; min-width: 160px;
    }

    .loading-state, .empty-state {
      text-align: center; padding: 48px 24px; color: #64748b; font-size: 15px;
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
    }
    .empty-hint { font-size: 13px; color: #94a3b8; margin-top: 8px; }

    .table-container {
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
      overflow: hidden;
    }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 12px 16px; font-size: 12px; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td {
      padding: 12px 16px; font-size: 14px; color: #334155;
      border-bottom: 1px solid #f1f5f9;
    }
    .clickable-row { cursor: pointer; transition: background 0.1s; }
    .clickable-row:hover { background: #f8fafc; }
    .activity-name { font-weight: 600; color: #1e293b; }
    .activity-slug { font-size: 12px; color: #94a3b8; font-family: monospace; }

    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
    }
    .badge-category { background: #ede9fe; color: #6d28d9; }
    .badge-operation { background: #dbeafe; color: #1d4ed8; }
    .badge-type { background: #fef3c7; color: #92400e; }
    .badge-system { background: #e0e7ff; color: #3730a3; }
    .badge-custom { background: #f0fdf4; color: #166534; }
    .badge-component { background: #fff7ed; color: #c2410c; }
    .badge-workflow { background: #eff6ff; color: #1d4ed8; }
  `],
})
export class ActivityListComponent implements OnInit {
  private activityService = inject(AutomatedActivityService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  /** Component mode: Provider section (/provider/activities) OR tenant Infrastructure (/activities) */
  private get isComponentRoute(): boolean {
    return this.router.url.includes('/provider/activities') || this.router.url.startsWith('/activities');
  }

  /** Workflow catalog mode: /workflows/activities — shows ALL activities regardless of scope */
  private get isWorkflowCatalogRoute(): boolean {
    return this.router.url.includes('/workflows/activities');
  }

  private get basePath(): string {
    if (this.router.url.includes('/provider/activities')) return '/provider/activities';
    if (this.router.url.startsWith('/activities')) return '/activities';
    return '/workflows/activities';
  }

  activities = signal<AutomatedActivity[]>([]);
  loading = signal(false);
  search = signal('');
  categoryFilter = signal('');
  operationKindFilter = signal('');
  subTab = signal<string>('all');

  isComponentMode = computed(() => this.isComponentRoute);

  pageTitle = computed(() =>
    this.isComponentMode() ? 'Component Activities' : 'Automation Catalog'
  );

  pageSubtitle = computed(() =>
    this.isComponentMode()
      ? 'Infrastructure operations for deployed components — day-2 and deployment activities'
      : 'All available activities — component, workflow, builtin and custom'
  );

  /** Client-side sub-tab filtering after server scope filter */
  filteredActivities = computed(() => {
    const list = this.activities();
    const tab = this.subTab();

    if (this.isComponentMode()) {
      const DAY2_OPS = new Set(['REMEDIATE', 'VALIDATE', 'BACKUP', 'RESTORE', 'UPDATE', 'READ']);
      const DEPLOY_OPS = new Set(['CREATE', 'DELETE']);
      if (tab === 'day2') return list.filter(a => DAY2_OPS.has(a.operationKind));
      if (tab === 'deployment') return list.filter(a => DEPLOY_OPS.has(a.operationKind));
    } else {
      if (tab === 'component') return list.filter(a => a.scope === 'COMPONENT');
      if (tab === 'workflow') return list.filter(a => a.scope === 'WORKFLOW');
      if (tab === 'builtin') return list.filter(a => a.isSystem);
      if (tab === 'custom') return list.filter(a => !a.isSystem);
    }
    return list;
  });

  ngOnInit(): void {
    // Default to day2 tab for component mode
    if (this.isComponentRoute) {
      this.subTab.set('day2');
    }
    this.loadActivities();
  }

  loadActivities(): void {
    this.loading.set(true);
    // Component routes filter by COMPONENT scope; workflow catalog shows ALL (no scope filter)
    const scope = this.isComponentRoute ? 'COMPONENT' : undefined;
    this.activityService.listActivities({
      scope,
      search: this.search() || undefined,
      category: this.categoryFilter() || undefined,
      operationKind: this.operationKindFilter() || undefined,
    }).subscribe({
      next: (list) => {
        this.activities.set(list);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openActivity(id: string): void {
    this.router.navigate([this.basePath, id]);
  }

  createActivity(): void {
    this.router.navigate([this.basePath, 'new']);
  }

  formatOperationKind(kind: string): string {
    return kind.charAt(0) + kind.slice(1).toLowerCase();
  }

  formatImplType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\bHttp\b/, 'HTTP');
  }
}
