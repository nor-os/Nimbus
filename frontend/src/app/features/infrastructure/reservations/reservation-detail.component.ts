/**
 * Overview: DR reservation detail view — displays reservation metadata, type/status badges,
 *     RTO/RPO, cost, test results, sync policies table, and Claim/Release/Test actions.
 * Architecture: Infrastructure DR reservation detail UI (Section 8)
 * Dependencies: @angular/core, @angular/router, cluster.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import {
  StackReservation,
  ReservationType,
  ReservationStatus,
  TestResult,
  SyncMethod,
} from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-reservation-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (loading()) {
          <div class="loading-state">Loading reservation...</div>
        } @else if (!reservation()) {
          <div class="empty-state">Reservation not found.</div>
        } @else {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/deployments/stacks" class="breadcrumb-link">Stack Instances</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ reservation()!.id }}</span>
              </div>
              <h1 class="page-title">DR Reservation</h1>
            </div>
            <div class="header-actions">
              <span class="badge" [ngClass]="getTypeClass(reservation()!.reservationType)">
                {{ formatType(reservation()!.reservationType) }}
              </span>
              <span class="badge" [ngClass]="getStatusClass(reservation()!.status)">
                {{ reservation()!.status }}
              </span>
              @if (canClaim(reservation()!.status)) {
                <button
                  *nimbusHasPermission="'infrastructure:reservation:manage'"
                  class="btn btn-primary"
                  (click)="onClaim()"
                >Claim</button>
              }
              @if (canRelease(reservation()!.status)) {
                <button
                  *nimbusHasPermission="'infrastructure:reservation:manage'"
                  class="btn btn-outline"
                  (click)="onRelease()"
                >Release</button>
              }
              <button
                *nimbusHasPermission="'infrastructure:reservation:manage'"
                class="btn btn-warning"
                (click)="onTestFailover()"
              >Test Failover</button>
            </div>
          </div>

          <!-- Reservation Info -->
          <div class="info-row">
            <div class="info-card">
              <div class="info-label">Stack Instance</div>
              <div class="info-value-sm">{{ reservation()!.stackInstanceId }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Target Environment</div>
              <div class="info-value-sm">{{ reservation()!.targetEnvironmentId || '--' }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Target Provider</div>
              <div class="info-value-sm">{{ reservation()!.targetProviderId || '--' }}</div>
            </div>
          </div>

          <div class="info-row">
            <div class="info-card">
              <div class="info-label">RTO</div>
              <div class="info-value">{{ formatSeconds(reservation()!.rtoSeconds) }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">RPO</div>
              <div class="info-value">{{ formatSeconds(reservation()!.rpoSeconds) }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Cost / Hour</div>
              <div class="info-value">{{ reservation()!.costPerHour != null ? ('$' + reservation()!.costPerHour!.toFixed(2)) : '--' }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Last Tested</div>
              <div class="info-value-sm">{{ reservation()!.lastTestedAt ? (reservation()!.lastTestedAt | date:'medium') : 'Never' }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Test Result</div>
              <div>
                @if (reservation()!.testResult) {
                  <span class="badge" [ngClass]="getTestResultClass(reservation()!.testResult!)">
                    {{ reservation()!.testResult }}
                  </span>
                } @else {
                  <span class="text-muted">Not tested</span>
                }
              </div>
            </div>
          </div>

          <!-- Sync Policies -->
          <div class="sync-section">
            <h2 class="section-title">Sync Policies ({{ reservation()!.syncPolicies?.length || 0 }})</h2>
            @if (reservation()!.syncPolicies?.length) {
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Source Node</th>
                      <th>Target Node</th>
                      <th>Sync Method</th>
                      <th>Interval</th>
                      <th>Last Synced</th>
                      <th>Lag</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (policy of reservation()!.syncPolicies; track policy.id) {
                      <tr>
                        <td><code class="code-value">{{ policy.sourceNodeId }}</code></td>
                        <td><code class="code-value">{{ policy.targetNodeId }}</code></td>
                        <td>
                          <span class="badge badge-sync">{{ formatSyncMethod(policy.syncMethod) }}</span>
                        </td>
                        <td>{{ policy.syncIntervalSeconds ? formatSeconds(policy.syncIntervalSeconds) : '--' }}</td>
                        <td class="text-muted">{{ policy.lastSyncedAt ? (policy.lastSyncedAt | date:'medium') : 'Never' }}</td>
                        <td>
                          @if (policy.syncLagSeconds != null) {
                            <span [ngClass]="policy.syncLagSeconds > 300 ? 'text-danger' : 'text-success'">
                              {{ formatSeconds(policy.syncLagSeconds) }}
                            </span>
                          } @else {
                            <span class="text-muted">--</span>
                          }
                        </td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="empty-state-sm">No sync policies configured. Add policies to define data replication between source and DR target.</div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .breadcrumb { font-size: 0.8rem; color: #64748b; margin-bottom: 2px; }
    .breadcrumb-link { color: #3b82f6; text-decoration: none; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { margin: 0 4px; }
    .header-actions { display: flex; gap: 8px; align-items: center; }

    .info-row { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .info-card {
      flex: 1; min-width: 140px; padding: 16px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .info-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .info-value { font-size: 1.1rem; font-weight: 600; color: #1e293b; }
    .info-value-sm { font-size: 0.85rem; font-weight: 500; color: #1e293b; word-break: break-all; }

    .sync-section { margin-top: 8px; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0 0 12px; }
    .table-container { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 10px 14px; font-size: 0.75rem; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.875rem; }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover { background: #f8fafc; }
    .text-muted { color: #64748b; }
    .text-danger { color: #dc2626; font-weight: 500; }
    .text-success { color: #16a34a; font-weight: 500; }
    .code-value { font-size: 0.8rem; font-family: monospace; color: #0284c7; background: #f0f9ff; padding: 1px 5px; border-radius: 3px; }

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
    .badge-sync { background: #f0f9ff; color: #0c4a6e; }

    .empty-state-sm { padding: 32px; text-align: center; color: #94a3b8; font-size: 0.85rem; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }

    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-warning { background: #f59e0b; color: #fff; }
    .btn-warning:hover { background: #d97706; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class ReservationDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clusterService = inject(ClusterService);

  reservation = signal<StackReservation | null>(null);
  loading = signal(false);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadReservation(id);
    }
  }

  loadReservation(id: string): void {
    this.loading.set(true);
    this.clusterService.getReservation(id).subscribe({
      next: (res) => {
        this.reservation.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  canClaim(status: ReservationStatus): boolean {
    return status === 'ACTIVE';
  }

  canRelease(status: ReservationStatus): boolean {
    return status === 'CLAIMED';
  }

  onClaim(): void {
    if (!this.reservation()) return;
    this.clusterService.claimReservation(this.reservation()!.id).subscribe({
      next: (updated) => this.reservation.set(updated),
    });
  }

  onRelease(): void {
    if (!this.reservation()) return;
    if (!confirm('Release this DR reservation? The reserved resources will be freed.')) return;
    this.clusterService.releaseReservation(this.reservation()!.id).subscribe({
      next: (updated) => this.reservation.set(updated),
    });
  }

  onTestFailover(): void {
    if (!this.reservation()) return;
    if (!confirm('Initiate a failover test? This will validate DR readiness.')) return;
    this.clusterService.testFailover(this.reservation()!.id, 'PENDING').subscribe({
      next: (updated) => this.reservation.set(updated),
    });
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

  formatSyncMethod(method: SyncMethod): string {
    return method.replace(/_/g, ' ');
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

  getStatusClass(status: ReservationStatus): string {
    return 'badge-res-' + status.toLowerCase();
  }

  getTestResultClass(result: TestResult): string {
    return 'badge-test-' + result.toLowerCase();
  }
}
