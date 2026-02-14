/**
 * Overview: Stack blueprint list — searchable table with pagination and slot/member counts.
 * Architecture: Architecture blueprint management UI (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, cluster.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import { ServiceCluster } from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-cluster-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Stack Blueprints</h1>
            <p class="page-subtitle">Reusable infrastructure stack templates with slot-based CI assignment</p>
          </div>
          <a *nimbusHasPermission="'cmdb:cluster:create'" routerLink="/architecture/blueprints/new" class="btn btn-primary">
            + New Blueprint
          </a>
        </div>

        <div class="filters-bar">
          <input
            type="text"
            class="search-input"
            placeholder="Search clusters..."
            [(ngModel)]="searchTerm"
            (ngModelChange)="onSearch()"
          />
        </div>

        <div class="table-container">
          @if (loading()) {
            <div class="loading-state">Loading blueprints...</div>
          } @else if (clusters().length === 0) {
            <div class="empty-state">
              <p>No stack blueprints found.</p>
              <a *nimbusHasPermission="'cmdb:cluster:create'" routerLink="/architecture/blueprints/new" class="btn btn-primary">
                Create your first blueprint
              </a>
            </div>
          } @else {
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Slots</th>
                  <th>Parameters</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (cluster of clusters(); track cluster.id) {
                  <tr>
                    <td>
                      <a [routerLink]="'/architecture/blueprints/' + cluster.id" class="link-primary">
                        {{ cluster.name }}
                      </a>
                      @if (cluster.description) {
                        <div class="text-muted text-sm">{{ cluster.description }}</div>
                      }
                    </td>
                    <td>{{ cluster.slots.length || 0 }}</td>
                    <td>{{ cluster.parameters.length || 0 }}</td>
                    <td class="text-muted">{{ cluster.createdAt | date:'mediumDate' }}</td>
                    <td class="actions-cell">
                      <a
                        *nimbusHasPermission="'cmdb:cluster:manage'"
                        [routerLink]="'/architecture/blueprints/' + cluster.id + '/edit'"
                        class="btn btn-sm btn-outline"
                      >Edit</a>
                    </td>
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
    .link-primary { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .link-primary:hover { text-decoration: underline; }
    .text-muted { color: #64748b; }
    .text-sm { font-size: 0.8rem; }
    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .actions-cell { text-align: right; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
    .empty-state .btn { margin-top: 12px; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px 16px; border-top: 1px solid #e2e8f0; }
    .pagination-info { font-size: 0.875rem; color: #64748b; }
  `],
})
export class ClusterListComponent implements OnInit {
  private clusterService = inject(ClusterService);

  clusters = signal<ServiceCluster[]>([]);
  total = signal(0);
  loading = signal(false);
  offset = signal(0);
  limit = 25;
  searchTerm = '';

  Math = Math;

  private searchTimeout: ReturnType<typeof setTimeout> | null = null;

  ngOnInit(): void {
    this.loadClusters();
  }

  loadClusters(): void {
    this.loading.set(true);
    this.clusterService.listClusters({
      search: this.searchTerm || undefined,
      offset: this.offset(),
      limit: this.limit,
    }).subscribe({
      next: (result) => {
        this.clusters.set(result.items);
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
      this.loadClusters();
    }, 300);
  }

  prevPage(): void {
    this.offset.set(Math.max(0, this.offset() - this.limit));
    this.loadClusters();
  }

  nextPage(): void {
    this.offset.set(this.offset() + this.limit);
    this.loadClusters();
  }
}
