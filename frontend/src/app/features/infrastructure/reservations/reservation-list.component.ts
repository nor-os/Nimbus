/**
 * Overview: Tenant-level DR reservation list — filterable table with type/status/test-result
 *     badges, RTO/RPO values, cost, and pagination.
 * Architecture: Infrastructure DR reservation management UI (Section 8)
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
import {
  StackReservation,
  ReservationStatus,
  ReservationType,
  TestResult,
} from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-reservation-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">DR Reservations</h1>
            <p class="page-subtitle">Disaster recovery reservations with failover testing and sync monitoring</p>
          </div>
        </div>

        <div class="filters-bar">
          <select class="filter-select" [(ngModel)]="statusFilter" (ngModelChange)="onFilterChange()">
            <option value="">All Statuses</option>
            <option *ngFor="let s of statuses" [value]="s">{{ s }}</option>
          </select>
        </div>

        <div class="table-container">
          @if (loading()) {
            <div class="loading-state">Loading reservations...</div>
          } @else if (reservations().length === 0) {
            <div class="empty-state">
              <p>No DR reservations found.</p>
              <p class="text-muted text-sm">Create a reservation from a stack instance to enable disaster recovery.</p>
            </div>
          } @else {
            <table class="data-table">
              <thead>
                <tr>
                  <th>Stack Instance</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>RTO</th>
                  <th>RPO</th>
                  <th>Cost/hr</th>
                  <th>Last Tested</th>
                  <th>Test Result</th>
                </tr>
              </thead>
              <tbody>
                @for (res of reservations(); track res.id) {
                  <tr class="clickable-row" (click)="navigateToDetail(res.id)">
                    <td class="link-primary">{{ res.stackInstanceId }}</td>
                    <td>
                      <span class="badge" [ngClass]="getTypeClass(res.reservationType)">
                        {{ formatType(res.reservationType) }}
                      </span>
                    </td>
                    <td>
                      <span class="badge" [ngClass]="getReservationStatusClass(res.status)">
                        {{ res.status }}
                      </span>
                    </td>
                    <td>{{ formatSeconds(res.rtoSeconds) }}</td>
                    <td>{{ formatSeconds(res.rpoSeconds) }}</td>
                    <td>{{ res.costPerHour != null ? ('$' + res.costPerHour.toFixed(2)) : '--' }}</td>
                    <td class="text-muted">{{ res.lastTestedAt ? (res.lastTestedAt | date:'mediumDate') : 'Never' }}</td>
                    <td>
                      @if (res.testResult) {
                        <span class="badge" [ngClass]="getTestResultClass(res.testResult)">
                          {{ res.testResult }}
                        </span>
                      } @else {
                        <span class="text-muted">--</span>
                      }
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
    .badge-type-hot { background: #fef2f2; color: #991b1b; }
    .badge-type-warm { background: #fff7ed; color: #9a3412; }
    .badge-type-cold { background: #dbeafe; color: #1e40af; }
    .badge-type-pilot { background: #f1f5f9; color: #475569; }
    .badge-res-pending { background: #f1f5f9; color: #475569; }
    .badge-res-active { background: #dcfce7; color: #166534; }
    .badge-res-claimed { background: #dbeafe; color: #1e40af; }
    .badge-res-released { background: #f5f3ff; color: #5b21b6; }
    .badge-res-expired { background: #fff; color: #94a3b8; border: 1px solid #e2e8f0; }
    .badge-test-passed { background: #dcfce7; color: #166534; }
    .badge-test-failed { background: #fef2f2; color: #991b1b; }
    .badge-test-partial { background: #fef3c7; color: #92400e; }
    .badge-test-not_tested { background: #f1f5f9; color: #475569; }
    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
    .pagination { display: flex; align-items: center; justify-content: center; gap: 12px; padding: 12px 16px; border-top: 1px solid #e2e8f0; }
    .pagination-info { font-size: 0.875rem; color: #64748b; }
  `],
})
export class ReservationListComponent implements OnInit {
  private clusterService = inject(ClusterService);
  private router = inject(Router);

  reservations = signal<StackReservation[]>([]);
  total = signal(0);
  loading = signal(false);
  offset = signal(0);
  limit = 25;
  statusFilter = '';

  Math = Math;

  statuses: ReservationStatus[] = ['PENDING', 'ACTIVE', 'CLAIMED', 'RELEASED', 'EXPIRED'];

  ngOnInit(): void {
    this.loadReservations();
  }

  loadReservations(): void {
    this.loading.set(true);
    this.clusterService.listReservations({
      status: this.statusFilter || undefined,
      offset: this.offset(),
      limit: this.limit,
    }).subscribe({
      next: (result) => {
        this.reservations.set(result.items);
        this.total.set(result.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onFilterChange(): void {
    this.offset.set(0);
    this.loadReservations();
  }

  navigateToDetail(id: string): void {
    this.router.navigate(['/infrastructure/reservations', id]);
  }

  formatType(type: ReservationType): string {
    return type.replace(/_/g, ' ');
  }

  formatSeconds(seconds: number | null): string {
    if (seconds == null) return '--';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }

  getTypeClass(type: ReservationType): string {
    const map: Record<ReservationType, string> = {
      HOT_STANDBY: 'badge-type-hot',
      WARM_STANDBY: 'badge-type-warm',
      COLD_STANDBY: 'badge-type-cold',
      PILOT_LIGHT: 'badge-type-pilot',
    };
    return map[type] || 'badge-type-pilot';
  }

  getReservationStatusClass(status: ReservationStatus): string {
    return 'badge-res-' + status.toLowerCase();
  }

  getTestResultClass(result: TestResult): string {
    return 'badge-test-' + result.toLowerCase();
  }

  prevPage(): void {
    this.offset.set(Math.max(0, this.offset() - this.limit));
    this.loadReservations();
  }

  nextPage(): void {
    this.offset.set(this.offset() + this.limit);
    this.loadReservations();
  }
}
