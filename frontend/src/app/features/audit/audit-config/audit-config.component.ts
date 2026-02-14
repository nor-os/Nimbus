/**
 * Overview: Audit configuration page with tabs for retention, redaction rules, chain verification, and archives.
 * Architecture: Feature component for audit configuration (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/audit.service
 * Concepts: Retention policies, per-category overrides, redaction rules, hash chain verification, archive management
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { AuditService } from '@core/services/audit.service';
import {
  AuditLoggingConfig,
  CategoryRetentionOverride,
  EventCategory,
  RetentionPolicy,
  RedactionRule,
  ArchiveEntry,
  VerifyChainResult,
} from '@shared/models/audit.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ToastService } from '@shared/services/toast.service';

type Tab = 'logging' | 'retention' | 'redaction' | 'verification' | 'archives';

const ALL_CATEGORIES: EventCategory[] = [
  'API', 'AUTH', 'DATA', 'PERMISSION', 'SYSTEM', 'SECURITY', 'TENANT', 'USER',
];

const CATEGORY_LABELS: Record<EventCategory, string> = {
  API: 'API Requests',
  AUTH: 'Authentication',
  DATA: 'Data Operations',
  PERMISSION: 'Permissions',
  SYSTEM: 'System Events',
  SECURITY: 'Security',
  TENANT: 'Tenant Management',
  USER: 'User Accounts',
};

interface CategoryRow {
  category: EventCategory;
  label: string;
  hotDays: number;
  coldDays: number;
  hasOverride: boolean;
  editing: boolean;
}

@Component({
  selector: 'nimbus-audit-config',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="config-page">
        <h1>Audit Configuration</h1>

        <div class="tab-bar">
          @for (tab of tabs; track tab.key) {
            <button
              class="tab-btn"
              [class.active]="activeTab() === tab.key"
              (click)="activeTab.set(tab.key)"
            >{{ tab.label }}</button>
          }
        </div>

        <!-- Logging Tab -->
        @if (activeTab() === 'logging') {
          <div class="tab-content">
            <h2>Logging Configuration</h2>
            <p class="description">Control which HTTP requests the audit middleware captures. Service-layer audit events (user CRUD, permission changes, etc.) are always logged.</p>

            <div class="toggle-group">
              <div class="toggle-item">
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="logApiReads" (ngModelChange)="saveLoggingConfig()" />
                  <span class="toggle-text">Log API read requests</span>
                </label>
                <span class="toggle-description">Capture GET, HEAD, and OPTIONS requests (event type: api.request)</span>
              </div>

              <div class="toggle-item">
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="logApiWrites" (ngModelChange)="saveLoggingConfig()" />
                  <span class="toggle-text">Log API write requests</span>
                </label>
                <span class="toggle-description">Capture POST, PUT, PATCH, and DELETE requests (event type: api.request)</span>
              </div>

              <div class="toggle-item">
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="logAuthEvents" (ngModelChange)="saveLoggingConfig()" />
                  <span class="toggle-text">Log authentication events</span>
                </label>
                <span class="toggle-description">Capture login, logout, token refresh, and token revoke events</span>
              </div>

              <div class="toggle-item">
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="logGraphql" (ngModelChange)="saveLoggingConfig()" />
                  <span class="toggle-text">Log GraphQL requests</span>
                </label>
                <span class="toggle-description">Capture all requests to the /graphql endpoint</span>
              </div>

              <div class="toggle-item">
                <label class="toggle-label">
                  <input type="checkbox" [(ngModel)]="logErrors" (ngModelChange)="saveLoggingConfig()" />
                  <span class="toggle-text">Always log errors</span>
                </label>
                <span class="toggle-description">Capture any request with a 4xx or 5xx response regardless of other settings</span>
              </div>
            </div>
          </div>
        }

        <!-- Retention Tab -->
        @if (activeTab() === 'retention') {
          <div class="tab-content">
            <h2>Retention Policy</h2>
            <p class="description">Configure how long audit logs are kept. Set global defaults, then optionally override per event category.</p>

            @if (retention()) {
              <div class="global-retention">
                <h3>Global Defaults</h3>
                <div class="retention-row">
                  <div class="form-group">
                    <label>Hot storage (days)</label>
                    <input type="number" [(ngModel)]="retentionHotDays" min="1" class="form-input" (blur)="saveRetention()" />
                  </div>
                  <div class="form-group">
                    <label>Cold storage (days)</label>
                    <input type="number" [(ngModel)]="retentionColdDays" min="1" class="form-input" (blur)="saveRetention()" />
                  </div>
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input type="checkbox" [(ngModel)]="retentionArchiveEnabled" (ngModelChange)="saveRetention()" />
                      Enable automatic archival
                    </label>
                  </div>
                </div>
              </div>

              <div class="category-overrides">
                <h3>Per-Category Overrides</h3>
                <p class="sub-description">Categories without an override use the global defaults above.</p>
                <table class="table">
                  <thead>
                    <tr>
                      <th>Category</th>
                      <th>Hot (days)</th>
                      <th>Cold (days)</th>
                      <th>Status</th>
                      <th>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (row of categoryRows(); track row.category) {
                      <tr [class.override-row]="row.hasOverride">
                        <td>
                          <span class="category-name">{{ row.label }}</span>
                          <span class="category-key">{{ row.category }}</span>
                        </td>
                        @if (row.editing) {
                          <td>
                            <input
                              type="number"
                              [(ngModel)]="row.hotDays"
                              min="1"
                              class="form-input inline"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              [(ngModel)]="row.coldDays"
                              min="1"
                              class="form-input inline"
                            />
                          </td>
                          <td>
                            <span class="badge badge-editing">Editing</span>
                          </td>
                          <td>
                            <button class="btn-link" (click)="saveCategoryOverride(row)">Save</button>
                            <button class="btn-link" (click)="cancelEditCategory(row)">Cancel</button>
                          </td>
                        } @else {
                          <td>{{ row.hotDays }}</td>
                          <td>{{ row.coldDays }}</td>
                          <td>
                            @if (row.hasOverride) {
                              <span class="badge badge-active">Custom</span>
                            } @else {
                              <span class="badge badge-default">Default</span>
                            }
                          </td>
                          <td>
                            <button class="btn-link" (click)="editCategory(row)">Edit</button>
                            @if (row.hasOverride) {
                              <button class="btn-link danger" (click)="resetCategory(row)">Reset</button>
                            }
                          </td>
                        }
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </div>
        }

        <!-- Redaction Tab -->
        @if (activeTab() === 'redaction') {
          <div class="tab-content">
            <div class="section-header">
              <h2>Redaction Rules</h2>
              <button class="btn btn-primary btn-sm" (click)="showNewRule.set(true)">Add Rule</button>
            </div>

            @if (showNewRule()) {
              <div class="new-rule-form">
                <input
                  type="text"
                  [(ngModel)]="newRulePattern"
                  placeholder="Field pattern (regex)"
                  class="form-input"
                />
                <input
                  type="text"
                  [(ngModel)]="newRuleReplacement"
                  placeholder="Replacement text"
                  class="form-input"
                />
                <input
                  type="number"
                  [(ngModel)]="newRulePriority"
                  placeholder="Priority"
                  class="form-input sm"
                  min="0"
                />
                <button class="btn btn-primary btn-sm" (click)="createRule()">Create</button>
                <button class="btn btn-sm" (click)="showNewRule.set(false)">Cancel</button>
              </div>
            }

            <table class="table">
              <thead>
                <tr>
                  <th>Pattern</th>
                  <th>Replacement</th>
                  <th>Priority</th>
                  <th>Active</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (rule of redactionRules(); track rule.id) {
                  <tr>
                    <td class="mono">{{ rule.field_pattern }}</td>
                    <td>{{ rule.replacement }}</td>
                    <td>{{ rule.priority }}</td>
                    <td>
                      <span class="badge" [class.badge-active]="rule.is_active" [class.badge-inactive]="!rule.is_active">
                        {{ rule.is_active ? 'Yes' : 'No' }}
                      </span>
                    </td>
                    <td>
                      <button class="btn-link" (click)="toggleRule(rule)">
                        {{ rule.is_active ? 'Disable' : 'Enable' }}
                      </button>
                      <button class="btn-link danger" (click)="deleteRule(rule.id)">Delete</button>
                    </td>
                  </tr>
                } @empty {
                  <tr><td colspan="5" class="empty-state">No redaction rules configured</td></tr>
                }
              </tbody>
            </table>
          </div>
        }

        <!-- Verification Tab -->
        @if (activeTab() === 'verification') {
          <div class="tab-content">
            <h2>Hash Chain Verification</h2>
            <p class="description">Verify the integrity of audit log entries using the SHA-256 hash chain.</p>
            <div class="verify-controls">
              <button class="btn btn-primary" (click)="verifyChain()" [disabled]="verifying()">
                {{ verifying() ? 'Verifying...' : 'Verify Chain' }}
              </button>
            </div>
            @if (verifyResult()) {
              <div class="verify-result" [class.valid]="verifyResult()!.valid" [class.invalid]="!verifyResult()!.valid">
                <div class="result-header">
                  {{ verifyResult()!.valid ? 'Chain Valid' : 'Chain Broken' }}
                </div>
                <div class="result-detail">
                  Checked {{ verifyResult()!.total_checked }} entries.
                  @if (verifyResult()!.broken_links.length > 0) {
                    {{ verifyResult()!.broken_links.length }} broken link(s) found.
                  }
                </div>
              </div>
            }
          </div>
        }

        <!-- Archives Tab -->
        @if (activeTab() === 'archives') {
          <div class="tab-content">
            <h2>Archives</h2>
            <table class="table">
              <thead>
                <tr>
                  <th>Key</th>
                  <th>Size</th>
                  <th>Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (archive of archives(); track archive.key) {
                  <tr>
                    <td class="mono">{{ archive.key }}</td>
                    <td>{{ formatSize(archive.size) }}</td>
                    <td>{{ archive.last_modified | date: 'medium' }}</td>
                    <td>
                      <button class="btn-link" (click)="downloadArchive(archive.key)">Download</button>
                    </td>
                  </tr>
                } @empty {
                  <tr><td colspan="4" class="empty-state">No archives available</td></tr>
                }
              </tbody>
            </table>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .config-page { padding: 0; }
    h1 { margin: 0 0 1rem; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    h2 { margin: 0 0 1rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    h3 { margin: 0 0 0.75rem; font-size: 0.9375rem; font-weight: 600; color: #334155; }
    .tab-bar {
      display: flex; gap: 0.25rem; margin-bottom: 1.5rem;
      border-bottom: 2px solid #e2e8f0; padding-bottom: 0;
    }
    .tab-btn {
      padding: 0.5rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; margin-bottom: -2px;
      font-family: inherit; transition: color 0.15s, border-color 0.15s;
    }
    .tab-btn:hover { color: #1e293b; }
    .tab-btn.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab-content {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.5rem;
    }
    .section-header { display: flex; justify-content: space-between; align-items: center; }
    .form-group { margin-bottom: 1rem; }
    .form-group label { display: block; margin-bottom: 0.375rem; font-size: 0.8125rem; font-weight: 500; color: #475569; }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; width: 200px; font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; }
    .form-input.sm { width: 80px; }
    .form-input.inline { width: 80px; }
    .new-rule-form {
      display: flex; gap: 0.5rem; align-items: center; margin-bottom: 1rem;
      padding: 0.75rem; background: #f8fafc; border-radius: 6px;
    }
    .btn-primary {
      background: #3b82f6; color: white; padding: 0.5rem 1rem; border: none;
      border-radius: 6px; font-size: 0.8125rem; font-weight: 500; cursor: pointer;
      font-family: inherit; -webkit-text-fill-color: white;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.375rem 0.75rem; }
    .btn { padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem; font-family: inherit; }
    .btn:hover { background: #f8fafc; }
    .btn-link {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; padding: 0.25rem 0.5rem; font-family: inherit;
    }
    .btn-link:hover { color: #2563eb; text-decoration: underline; }
    .btn-link.danger { color: #dc2626; }
    .btn-link.danger:hover { color: #b91c1c; }
    .table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; margin-top: 0.75rem; }
    .table th, .table td { padding: 0.625rem 0.75rem; text-align: left; border-bottom: 1px solid #f1f5f9; }
    .table th { font-weight: 600; color: #64748b; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }
    .mono { font-family: monospace; font-size: 0.75rem; }
    .badge { padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }
    .badge-default { background: #f1f5f9; color: #64748b; }
    .badge-editing { background: #fef3c7; color: #d97706; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .description { color: #64748b; font-size: 0.875rem; margin-bottom: 1rem; }
    .sub-description { color: #94a3b8; font-size: 0.75rem; margin: -0.5rem 0 0.75rem; }
    .verify-controls { margin-bottom: 1rem; }
    .verify-result { padding: 1rem; border-radius: 8px; margin-top: 1rem; }
    .verify-result.valid { background: #f0fdf4; border: 1px solid #bbf7d0; }
    .verify-result.invalid { background: #fef2f2; border: 1px solid #fecaca; }
    .result-header { font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem; }
    .valid .result-header { color: #16a34a; }
    .invalid .result-header { color: #dc2626; }
    .result-detail { font-size: 0.875rem; color: #475569; }
    .toggle-group { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.5rem; }
    .toggle-item {
      padding: 0.75rem 1rem; border: 1px solid #e2e8f0; border-radius: 8px;
      background: #f8fafc; display: flex; flex-direction: column; gap: 0.25rem;
    }
    .toggle-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; }
    .toggle-text { font-size: 0.875rem; font-weight: 500; color: #1e293b; }
    .toggle-description { font-size: 0.75rem; color: #64748b; margin-left: 1.375rem; }

    /* ── Retention-specific ──────────────────────────── */
    .global-retention { margin-bottom: 2rem; }
    .retention-row { display: flex; gap: 1.5rem; align-items: flex-end; flex-wrap: wrap; }
    .checkbox-label { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; margin-bottom: 0; }
    .category-overrides { margin-top: 0.5rem; }
    .category-name { font-weight: 500; color: #1e293b; }
    .category-key { display: block; font-size: 0.6875rem; color: #94a3b8; font-family: monospace; }
    .override-row { background: #f0f9ff; }
  `],
})
export class AuditConfigComponent implements OnInit {
  private auditService = inject(AuditService);
  private toastService = inject(ToastService);

  activeTab = signal<Tab>('logging');
  loggingConfig = signal<AuditLoggingConfig | null>(null);
  retention = signal<RetentionPolicy | null>(null);
  redactionRules = signal<RedactionRule[]>([]);
  archives = signal<ArchiveEntry[]>([]);
  verifyResult = signal<VerifyChainResult | null>(null);
  verifying = signal(false);
  showNewRule = signal(false);

  retentionHotDays = 30;
  retentionColdDays = 365;
  retentionArchiveEnabled = true;

  logApiReads = false;
  logApiWrites = true;
  logAuthEvents = true;
  logGraphql = true;
  logErrors = true;

  newRulePattern = '';
  newRuleReplacement = '[REDACTED]';
  newRulePriority = 0;

  // Per-category override state
  private categoryOverridesRaw = signal<CategoryRetentionOverride[]>([]);

  categoryRows = computed<CategoryRow[]>(() => {
    const policy = this.retention();
    const overrides = this.categoryOverridesRaw();
    const defaultHot = policy?.hot_days ?? 30;
    const defaultCold = policy?.cold_days ?? 365;
    const overrideMap = new Map(overrides.map(o => [o.event_category, o]));

    return ALL_CATEGORIES.map(cat => {
      const ov = overrideMap.get(cat);
      return {
        category: cat,
        label: CATEGORY_LABELS[cat],
        hotDays: ov ? ov.hot_days : defaultHot,
        coldDays: ov ? ov.cold_days : defaultCold,
        hasOverride: !!ov,
        editing: false,
      };
    });
  });

  tabs = [
    { key: 'logging' as Tab, label: 'Logging' },
    { key: 'retention' as Tab, label: 'Retention' },
    { key: 'redaction' as Tab, label: 'Redaction Rules' },
    { key: 'verification' as Tab, label: 'Chain Verification' },
    { key: 'archives' as Tab, label: 'Archives' },
  ];

  ngOnInit(): void {
    this.loadLoggingConfig();
    this.loadRetention();
    this.loadRedactionRules();
    this.loadArchives();
  }

  saveLoggingConfig(): void {
    this.auditService.updateLoggingConfig({
      log_api_reads: this.logApiReads,
      log_api_writes: this.logApiWrites,
      log_auth_events: this.logAuthEvents,
      log_graphql: this.logGraphql,
      log_errors: this.logErrors,
    }).subscribe({
      next: (config) => {
        this.loggingConfig.set(config);
        this.toastService.success('Logging configuration updated');
      },
      error: () => this.toastService.error('Failed to update logging configuration'),
    });
  }

  saveRetention(): void {
    this.auditService.updateRetentionPolicy({
      hot_days: this.retentionHotDays,
      cold_days: this.retentionColdDays,
      archive_enabled: this.retentionArchiveEnabled,
    }).subscribe({
      next: (policy) => {
        this.applyRetentionPolicy(policy);
        this.toastService.success('Retention policy updated');
      },
      error: () => this.toastService.error('Failed to update retention policy'),
    });
  }

  // ── Category override methods ────────────────────────

  editCategory(row: CategoryRow): void {
    row.editing = true;
  }

  cancelEditCategory(row: CategoryRow): void {
    row.editing = false;
    // Reset values from signal
    const policy = this.retention();
    const overrides = this.categoryOverridesRaw();
    const ov = overrides.find(o => o.event_category === row.category);
    row.hotDays = ov ? ov.hot_days : (policy?.hot_days ?? 30);
    row.coldDays = ov ? ov.cold_days : (policy?.cold_days ?? 365);
  }

  saveCategoryOverride(row: CategoryRow): void {
    if (row.hotDays < 1 || row.coldDays < 1) {
      this.toastService.error('Days must be at least 1');
      return;
    }
    this.auditService.upsertCategoryOverride({
      event_category: row.category,
      hot_days: row.hotDays,
      cold_days: row.coldDays,
    }).subscribe({
      next: () => {
        row.editing = false;
        this.toastService.success(`Retention override saved for ${row.label}`);
        this.loadRetention();
      },
      error: () => this.toastService.error('Failed to save category override'),
    });
  }

  resetCategory(row: CategoryRow): void {
    this.auditService.deleteCategoryOverride(row.category).subscribe({
      next: () => {
        this.toastService.success(`${row.label} reverted to global defaults`);
        this.loadRetention();
      },
      error: () => this.toastService.error('Failed to reset category override'),
    });
  }

  // ── Existing methods ─────────────────────────────────

  createRule(): void {
    if (!this.newRulePattern.trim()) return;
    this.auditService.createRedactionRule({
      field_pattern: this.newRulePattern,
      replacement: this.newRuleReplacement,
      priority: this.newRulePriority,
    }).subscribe({
      next: () => {
        this.toastService.success('Redaction rule created');
        this.showNewRule.set(false);
        this.newRulePattern = '';
        this.newRuleReplacement = '[REDACTED]';
        this.newRulePriority = 0;
        this.loadRedactionRules();
      },
      error: () => this.toastService.error('Failed to create redaction rule'),
    });
  }

  toggleRule(rule: RedactionRule): void {
    this.auditService.updateRedactionRule(rule.id, { is_active: !rule.is_active }).subscribe({
      next: () => this.loadRedactionRules(),
    });
  }

  deleteRule(ruleId: string): void {
    this.auditService.deleteRedactionRule(ruleId).subscribe({
      next: () => {
        this.toastService.success('Redaction rule deleted');
        this.loadRedactionRules();
      },
      error: () => this.toastService.error('Failed to delete redaction rule'),
    });
  }

  verifyChain(): void {
    this.verifying.set(true);
    this.verifyResult.set(null);
    this.auditService.verifyChain().subscribe({
      next: (result) => {
        this.verifyResult.set(result);
        this.verifying.set(false);
      },
      error: () => {
        this.toastService.error('Failed to verify chain');
        this.verifying.set(false);
      },
    });
  }

  downloadArchive(key: string): void {
    this.auditService.getArchiveDownloadUrl(key).subscribe({
      next: (res) => {
        window.open(res.download_url, '_blank');
      },
      error: () => this.toastService.error('Failed to get download URL'),
    });
  }

  formatSize(bytes: number): string {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  private loadLoggingConfig(): void {
    this.auditService.getLoggingConfig().subscribe({
      next: (config) => {
        this.loggingConfig.set(config);
        this.logApiReads = config.log_api_reads;
        this.logApiWrites = config.log_api_writes;
        this.logAuthEvents = config.log_auth_events;
        this.logGraphql = config.log_graphql;
        this.logErrors = config.log_errors;
      },
    });
  }

  private loadRetention(): void {
    this.auditService.getRetentionPolicy().subscribe({
      next: (policy) => this.applyRetentionPolicy(policy),
    });
  }

  private applyRetentionPolicy(policy: RetentionPolicy): void {
    this.retention.set(policy);
    this.retentionHotDays = policy.hot_days;
    this.retentionColdDays = policy.cold_days;
    this.retentionArchiveEnabled = policy.archive_enabled;
    this.categoryOverridesRaw.set(policy.category_overrides ?? []);
  }

  private loadRedactionRules(): void {
    this.auditService.listRedactionRules().subscribe({
      next: (rules) => this.redactionRules.set(rules),
    });
  }

  private loadArchives(): void {
    this.auditService.listArchives().subscribe({
      next: (archives) => this.archives.set(archives),
    });
  }
}
