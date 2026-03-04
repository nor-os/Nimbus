/**
 * Overview: Activity list — unified catalog of automated activities with operation kind and component filtering.
 * Architecture: Feature component for activity catalog (Section 11.5)
 * Dependencies: @angular/core, @angular/router, AutomatedActivityService
 * Concepts: Activity catalog, template vs component activity, search/filter, permission-gated actions
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
import { AutomatedActivityService } from '@core/services/automated-activity.service';
import { AutomatedActivity } from '@shared/models/automated-activity.model';
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
            <h1>Activities</h1>
            <p class="page-subtitle">All activities — templates and component-bound automation</p>
          </div>
          <div class="header-actions" *nimbusHasPermission="'automation:activity:create'">
            <button class="btn btn-primary" (click)="createActivity()">+ New Activity</button>
          </div>
        </div>

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
          <select [ngModel]="componentFilter()" (ngModelChange)="componentFilter.set($event); loadActivities()">
            <option value="">All Activities</option>
            <option value="component">Component Activities</option>
            <option value="template">Template Activities</option>
          </select>
        </div>

        <!-- Table -->
        @if (loading()) {
          <div class="loading-state">Loading activities...</div>
        }

        @if (!loading() && filteredActivities().length === 0) {
          <div class="empty-state">
            <p>No activities found.</p>
            <p class="empty-hint">Activities are automation building blocks — either templates or component-bound.</p>
          </div>
        }

        @if (!loading() && filteredActivities().length > 0) {
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Operation</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Impl</th>
                  <th>Updated</th>
                </tr>
              </thead>
              <tbody>
                @for (activity of filteredActivities(); track activity.id) {
                  <tr class="clickable-row" (click)="openActivity(activity)">
                    <td>
                      <div class="activity-name">
                        {{ activity.name }}
                        @if (activity.isMandatory) {
                          <span class="badge badge-mandatory">Mandatory</span>
                        }
                      </div>
                      <div class="activity-slug">{{ activity.slug }}</div>
                    </td>
                    <td><span class="badge badge-operation">{{ formatOperationKind(activity.operationKind) }}</span></td>
                    <td>
                      @if (activity.isComponentActivity) {
                        <span class="badge badge-component">Component</span>
                      } @else {
                        <span class="badge badge-template">Template</span>
                      }
                    </td>
                    <td>
                      @if (activity.templateActivityId && activity.forkedAtVersion !== null) {
                        @if (isCustomized(activity)) {
                          <span class="badge badge-customized">Customized</span>
                        } @else {
                          <span class="badge badge-default">Default</span>
                        }
                        <span class="forked-version">from v{{ activity.forkedAtVersion }}</span>
                      } @else {
                        <span class="text-muted">—</span>
                      }
                    </td>
                    <td><span class="badge badge-type">{{ formatImplType(activity.implementationType) }}</span></td>
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
    .page-container { padding: 0; max-width: 1200px; }
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
    .activity-name { font-weight: 600; color: #1e293b; display: flex; align-items: center; gap: 6px; }
    .activity-slug { font-size: 12px; color: #94a3b8; font-family: monospace; }

    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
    }
    .badge-operation { background: #dbeafe; color: #1d4ed8; }
    .badge-type { background: #fef3c7; color: #92400e; }
    .badge-mandatory { background: #fef2f2; color: #991b1b; font-size: 10px; padding: 1px 6px; }
    .badge-component { background: #fff7ed; color: #c2410c; }
    .badge-template { background: #e0e7ff; color: #3730a3; }
    .badge-customized { background: #fef3c7; color: #92400e; }
    .badge-default { background: #f1f5f9; color: #64748b; }
    .forked-version { font-size: 11px; color: #94a3b8; margin-left: 4px; }
    .text-muted { color: #94a3b8; }
  `],
})
export class ActivityListComponent implements OnInit {
  private activityService = inject(AutomatedActivityService);
  private router = inject(Router);

  activities = signal<AutomatedActivity[]>([]);
  loading = signal(false);
  search = signal('');
  operationKindFilter = signal('');
  componentFilter = signal('');

  filteredActivities = computed(() => {
    let list = this.activities();
    const filter = this.componentFilter();

    if (filter === 'component') {
      list = list.filter(a => a.isComponentActivity);
    } else if (filter === 'template') {
      list = list.filter(a => !a.isComponentActivity);
    }

    return list;
  });

  ngOnInit(): void {
    this.loadActivities();
  }

  loadActivities(): void {
    this.loading.set(true);
    this.activityService.listActivities({
      search: this.search() || undefined,
      operationKind: this.operationKindFilter() || undefined,
      isComponentActivity: this.componentFilter() === 'component' ? true : this.componentFilter() === 'template' ? false : undefined,
    }).subscribe({
      next: (list) => {
        this.activities.set(list);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  openActivity(activity: AutomatedActivity): void {
    if (activity.componentId) {
      this.router.navigate(['/infrastructure/components', activity.componentId, 'edit']);
    } else {
      this.router.navigate(['/provider/activities', activity.id]);
    }
  }

  createActivity(): void {
    this.router.navigate(['/provider/activities', 'new']);
  }

  isCustomized(activity: AutomatedActivity): boolean {
    return !!(activity.templateActivityId && activity.versions && activity.versions.length > 1);
  }

  formatOperationKind(kind: string): string {
    return kind.charAt(0) + kind.slice(1).toLowerCase();
  }

  formatImplType(type: string): string {
    return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()).replace(/\bHttp\b/, 'HTTP');
  }
}
