/**
 * Overview: Stack instance detail view — tabbed layout with instance metadata, status, health,
 *     input/output values, component instances table, and inline reservations tab.
 * Architecture: Infrastructure stack instance detail UI (Section 8)
 * Dependencies: @angular/core, @angular/router, cluster.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import {
  StackRuntimeInstance,
  StackInstanceStatus,
  HealthStatus,
  ComponentInstanceStatus,
  StackReservation,
  ReservationStatus,
  ReservationType,
  TestResult,
} from '@shared/models/cluster.model';

type TabId = 'details' | 'reservations';

@Component({
  selector: 'nimbus-stack-instance-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (loading()) {
          <div class="loading-state">Loading stack instance...</div>
        } @else if (!instance()) {
          <div class="empty-state">Stack instance not found.</div>
        } @else {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/deployments/stacks" class="breadcrumb-link">Stack Instances</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ instance()!.name }}</span>
              </div>
              <h1 class="page-title">{{ instance()!.name }}</h1>
            </div>
            <div class="header-actions">
              <span class="badge" [ngClass]="getStatusClass(instance()!.status)">
                {{ instance()!.status }}
              </span>
              <span class="badge" [ngClass]="getHealthClass(instance()!.healthStatus)">
                {{ instance()!.healthStatus }}
              </span>
              @if (canDecommission(instance()!.status)) {
                <button
                  *nimbusHasPermission="'infrastructure:stack:manage'"
                  class="btn btn-danger"
                  (click)="onDecommission()"
                >Decommission</button>
              }
            </div>
          </div>

          <!-- Tab Bar -->
          <div class="tab-bar">
            <button
              class="tab-btn"
              [class.tab-active]="activeTab() === 'details'"
              (click)="setTab('details')"
            >Details</button>
            <button
              class="tab-btn"
              [class.tab-active]="activeTab() === 'reservations'"
              (click)="setTab('reservations')"
            >Reservations ({{ reservations().length }})</button>
          </div>

          <!-- Details Tab -->
          @if (activeTab() === 'details') {
            <div class="info-row">
              <div class="info-card">
                <div class="info-label">Blueprint ID</div>
                <div class="info-value-sm">{{ instance()!.blueprintId }}</div>
              </div>
              <div class="info-card">
                <div class="info-label">Version</div>
                <div class="info-value">v{{ instance()!.blueprintVersion }}</div>
              </div>
              <div class="info-card">
                <div class="info-label">Environment</div>
                <div class="info-value-sm">{{ instance()!.environmentId || '--' }}</div>
              </div>
              <div class="info-card">
                <div class="info-label">Deployed</div>
                <div class="info-value-sm">{{ instance()!.deployedAt | date:'medium' }}</div>
              </div>
            </div>

            <div class="json-section">
              <div class="json-card">
                <h2 class="section-title">Input Values</h2>
                @if (instance()!.inputValues) {
                  <pre class="json-block">{{ instance()!.inputValues | json }}</pre>
                } @else {
                  <p class="text-muted text-sm">No input values.</p>
                }
              </div>
              <div class="json-card">
                <h2 class="section-title">Output Values</h2>
                @if (instance()!.outputValues) {
                  <pre class="json-block">{{ instance()!.outputValues | json }}</pre>
                } @else {
                  <p class="text-muted text-sm">No output values.</p>
                }
              </div>
            </div>

            <div class="components-section">
              <h2 class="section-title">Component Instances ({{ instance()!.components.length || 0 }})</h2>
              @if (instance()!.components.length) {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Component ID</th>
                        <th>Status</th>
                        <th>Resolved Parameters</th>
                        <th>Outputs</th>
                        <th>Updated</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (comp of instance()!.components; track comp.id) {
                        <tr>
                          <td class="text-bold">{{ comp.componentId }}</td>
                          <td>
                            <span class="badge" [ngClass]="getCompStatusClass(comp.status)">
                              {{ comp.status }}
                            </span>
                          </td>
                          <td>
                            @if (comp.resolvedParameters) {
                              <pre class="json-inline">{{ comp.resolvedParameters | json }}</pre>
                            } @else {
                              <span class="text-muted">--</span>
                            }
                          </td>
                          <td>
                            @if (comp.outputs) {
                              <pre class="json-inline">{{ comp.outputs | json }}</pre>
                            } @else {
                              <span class="text-muted">--</span>
                            }
                          </td>
                          <td class="text-muted">{{ comp.updatedAt | date:'mediumDate' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              } @else {
                <div class="empty-state-sm">No component instances.</div>
              }
            </div>
          }

          <!-- Reservations Tab -->
          @if (activeTab() === 'reservations') {
            <div class="reservations-section">
              @if (reservationsLoading()) {
                <div class="loading-state">Loading reservations...</div>
              } @else if (reservations().length === 0) {
                <div class="empty-state">
                  <p>No reservations for this stack instance.</p>
                  <p class="text-muted text-sm">Create a DR reservation to enable disaster recovery.</p>
                </div>
              } @else {
                <div class="table-container">
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>Type</th>
                        <th>Status</th>
                        <th>RTO</th>
                        <th>RPO</th>
                        <th>Cost/hr</th>
                        <th>Last Tested</th>
                        <th>Test Result</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (res of reservations(); track res.id) {
                        <tr>
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
                          <td>
                            <div class="action-btns">
                              @if (res.status === 'ACTIVE') {
                                <button class="btn btn-sm btn-outline" (click)="onClaimReservation(res.id)">Claim</button>
                                <button class="btn btn-sm btn-outline" (click)="onTestFailover(res.id)">Test</button>
                              }
                              @if (res.status === 'CLAIMED') {
                                <button class="btn btn-sm btn-outline" (click)="onReleaseReservation(res.id)">Release</button>
                              }
                            </div>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
            </div>
          }
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

    .tab-bar {
      display: flex; gap: 0; margin-bottom: 24px; border-bottom: 2px solid #e2e8f0;
    }
    .tab-btn {
      padding: 10px 20px; border: none; background: none; cursor: pointer;
      font-size: 0.875rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; margin-bottom: -2px; transition: all 0.15s;
    }
    .tab-btn:hover { color: #1e293b; }
    .tab-active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .info-row { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .info-card {
      flex: 1; min-width: 140px; padding: 16px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .info-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .info-value { font-size: 1.1rem; font-weight: 600; color: #1e293b; }
    .info-value-sm { font-size: 0.85rem; font-weight: 500; color: #1e293b; word-break: break-all; }

    .json-section { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
    .json-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px;
    }
    .json-block {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;
      font-size: 0.8rem; color: #1e293b; overflow-x: auto; max-height: 200px;
      font-family: 'Consolas', 'Monaco', monospace; margin: 8px 0 0;
    }
    .json-inline {
      font-size: 0.75rem; color: #475569; font-family: 'Consolas', 'Monaco', monospace;
      background: #f8fafc; padding: 2px 6px; border-radius: 3px; max-width: 250px;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap; display: block; margin: 0;
    }

    .components-section { margin-top: 8px; }
    .reservations-section { margin-top: 0; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0 0 12px; }
    .table-container { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 10px 14px; font-size: 0.75rem; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td { padding: 10px 14px; border-bottom: 1px solid #f1f5f9; color: #1e293b; font-size: 0.875rem; vertical-align: top; }
    .data-table tr:last-child td { border-bottom: none; }
    .data-table tr:hover { background: #f8fafc; }
    .text-bold { font-weight: 500; }
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
    .badge-comp-active { background: #dcfce7; color: #166534; }
    .badge-comp-pending { background: #f1f5f9; color: #475569; }
    .badge-comp-provisioning { background: #dbeafe; color: #1e40af; }
    .badge-comp-updating { background: #e0e7ff; color: #3730a3; }
    .badge-comp-failed { background: #fef2f2; color: #991b1b; }
    .badge-comp-decommissioned { background: #fff; color: #94a3b8; border: 1px solid #e2e8f0; }
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

    .action-btns { display: flex; gap: 6px; }
    .empty-state-sm { padding: 32px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }

    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-danger { background: #ef4444; color: #fff; }
    .btn-danger:hover { background: #dc2626; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class StackInstanceDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clusterService = inject(ClusterService);

  instance = signal<StackRuntimeInstance | null>(null);
  loading = signal(false);
  activeTab = signal<TabId>('details');
  reservations = signal<StackReservation[]>([]);
  reservationsLoading = signal(false);

  private instanceId: string | null = null;

  ngOnInit(): void {
    this.instanceId = this.route.snapshot.paramMap.get('id');
    if (this.instanceId) {
      this.loadInstance(this.instanceId);
    }
  }

  loadInstance(id: string): void {
    this.loading.set(true);
    this.clusterService.getStackInstance(id).subscribe({
      next: (inst) => {
        this.instance.set(inst);
        this.loading.set(false);
        this.loadReservations();
      },
      error: () => this.loading.set(false),
    });
  }

  setTab(tab: TabId): void {
    this.activeTab.set(tab);
  }

  loadReservations(): void {
    if (!this.instanceId) return;
    this.reservationsLoading.set(true);
    this.clusterService.listReservations({ stackInstanceId: this.instanceId }).subscribe({
      next: (result) => {
        this.reservations.set(result.items);
        this.reservationsLoading.set(false);
      },
      error: () => this.reservationsLoading.set(false),
    });
  }

  canDecommission(status: StackInstanceStatus): boolean {
    return ['ACTIVE', 'DEGRADED', 'FAILED'].includes(status);
  }

  onDecommission(): void {
    if (!this.instance()) return;
    if (!confirm(`Decommission stack instance "${this.instance()!.name}"? This will tear down all resources.`)) return;
    this.clusterService.decommissionStack(this.instance()!.id).subscribe({
      next: (updated) => {
        this.instance.set(updated);
      },
    });
  }

  onClaimReservation(id: string): void {
    this.clusterService.claimReservation(id).subscribe({
      next: () => this.loadReservations(),
    });
  }

  onReleaseReservation(id: string): void {
    this.clusterService.releaseReservation(id).subscribe({
      next: () => this.loadReservations(),
    });
  }

  onTestFailover(id: string): void {
    this.clusterService.testFailover(id, 'NOT_TESTED').subscribe({
      next: () => this.loadReservations(),
    });
  }

  getStatusClass(status: StackInstanceStatus): string {
    return 'badge-status-' + status.toLowerCase();
  }

  getHealthClass(health: HealthStatus): string {
    return 'badge-health-' + health.toLowerCase();
  }

  getCompStatusClass(status: ComponentInstanceStatus): string {
    return 'badge-comp-' + status.toLowerCase();
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
}
