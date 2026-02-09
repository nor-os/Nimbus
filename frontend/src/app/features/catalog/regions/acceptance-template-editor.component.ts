/**
 * Overview: Region acceptance template editor — manage templates and their rules
 *     defining which delivery regions are preferred, accepted, or blocked.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms,
 *     app/core/services/delivery.service, app/shared/services/toast.service,
 *     app/shared/services/confirm.service
 * Concepts: Region acceptance templates, template rules, compliance, delivery regions
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
import { DeliveryService } from '@core/services/delivery.service';
import {
  RegionAcceptanceTemplate,
  RegionAcceptanceTemplateRule,
  RegionAcceptanceTemplateRuleCreateInput,
  DeliveryRegion,
  RegionAcceptanceType,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent } from '@shared/components/searchable-select/searchable-select.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-acceptance-template-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="ate-page">
        <!-- Page header -->
        <div class="page-header">
          <h1>Region Acceptance Templates</h1>
          <button
            class="btn btn-primary"
            *nimbusHasPermission="'catalog:compliance:manage'"
            (click)="showCreateForm.set(true)"
          >
            Create Template
          </button>
        </div>

        <!-- Create template form (inline) -->
        @if (showCreateForm()) {
          <div class="card create-form-card">
            <h3>New Template</h3>
            <div class="form-row">
              <div class="form-group">
                <label for="newTplName">Name *</label>
                <input
                  id="newTplName"
                  class="form-input"
                  [(ngModel)]="newTemplateName"
                  placeholder="Template name"
                />
              </div>
              <div class="form-group form-group-wide">
                <label for="newTplDesc">Description</label>
                <input
                  id="newTplDesc"
                  class="form-input"
                  [(ngModel)]="newTemplateDescription"
                  placeholder="Optional description"
                />
              </div>
            </div>
            <div class="form-actions-inline">
              <button
                class="btn btn-primary btn-sm"
                [disabled]="!newTemplateName.trim() || creatingTemplate()"
                (click)="createTemplate()"
              >
                {{ creatingTemplate() ? 'Creating...' : 'Create' }}
              </button>
              <button class="btn btn-secondary btn-sm" (click)="cancelCreate()">
                Cancel
              </button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="loading">Loading templates...</div>
        }

        @if (!loading()) {
          <div class="split-layout">
            <!-- Left panel: template list -->
            <div class="panel panel-left">
              <div class="panel-header">
                <h2>Templates</h2>
              </div>
              <div class="template-list">
                @for (tpl of templates(); track tpl.id) {
                  <button
                    class="template-item"
                    [class.selected]="selectedTemplate()?.id === tpl.id"
                    (click)="selectTemplate(tpl)"
                  >
                    <span class="template-name">{{ tpl.name }}</span>
                    @if (tpl.isSystem) {
                      <span class="badge badge-system">System</span>
                    }
                  </button>
                } @empty {
                  <div class="empty-list">No templates defined yet.</div>
                }
              </div>
            </div>

            <!-- Right panel: selected template rules -->
            <div class="panel panel-right">
              @if (selectedTemplate(); as tpl) {
                <div class="panel-header">
                  <div class="panel-title-group">
                    <h2>{{ tpl.name }}</h2>
                    @if (tpl.description) {
                      <p class="panel-description">{{ tpl.description }}</p>
                    }
                  </div>
                  <button
                    class="btn btn-danger btn-sm"
                    *nimbusHasPermission="'catalog:compliance:manage'"
                    [disabled]="tpl.isSystem || deletingTemplate()"
                    [title]="tpl.isSystem ? 'System templates cannot be deleted' : 'Delete template'"
                    (click)="deleteTemplate(tpl)"
                  >
                    {{ deletingTemplate() ? 'Deleting...' : 'Delete Template' }}
                  </button>
                </div>

                @if (loadingRules()) {
                  <div class="loading">Loading rules...</div>
                }

                @if (!loadingRules()) {
                  <!-- Rules table -->
                  <div class="rules-table-wrapper">
                    <table class="rules-table">
                      <thead>
                        <tr>
                          <th>Region</th>
                          <th>Acceptance</th>
                          <th>Reason</th>
                          <th class="col-actions">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (rule of rules(); track rule.id) {
                          <tr>
                            <td>{{ regionDisplayName(rule.deliveryRegionId) }}</td>
                            <td>
                              <span
                                class="badge"
                                [class.badge-preferred]="rule.acceptanceType === 'preferred'"
                                [class.badge-accepted]="rule.acceptanceType === 'accepted'"
                                [class.badge-blocked]="rule.acceptanceType === 'blocked'"
                              >
                                {{ rule.acceptanceType }}
                              </span>
                            </td>
                            <td class="cell-reason">{{ rule.reason || '--' }}</td>
                            <td class="col-actions">
                              <button
                                class="btn btn-remove btn-sm"
                                *nimbusHasPermission="'catalog:compliance:manage'"
                                (click)="deleteRule(rule)"
                                title="Delete rule"
                              >
                                Delete
                              </button>
                            </td>
                          </tr>
                        } @empty {
                          <tr>
                            <td colspan="4" class="empty-row">
                              No rules defined for this template.
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  </div>

                  <!-- Add rule form -->
                  <div
                    class="add-rule-form"
                    *nimbusHasPermission="'catalog:compliance:manage'"
                  >
                    <h3>Add Rule</h3>
                    <div class="add-rule-row">
                      <div class="form-group">
                        <label for="ruleRegion">Region *</label>
                        <nimbus-searchable-select [(ngModel)]="newRuleRegionId" [options]="regionOptions()" placeholder="Select region..." />
                      </div>

                      <div class="form-group">
                        <label for="ruleType">Acceptance *</label>
                        <select
                          id="ruleType"
                          class="form-input form-select"
                          [(ngModel)]="newRuleAcceptanceType"
                        >
                          <option value="">-- Select --</option>
                          <option value="preferred">Preferred</option>
                          <option value="accepted">Accepted</option>
                          <option value="blocked">Blocked</option>
                        </select>
                      </div>

                      <div class="form-group form-group-wide">
                        <label for="ruleReason">Reason</label>
                        <input
                          id="ruleReason"
                          class="form-input"
                          [(ngModel)]="newRuleReason"
                          placeholder="Optional reason"
                        />
                      </div>

                      <div class="form-group form-group-action">
                        <label>&nbsp;</label>
                        <button
                          class="btn btn-primary btn-sm"
                          [disabled]="!newRuleRegionId || !newRuleAcceptanceType || addingRule()"
                          (click)="addRule()"
                        >
                          {{ addingRule() ? 'Adding...' : 'Add' }}
                        </button>
                      </div>
                    </div>
                  </div>
                }
              } @else {
                <div class="empty-panel">
                  <p>Select a template from the list to view and manage its rules.</p>
                </div>
              }
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .ate-page { padding: 0; }

    /* ── Page header ──────────────────────────────────────────────── */
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }

    /* ── Create template form ─────────────────────────────────────── */
    .create-form-card {
      margin-bottom: 1.5rem;
    }
    .create-form-card h3 {
      margin: 0 0 1rem; font-size: 1rem; font-weight: 600; color: #1e293b;
    }
    .form-row {
      display: flex; gap: 0.75rem; margin-bottom: 0.75rem;
    }
    .form-actions-inline {
      display: flex; gap: 0.5rem;
    }

    /* ── Loading ───────────────────────────────────────────────────── */
    .loading {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    /* ── Split layout ──────────────────────────────────────────────── */
    .split-layout {
      display: flex; gap: 1.5rem; min-height: 480px;
    }

    .panel {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      display: flex; flex-direction: column;
    }
    .panel-left { width: 280px; min-width: 280px; }
    .panel-right { flex: 1; min-width: 0; }

    .panel-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0;
    }
    .panel-header h2 {
      margin: 0; font-size: 1rem; font-weight: 600; color: #1e293b;
    }
    .panel-title-group { flex: 1; min-width: 0; }
    .panel-description {
      margin: 0.25rem 0 0; font-size: 0.8125rem; color: #64748b;
    }

    /* ── Template list ─────────────────────────────────────────────── */
    .template-list {
      flex: 1; overflow-y: auto; padding: 0.5rem;
    }
    .template-item {
      display: flex; align-items: center; gap: 0.5rem;
      width: 100%; padding: 0.625rem 0.75rem;
      border: 1px solid transparent; border-radius: 6px;
      background: none; cursor: pointer; text-align: left;
      font-family: inherit; font-size: 0.8125rem; color: #374151;
      transition: background 0.15s, border-color 0.15s;
    }
    .template-item:hover { background: #f8fafc; border-color: #e2e8f0; }
    .template-item.selected {
      background: #eff6ff; border-color: #bfdbfe; color: #1e40af;
    }
    .template-name { flex: 1; font-weight: 500; }

    .empty-list {
      padding: 2rem 1rem; text-align: center; color: #94a3b8;
      font-size: 0.8125rem;
    }
    .empty-panel {
      display: flex; align-items: center; justify-content: center;
      flex: 1; padding: 2rem; color: #94a3b8; font-size: 0.875rem;
    }
    .empty-panel p { margin: 0; }

    /* ── Rules table ───────────────────────────────────────────────── */
    .rules-table-wrapper {
      flex: 1; overflow-y: auto; padding: 0;
    }
    .rules-table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .rules-table thead th {
      position: sticky; top: 0; background: #f8fafc;
      padding: 0.625rem 1rem; text-align: left; font-weight: 600;
      color: #64748b; font-size: 0.6875rem; text-transform: uppercase;
      letter-spacing: 0.05em; border-bottom: 1px solid #e2e8f0;
    }
    .rules-table tbody td {
      padding: 0.625rem 1rem; color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .rules-table tbody tr:hover { background: #f8fafc; }
    .col-actions { width: 90px; text-align: right; }
    .cell-reason {
      max-width: 200px; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap; color: #64748b;
    }
    .empty-row {
      text-align: center; color: #94a3b8; padding: 2rem 1rem !important;
    }

    /* ── Add rule form ─────────────────────────────────────────────── */
    .add-rule-form {
      padding: 1rem 1.25rem; border-top: 1px solid #e2e8f0;
    }
    .add-rule-form h3 {
      margin: 0 0 0.75rem; font-size: 0.875rem; font-weight: 600; color: #1e293b;
    }
    .add-rule-row {
      display: flex; gap: 0.75rem; align-items: flex-end; flex-wrap: wrap;
    }

    /* ── Card ──────────────────────────────────────────────────────── */
    .card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem;
    }

    /* ── Form elements ─────────────────────────────────────────────── */
    .form-group { display: flex; flex-direction: column; min-width: 140px; }
    .form-group-wide { flex: 1; min-width: 180px; }
    .form-group-action { min-width: auto; }
    .form-group label {
      display: block; margin-bottom: 0.375rem; font-size: 0.8125rem;
      font-weight: 600; color: #374151;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; transition: border-color 0.15s;
      background: #fff; color: #1e293b;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus {
      border-color: #3b82f6; outline: none;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .form-select { cursor: pointer; }
    .form-select option { background: #fff; color: #1e293b; }

    /* ── Badges ────────────────────────────────────────────────────── */
    .badge {
      display: inline-block; padding: 0.125rem 0.5rem;
      border-radius: 9999px; font-size: 0.6875rem; font-weight: 600;
      text-transform: capitalize;
    }
    .badge-preferred { background: #dbeafe; color: #2563eb; }
    .badge-accepted { background: #dcfce7; color: #16a34a; }
    .badge-blocked { background: #fee2e2; color: #dc2626; }
    .badge-system {
      background: #f0f9ff; color: #0284c7; font-size: 0.625rem;
      padding: 0.0625rem 0.375rem;
    }

    /* ── Buttons ───────────────────────────────────────────────────── */
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      border: none;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1.25rem;
    }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
      padding: 0.5rem 1.25rem;
    }
    .btn-secondary:hover:not(:disabled) { background: #f8fafc; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-danger {
      background: #fff; color: #dc2626; border: 1px solid #fecaca;
      padding: 0.375rem 0.75rem;
    }
    .btn-danger:hover:not(:disabled) { background: #fef2f2; }
    .btn-remove {
      background: #fff; color: #dc2626; border: 1px solid #fecaca;
    }
    .btn-remove:hover:not(:disabled) { background: #fef2f2; }
  `],
})
export class AcceptanceTemplateEditorComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);

  // ── State signals ─────────────────────────────────────────────────
  loading = signal(false);
  loadingRules = signal(false);
  creatingTemplate = signal(false);
  deletingTemplate = signal(false);
  addingRule = signal(false);
  showCreateForm = signal(false);

  templates = signal<RegionAcceptanceTemplate[]>([]);
  selectedTemplate = signal<RegionAcceptanceTemplate | null>(null);
  rules = signal<RegionAcceptanceTemplateRule[]>([]);
  regions = signal<DeliveryRegion[]>([]);

  regionOptions = computed(() => this.regions().map(r => ({ value: r.id, label: r.displayName })));

  // ── Create template form state ────────────────────────────────────
  newTemplateName = '';
  newTemplateDescription = '';

  // ── Add rule form state ───────────────────────────────────────────
  newRuleRegionId = '';
  newRuleAcceptanceType: RegionAcceptanceType | '' = '';
  newRuleReason = '';

  // ── Region lookup map ─────────────────────────────────────────────
  private regionMap = new Map<string, DeliveryRegion>();

  ngOnInit(): void {
    this.loadRegions();
    this.loadTemplates();
  }

  // ── Template selection ────────────────────────────────────────────

  selectTemplate(tpl: RegionAcceptanceTemplate): void {
    this.selectedTemplate.set(tpl);
    this.loadRules(tpl.id);
  }

  // ── Create template ───────────────────────────────────────────────

  createTemplate(): void {
    const name = this.newTemplateName.trim();
    if (!name) return;

    this.creatingTemplate.set(true);
    this.deliveryService
      .createAcceptanceTemplate({
        name,
        description: this.newTemplateDescription.trim() || null,
      })
      .subscribe({
        next: (tpl) => {
          this.creatingTemplate.set(false);
          this.toastService.success(`Template "${tpl.name}" created`);
          this.cancelCreate();
          this.loadTemplates();
          this.selectTemplate(tpl);
        },
        error: (err) => {
          this.creatingTemplate.set(false);
          this.toastService.error(err.message || 'Failed to create template');
        },
      });
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
    this.newTemplateName = '';
    this.newTemplateDescription = '';
  }

  // ── Delete template ───────────────────────────────────────────────

  async deleteTemplate(tpl: RegionAcceptanceTemplate): Promise<void> {
    if (tpl.isSystem) return;

    const confirmed = await this.confirmService.confirm({
      title: 'Delete Template',
      message: `Are you sure you want to delete "${tpl.name}"? This will also remove all its rules.`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;

    this.deletingTemplate.set(true);
    this.deliveryService.deleteAcceptanceTemplate(tpl.id).subscribe({
      next: () => {
        this.deletingTemplate.set(false);
        this.toastService.success(`Template "${tpl.name}" deleted`);
        if (this.selectedTemplate()?.id === tpl.id) {
          this.selectedTemplate.set(null);
          this.rules.set([]);
        }
        this.loadTemplates();
      },
      error: (err) => {
        this.deletingTemplate.set(false);
        this.toastService.error(err.message || 'Failed to delete template');
      },
    });
  }

  // ── Add rule ──────────────────────────────────────────────────────

  addRule(): void {
    const tpl = this.selectedTemplate();
    if (!tpl || !this.newRuleRegionId || !this.newRuleAcceptanceType) return;

    this.addingRule.set(true);
    const input: RegionAcceptanceTemplateRuleCreateInput = {
      deliveryRegionId: this.newRuleRegionId,
      acceptanceType: this.newRuleAcceptanceType as RegionAcceptanceType,
      reason: this.newRuleReason.trim() || null,
    };

    this.deliveryService.addTemplateRule(tpl.id, input).subscribe({
      next: () => {
        this.addingRule.set(false);
        this.toastService.success('Rule added');
        this.newRuleRegionId = '';
        this.newRuleAcceptanceType = '';
        this.newRuleReason = '';
        this.loadRules(tpl.id);
      },
      error: (err) => {
        this.addingRule.set(false);
        this.toastService.error(err.message || 'Failed to add rule');
      },
    });
  }

  // ── Delete rule ───────────────────────────────────────────────────

  async deleteRule(rule: RegionAcceptanceTemplateRule): Promise<void> {
    const regionName = this.regionDisplayName(rule.deliveryRegionId);
    const confirmed = await this.confirmService.confirm({
      title: 'Delete Rule',
      message: `Remove the "${rule.acceptanceType}" rule for ${regionName}?`,
      confirmLabel: 'Delete',
      cancelLabel: 'Cancel',
    });
    if (!confirmed) return;

    this.deliveryService.deleteTemplateRule(rule.id).subscribe({
      next: () => {
        this.toastService.success('Rule deleted');
        const tpl = this.selectedTemplate();
        if (tpl) this.loadRules(tpl.id);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete rule');
      },
    });
  }

  // ── Region display name lookup ────────────────────────────────────

  regionDisplayName(regionId: string): string {
    return this.regionMap.get(regionId)?.displayName || regionId;
  }

  // ── Private data loading ──────────────────────────────────────────

  private loadTemplates(): void {
    this.loading.set(true);
    this.deliveryService.listAcceptanceTemplates().subscribe({
      next: (list) => {
        this.templates.set(list);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load templates');
      },
    });
  }

  private loadRules(templateId: string): void {
    this.loadingRules.set(true);
    this.deliveryService.listTemplateRules(templateId).subscribe({
      next: (list) => {
        this.rules.set(list);
        this.loadingRules.set(false);
      },
      error: (err) => {
        this.loadingRules.set(false);
        this.toastService.error(err.message || 'Failed to load rules');
      },
    });
  }

  private loadRegions(): void {
    this.deliveryService.listRegions({ limit: 500 }).subscribe({
      next: (result) => {
        this.regions.set(result.items);
        this.regionMap.clear();
        for (const r of result.items) {
          this.regionMap.set(r.id, r);
        }
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load regions');
      },
    });
  }
}
