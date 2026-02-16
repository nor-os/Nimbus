/**
 * Overview: Cloud backend detail — tabbed view with Overview, Credentials, and IAM Mappings.
 *     Foundation config, tags, and IPAM are managed on the Landing Zone designer page.
 * Architecture: Feature component for cloud backend detail/edit (Section 11)
 * Dependencies: @angular/core, @angular/router, @angular/forms, cloud-backend.service,
 *     landing-zone.service, permission.service, searchable-select
 * Concepts: Credentials are write-only (set but never read back). Connectivity testing
 *     validates credentials against the provider. IAM mappings link Nimbus roles to cloud identities
 *     with provider-specific dynamic forms driven by IAM identity schemas. Landing zone link card
 *     directs users to the dedicated visual designer page.
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
import { ActivatedRoute, Router } from '@angular/router';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { PermissionService } from '@core/services/permission.service';
import { Role } from '@core/models/permission.model';
import {
  CloudBackend,
  CloudBackendIAMMapping,
  CloudBackendIAMMappingInput,
  CloudBackendUpdateInput,
} from '@shared/models/cloud-backend.model';
import { LandingZone } from '@shared/models/landing-zone.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { SchemaFormRendererComponent } from '@shared/components/schema-form/schema-form-renderer.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

interface SchemaProperty {
  type: string;
  title: string;
  description?: string;
  placeholder?: string;
  enum?: string[];
  enumLabels?: string[];
  showWhen?: Record<string, string>;
}

type TabKey = 'overview' | 'credentials' | 'iam';

@Component({
  selector: 'nimbus-backend-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, SearchableSelectComponent, HasPermissionDirective, SchemaFormRendererComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="detail-page">
        @if (loading()) {
          <div class="loading">Loading backend...</div>
        }

        @if (!loading() && !backend()) {
          <div class="empty-state">Backend not found.</div>
        }

        @if (!loading() && backend(); as b) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <button class="btn-back" (click)="goBack()">&larr;</button>
              <div>
                <h1>{{ b.name }}</h1>
                <div class="header-meta">
                  <span class="badge badge-provider">{{ b.providerDisplayName }}</span>
                  <span class="badge" [class]="'badge-' + b.status">{{ b.status }}</span>
                  @if (b.isShared) {
                    <span class="badge badge-shared">Shared</span>
                  }
                </div>
              </div>
            </div>
            <div class="header-actions">
              <button
                *nimbusHasPermission="'cloud:backend:test'"
                class="btn btn-secondary"
                (click)="testConnectivity()"
                [disabled]="testing()"
              >
                {{ testing() ? 'Testing...' : 'Test Connection' }}
              </button>
            </div>
          </div>

          <!-- Landing Zone link card -->
          @if (landingZone()) {
            <div class="lz-card" (click)="openLandingZone()">
              <div class="lz-card-icon">&#9878;</div>
              <div class="lz-card-body">
                <div class="lz-card-title">{{ landingZone()!.name }}</div>
                <div class="lz-card-meta">
                  <span class="badge" [class]="'badge-' + landingZone()!.status.toLowerCase()">{{ landingZone()!.status }}</span>
                  <span class="lz-card-hint">Foundation config, tags, IPAM &amp; visual designer</span>
                </div>
              </div>
              <span class="lz-card-arrow">&rarr;</span>
            </div>
          } @else if (!landingZoneLoading()) {
            <div class="lz-card lz-card-empty">
              <div class="lz-card-icon">&#9878;</div>
              <div class="lz-card-body">
                <div class="lz-card-title">No Landing Zone</div>
                <div class="lz-card-hint">Initialize a landing zone to configure infrastructure blueprints.</div>
              </div>
              <button class="btn btn-primary btn-sm" (click)="initializeLandingZone()" [disabled]="saving()">
                {{ saving() ? 'Creating...' : 'Initialize' }}
              </button>
            </div>
          }

          <!-- Tabs -->
          <div class="tabs">
            <button
              class="tab" [class.active]="activeTab() === 'overview'"
              (click)="activeTab.set('overview')"
            >Overview</button>
            <button
              class="tab" [class.active]="activeTab() === 'credentials'"
              (click)="activeTab.set('credentials')"
            >Credentials</button>
            <button
              class="tab" [class.active]="activeTab() === 'iam'"
              (click)="loadIAMMappings(); activeTab.set('iam')"
            >IAM Mappings ({{ b.iamMappingCount }})</button>
          </div>

          <!-- Overview Tab -->
          @if (activeTab() === 'overview') {
            <div class="tab-content">
              <div class="form-card">
                <div class="form-row">
                  <div class="form-group half">
                    <label class="form-label">Name</label>
                    <input class="form-input" [(ngModel)]="editName" />
                  </div>
                  <div class="form-group half">
                    <label class="form-label">Status</label>
                    <select class="form-input" [(ngModel)]="editStatus">
                      <option value="active">Active</option>
                      <option value="disabled">Disabled</option>
                      <option value="error">Error</option>
                    </select>
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">Description</label>
                  <textarea
                    class="form-input textarea"
                    [(ngModel)]="editDescription"
                    rows="2"
                  ></textarea>
                </div>
                <div class="form-group">
                  <label class="form-label">Endpoint URL</label>
                  <input class="form-input" [(ngModel)]="editEndpointUrl" placeholder="https://..." />
                </div>
                @if (scopeSchema()) {
                  <div class="form-group">
                    <label class="form-label">Scope Config</label>
                    <nimbus-schema-form-renderer
                      [schema]="scopeSchema()!"
                      [values]="scopeValues()"
                      (valuesChange)="scopeValues.set($event)"
                    />
                  </div>
                } @else {
                  <div class="form-group">
                    <label class="form-label">Scope Config (JSON)</label>
                    <textarea class="form-input textarea mono" [(ngModel)]="editScopeConfig" rows="3"
                      placeholder='{"regions": ["us-east-1"]}'></textarea>
                  </div>
                }
                <div class="form-group">
                  <label class="form-check-label">
                    <input type="checkbox" [(ngModel)]="editIsShared" class="form-check" />
                    Share with child tenants
                  </label>
                </div>
                <div class="form-actions">
                  <button
                    *nimbusHasPermission="'cloud:backend:update'"
                    class="btn btn-primary"
                    (click)="saveOverview()"
                    [disabled]="saving()"
                  >
                    {{ saving() ? 'Saving...' : 'Save Changes' }}
                  </button>
                </div>

                <!-- Connectivity info -->
                @if (b.lastConnectivityCheck) {
                  <div class="connectivity-info">
                    <h3>Last Connectivity Check</h3>
                    <div class="info-row">
                      <span class="info-label">Status:</span>
                      <span class="badge"
                        [class.badge-connected]="b.lastConnectivityStatus === 'connected'"
                        [class.badge-failed]="b.lastConnectivityStatus === 'failed'"
                      >{{ b.lastConnectivityStatus }}</span>
                    </div>
                    <div class="info-row">
                      <span class="info-label">Checked:</span>
                      <span>{{ b.lastConnectivityCheck }}</span>
                    </div>
                    @if (b.lastConnectivityError) {
                      <div class="info-row error-text">
                        <span class="info-label">Error:</span>
                        <span>{{ b.lastConnectivityError }}</span>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }

          <!-- Credentials Tab -->
          @if (activeTab() === 'credentials') {
            <div class="tab-content">
              <div class="form-card">
                <div class="cred-status">
                  <span class="info-label">Current status:</span>
                  <span class="badge" [class.badge-has-creds]="b.hasCredentials" [class.badge-no-creds]="!b.hasCredentials">
                    {{ b.hasCredentials ? 'Credentials configured' : 'No credentials' }}
                  </span>
                </div>
                <p class="cred-notice">
                  Credentials are encrypted at rest and never returned by the API. Enter new credentials below to set or replace them.
                </p>

                @if (credSchema()) {
                  @for (field of credSchemaFields(); track field.key) {
                    @if (isCredFieldVisible(field)) {
                      <div class="form-group">
                        <label class="form-label">
                          {{ field.title || field.key }}
                          @if (credSchemaRequired().includes(field.key)) { <span class="required-mark">*</span> }
                        </label>
                        @if (field.enum) {
                          <select class="form-input" [ngModel]="credValues[field.key] || ''" (ngModelChange)="onCredFieldChange(field.key, $event)">
                            <option value="" disabled>Select...</option>
                            @for (opt of field.enum; track opt) { <option [value]="opt">{{ opt }}</option> }
                          </select>
                        } @else if (field.key === 'service_account_json' || field.key === 'private_key') {
                          <textarea class="form-input textarea mono" [ngModel]="credValues[field.key] || ''" (ngModelChange)="onCredFieldChange(field.key, $event)" rows="4"
                            [placeholder]="field.description || ''"></textarea>
                        } @else {
                          <input [type]="isSecretField(field.key) ? 'password' : 'text'" class="form-input"
                            [ngModel]="credValues[field.key] || ''" (ngModelChange)="onCredFieldChange(field.key, $event)"
                            [placeholder]="field.description || ''" />
                        }
                        @if (field.description) { <span class="field-hint">{{ field.description }}</span> }
                      </div>
                    }
                  }
                } @else {
                  <div class="form-group">
                    <label class="form-label">Credentials (JSON)</label>
                    <textarea
                      class="form-input textarea mono"
                      [(ngModel)]="credentialsJson"
                      rows="8"
                      placeholder='{ "auth_type": "api_token", "cluster_url": "https://...", "token_id": "...", "secret": "..." }'
                    ></textarea>
                  </div>
                }

                <div class="form-actions">
                  <button
                    *nimbusHasPermission="'cloud:backend:update'"
                    class="btn btn-primary"
                    (click)="saveCredentials()"
                    [disabled]="saving() || !canSaveCredentials()"
                  >
                    {{ saving() ? 'Saving...' : 'Save Credentials' }}
                  </button>
                </div>
              </div>
            </div>
          }

          <!-- IAM Mappings Tab -->
          @if (activeTab() === 'iam') {
            <div class="tab-content">
              <div class="form-card">
                <div class="section-header">
                  <h3>IAM Mappings</h3>
                  <button
                    *nimbusHasPermission="'cloud:backend:manage_iam'"
                    class="btn btn-primary btn-sm"
                    (click)="openIAMForm()"
                  >
                    Add Mapping
                  </button>
                </div>

                <p class="iam-hint">
                  Map Nimbus roles to cloud-specific identities. When a user with a given role
                  operates on this backend, the mapped cloud identity is used.
                </p>

                @if (showIAMForm()) {
                  <div class="iam-form">
                    <h4>{{ editingMappingId ? 'Edit' : 'New' }} IAM Mapping</h4>

                    <div class="form-row">
                      <div class="form-group half">
                        <label class="form-label">Nimbus Role *</label>
                        <nimbus-searchable-select
                          [options]="roleOptions()"
                          [(ngModel)]="iamRoleId"
                          placeholder="Select role..."
                        ></nimbus-searchable-select>
                      </div>
                      <div class="form-group half">
                        <label class="form-label">Description</label>
                        <input class="form-input" [(ngModel)]="iamDescription" placeholder="e.g. Production admin access" />
                      </div>
                    </div>

                    <!-- Dynamic cloud identity fields from schema -->
                    @if (iamSchema()) {
                      <div class="iam-identity-section">
                        <label class="form-label section-label">{{ iamSchema()!['title'] || 'Cloud Identity' }}</label>
                        @for (field of iamSchemaFields(); track field.key) {
                          @if (isFieldVisible(field)) {
                            <div class="form-group">
                              <label class="form-label">
                                {{ field.title }}
                                @if (iamSchemaRequired().includes(field.key)) {
                                  <span class="required-mark">*</span>
                                }
                              </label>
                              @if (field.enum) {
                                <select
                                  class="form-input"
                                  [ngModel]="iamIdentityValues[field.key] || ''"
                                  (ngModelChange)="onIdentityFieldChange(field.key, $event)"
                                >
                                  <option value="" disabled>Select...</option>
                                  @for (opt of field.enum; track opt; let i = $index) {
                                    <option [value]="opt">{{ field.enumLabels?.[i] || opt }}</option>
                                  }
                                </select>
                              } @else {
                                <input
                                  class="form-input"
                                  [ngModel]="iamIdentityValues[field.key] || ''"
                                  (ngModelChange)="onIdentityFieldChange(field.key, $event)"
                                  [placeholder]="field.placeholder || ''"
                                />
                              }
                              @if (field.description) {
                                <span class="field-hint">{{ field.description }}</span>
                              }
                            </div>
                          }
                        }
                      </div>
                    } @else {
                      <!-- Fallback: raw JSON for unknown providers -->
                      <div class="form-group">
                        <label class="form-label">Cloud Identity (JSON) *</label>
                        <textarea
                          class="form-input textarea mono"
                          [(ngModel)]="iamCloudIdentityRaw"
                          rows="3"
                          placeholder='{ "username": "admin" }'
                        ></textarea>
                      </div>
                    }

                    <div class="form-group">
                      <label class="form-check-label">
                        <input type="checkbox" [(ngModel)]="iamIsActive" class="form-check" />
                        Active
                      </label>
                    </div>

                    <div class="form-actions">
                      <button class="btn btn-secondary btn-sm" (click)="cancelIAMForm()">Cancel</button>
                      <button
                        class="btn btn-primary btn-sm"
                        (click)="saveIAMMapping()"
                        [disabled]="!canSaveIAMMapping()"
                      >{{ editingMappingId ? 'Update' : 'Create' }}</button>
                    </div>
                  </div>
                }

                @if (iamMappings().length === 0 && !showIAMForm()) {
                  <div class="empty-state-sm">No IAM mappings configured. Add one to link a Nimbus role to a cloud identity.</div>
                }

                @if (iamMappings().length > 0) {
                  <div class="table-container">
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Nimbus Role</th>
                          <th>Cloud Identity</th>
                          <th>Description</th>
                          <th>Status</th>
                          <th class="th-actions">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (m of iamMappings(); track m.id) {
                          <tr>
                            <td class="name-cell">{{ m.roleName }}</td>
                            <td>
                              <div class="identity-pills">
                                @for (entry of getIdentityEntries(m.cloudIdentity); track entry.key) {
                                  <span class="identity-pill">
                                    <span class="pill-key">{{ entry.key }}:</span>
                                    <span class="pill-value">{{ entry.value }}</span>
                                  </span>
                                }
                              </div>
                            </td>
                            <td class="desc-cell">{{ m.description || '\u2014' }}</td>
                            <td>
                              <button
                                class="status-toggle"
                                [class.status-active]="m.isActive"
                                [class.status-inactive]="!m.isActive"
                                (click)="toggleIAMActive(m)"
                                title="Click to toggle"
                              >{{ m.isActive ? 'Active' : 'Inactive' }}</button>
                            </td>
                            <td class="td-actions">
                              <button
                                *nimbusHasPermission="'cloud:backend:manage_iam'"
                                class="btn-icon"
                                title="Edit"
                                (click)="editIAMMapping(m)"
                              >&#9998;</button>
                              <button
                                *nimbusHasPermission="'cloud:backend:manage_iam'"
                                class="btn-icon btn-danger"
                                title="Delete"
                                (click)="confirmDeleteIAMMapping(m)"
                              >&times;</button>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>
                }
              </div>
            </div>
          }

        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .detail-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 1rem; }
    .header-left h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .header-meta { display: flex; gap: 0.5rem; margin-top: 0.25rem; }
    .header-actions { display: flex; gap: 0.5rem; }
    .btn-back {
      background: none; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 0.375rem 0.75rem; cursor: pointer; font-size: 1rem; color: #64748b;
    }
    .btn-back:hover { background: #f8fafc; }

    /* -- Tabs --------------------------------------------------------- */
    .tabs {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem;
    }
    .tab {
      padding: 0.625rem 0.875rem; font-size: 0.8125rem; font-weight: 500;
      color: #64748b; background: none; border: none; cursor: pointer;
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      font-family: inherit; transition: color 0.15s; white-space: nowrap;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { animation: fadeIn 0.15s ease-in; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

    /* -- Form card ---------------------------------------------------- */
    .form-card {
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 1.5rem;
    }
    .form-group { margin-bottom: 1rem; }
    .form-label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .textarea { resize: vertical; min-height: 2.5rem; }
    .mono { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.75rem; }
    .mono-cell { font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.75rem; }
    .form-row { display: flex; gap: 1rem; }
    .form-group.half { flex: 1; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }
    .form-check { margin-right: 0.5rem; }
    .form-check-label {
      font-size: 0.8125rem; color: #374151; cursor: pointer;
      display: flex; align-items: center;
    }

    /* -- Connectivity info -------------------------------------------- */
    .connectivity-info {
      margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    .connectivity-info h3 {
      font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem;
    }
    .info-row { font-size: 0.8125rem; color: #374151; margin-bottom: 0.375rem; }
    .info-label { font-weight: 600; margin-right: 0.5rem; color: #64748b; }
    .error-text { color: #dc2626; }

    /* -- Credential tab ----------------------------------------------- */
    .cred-status { margin-bottom: 0.75rem; }
    .cred-notice {
      font-size: 0.8125rem; color: #64748b; margin-bottom: 1rem;
      padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
    }
    .schema-preview {
      margin-top: 1.5rem; padding-top: 1rem; border-top: 1px solid #e2e8f0;
    }
    .schema-preview h3 {
      font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 0.5rem;
    }
    .schema-preview pre {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1rem; font-size: 0.75rem; overflow-x: auto; color: #374151;
    }

    /* -- Section header/hint ------------------------------------------ */
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .section-header h3 {
      font-size: 0.9375rem; font-weight: 600; color: #1e293b; margin: 0;
    }
    .section-hint {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 1rem;
    }
    .iam-hint {
      font-size: 0.8125rem; color: #64748b; margin: 0 0 1rem;
    }
    .iam-form {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 1.25rem; margin-bottom: 1rem;
    }
    .iam-form h4 {
      font-size: 0.875rem; font-weight: 600; color: #1e293b;
      margin: 0 0 1rem; padding-bottom: 0.5rem; border-bottom: 1px solid #e2e8f0;
    }
    .iam-identity-section {
      margin-top: 0.5rem; padding-top: 0.75rem; border-top: 1px dashed #e2e8f0;
    }
    .section-label {
      font-size: 0.875rem !important; font-weight: 600 !important;
      color: #1e293b !important; margin-bottom: 0.75rem !important;
    }
    .required-mark { color: #dc2626; margin-left: 2px; }
    .field-hint {
      display: block; font-size: 0.6875rem; color: #94a3b8; margin-top: 0.25rem;
    }
    .identity-pills {
      display: flex; flex-wrap: wrap; gap: 0.375rem;
    }
    .identity-pill {
      display: inline-flex; align-items: center; gap: 0.25rem;
      padding: 0.125rem 0.5rem; background: #f1f5f9; border-radius: 4px;
      font-size: 0.6875rem; border: 1px solid #e2e8f0;
    }
    .pill-key {
      font-weight: 600; color: #64748b;
    }
    .pill-value {
      color: #1e293b; font-family: 'Cascadia Code', 'Fira Code', monospace;
      max-width: 280px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .desc-cell { color: #64748b; font-size: 0.8125rem; max-width: 200px; }
    .muted { color: #94a3b8; }
    .status-toggle {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; border: none; cursor: pointer;
      transition: background 0.15s, color 0.15s;
    }
    .status-active { background: #dcfce7; color: #166534; }
    .status-active:hover { background: #bbf7d0; }
    .status-inactive { background: #f1f5f9; color: #64748b; }
    .status-inactive:hover { background: #e2e8f0; }
    .empty-state-sm {
      padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* -- Landing Zone card -------------------------------------------- */
    .lz-card {
      display: flex; align-items: center; gap: 1rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1.5rem; cursor: pointer;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .lz-card:hover { border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08); }
    .lz-card-empty { cursor: default; border-style: dashed; }
    .lz-card-empty:hover { border-color: #e2e8f0; box-shadow: none; }
    .lz-card-icon { font-size: 1.5rem; color: #3b82f6; flex-shrink: 0; }
    .lz-card-body { flex: 1; min-width: 0; }
    .lz-card-title { font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .lz-card-meta { display: flex; align-items: center; gap: 0.5rem; margin-top: 0.25rem; }
    .lz-card-hint { font-size: 0.75rem; color: #94a3b8; }
    .lz-card-arrow { font-size: 1.25rem; color: #94a3b8; flex-shrink: 0; }

    /* -- Table -------------------------------------------------------- */
    .table-container {
      overflow-x: auto; border: 1px solid #e2e8f0; border-radius: 6px; margin-top: 1rem;
    }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .table th, .table td {
      padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr { color: #374151; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .th-actions, .td-actions { width: 60px; text-align: right; }

    /* -- Badges ------------------------------------------------------- */
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; text-transform: capitalize;
    }
    .badge-active { background: #dcfce7; color: #166534; }
    .badge-disabled { background: #f1f5f9; color: #64748b; }
    .badge-error { background: #fef2f2; color: #dc2626; }
    .badge-provider { background: #dbeafe; color: #1d4ed8; }
    .badge-shared { background: #ede9fe; color: #6d28d9; }
    .badge-has-creds { background: #dcfce7; color: #166534; }
    .badge-no-creds { background: #fef3c7; color: #92400e; }
    .badge-connected { background: #dcfce7; color: #166534; }
    .badge-failed { background: #fef2f2; color: #dc2626; }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #d1fae5; color: #065f46; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .badge-cidr { background: #dbeafe; color: #1d4ed8; font-family: 'Cascadia Code', 'Fira Code', monospace; }
    .badge-type { background: #f0fdf4; color: #166534; }
    .badge-allocated { background: #dbeafe; color: #1d4ed8; }
    .badge-in_use { background: #dcfce7; color: #166534; }
    .badge-planned { background: #fef3c7; color: #92400e; }
    .badge-released { background: #f1f5f9; color: #64748b; }
    .badge-reserved { background: #ede9fe; color: #6d28d9; }
    .badge-exhausted { background: #fef2f2; color: #dc2626; }
    .badge-env-active { background: #dcfce7; color: #166534; }
    .badge-env-planned { background: #fef3c7; color: #92400e; }
    .badge-env-provisioning { background: #dbeafe; color: #1d4ed8; }
    .badge-env-suspended { background: #f1f5f9; color: #64748b; }
    .badge-env-decommissioning { background: #fef2f2; color: #dc2626; }
    .badge-env-decommissioned { background: #f1f5f9; color: #64748b; }

    /* -- States ------------------------------------------------------- */
    .loading, .empty-state {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* -- Buttons ------------------------------------------------------ */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      border: none;
    }
    .btn-sm { font-size: 0.75rem; padding: 0.375rem 0.75rem; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
      background: #fff; color: #374151; padding: 0.5rem 1rem;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-secondary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }
  `],
})
export class BackendDetailComponent implements OnInit {
  private backendService = inject(CloudBackendService);
  private landingZoneService = inject(LandingZoneService);
  private permissionService = inject(PermissionService);
  private confirmService = inject(ConfirmService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastService = inject(ToastService);

  backend = signal<CloudBackend | null>(null);
  iamMappings = signal<CloudBackendIAMMapping[]>([]);
  roles = signal<Role[]>([]);
  loading = signal(false);
  saving = signal(false);
  testing = signal(false);
  activeTab = signal<TabKey>('overview');
  credentialSchema = signal<Record<string, unknown> | null>(null);
  scopeSchema = signal<Record<string, unknown> | null>(null);
  scopeValues = signal<Record<string, unknown>>({});
  credSchema = signal<Record<string, unknown> | null>(null);
  showIAMForm = signal(false);

  // Landing zone data (for link card)
  landingZone = signal<LandingZone | null>(null);
  landingZoneLoading = signal(false);


  // IAM identity schema from backend
  iamSchema = signal<Record<string, unknown> | null>(null);
  iamSchemaFields = computed(() => {
    const schema = this.iamSchema();
    if (!schema || !schema['properties']) return [];
    const props = schema['properties'] as Record<string, SchemaProperty>;
    return Object.entries(props).map(([key, prop]) => ({
      key,
      ...prop,
    }));
  });
  iamSchemaRequired = computed(() => {
    const schema = this.iamSchema();
    return ((schema?.['required'] as string[]) || []);
  });

  // Credential schema fields (dynamic form)
  credSchemaFields = computed(() => {
    const schema = this.credSchema();
    if (!schema?.['properties']) return [];
    const props = schema['properties'] as Record<string, SchemaProperty>;
    return Object.entries(props).map(([key, prop]) => ({ key, ...prop }));
  });
  credSchemaRequired = computed(() => {
    const schema = this.credSchema();
    const base = (schema?.['required'] as string[]) || [];
    const authType = this.credValues['auth_type'] || '';
    const allOf = (schema?.['allOf'] as { if?: { properties?: { auth_type?: { const?: string } } }; then?: { required?: string[] } }[]) || [];
    let extra: string[] = [];
    for (const rule of allOf) {
      const constVal = rule?.if?.properties?.auth_type?.const;
      if (constVal === authType) {
        extra = rule?.then?.required || [];
      }
    }
    return [...base, ...extra];
  });

  // Role dropdown options
  roleOptions = computed<SelectOption[]>(() =>
    this.roles().map((r) => ({ value: r.id, label: r.name }))
  );

  // Overview edit fields
  editName = '';
  editDescription = '';
  editEndpointUrl = '';
  editStatus = 'active';
  editScopeConfig = '';
  editIsShared = false;

  // Credentials
  credentialsJson = '';
  credValues: Record<string, string> = {};

  // IAM form fields
  iamRoleId = '';
  iamDescription = '';
  iamIdentityValues: Record<string, string> = {};
  iamCloudIdentityRaw = '';
  iamIsActive = true;
  editingMappingId: string | null = null;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadBackend(id);
    }
    this.loadRoles();
  }

  loadBackend(id: string): void {
    this.loading.set(true);
    this.backendService.getBackend(id).subscribe({
      next: (b) => {
        this.backend.set(b);
        if (b) {
          this.editName = b.name;
          this.editDescription = b.description || '';
          this.editEndpointUrl = b.endpointUrl || '';
          this.editStatus = b.status;
          this.editScopeConfig = b.scopeConfig ? JSON.stringify(b.scopeConfig, null, 2) : '';
          this.editIsShared = b.isShared;
          this.scopeValues.set(b.scopeConfig || {});
          this.loadLandingZone();
          // Load schemas for scope and credentials
          this.backendService.getScopeSchema(b.providerName).subscribe({
            next: (schema) => this.scopeSchema.set(schema),
            error: () => {},
          });
          this.backendService.getCredentialSchema(b.providerName).subscribe({
            next: (schema) => this.credSchema.set(schema),
            error: () => {},
          });
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load backend');
        this.loading.set(false);
      },
    });
  }

  saveOverview(): void {
    const b = this.backend();
    if (!b) return;

    let scopeConfig: Record<string, unknown> | null = null;
    if (this.scopeSchema()) {
      const vals = this.scopeValues();
      scopeConfig = Object.keys(vals).length > 0 ? vals : null;
    } else if (this.editScopeConfig.trim()) {
      try {
        scopeConfig = JSON.parse(this.editScopeConfig);
      } catch {
        this.toastService.error('Invalid JSON in Scope Config');
        return;
      }
    }

    const input: CloudBackendUpdateInput = {
      name: this.editName.trim(),
      description: this.editDescription.trim() || null,
      endpointUrl: this.editEndpointUrl.trim() || null,
      status: this.editStatus,
      scopeConfig,
      isShared: this.editIsShared,
    };

    this.saving.set(true);
    this.backendService.updateBackend(b.id, input).subscribe({
      next: (updated) => {
        this.saving.set(false);
        if (updated) {
          this.backend.set(updated);
          this.toastService.success('Backend updated');
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.message || 'Failed to update backend');
      },
    });
  }

  saveCredentials(): void {
    const b = this.backend();
    if (!b) return;

    let credentials: Record<string, unknown>;
    if (this.credSchema()) {
      credentials = {};
      for (const [key, value] of Object.entries(this.credValues)) {
        if (value !== undefined && value !== '') {
          credentials[key] = value;
        }
      }
    } else {
      try {
        credentials = JSON.parse(this.credentialsJson);
      } catch {
        this.toastService.error('Invalid JSON in credentials');
        return;
      }
    }

    this.saving.set(true);
    this.backendService.updateBackend(b.id, { credentials }).subscribe({
      next: (updated) => {
        this.saving.set(false);
        if (updated) {
          this.backend.set(updated);
          this.credentialsJson = '';
          this.credValues = {};
          this.toastService.success('Credentials saved (encrypted)');
        }
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.message || 'Failed to save credentials');
      },
    });
  }

  testConnectivity(): void {
    const b = this.backend();
    if (!b) return;

    this.testing.set(true);
    this.backendService.testConnectivity(b.id).subscribe({
      next: (result) => {
        this.testing.set(false);
        if (result.success) {
          this.toastService.success(result.message);
        } else {
          this.toastService.error(result.message);
        }
        this.loadBackend(b.id);
      },
      error: (err) => {
        this.testing.set(false);
        this.toastService.error(err.message || 'Connectivity test failed');
      },
    });
  }

  loadCredentialSchema(): void {
    const b = this.backend();
    if (!b) return;
    this.backendService.getCredentialSchema(b.providerName).subscribe({
      next: (schema) => this.credentialSchema.set(schema),
      error: () => this.toastService.error('Failed to load credential schema'),
    });
  }

  // -- Credential form helpers -----------------------------------------------

  onCredFieldChange(key: string, value: string): void {
    this.credValues = { ...this.credValues, [key]: value };
  }

  isSecretField(key: string): boolean {
    return ['secret', 'password', 'client_secret', 'secret_access_key', 'private_key'].includes(key);
  }

  isCredFieldVisible(field: { key: string; type: string }): boolean {
    const schema = this.credSchema();
    if (!schema) return true;
    const allOf = (schema['allOf'] as { if?: { properties?: { auth_type?: { const?: string } } }; then?: { required?: string[] } }[]) || [];
    if (allOf.length === 0) return true;

    const authType = this.credValues['auth_type'] || '';
    const baseRequired = (schema['required'] as string[]) || [];

    // Collect all conditional fields across all auth_type rules
    const allConditionalFields = new Set<string>();
    let activeConditionalFields = new Set<string>();
    for (const rule of allOf) {
      const constVal = rule?.if?.properties?.auth_type?.const;
      const reqFields = rule?.then?.required || [];
      for (const f of reqFields) allConditionalFields.add(f);
      if (constVal === authType) {
        activeConditionalFields = new Set(reqFields);
      }
    }

    // Always show base required, auth_type, and non-conditional fields
    if (baseRequired.includes(field.key)) return true;
    // If the field is in a conditional group, show only if it's in the active group
    if (allConditionalFields.has(field.key)) return activeConditionalFields.has(field.key);
    // Non-conditional fields are always visible (e.g. verify_ssl, optional fields)
    return true;
  }

  canSaveCredentials(): boolean {
    if (this.credSchema()) {
      const required = this.credSchemaRequired();
      for (const key of required) {
        if (!this.credValues[key]?.trim()) return false;
      }
      return required.length > 0;
    }
    return !!this.credentialsJson.trim();
  }

  // -- Roles ---------------------------------------------------------------

  private loadRoles(): void {
    this.permissionService.listRoles().subscribe({
      next: (roles) => this.roles.set(roles),
      error: () => this.toastService.error('Failed to load roles'),
    });
  }

  // -- IAM Schema ----------------------------------------------------------

  private loadIAMSchema(): void {
    const b = this.backend();
    if (!b) return;
    this.backendService.getIamIdentitySchema(b.providerName).subscribe({
      next: (schema) => this.iamSchema.set(schema),
      error: () => {},
    });
  }

  // -- IAM Mappings --------------------------------------------------------

  loadIAMMappings(): void {
    const b = this.backend();
    if (!b) return;
    this.backendService.listIAMMappings(b.id).subscribe({
      next: (mappings) => this.iamMappings.set(mappings),
      error: () => this.toastService.error('Failed to load IAM mappings'),
    });
  }

  openIAMForm(): void {
    this.resetIAMForm();
    this.showIAMForm.set(true);
    if (!this.iamSchema()) {
      this.loadIAMSchema();
    }
  }

  cancelIAMForm(): void {
    this.showIAMForm.set(false);
    this.resetIAMForm();
  }

  private resetIAMForm(): void {
    this.iamRoleId = '';
    this.iamDescription = '';
    this.iamIdentityValues = {};
    this.iamCloudIdentityRaw = '';
    this.iamIsActive = true;
    this.editingMappingId = null;
  }

  onIdentityFieldChange(key: string, value: string): void {
    this.iamIdentityValues = { ...this.iamIdentityValues, [key]: value };
  }

  isFieldVisible(field: { key: string; showWhen?: Record<string, string> }): boolean {
    if (!field.showWhen) return true;
    return Object.entries(field.showWhen).every(
      ([depKey, depValue]) => this.iamIdentityValues[depKey] === depValue
    );
  }

  canSaveIAMMapping(): boolean {
    if (!this.iamRoleId) return false;

    if (this.iamSchema()) {
      const required = this.iamSchemaRequired();
      for (const key of required) {
        if (!this.iamIdentityValues[key]?.trim()) return false;
      }
      return true;
    }
    return !!this.iamCloudIdentityRaw.trim();
  }

  private buildCloudIdentity(): Record<string, unknown> | null {
    if (this.iamSchema()) {
      const result: Record<string, unknown> = {};
      for (const field of this.iamSchemaFields()) {
        const val = this.iamIdentityValues[field.key];
        if (val !== undefined && val !== '') {
          if (!this.isFieldVisible(field)) continue;
          result[field.key] = val;
        }
      }
      return result;
    }
    try {
      return JSON.parse(this.iamCloudIdentityRaw);
    } catch {
      this.toastService.error('Invalid JSON in Cloud Identity');
      return null;
    }
  }

  saveIAMMapping(): void {
    const b = this.backend();
    if (!b) return;

    const cloudIdentity = this.buildCloudIdentity();
    if (!cloudIdentity) return;

    if (this.editingMappingId) {
      this.backendService.updateIAMMapping(b.id, this.editingMappingId, {
        cloudIdentity,
        description: this.iamDescription.trim() || null,
        isActive: this.iamIsActive,
      }).subscribe({
        next: (updated) => {
          if (updated) {
            this.iamMappings.update((list) =>
              list.map((m) => (m.id === updated.id ? updated : m))
            );
            this.showIAMForm.set(false);
            this.resetIAMForm();
            this.toastService.success('IAM mapping updated');
          }
        },
        error: (err) => this.toastService.error(err.message || 'Failed to update IAM mapping'),
      });
    } else {
      const input: CloudBackendIAMMappingInput = {
        roleId: this.iamRoleId,
        cloudIdentity,
        description: this.iamDescription.trim() || undefined,
        isActive: this.iamIsActive,
      };

      this.backendService.createIAMMapping(b.id, input).subscribe({
        next: (mapping) => {
          if (mapping) {
            this.iamMappings.update((list) => [...list, mapping]);
            this.showIAMForm.set(false);
            this.resetIAMForm();
            this.toastService.success('IAM mapping created');
            this.loadBackend(b.id);
          }
        },
        error: (err) => this.toastService.error(err.message || 'Failed to create IAM mapping'),
      });
    }
  }

  editIAMMapping(m: CloudBackendIAMMapping): void {
    this.editingMappingId = m.id;
    this.iamRoleId = m.roleId;
    this.iamDescription = m.description || '';
    this.iamIsActive = m.isActive;

    this.iamIdentityValues = {};
    for (const [key, value] of Object.entries(m.cloudIdentity)) {
      this.iamIdentityValues[key] = String(value);
    }
    this.iamCloudIdentityRaw = JSON.stringify(m.cloudIdentity, null, 2);

    if (!this.iamSchema()) {
      this.loadIAMSchema();
    }
    this.showIAMForm.set(true);
  }

  toggleIAMActive(m: CloudBackendIAMMapping): void {
    const b = this.backend();
    if (!b) return;

    this.backendService.updateIAMMapping(b.id, m.id, {
      isActive: !m.isActive,
    }).subscribe({
      next: (updated) => {
        if (updated) {
          this.iamMappings.update((list) =>
            list.map((x) => (x.id === updated.id ? updated : x))
          );
          this.toastService.success(
            `Mapping ${updated.isActive ? 'activated' : 'deactivated'}`
          );
        }
      },
      error: (err) => this.toastService.error(err.message || 'Failed to update mapping'),
    });
  }

  async confirmDeleteIAMMapping(m: CloudBackendIAMMapping): Promise<void> {
    const ok = await this.confirmService.confirm({
      title: 'Delete IAM Mapping',
      message: `Delete the mapping for role "${m.roleName}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    const b = this.backend();
    if (!b) return;

    this.backendService.deleteIAMMapping(b.id, m.id).subscribe({
      next: (deleted) => {
        if (deleted) {
          this.iamMappings.update((list) => list.filter((x) => x.id !== m.id));
          this.toastService.success('IAM mapping deleted');
          this.loadBackend(b.id);
        }
      },
      error: (err) => this.toastService.error(err.message || 'Failed to delete IAM mapping'),
    });
  }

  getIdentityEntries(identity: Record<string, unknown>): { key: string; value: string }[] {
    return Object.entries(identity).map(([key, value]) => ({
      key,
      value: String(value),
    }));
  }

  // -- Landing Zone --------------------------------------------------------

  private loadLandingZone(): void {
    const b = this.backend();
    if (!b) return;
    this.landingZoneLoading.set(true);
    this.landingZoneService.getByBackendId(b.id).subscribe({
      next: (zone) => {
        this.landingZone.set(zone);
        this.landingZoneLoading.set(false);
      },
      error: () => {
        this.landingZoneLoading.set(false);
        this.toastService.error('Failed to load landing zone');
      },
    });
  }

  initializeLandingZone(): void {
    const b = this.backend();
    if (!b) return;

    this.saving.set(true);
    this.backendService.initializeLandingZone(b.id).subscribe({
      next: () => {
        this.saving.set(false);
        this.toastService.success('Landing zone initialized');
        this.loadLandingZone();
      },
      error: (err) => {
        this.saving.set(false);
        this.toastService.error(err.message || 'Failed to initialize landing zone');
      },
    });
  }

  openLandingZone(): void {
    const zone = this.landingZone();
    if (zone) {
      this.router.navigate(['/landing-zones', zone.id]);
    }
  }

  goBack(): void {
    this.router.navigate(['/backends']);
  }
}
