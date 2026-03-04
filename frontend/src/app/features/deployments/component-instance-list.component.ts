/**
 * Overview: Component instance list — unified view of all deployed component instances
 *     across standalone deployments, topology deployments, and stack instances.
 * Architecture: Deployment management UI (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, deployment.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { DeploymentService } from '@core/services/deployment.service';
import { ComponentInstance, ComponentInstanceSourceType } from '@shared/models/deployment.model';

@Component({
  selector: 'nimbus-component-instance-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Component Instances</h1>
            <p class="page-subtitle">All deployed component instances across topologies, stacks, and standalone deployments</p>
          </div>
        </div>

        <div class="filters-bar">
          <input
            type="text"
            class="search-input"
            placeholder="Search by component name..."
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
          />
          <select class="filter-select" [(ngModel)]="sourceTypeFilter" (ngModelChange)="applyFilters()">
            <option value="">All Sources</option>
            <option value="standalone">Standalone</option>
            <option value="topology">Topology</option>
            <option value="stack">Stack</option>
          </select>
        </div>

        <div class="table-container">
          @if (loading()) {
            <div class="loading-state">Loading component instances...</div>
          } @else if (filtered().length === 0) {
            <div class="empty-state">
              <p>No component instances found.</p>
              <p class="text-muted text-sm">Deploy components via topologies, stacks, or standalone deployments.</p>
            </div>
          } @else {
            <table class="data-table">
              <thead>
                <tr>
                  <th>Component</th>
                  <th>Version</th>
                  <th>Environment</th>
                  <th>Status</th>
                  <th>Source</th>
                  <th>Source Name</th>
                  <th>Deployed At</th>
                </tr>
              </thead>
              <tbody>
                @for (inst of filtered(); track inst.id) {
                  <tr>
                    <td>
                      <span class="text-bold">{{ inst.componentDisplayName }}</span>
                    </td>
                    <td>{{ inst.componentVersion != null ? ('v' + inst.componentVersion) : '--' }}</td>
                    <td class="text-muted">{{ inst.environmentId || '--' }}</td>
                    <td>
                      <span class="badge badge-status" [ngClass]="getStatusClass(inst.status)">
                        {{ inst.status }}
                      </span>
                    </td>
                    <td>
                      <span class="badge" [ngClass]="getSourceClass(inst.sourceType)">
                        {{ inst.sourceType }}
                      </span>
                    </td>
                    <td>
                      <a [href]="getSourceLink(inst)" class="link-primary" (click)="navigateToSource($event, inst)">
                        {{ inst.sourceName }}
                      </a>
                    </td>
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
    .text-bold { font-weight: 500; }
    .text-muted { color: #64748b; }
    .text-sm { font-size: 0.8rem; }
    .link-primary { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .link-primary:hover { text-decoration: underline; }
    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.03em;
    }
    .badge-source-standalone { background: #dbeafe; color: #1e40af; }
    .badge-source-topology { background: #f3e8ff; color: #6b21a8; }
    .badge-source-stack { background: #dcfce7; color: #166534; }
    .badge-status-deployed, .badge-status-active { background: #dcfce7; color: #166534; }
    .badge-status-planned, .badge-status-pending { background: #f1f5f9; color: #475569; }
    .badge-status-deploying, .badge-status-provisioning { background: #dbeafe; color: #1e40af; }
    .badge-status-failed { background: #fef2f2; color: #991b1b; }
    .badge-status-pending_approval { background: #fef3c7; color: #92400e; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
  `],
})
export class ComponentInstanceListComponent implements OnInit {
  private deploymentService = inject(DeploymentService);
  private router = inject(Router);

  instances = signal<ComponentInstance[]>([]);
  filtered = signal<ComponentInstance[]>([]);
  loading = signal(false);
  searchTerm = '';
  sourceTypeFilter = '';

  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadInstances();
  }

  loadInstances(): void {
    this.loading.set(true);
    this.deploymentService.listComponentInstances().subscribe({
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

  applyFilters(): void {
    let items = this.instances();
    if (this.sourceTypeFilter) {
      items = items.filter(i => i.sourceType === this.sourceTypeFilter);
    }
    if (this.searchTerm) {
      const term = this.searchTerm.toLowerCase();
      items = items.filter(i => i.componentDisplayName.toLowerCase().includes(term));
    }
    this.filtered.set(items);
  }

  getSourceClass(sourceType: ComponentInstanceSourceType): string {
    return 'badge-source-' + sourceType;
  }

  getStatusClass(status: string): string {
    return 'badge-status-' + status.toLowerCase();
  }

  getSourceLink(inst: ComponentInstance): string {
    switch (inst.sourceType) {
      case 'topology': return `/#/deployments/topologies/${inst.sourceId}`;
      case 'stack': return `/#/deployments/stacks/${inst.sourceId}`;
      default: return `/#/deployments/topologies/${inst.sourceId}`;
    }
  }

  navigateToSource(event: Event, inst: ComponentInstance): void {
    event.preventDefault();
    switch (inst.sourceType) {
      case 'topology':
        this.router.navigate(['/deployments/topologies', inst.sourceId]);
        break;
      case 'stack':
        this.router.navigate(['/deployments/stacks', inst.sourceId]);
        break;
      default:
        this.router.navigate(['/deployments/topologies', inst.sourceId]);
        break;
    }
  }
}
