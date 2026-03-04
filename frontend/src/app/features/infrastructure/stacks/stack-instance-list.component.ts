/**
 * Overview: Tenant-level stack instance list — searchable table with status/health badges,
 *     environment info, pagination, and navigation to instance detail.
 * Architecture: Infrastructure stack instance management UI (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, cluster.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import { StackRuntimeInstance, StackInstanceStatus, HealthStatus } from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-stack-instance-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Stack Instances</h1>
            <p class="page-subtitle">Deployed infrastructure stacks with real-time status and health monitoring</p>
          </div>
          <button *nimbusHasPermission="'infrastructure:stack:deploy'" class="btn btn-primary" (click)="onDeployStack()">
            + Deploy Stack
          </button>
        </div>

        <div class="filters-bar">
          <input
            type="text"
            class="search-input"
            placeholder="Search stack instances..."
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
          />
          <select class="filter-select" [(ngModel)]="statusFilter" (ngModelChange)="onFilterChange()">
            <option value="">All Statuses</option>
            <option *ngFor="let s of statuses" [value]="s">{{ s }}</option>
          </select>
        </div>

        <div class="table-container">
          @if (loading()) {
            <div class="loading-state">Loading stack instances...</div>
          } @else if (instances().length === 0) {
            <div class="empty-state">
              <p>No stack instances found.</p>
              <p class="text-muted text-sm">Deploy a stack from a published blueprint to get started.</p>
            </div>
          } @else {
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Blueprint</th>
                  <th>Status</th>
                  <th>Health</th>
                  <th>Environment</th>
                  <th>Deployed</th>
                </tr>
              </thead>
              <tbody>
                @for (inst of instances(); track inst.id) {
                  <tr class="clickable-row" (click)="navigateToDetail(inst.id)">
                    <td>
                      <span class="link-primary">{{ inst.name }}</span>
                    </td>
                    <td class="text-muted">{{ inst.blueprintId }}</td>
                    <td>
                      <span class="badge" [ngClass]="getStatusClass(inst.status)">
                        {{ inst.status }}
                      </span>
                    </td>
                    <td>
                      <span class="badge" [ngClass]="getHealthClass(inst.healthStatus)">
                        {{ inst.healthStatus }}
                      </span>
                    </td>
                    <td class="text-muted">{{ inst.environmentId || '--' }}</td>
                    <td class="text-muted">{{ inst.deployedAt | date:'mediumDate' }}</td>
                  </tr>
                }
              </tbody>
            </table>

            @if (total() > limit) {
              <div class="pagination">
                <button
                  class="btn btn-sm btn-outline"
                  [disabled]="offset() === 0"
                  (click)="prevPage()"
                >Previous</button>
                <span class="pagination-info">
                  {{ offset() + 1 }}–{{ Math.min(offset() + limit, total()) }} of {{ total() }}
                </span>
                <button
                  class="btn btn-sm btn-outline"
                  [disabled]="offset() + limit >= total()"
                  (click)="nextPage()"
                >Next</button>
              </div>
            }
          }
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .filters-bar { display: flex; gap: 12px; margin-bottom: 16px; }
    .search-input {
      flex: 1; padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; background: #fff; color: #1e293b;
    }
    .search-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
    .filter-select {
      padding: 8px 12px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; background: #fff; color: #1e293b; min-width: 160px;
    }
    .filter-select:focus { outline: none; border-color: #3b82f6; }
    .table-container { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 12px 16px; font-size: 0.75rem; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td { padding: 12px 16px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.875rem; }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover { background: #f8fafc; }
    .clickable-row { cursor: pointer; }
    .link-primary { color: #3b82f6; font-weight: 500; }
    .text-muted { color: #64748b; }
    .text-sm { font-size: 0.8rem; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
    }
    .badge-status-active { background: #dcfce7; color: #166534; }
    .badge-status-provisioning { background: #dbeafe; color: #1e40af; }
    .badge-status-planned { background: #f1f5f9; color: #475569; }
    .badge-status-degraded { background: #fef3c7; color: #92400e; }
    .badge-status-failed { background: #fef2f2; color: #991b1b; }
    .badge-status-decommissioned { background: #fff; color: #94a3b8; border: 1px solid #e2e8f0; }
    .badge-status-updating { background: #e0e7ff; color: #3730a3; }
    .badge-status-decommissioning { background: #f5f3ff; color: #6b21a8; }
    .badge-health-healthy { background: #dcfce7; color: #166534; }
    .badge-health-degraded { background: #fef3c7; color: #92400e; }
    .badge-health-unhealthy { background: #fef2f2; color: #991b1b; }
    .badge-health-unknown { background: #f1f5f9; color: #475569; }
    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px 16px; border-top: 1px solid #e2e8f0; }
    .pagination-info { font-size: 0.875rem; color: #64748b; }
  `],
})
export class StackInstanceListComponent implements OnInit {
  private clusterService = inject(ClusterService);
  private router = inject(Router);

  instances = signal<StackRuntimeInstance[]>([]);
  total = signal(0);
  loading = signal(false);
  offset = signal(0);
  limit = 25;
  searchTerm = '';
  statusFilter = '';

  Math = Math;

  statuses: StackInstanceStatus[] = [
    'PLANNED', 'PROVISIONING', 'ACTIVE', 'UPDATING', 'DEGRADED',
    'DECOMMISSIONING', 'DECOMMISSIONED', 'FAILED',
  ];

  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadInstances();
  }

  loadInstances(): void {
    this.loading.set(true);
    this.clusterService.listStackInstances({
      status: this.statusFilter || undefined,
      offset: this.offset(),
      limit: this.limit,
    }).subscribe({
      next: (result) => {
        this.instances.set(result.items);
        this.total.set(result.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onSearch(): void {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => {
      this.offset.set(0);
      this.loadInstances();
    }, 300);
  }

  onFilterChange(): void {
    this.offset.set(0);
    this.loadInstances();
  }

  navigateToDetail(id: string): void {
    this.router.navigate(['/deployments/stacks', id]);
  }

  onDeployStack(): void {
    this.router.navigate(['/provider/infrastructure/blueprints']);
  }

  getStatusClass(status: StackInstanceStatus): string {
    return 'badge-status-' + status.toLowerCase();
  }

  getHealthClass(health: HealthStatus): string {
    return 'badge-health-' + health.toLowerCase();
  }

  prevPage(): void {
    this.offset.set(Math.max(0, this.offset() - this.limit));
    this.loadInstances();
  }

  nextPage(): void {
    this.offset.set(this.offset() + this.limit);
    this.loadInstances();
  }
}
