/**
 * Overview: Environment detail page — tabbed layout with overview, network, access control, security, monitoring, and deployments.
 * Architecture: Feature component for environment detail view (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common, @angular/forms, landing-zone.service, deployment.service, architecture.service
 * Concepts: Environment detail, schema-driven config forms, deployment listing, topology picker, permission gating, light theme
 */
import { Component, ChangeDetectionStrategy, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { DeploymentService } from '@core/services/deployment.service';
import { ArchitectureService } from '@core/services/architecture.service';
import { ComponentService } from '@core/services/component.service';
import { TenantEnvironment } from '@shared/models/landing-zone.model';
import { Deployment } from '@shared/models/deployment.model';
import { Resolver, ResolverConfiguration } from '@shared/models/component.model';
import { ArchitectureTopology } from '@shared/models/architecture.model';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { SchemaFormRendererComponent } from '@shared/components/schema-form/schema-form-renderer.component';

@Component({
  selector: 'nimbus-environment-detail',
  standalone: true,
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    CommonModule,
    RouterLink,
    FormsModule,
    LayoutComponent,
    HasPermissionDirective,
    SchemaFormRendererComponent,
  ],
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (env()) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <a routerLink="/environments" class="back-link">&larr; Environments</a>
              <div class="title-row">
                <h1 class="page-title">{{ env()!.displayName }}</h1>
                <span class="status-badge" [class]="'badge-' + env()!.status.toLowerCase()">{{ env()!.status }}</span>
              </div>
            </div>
          </div>

          <!-- Tab Bar -->
          <div class="tabs">
            <button
              class="tab"
              [class.active]="activeTab() === 'overview'"
              (click)="activeTab.set('overview')"
            >Overview</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'network'"
              (click)="switchTab('network')"
            >Network</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'access'"
              (click)="switchTab('access')"
            >Access Control</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'security'"
              (click)="switchTab('security')"
            >Security</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'monitoring'"
              (click)="switchTab('monitoring')"
            >Monitoring</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'resolvers'"
              (click)="onResolversTab()"
            >Resolvers</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'deployments'"
              (click)="activeTab.set('deployments')"
            >Deployments</button>
          </div>

          <!-- Tab: Overview -->
          @if (activeTab() === 'overview') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Environment Details</h2>
                  <button
                    *nimbusHasPermission="'landingzone:environment:update'"
                    class="btn btn-sm btn-outline"
                    (click)="toggleEdit()"
                  >{{ editing() ? 'Cancel' : 'Edit' }}</button>
                </div>
                <div class="config-grid">
                  <div class="config-item">
                    <span class="config-label">Display Name</span>
                    @if (editing()) {
                      <input class="form-input" [(ngModel)]="editForm.displayName" />
                    } @else {
                      <span class="config-value">{{ env()!.displayName }}</span>
                    }
                  </div>
                  <div class="config-item">
                    <span class="config-label">Name (Slug)</span>
                    <span class="config-value">{{ env()!.name }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Landing Zone ID</span>
                    <span class="config-value mono">{{ env()!.landingZoneId }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Provider</span>
                    <span class="config-value">{{ env()!.providerName || '—' }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Template</span>
                    <span class="config-value">{{ env()!.templateId || '—' }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Status</span>
                    <span class="config-value">
                      <span class="status-badge" [class]="'badge-' + env()!.status.toLowerCase()">{{ env()!.status }}</span>
                    </span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Created By</span>
                    <span class="config-value">{{ env()!.createdBy }}</span>
                  </div>
                  <div class="config-item">
                    <span class="config-label">Created At</span>
                    <span class="config-value">{{ env()!.createdAt | date:'medium' }}</span>
                  </div>
                  <div class="config-item full-width">
                    <span class="config-label">Description</span>
                    @if (editing()) {
                      <input class="form-input" [(ngModel)]="editForm.description" />
                    } @else {
                      <span class="config-value">{{ env()!.description || '—' }}</span>
                    }
                  </div>
                </div>
                @if (editing()) {
                  <div class="form-actions">
                    <button class="btn btn-primary btn-sm" (click)="onSaveConfig()">Save</button>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Tab: Network -->
          @if (activeTab() === 'network') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Network Configuration</h2>
                </div>
                @if (!env()?.providerName) {
                  <p class="empty-hint">No provider associated. Configure a cloud backend first.</p>
                } @else if (networkSchema()) {
                  <nimbus-schema-form-renderer
                    [schema]="networkSchema()!"
                    [values]="networkValues()"
                    (valuesChange)="networkValues.set($event)"
                  />
                  <div class="form-actions">
                    <button class="btn btn-primary btn-sm" (click)="saveNetworkConfig()">Save Network Config</button>
                  </div>
                } @else {
                  <p class="empty-hint">Loading schema...</p>
                }
              </div>
            </div>
          }

          <!-- Tab: Access Control -->
          @if (activeTab() === 'access') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Access Control Configuration</h2>
                </div>
                @if (!env()?.providerName) {
                  <p class="empty-hint">No provider associated. Configure a cloud backend first.</p>
                } @else if (iamSchema()) {
                  <nimbus-schema-form-renderer
                    [schema]="iamSchema()!"
                    [values]="iamValues()"
                    (valuesChange)="iamValues.set($event)"
                  />
                  <div class="form-actions">
                    <button class="btn btn-primary btn-sm" (click)="saveIamConfig()">Save Access Control Config</button>
                  </div>
                } @else {
                  <p class="empty-hint">Loading schema...</p>
                }
              </div>
            </div>
          }

          <!-- Tab: Security -->
          @if (activeTab() === 'security') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Security Configuration</h2>
                </div>
                @if (!env()?.providerName) {
                  <p class="empty-hint">No provider associated. Configure a cloud backend first.</p>
                } @else if (securitySchema()) {
                  <nimbus-schema-form-renderer
                    [schema]="securitySchema()!"
                    [values]="securityValues()"
                    (valuesChange)="securityValues.set($event)"
                  />
                  <div class="form-actions">
                    <button class="btn btn-primary btn-sm" (click)="saveSecurityConfig()">Save Security Config</button>
                  </div>
                } @else {
                  <p class="empty-hint">Loading schema...</p>
                }
              </div>
            </div>
          }

          <!-- Tab: Monitoring -->
          @if (activeTab() === 'monitoring') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Monitoring Configuration</h2>
                </div>
                @if (!env()?.providerName) {
                  <p class="empty-hint">No provider associated. Configure a cloud backend first.</p>
                } @else if (monitoringSchema()) {
                  <nimbus-schema-form-renderer
                    [schema]="monitoringSchema()!"
                    [values]="monitoringValues()"
                    (valuesChange)="monitoringValues.set($event)"
                  />
                  <div class="form-actions">
                    <button class="btn btn-primary btn-sm" (click)="saveMonitoringConfig()">Save Monitoring Config</button>
                  </div>
                } @else {
                  <p class="empty-hint">Loading schema...</p>
                }
              </div>
            </div>
          }

          <!-- Tab: Resolvers -->
          @if (activeTab() === 'resolvers') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Resolver Configurations</h2>
                  <button
                    *nimbusHasPermission="'landingzone:environment:update'"
                    class="btn btn-primary btn-sm"
                    (click)="showResolverForm = true"
                  >Add Config</button>
                </div>

                @if (showResolverForm) {
                  <div class="deploy-form">
                    <div class="form-group">
                      <label class="form-label">Resolver Type</label>
                      <select class="form-input" [(ngModel)]="resolverFormType" (ngModelChange)="onResolverTypeChange()">
                        <option value="">Select resolver...</option>
                        @for (r of availableResolvers(); track r.id) {
                          <option [value]="r.id">{{ r.displayName }}{{ r.category ? ' (' + r.category + ')' : '' }}</option>
                        }
                      </select>
                    </div>
                    @if (selectedResolverDef(); as rDef) {
                      <p class="empty-hint">{{ rDef.description }}</p>
                      @if (rDef.instanceConfigSchema) {
                        <nimbus-schema-form-renderer
                          [schema]="rDef.instanceConfigSchema"
                          [values]="resolverSchemaValues()"
                          (valuesChange)="onResolverSchemaValuesChange($event)"
                        ></nimbus-schema-form-renderer>
                      } @else {
                        @for (f of resolverConfigFields(); track f.key) {
                          <div class="form-group">
                            <label class="form-label">{{ f.label }}</label>
                            <input class="form-input" [(ngModel)]="resolverConfigValues[f.key]" [placeholder]="f.placeholder" />
                          </div>
                        }
                      }
                    }
                    <div class="form-actions">
                      <button class="btn btn-outline btn-sm" (click)="cancelResolverForm()">Cancel</button>
                      <button class="btn btn-primary btn-sm" (click)="saveResolverConfig()" [disabled]="!resolverFormType">Save</button>
                    </div>
                  </div>
                }

                @if (resolverConfigs().length === 0 && !showResolverForm) {
                  <p class="empty-hint">No resolver configurations. Add configs for automatic parameter resolution at deploy time.</p>
                }

                @for (rc of resolverConfigs(); track rc.id) {
                  <div class="resolver-item">
                    <div class="resolver-item-header">
                      <span class="status-badge badge-active">{{ rc.resolverType }}</span>
                      <div class="resolver-config-kv">
                        @for (entry of getConfigEntries(rc.config); track entry.key) {
                          <span class="config-kv-pair">{{ entry.key }}: {{ entry.value }}</span>
                        }
                      </div>
                    </div>
                    <button
                      *nimbusHasPermission="'landingzone:environment:update'"
                      class="action-btn danger"
                      (click)="deleteResolverConfig(rc.id)"
                    >Delete</button>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Tab: Deployments -->
          @if (activeTab() === 'deployments') {
            <div class="tab-content">
              <div class="section-card">
                <div class="section-header">
                  <h2 class="section-title">Deployments</h2>
                  <button
                    *nimbusHasPermission="'deployment:deployment:create'"
                    class="btn btn-primary btn-sm"
                    (click)="showDeploy.set(!showDeploy())"
                  >{{ showDeploy() ? 'Cancel' : 'Deploy Topology' }}</button>
                </div>

                @if (showDeploy()) {
                  <div class="deploy-form">
                    <div class="form-grid">
                      <div class="form-group">
                        <label class="form-label">Topology</label>
                        <select class="form-input" [(ngModel)]="deployForm.topologyId">
                          <option value="">Select published topology...</option>
                          @for (t of topologies(); track t.id) {
                            <option [value]="t.id">{{ t.name }} (v{{ t.version }})</option>
                          }
                        </select>
                      </div>
                      <div class="form-group">
                        <label class="form-label">Deployment Name</label>
                        <input type="text" class="form-input" [(ngModel)]="deployForm.name" placeholder="e.g. prod-deploy-1" />
                      </div>
                      <div class="form-group full-width">
                        <label class="form-label">Description</label>
                        <input type="text" class="form-input" [(ngModel)]="deployForm.description" placeholder="Optional description" />
                      </div>
                    </div>
                    <div class="form-actions">
                      <button
                        class="btn btn-primary btn-sm"
                        (click)="onDeploy()"
                        [disabled]="!deployForm.topologyId || !deployForm.name"
                      >Create Deployment</button>
                    </div>
                  </div>
                }

                <div class="table-container">
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Topology</th>
                        <th>Status</th>
                        <th>Created By</th>
                        <th>Created At</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (dep of deployments(); track dep.id) {
                        <tr>
                          <td class="name-cell">{{ dep.name }}</td>
                          <td>{{ getTopologyName(dep.topologyId) }}</td>
                          <td>
                            <span class="status-badge" [class]="'badge-' + dep.status.toLowerCase().replace('_', '-')">
                              {{ dep.status.replace('_', ' ') }}
                            </span>
                          </td>
                          <td>{{ dep.deployedBy }}</td>
                          <td>{{ dep.createdAt | date:'short' }}</td>
                          <td>
                            <button
                              *nimbusHasPermission="'deployment:deployment:delete'"
                              class="action-btn danger"
                              (click)="onDeleteDeployment(dep)"
                            >Delete</button>
                          </td>
                        </tr>
                      }
                      @if (deployments().length === 0 && !loadingDeploys()) {
                        <tr>
                          <td colspan="6" class="empty-cell">No deployments yet. Deploy a topology to get started.</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          }
        } @else if (loading()) {
          <div class="loading-text">Loading environment...</div>
        } @else {
          <div class="loading-text">Environment not found</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { margin-bottom: 1rem; }
    .header-left { display: flex; flex-direction: column; gap: 4px; }
    .back-link { font-size: 0.8125rem; color: #3b82f6; text-decoration: none; margin-bottom: 4px; }
    .back-link:hover { text-decoration: underline; }
    .title-row { display: flex; align-items: center; gap: 12px; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }

    /* Tab bar */
    .tabs { display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem; }
    .tab {
      padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 500; color: #64748b;
      background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; font-family: inherit;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { }

    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
      cursor: pointer; text-decoration: none; border: none; display: inline-flex;
      align-items: center; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm { padding: 6px 12px; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }

    .section-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 20px;
      margin-bottom: 16px;
    }
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
    .section-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0; }

    .config-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .config-item { display: flex; flex-direction: column; gap: 4px; }
    .config-item.full-width { grid-column: 1 / -1; }
    .config-label { font-size: 0.6875rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    .config-value { font-size: 0.8125rem; color: #374151; }
    .config-value.mono { font-family: monospace; font-size: 0.75rem; color: #64748b; word-break: break-all; }

    .form-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    .form-group.full-width { grid-column: 1 / -1; }
    .form-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em; }
    .form-input {
      padding: 8px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      outline: none;
      font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; }
    .form-actions { display: flex; gap: 8px; margin-top: 16px; }

    .deploy-form {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 16px;
      margin-bottom: 16px;
    }

    .table-container {
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .table { width: 100%; border-collapse: collapse; }
    .table th {
      padding: 10px 16px;
      text-align: left;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
      border-bottom: 1px solid #e2e8f0;
      background: #fafbfc;
    }
    .table td {
      padding: 12px 16px;
      font-size: 0.8125rem;
      color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .table tr:last-child td { border-bottom: none; }
    .table tr:hover td { background: #fafbfc; }
    .name-cell { font-weight: 500; color: #1e293b; }

    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-planned { background: #fef3c7; color: #92400e; }
    .badge-pending-approval { background: #dbeafe; color: #1e40af; }
    .badge-approved { background: #d1fae5; color: #065f46; }
    .badge-deploying { background: #dbeafe; color: #1e40af; }
    .badge-deployed { background: #d1fae5; color: #065f46; }
    .badge-failed { background: #fee2e2; color: #991b1b; }
    .badge-rolled-back { background: #f1f5f9; color: #64748b; }
    .badge-provisioning { background: #dbeafe; color: #1e40af; }
    .badge-active { background: #d1fae5; color: #065f46; }
    .badge-suspended { background: #fee2e2; color: #991b1b; }
    .badge-decommissioning { background: #fef3c7; color: #92400e; }
    .badge-decommissioned { background: #f1f5f9; color: #64748b; }

    .action-btn {
      padding: 4px 8px;
      border: none;
      background: none;
      color: #3b82f6;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      font-family: inherit;
    }
    .action-btn:hover { text-decoration: underline; }
    .action-btn.danger { color: #ef4444; }
    .empty-cell {
      text-align: center;
      padding: 32px 16px !important;
      color: #94a3b8;
    }
    .empty-hint { color: #94a3b8; font-size: 0.8125rem; padding: 16px 0; }
    .loading-text { color: #94a3b8; font-size: 0.875rem; padding: 32px 0; text-align: center; }

    .resolver-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 10px 16px; border: 1px solid #e2e8f0; border-radius: 6px;
      margin-bottom: 8px; background: #f8fafc;
    }
    .resolver-item-header { display: flex; align-items: center; gap: 12px; flex: 1; flex-wrap: wrap; }
    .resolver-config-kv { display: flex; gap: 12px; flex-wrap: wrap; }
    .config-kv-pair { font-size: 0.75rem; color: #374151; background: #fff; padding: 2px 8px; border-radius: 4px; border: 1px solid #e2e8f0; }
  `],
})
export class EnvironmentDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private lzService = inject(LandingZoneService);
  private deploymentService = inject(DeploymentService);
  private archService = inject(ArchitectureService);
  private componentService = inject(ComponentService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);

  /** Core state */
  env = signal<TenantEnvironment | null>(null);
  activeTab = signal<string>('overview');
  loading = signal(true);
  editing = signal(false);

  /** Schema signals for config tabs */
  networkSchema = signal<Record<string, unknown> | null>(null);
  iamSchema = signal<Record<string, unknown> | null>(null);
  securitySchema = signal<Record<string, unknown> | null>(null);
  monitoringSchema = signal<Record<string, unknown> | null>(null);

  /** Config value signals */
  networkValues = signal<Record<string, unknown>>({});
  iamValues = signal<Record<string, unknown>>({});
  securityValues = signal<Record<string, unknown>>({});
  monitoringValues = signal<Record<string, unknown>>({});

  /** Deployment state */
  deployments = signal<Deployment[]>([]);
  topologies = signal<ArchitectureTopology[]>([]);
  loadingDeploys = signal(false);
  showDeploy = signal(false);

  /** Resolver state */
  availableResolvers = signal<Resolver[]>([]);
  resolverConfigs = signal<ResolverConfiguration[]>([]);
  showResolverForm = false;
  resolverFormType = '';
  resolverConfigValues: Record<string, string> = {};
  resolverSchemaValues = signal<Record<string, unknown>>({});

  selectedResolverDef = computed((): Resolver | null => {
    const id = this.resolverFormType;
    return this.availableResolvers().find(r => r.id === id) || null;
  });

  resolverConfigFields = computed((): { key: string; label: string; placeholder: string }[] => {
    const def = this.selectedResolverDef();
    if (!def?.inputSchema) return [];
    const schema = def.inputSchema as Record<string, unknown>;
    const props = (schema['properties'] || {}) as Record<string, Record<string, unknown>>;
    return Object.entries(props).map(([key, prop]) => ({
      key,
      label: (prop['title'] as string) || key,
      placeholder: (prop['description'] as string) || '',
    }));
  });

  editForm = { displayName: '', description: '' };
  deployForm = { topologyId: '', name: '', description: '' };

  private envId = '';

  ngOnInit(): void {
    this.envId = this.route.snapshot.paramMap.get('id') ?? '';
    this.loadEnvironment();
    this.loadDeployments();
    this.loadTopologies();
  }

  loadEnvironment(): void {
    this.loading.set(true);
    this.lzService.getTenantEnvironment(this.envId).subscribe({
      next: (e: TenantEnvironment | null) => {
        this.env.set(e);
        if (e) {
          this.editForm = { displayName: e.displayName, description: e.description ?? '' };
          this.networkValues.set(e.networkConfig ?? {});
          this.iamValues.set(e.iamConfig ?? {});
          this.securityValues.set(e.securityConfig ?? {});
          this.monitoringValues.set(e.monitoringConfig ?? {});
          if (e.providerName) {
            this.loadAllSchemas(e.providerName);
          }
        }
        this.loading.set(false);
      },
      error: () => {
        this.toast.error('Failed to load environment');
        this.loading.set(false);
      },
    });
  }

  loadDeployments(): void {
    this.loadingDeploys.set(true);
    this.deploymentService.listDeployments(this.envId).subscribe({
      next: (deps) => {
        this.deployments.set(deps);
        this.loadingDeploys.set(false);
      },
      error: () => {
        this.toast.error('Failed to load deployments');
        this.loadingDeploys.set(false);
      },
    });
  }

  loadTopologies(): void {
    this.archService.listTopologies({ status: 'PUBLISHED' }).subscribe({
      next: (ts) => this.topologies.set(ts),
      error: () => {},
    });
  }

  /** Preload all four config schemas for the provider */
  private loadAllSchemas(providerName: string): void {
    if (!this.networkSchema()) {
      this.lzService.getEnvNetworkConfigSchema(providerName).subscribe({
        next: (s: Record<string, unknown> | null) => this.networkSchema.set(s),
        error: () => {},
      });
    }
    if (!this.iamSchema()) {
      this.lzService.getEnvIamConfigSchema(providerName).subscribe({
        next: (s: Record<string, unknown> | null) => this.iamSchema.set(s),
        error: () => {},
      });
    }
    if (!this.securitySchema()) {
      this.lzService.getEnvSecurityConfigSchema(providerName).subscribe({
        next: (s: Record<string, unknown> | null) => this.securitySchema.set(s),
        error: () => {},
      });
    }
    if (!this.monitoringSchema()) {
      this.lzService.getEnvMonitoringConfigSchema(providerName).subscribe({
        next: (s: Record<string, unknown> | null) => this.monitoringSchema.set(s),
        error: () => {},
      });
    }
  }

  /** Switch to a config tab, ensuring schema is loaded */
  switchTab(tab: string): void {
    this.activeTab.set(tab);
    const provider = this.env()?.providerName;
    if (!provider) return;

    switch (tab) {
      case 'network':
        if (!this.networkSchema()) {
          this.lzService.getEnvNetworkConfigSchema(provider).subscribe({
            next: (s: Record<string, unknown> | null) => this.networkSchema.set(s),
            error: () => {},
          });
        }
        break;
      case 'access':
        if (!this.iamSchema()) {
          this.lzService.getEnvIamConfigSchema(provider).subscribe({
            next: (s: Record<string, unknown> | null) => this.iamSchema.set(s),
            error: () => {},
          });
        }
        break;
      case 'security':
        if (!this.securitySchema()) {
          this.lzService.getEnvSecurityConfigSchema(provider).subscribe({
            next: (s: Record<string, unknown> | null) => this.securitySchema.set(s),
            error: () => {},
          });
        }
        break;
      case 'monitoring':
        if (!this.monitoringSchema()) {
          this.lzService.getEnvMonitoringConfigSchema(provider).subscribe({
            next: (s: Record<string, unknown> | null) => this.monitoringSchema.set(s),
            error: () => {},
          });
        }
        break;
    }
  }

  toggleEdit(): void {
    if (this.editing()) {
      this.editing.set(false);
      const e = this.env();
      if (e) {
        this.editForm = { displayName: e.displayName, description: e.description ?? '' };
      }
    } else {
      this.editing.set(true);
    }
  }

  getTopologyName(id: string): string {
    const t = this.topologies().find(t => t.id === id);
    return t?.name ?? id.slice(0, 8) + '...';
  }

  onSaveConfig(): void {
    this.lzService.updateTenantEnvironment(this.envId, {
      displayName: this.editForm.displayName || undefined,
      description: this.editForm.description || undefined,
    }).subscribe({
      next: () => {
        this.toast.success('Environment updated');
        this.editing.set(false);
        this.loadEnvironment();
      },
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to update'),
    });
  }

  saveNetworkConfig(): void {
    this.lzService.updateTenantEnvironment(this.envId, {
      networkConfig: this.networkValues(),
    }).subscribe({
      next: () => this.toast.success('Network configuration saved'),
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to save network config'),
    });
  }

  saveIamConfig(): void {
    this.lzService.updateTenantEnvironment(this.envId, {
      iamConfig: this.iamValues(),
    }).subscribe({
      next: () => this.toast.success('Access control configuration saved'),
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to save access control config'),
    });
  }

  saveSecurityConfig(): void {
    this.lzService.updateTenantEnvironment(this.envId, {
      securityConfig: this.securityValues(),
    }).subscribe({
      next: () => this.toast.success('Security configuration saved'),
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to save security config'),
    });
  }

  saveMonitoringConfig(): void {
    this.lzService.updateTenantEnvironment(this.envId, {
      monitoringConfig: this.monitoringValues(),
    }).subscribe({
      next: () => this.toast.success('Monitoring configuration saved'),
      error: (e: { message?: string }) => this.toast.error(e.message || 'Failed to save monitoring config'),
    });
  }

  onDeploy(): void {
    if (!this.deployForm.topologyId || !this.deployForm.name) return;
    this.deploymentService.createDeployment({
      environmentId: this.envId,
      topologyId: this.deployForm.topologyId,
      name: this.deployForm.name,
      description: this.deployForm.description || undefined,
    }).subscribe({
      next: () => {
        this.toast.success('Deployment created (PLANNED)');
        this.showDeploy.set(false);
        this.deployForm = { topologyId: '', name: '', description: '' };
        this.loadDeployments();
      },
      error: (e) => this.toast.error(e.message || 'Failed to create deployment'),
    });
  }

  async onDeleteDeployment(dep: Deployment): Promise<void> {
    const ok = await this.confirm.confirm({
      title: 'Delete Deployment',
      message: `Delete deployment "${dep.name}"?`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.deploymentService.deleteDeployment(dep.id).subscribe({
      next: () => {
        this.toast.success('Deployment deleted');
        this.loadDeployments();
      },
      error: (e: Error) => this.toast.error(e.message || 'Failed to delete'),
    });
  }

  // ── Resolver config methods ────────────────────────────────────

  onResolversTab(): void {
    this.activeTab.set('resolvers');
    this.loadResolverData();
  }

  private loadResolverData(): void {
    this.componentService.listResolvers().subscribe({
      next: resolvers => this.availableResolvers.set(resolvers),
    });
    this.componentService.listResolverConfigurations(undefined, this.envId).subscribe({
      next: configs => this.resolverConfigs.set(configs),
    });
  }

  onResolverTypeChange(): void {
    this.resolverConfigValues = {};
    this.resolverSchemaValues.set({});
  }

  onResolverSchemaValuesChange(values: Record<string, unknown>): void {
    this.resolverSchemaValues.set(values);
  }

  cancelResolverForm(): void {
    this.showResolverForm = false;
    this.resolverFormType = '';
    this.resolverConfigValues = {};
    this.resolverSchemaValues.set({});
  }

  saveResolverConfig(): void {
    if (!this.resolverFormType) return;

    // Use schema-driven values if the selected resolver has instanceConfigSchema
    const rDef = this.selectedResolverDef();
    const config = rDef?.instanceConfigSchema
      ? { ...this.resolverSchemaValues() }
      : { ...this.resolverConfigValues };

    this.componentService.setResolverConfiguration({
      resolverId: this.resolverFormType,
      config,
      environmentId: this.envId,
    }).subscribe({
      next: () => {
        this.cancelResolverForm();
        this.loadResolverData();
        this.toast.success('Resolver configuration saved');
      },
      error: (err: Error) => this.toast.error(err.message || 'Failed to save resolver config'),
    });
  }

  deleteResolverConfig(configId: string): void {
    this.componentService.deleteResolverConfiguration(configId).subscribe({
      next: () => {
        this.loadResolverData();
        this.toast.success('Resolver configuration deleted');
      },
      error: (err: Error) => this.toast.error(err.message || 'Failed to delete resolver config'),
    });
  }

  getConfigEntries(config: Record<string, unknown>): { key: string; value: string }[] {
    return Object.entries(config).map(([key, val]) => ({
      key,
      value: String(val),
    }));
  }
}
