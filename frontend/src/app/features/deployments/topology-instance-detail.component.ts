/**
 * Overview: Topology instance detail — shows deployment metadata, status, parameters, linked CIs.
 * Architecture: Deployment management UI (Section 8)
 * Dependencies: @angular/core, @angular/router, deployment.service
 * Concepts: Standalone component, signals-based, light theme, LayoutComponent wrapper
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { DeploymentService } from '@core/services/deployment.service';
import { Deployment, DeploymentStatus } from '@shared/models/deployment.model';

@Component({
  selector: 'nimbus-topology-instance-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (loading()) {
          <div class="loading-state">Loading topology instance...</div>
        } @else if (!deployment()) {
          <div class="empty-state">Topology instance not found.</div>
        } @else {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/deployments/topologies" class="breadcrumb-link">Topology Instances</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ deployment()!.name }}</span>
              </div>
              <h1 class="page-title">{{ deployment()!.name }}</h1>
            </div>
            <div class="header-actions">
              <span class="badge" [ngClass]="getStatusClass(deployment()!.status)">
                {{ deployment()!.status }}
              </span>
              @if (deployment()!.status === 'PLANNED' || deployment()!.status === 'APPROVED') {
                <button
                  *nimbusHasPermission="'deployment:deployment:execute'"
                  class="btn btn-primary"
                  (click)="onExecute()"
                >Deploy</button>
              }
            </div>
          </div>

          <div class="info-row">
            <div class="info-card">
              <div class="info-label">Topology</div>
              <div class="info-value-sm">
                @if (deployment()!.topologyId) {
                  <a [routerLink]="['/infrastructure/topologies', deployment()!.topologyId]" class="link-primary">
                    {{ deployment()!.topologyId }}
                  </a>
                } @else {
                  --
                }
              </div>
            </div>
            <div class="info-card">
              <div class="info-label">Environment</div>
              <div class="info-value-sm">{{ deployment()!.environmentId }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Deployed By</div>
              <div class="info-value-sm">{{ deployment()!.deployedBy }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Deployed At</div>
              <div class="info-value-sm">{{ deployment()!.deployedAt ? (deployment()!.deployedAt | date:'medium') : '--' }}</div>
            </div>
          </div>

          @if (deployment()!.description) {
            <div class="description-card">
              <h2 class="section-title">Description</h2>
              <p class="description-text">{{ deployment()!.description }}</p>
            </div>
          }

          <div class="json-section">
            <div class="json-card">
              <h2 class="section-title">Parameters</h2>
              @if (deployment()!.parameters) {
                <pre class="json-block">{{ deployment()!.parameters | json }}</pre>
              } @else {
                <p class="text-muted text-sm">No parameters.</p>
              }
            </div>
            <div class="json-card">
              <h2 class="section-title">Resolved Parameters</h2>
              @if (deployment()!.resolvedParameters) {
                <pre class="json-block">{{ deployment()!.resolvedParameters | json }}</pre>
              } @else {
                <p class="text-muted text-sm">No resolved parameters.</p>
              }
            </div>
          </div>

          <div class="components-section">
            <h2 class="section-title">Linked CIs ({{ deployment()!.cis.length || 0 }})</h2>
            @if (deployment()!.cis.length) {
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Component ID</th>
                      <th>CI ID</th>
                      <th>Node ID</th>
                      <th>Version</th>
                      <th>Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (ci of deployment()!.cis; track ci.id) {
                      <tr>
                        <td class="text-bold">{{ ci.componentId }}</td>
                        <td class="text-muted">{{ ci.ciId || '--' }}</td>
                        <td class="text-muted">{{ ci.topologyNodeId || '--' }}</td>
                        <td>{{ ci.componentVersion != null ? ('v' + ci.componentVersion) : '--' }}</td>
                        <td class="text-muted">{{ ci.createdAt | date:'mediumDate' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            } @else {
              <div class="empty-state-sm">No linked configuration items.</div>
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
    .info-value-sm { font-size: 0.85rem; font-weight: 500; color: #1e293b; word-break: break-all; }

    .description-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 20px; }
    .description-text { font-size: 0.875rem; color: #475569; margin: 8px 0 0; }

    .json-section { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
    .json-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; }
    .json-block {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 12px;
      font-size: 0.8rem; color: #1e293b; overflow-x: auto; max-height: 200px;
      font-family: 'Consolas', 'Monaco', monospace; margin: 8px 0 0;
    }

    .components-section { margin-top: 8px; }
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
    .text-bold { font-weight: 500; }
    .text-muted { color: #64748b; }
    .text-sm { font-size: 0.8rem; }
    .link-primary { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .link-primary:hover { text-decoration: underline; }

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

    .empty-state-sm { padding: 32px; text-align: center; color: #94a3b8; font-size: 0.85rem; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }

    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
  `],
})
export class TopologyInstanceDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private deploymentService = inject(DeploymentService);

  deployment = signal<Deployment | null>(null);
  loading = signal(false);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadDeployment(id);
    }
  }

  loadDeployment(id: string): void {
    this.loading.set(true);
    this.deploymentService.getDeployment(id).subscribe({
      next: (d) => {
        this.deployment.set(d);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onExecute(): void {
    if (!this.deployment()) return;
    this.deploymentService.executeDeployment(this.deployment()!.id).subscribe({
      next: (updated) => this.deployment.set(updated),
    });
  }

  getStatusClass(status: DeploymentStatus): string {
    return 'badge-' + status.toLowerCase();
  }
}
