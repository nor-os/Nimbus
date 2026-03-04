/**
 * Overview: Topology instance list — deployments that have an associated topology.
 * Architecture: Deployment management UI (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, deployment.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { DeploymentService } from '@core/services/deployment.service';
import { Deployment, DeploymentStatus } from '@shared/models/deployment.model';

@Component({
  selector: 'nimbus-topology-instance-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Topology Instances</h1>
            <p class="page-subtitle">Deployed topology instances across environments</p>
          </div>
        </div>

        <div class="filters-bar">
          <input
            type="text"
            class="search-input"
            placeholder="Search topology instances..."
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
            <div class="loading-state">Loading topology instances...</div>
          } @else if (filtered().length === 0) {
            <div class="empty-state">
              <p>No topology instances found.</p>
              <p class="text-muted text-sm">Deploy a topology to an environment to get started.</p>
            </div>
          } @else {
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Topology</th>
                  <th>Environment</th>
                  <th>Status</th>
                  <th>Deployed By</th>
                  <th>Deployed At</th>
                </tr>
              </thead>
              <tbody>
                @for (inst of filtered(); track inst.id) {
                  <tr class="clickable-row" (click)="navigateToDetail(inst.id)">
                    <td>
                      <span class="link-primary">{{ inst.name }}</span>
                    </td>
                    <td class="text-muted">{{ inst.topologyId || '--' }}</td>
                    <td class="text-muted">{{ inst.environmentId }}</td>
                    <td>
                      <span class="badge" [ngClass]="getStatusClass(inst.status)">
                        {{ inst.status }}
                      </span>
                    </td>
                    <td class="text-muted">{{ inst.deployedBy }}</td>
                    <td class="text-muted">{{ inst.deployedAt ? (inst.deployedAt | date:'mediumDate') : '--' }}</td>
                  </tr>
                }
              </tbody>
            </table>
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
    .badge-planned { background: #f1f5f9; color: #475569; }
    .badge-pending_approval { background: #fef3c7; color: #92400e; }
    .badge-approved { background: #dbeafe; color: #1e40af; }
    .badge-deploying { background: #e0e7ff; color: #3730a3; }
    .badge-deployed { background: #dcfce7; color: #166534; }
    .badge-failed { background: #fef2f2; color: #991b1b; }
    .badge-rolled_back { background: #fff; color: #94a3b8; border: 1px solid #e2e8f0; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
  `],
})
export class TopologyInstanceListComponent implements OnInit {
  private deploymentService = inject(DeploymentService);
  private router = inject(Router);

  instances = signal<Deployment[]>([]);
  loading = signal(false);
  searchTerm = '';
  statusFilter = '';

  statuses: DeploymentStatus[] = [
    'PLANNED', 'PENDING_APPROVAL', 'APPROVED', 'DEPLOYING', 'DEPLOYED', 'FAILED', 'ROLLED_BACK',
  ];

  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  filtered = signal<Deployment[]>([]);

  ngOnInit(): void {
    this.loadInstances();
  }

  loadInstances(): void {
    this.loading.set(true);
    this.deploymentService.listTopologyInstances().subscribe({
      next: (items) => {
        this.instances.set(items);
        this.applyFilters();
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onSearch(): void {
    if (this.searchTimeout) clearTimeout(this.searchTimeout);
    this.searchTimeout = setTimeout(() => this.applyFilters(), 300);
  }

  onFilterChange(): void {
    this.applyFilters();
  }

  private applyFilters(): void {
    let items = this.instances();
    if (this.statusFilter) {
      items = items.filter(i => i.status === this.statusFilter);
    }
    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      items = items.filter(i => i.name.toLowerCase().includes(term));
    }
    this.filtered.set(items);
  }

  navigateToDetail(id: string): void {
    this.router.navigate(['/deployments/topologies', id]);
  }

  getStatusClass(status: DeploymentStatus): string {
    return 'badge-' + status.toLowerCase();
  }
}
