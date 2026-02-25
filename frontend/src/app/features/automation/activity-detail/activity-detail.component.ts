/**
 * Overview: Activity detail — create new activities or view/edit existing ones with tabbed interface
 *     for versions, config mutations, executions, and test execution.
 * Architecture: Feature component for activity detail (Section 11.5)
 * Dependencies: @angular/core, @angular/router, AutomatedActivityService, MonacoEditorComponent
 * Concepts: Activity versioning, config mutation visualization, test execution, Monaco editor
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
import { AutomatedActivityService } from '@core/services/automated-activity.service';
import {
  AutomatedActivity,
  AutomatedActivityVersion,
  ActivityExecution,
  ActivityVersionCreateInput,
  AutomatedActivityCreateInput,
} from '@shared/models/automated-activity.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { MonacoEditorComponent } from '@shared/components/monaco-editor/monaco-editor.component';
import { ToastService } from '@shared/services/toast.service';

type TabKey = 'definition' | 'versions' | 'mutations' | 'executions' | 'test';

@Component({
  selector: 'nimbus-activity-detail',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective, MonacoEditorComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="detail-page">
        @if (loading()) {
          <div class="loading">Loading activity...</div>
        }

        <!-- ══════════════ CREATE MODE ══════════════ -->
        @if (!loading() && isCreateMode()) {
          <div class="page-header">
            <div class="header-left">
              <button class="btn-back" (click)="goBack()">&larr;</button>
              <div>
                <h1>New Activity</h1>
                <p class="page-subtitle">Define a new automated activity</p>
              </div>
            </div>
          </div>

          <div class="create-form">
            <div class="form-section">
              <h2>Activity Definition</h2>
              <div class="form-grid">
                <div class="form-group">
                  <label>Name <span class="required">*</span></label>
                  <input type="text" [ngModel]="createForm.name" (ngModelChange)="createForm.name = $event"
                         placeholder="e.g. Resize Disk" />
                </div>
                <div class="form-group">
                  <label>Slug</label>
                  <input type="text" [ngModel]="createForm.slug" (ngModelChange)="createForm.slug = $event"
                         placeholder="Auto-generated from name" />
                  <span class="field-hint">URL-safe identifier. Leave empty to auto-generate.</span>
                </div>
                <div class="form-group full-width">
                  <label>Description</label>
                  <textarea [ngModel]="createForm.description" (ngModelChange)="createForm.description = $event"
                            placeholder="Describe what this activity does..." rows="3"></textarea>
                </div>
                <div class="form-group">
                  <label>Category</label>
                  <select [ngModel]="createForm.category" (ngModelChange)="createForm.category = $event">
                    <option value="">— Select —</option>
                    <option value="compute">Compute</option>
                    <option value="storage">Storage</option>
                    <option value="network">Network</option>
                    <option value="security">Security</option>
                    <option value="backup">Backup</option>
                    <option value="monitoring">Monitoring</option>
                    <option value="database">Database</option>
                    <option value="identity">Identity</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Operation Kind</label>
                  <select [ngModel]="createForm.operationKind" (ngModelChange)="createForm.operationKind = $event">
                    <option value="CREATE">Create</option>
                    <option value="READ">Read</option>
                    <option value="UPDATE">Update</option>
                    <option value="DELETE">Delete</option>
                    <option value="REMEDIATE">Remediate</option>
                    <option value="VALIDATE">Validate</option>
                    <option value="BACKUP">Backup</option>
                    <option value="RESTORE">Restore</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Implementation Type</label>
                  <select [ngModel]="createForm.implementationType" (ngModelChange)="createForm.implementationType = $event">
                    <option value="PYTHON_SCRIPT">Python Script</option>
                    <option value="SHELL_SCRIPT">Shell Script</option>
                    <option value="HTTP_WEBHOOK">HTTP Webhook</option>
                    <option value="PULUMI_OPERATION">Pulumi Operation</option>
                    <option value="MANUAL">Manual</option>
                  </select>
                </div>
                <div class="form-group">
                  <label>Timeout (seconds)</label>
                  <input type="number" [ngModel]="createForm.timeoutSeconds"
                         (ngModelChange)="createForm.timeoutSeconds = $event" min="10" max="86400" />
                </div>
                <div class="form-group checkbox-group">
                  <label>
                    <input type="checkbox" [ngModel]="createForm.idempotent"
                           (ngModelChange)="createForm.idempotent = $event" />
                    Idempotent
                  </label>
                  <span class="field-hint">Safe to retry without side effects</span>
                </div>
              </div>
            </div>

            <div class="form-section">
              <h2>Initial Source Code</h2>
              <p class="section-desc">Write the initial implementation. This becomes Version 1 (draft).</p>
              <nimbus-monaco-editor
                [value]="createForm.initialSourceCode"
                [language]="createFormLanguage()"
                [height]="'400px'"
                (valueChange)="createForm.initialSourceCode = $event"
              />
            </div>

            <div class="form-section">
              <h2>Schemas (optional)</h2>
              <div class="schema-panels">
                <div class="schema-panel">
                  <h3>Input Schema (JSON Schema)</h3>
                  <nimbus-monaco-editor
                    [value]="createForm.inputSchemaJson"
                    language="json"
                    [height]="'180px'"
                    (valueChange)="createForm.inputSchemaJson = $event"
                  />
                </div>
                <div class="schema-panel">
                  <h3>Output Schema (JSON Schema)</h3>
                  <nimbus-monaco-editor
                    [value]="createForm.outputSchemaJson"
                    language="json"
                    [height]="'180px'"
                    (valueChange)="createForm.outputSchemaJson = $event"
                  />
                </div>
              </div>
            </div>

            <div class="form-actions">
              <button class="btn btn-secondary" (click)="goBack()">Cancel</button>
              <button class="btn btn-primary" [disabled]="saving() || !createForm.name.trim()"
                      (click)="submitCreate()">
                {{ saving() ? 'Creating...' : 'Create Activity' }}
              </button>
            </div>
          </div>
        }

        <!-- ══════════════ EDIT/VIEW MODE ══════════════ -->
        @if (!loading() && !isCreateMode() && !activity()) {
          <div class="empty-state">Activity not found.</div>
        }

        @if (!loading() && !isCreateMode() && activity(); as a) {
          <!-- Header -->
          <div class="page-header">
            <div class="header-left">
              <button class="btn-back" (click)="goBack()">&larr;</button>
              <div>
                <h1>{{ a.name }}</h1>
                <div class="header-meta">
                  <span class="badge badge-operation">{{ a.operationKind }}</span>
                  <span class="badge badge-type">{{ a.implementationType.replace('_', ' ') }}</span>
                  <span class="badge" [class]="a.scope === 'COMPONENT' ? 'badge-component' : 'badge-workflow'">
                    {{ a.scope === 'COMPONENT' ? 'Component' : 'Workflow' }}
                  </span>
                  @if (a.isSystem) {
                    <span class="badge badge-system">System</span>
                  }
                  <span class="slug-text">{{ a.slug }}</span>
                </div>
              </div>
            </div>
            <div class="header-actions">
              @if (selectedVersion() && !selectedVersion()!.publishedAt) {
                <button class="btn btn-success" *nimbusHasPermission="'automation:activity:publish'"
                        (click)="publishVersion()">Publish v{{ selectedVersion()!.version }}</button>
              }
              <button class="btn btn-secondary" *nimbusHasPermission="'automation:activity:update'"
                      (click)="createNewVersion()">+ New Version</button>
            </div>
          </div>

          <!-- Version Selector -->
          @if (versions().length > 0) {
            <div class="version-selector">
              <label>Version:</label>
              <select [ngModel]="selectedVersionId()" (ngModelChange)="selectVersion($event)">
                @for (v of versions(); track v.id) {
                  <option [value]="v.id">
                    v{{ v.version }}{{ v.publishedAt ? ' (published)' : ' (draft)' }}
                  </option>
                }
              </select>
            </div>
          }

          <!-- Tabs -->
          <div class="tabs">
            <button class="tab" [class.active]="activeTab() === 'definition'" (click)="activeTab.set('definition')">Definition</button>
            <button class="tab" [class.active]="activeTab() === 'versions'" (click)="activeTab.set('versions')">Versions</button>
            <button class="tab" [class.active]="activeTab() === 'mutations'" (click)="activeTab.set('mutations')">Config Mutations</button>
            <button class="tab" [class.active]="activeTab() === 'executions'" (click)="activeTab.set('executions'); loadExecutions()">Executions</button>
            <button class="tab" [class.active]="activeTab() === 'test'" (click)="activeTab.set('test')">Test</button>
          </div>

          <div class="tab-content">
            <!-- Definition Tab -->
            @if (activeTab() === 'definition') {
              <div class="definition-tab">
                @if (selectedVersion(); as v) {
                  <div class="editor-header">
                    <span class="editor-label">Source Code ({{ a.implementationType === 'PYTHON_SCRIPT' ? 'Python' : a.implementationType === 'SHELL_SCRIPT' ? 'Shell' : 'Text' }})</span>
                    @if (!v.publishedAt) {
                      <button class="btn btn-sm btn-primary" *nimbusHasPermission="'automation:activity:update'"
                              (click)="saveSourceCode()">Save</button>
                    }
                  </div>
                  <nimbus-monaco-editor
                    [value]="v.sourceCode || ''"
                    [language]="editorLanguage()"
                    [readOnly]="!!v.publishedAt"
                    [height]="'500px'"
                    (valueChange)="draftSourceCode.set($event)"
                  />
                  <!-- Input/Output Schema -->
                  <div class="schema-panels">
                    <div class="schema-panel">
                      <h3>Input Schema</h3>
                      <pre class="schema-json">{{ v.inputSchema | json }}</pre>
                    </div>
                    <div class="schema-panel">
                      <h3>Output Schema</h3>
                      <pre class="schema-json">{{ v.outputSchema | json }}</pre>
                    </div>
                  </div>
                } @else {
                  <div class="empty-state">No versions yet. Create the first version.</div>
                }
              </div>
            }

            <!-- Versions Tab -->
            @if (activeTab() === 'versions') {
              <div class="versions-tab">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Version</th>
                      <th>Status</th>
                      <th>Changelog</th>
                      <th>Created</th>
                      <th>Published</th>
                    </tr>
                  </thead>
                  <tbody>
                    @for (v of versions(); track v.id) {
                      <tr class="clickable-row" (click)="selectVersion(v.id)"
                          [class.selected]="v.id === selectedVersionId()">
                        <td><strong>v{{ v.version }}</strong></td>
                        <td>
                          @if (v.publishedAt) {
                            <span class="badge badge-published">Published</span>
                          } @else {
                            <span class="badge badge-draft">Draft</span>
                          }
                        </td>
                        <td>{{ v.changelog || '—' }}</td>
                        <td>{{ v.createdAt | date:'short' }}</td>
                        <td>{{ v.publishedAt ? (v.publishedAt | date:'short') : '—' }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }

            <!-- Config Mutations Tab -->
            @if (activeTab() === 'mutations') {
              <div class="mutations-tab">
                @if (selectedVersion()?.configMutations; as mutations) {
                  <h3>Forward Mutations</h3>
                  <div class="mutation-rules">
                    @for (rule of asMutationArray(mutations); track $index) {
                      <div class="mutation-rule">
                        <span class="mutation-type badge badge-operation">{{ rule['mutation_type'] || rule['type'] }}</span>
                        <span class="mutation-path"><code>{{ rule['parameter_path'] || rule['path'] }}</code></span>
                        @if (rule['value'] !== undefined) {
                          <span class="mutation-value">= {{ rule['value'] | json }}</span>
                        }
                        @if (rule['source_field']) {
                          <span class="mutation-value">from output.{{ rule['source_field'] }}</span>
                        }
                        @if (rule['amount'] !== undefined) {
                          <span class="mutation-value">by {{ rule['amount'] }}</span>
                        }
                      </div>
                    }
                  </div>
                } @else {
                  <div class="empty-state">No config mutations defined for this version.</div>
                }

                @if (selectedVersion()?.rollbackMutations; as rollback) {
                  <h3 style="margin-top: 24px;">Rollback Mutations</h3>
                  <div class="mutation-rules">
                    @for (rule of asMutationArray(rollback); track $index) {
                      <div class="mutation-rule rollback">
                        <span class="mutation-type badge badge-rollback">{{ rule['mutation_type'] || rule['type'] }}</span>
                        <span class="mutation-path"><code>{{ rule['parameter_path'] || rule['path'] }}</code></span>
                        @if (rule['value'] !== undefined) {
                          <span class="mutation-value">= {{ rule['value'] | json }}</span>
                        }
                      </div>
                    }
                  </div>
                }
              </div>
            }

            <!-- Executions Tab -->
            @if (activeTab() === 'executions') {
              <div class="executions-tab">
                @if (executionsLoading()) {
                  <div class="loading">Loading executions...</div>
                }
                @if (!executionsLoading() && executions().length === 0) {
                  <div class="empty-state">No executions yet.</div>
                }
                @if (!executionsLoading() && executions().length > 0) {
                  <table class="data-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Status</th>
                        <th>Started</th>
                        <th>Completed</th>
                        <th>Error</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (exec of executions(); track exec.id) {
                        <tr>
                          <td><code>{{ exec.id.slice(0, 8) }}</code></td>
                          <td>
                            <span class="badge" [class]="'badge-' + exec.status.toLowerCase()">{{ exec.status }}</span>
                          </td>
                          <td>{{ exec.startedAt ? (exec.startedAt | date:'short') : '—' }}</td>
                          <td>{{ exec.completedAt ? (exec.completedAt | date:'short') : '—' }}</td>
                          <td class="error-cell">{{ exec.error || '—' }}</td>
                        </tr>
                      }
                    </tbody>
                  </table>
                }
              </div>
            }

            <!-- Test Tab -->
            @if (activeTab() === 'test') {
              <div class="test-tab">
                <h3>Test Execution</h3>
                <p class="test-desc">Execute this activity with test input data.</p>
                <div class="test-form">
                  <label>Input Data (JSON):</label>
                  <nimbus-monaco-editor
                    [value]="testInput()"
                    language="json"
                    [height]="'200px'"
                    (valueChange)="testInput.set($event)"
                  />
                  <div class="test-actions">
                    <button class="btn btn-primary" [disabled]="testRunning()"
                            *nimbusHasPermission="'automation:activity:execute'"
                            (click)="runTest()">
                      {{ testRunning() ? 'Running...' : 'Run Test' }}
                    </button>
                  </div>
                </div>
                @if (testResult()) {
                  <div class="test-result">
                    <h4>Result</h4>
                    <div class="result-status">
                      <span class="badge" [class]="'badge-' + testResult()!.status.toLowerCase()">{{ testResult()!.status }}</span>
                    </div>
                    @if (testResult()!.error) {
                      <div class="result-error">{{ testResult()!.error }}</div>
                    }
                    @if (testResult()!.outputSnapshot) {
                      <h4>Output</h4>
                      <pre class="schema-json">{{ testResult()!.outputSnapshot | json }}</pre>
                    }
                  </div>
                }
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .detail-page { padding: 24px; max-width: 1400px; margin: 0 auto; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 20px;
    }
    .header-left { display: flex; align-items: flex-start; gap: 12px; }
    .btn-back {
      background: none; border: 1px solid #d1d5db; border-radius: 6px;
      padding: 6px 12px; cursor: pointer; font-size: 16px; color: #64748b;
    }
    .btn-back:hover { background: #f1f5f9; }
    .page-header h1 { font-size: 22px; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 14px; color: #64748b; margin: 4px 0 0; }
    .header-meta { display: flex; gap: 8px; align-items: center; margin-top: 4px; flex-wrap: wrap; }
    .slug-text { font-size: 12px; color: #94a3b8; font-family: monospace; }
    .header-actions { display: flex; gap: 8px; }

    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 14px; font-weight: 500;
      cursor: pointer; border: 1px solid transparent; transition: all 0.15s;
    }
    .btn-sm { padding: 4px 12px; font-size: 13px; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #f1f5f9; color: #334155; border-color: #d1d5db; }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-success { background: #22c55e; color: #fff; }
    .btn-success:hover { background: #16a34a; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    /* ── Create Form ── */
    .create-form { display: flex; flex-direction: column; gap: 24px; }
    .form-section {
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 24px;
    }
    .form-section h2 { font-size: 18px; font-weight: 700; color: #1e293b; margin: 0 0 16px; }
    .section-desc { font-size: 14px; color: #64748b; margin: -8px 0 16px; }
    .form-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px;
    }
    .form-group { display: flex; flex-direction: column; gap: 4px; }
    .form-group.full-width { grid-column: 1 / -1; }
    .form-group.checkbox-group { flex-direction: row; align-items: center; gap: 8px; flex-wrap: wrap; }
    .form-group.checkbox-group label { display: flex; align-items: center; gap: 6px; font-size: 14px; color: #334155; cursor: pointer; }
    .form-group.checkbox-group input[type="checkbox"] { width: 16px; height: 16px; accent-color: #3b82f6; }
    .form-group label { font-size: 13px; font-weight: 600; color: #334155; }
    .required { color: #ef4444; }
    .field-hint { font-size: 12px; color: #94a3b8; }
    .form-group input[type="text"],
    .form-group input[type="number"],
    .form-group textarea,
    .form-group select {
      padding: 8px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 14px; background: #fff; color: #1e293b; font-family: inherit;
    }
    .form-group input:focus,
    .form-group textarea:focus,
    .form-group select:focus {
      outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,.15);
    }
    .form-group textarea { resize: vertical; min-height: 60px; }
    .form-actions {
      display: flex; justify-content: flex-end; gap: 12px; padding-top: 8px;
    }

    /* ── Existing styles ── */
    .version-selector {
      display: flex; align-items: center; gap: 8px; margin-bottom: 16px;
      font-size: 14px; color: #334155;
    }
    .version-selector select {
      padding: 6px 12px; border: 1px solid #d1d5db; border-radius: 6px;
      font-size: 14px; background: #fff; color: #1e293b; min-width: 200px;
    }

    .tabs {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 20px;
    }
    .tab {
      padding: 10px 20px; font-size: 14px; font-weight: 500; color: #64748b;
      background: none; border: none; cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; transition: all 0.15s;
    }
    .tab:hover { color: #334155; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content {
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 20px;
    }

    .loading, .empty-state {
      text-align: center; padding: 48px 24px; color: #64748b; font-size: 15px;
    }

    .editor-header {
      display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;
    }
    .editor-label { font-size: 14px; font-weight: 600; color: #334155; }

    .schema-panels { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 20px; }
    .schema-panel { background: #f8fafc; border-radius: 6px; padding: 16px; border: 1px solid #e2e8f0; }
    .schema-panel h3 { font-size: 14px; font-weight: 600; color: #1e293b; margin: 0 0 8px; }
    .schema-json {
      font-size: 12px; font-family: monospace; color: #334155;
      white-space: pre-wrap; word-break: break-all; margin: 0; max-height: 200px; overflow: auto;
    }

    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th {
      text-align: left; padding: 10px 14px; font-size: 12px; font-weight: 600;
      color: #64748b; text-transform: uppercase; letter-spacing: 0.05em;
      background: #f8fafc; border-bottom: 1px solid #e2e8f0;
    }
    .data-table td {
      padding: 10px 14px; font-size: 14px; color: #334155;
      border-bottom: 1px solid #f1f5f9;
    }
    .clickable-row { cursor: pointer; }
    .clickable-row:hover { background: #f8fafc; }
    .clickable-row.selected { background: #eff6ff; }

    .badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 12px; font-weight: 500;
    }
    .badge-operation { background: #dbeafe; color: #1d4ed8; }
    .badge-type { background: #fef3c7; color: #92400e; }
    .badge-system { background: #e0e7ff; color: #3730a3; }
    .badge-component { background: #fff7ed; color: #c2410c; }
    .badge-workflow { background: #eff6ff; color: #1d4ed8; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-rollback { background: #fee2e2; color: #991b1b; }
    .badge-succeeded, .badge-running { background: #dcfce7; color: #166534; }
    .badge-failed { background: #fee2e2; color: #991b1b; }
    .badge-pending { background: #fef3c7; color: #92400e; }
    .badge-cancelled { background: #f1f5f9; color: #64748b; }

    .mutation-rules { display: flex; flex-direction: column; gap: 8px; }
    .mutation-rule {
      display: flex; align-items: center; gap: 10px; padding: 10px 14px;
      background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0;
    }
    .mutation-rule.rollback { border-color: #fecaca; background: #fef2f2; }
    .mutation-path { font-family: monospace; font-size: 13px; color: #334155; }
    .mutation-value { font-size: 13px; color: #64748b; }
    .error-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #ef4444; }

    .test-tab h3 { font-size: 16px; font-weight: 600; color: #1e293b; margin: 0 0 8px; }
    .test-desc { font-size: 14px; color: #64748b; margin: 0 0 16px; }
    .test-form label { display: block; font-size: 14px; font-weight: 500; color: #334155; margin-bottom: 8px; }
    .test-actions { margin-top: 12px; }
    .test-result { margin-top: 20px; padding-top: 20px; border-top: 1px solid #e2e8f0; }
    .test-result h4 { font-size: 14px; font-weight: 600; color: #1e293b; margin: 0 0 8px; }
    .result-status { margin-bottom: 12px; }
    .result-error {
      padding: 12px; background: #fef2f2; border: 1px solid #fecaca; border-radius: 6px;
      color: #991b1b; font-size: 13px; margin-bottom: 12px;
    }
  `],
})
export class ActivityDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private activityService = inject(AutomatedActivityService);
  private toast = inject(ToastService);

  isCreateMode = signal(false);
  activity = signal<AutomatedActivity | null>(null);
  versions = signal<AutomatedActivityVersion[]>([]);
  selectedVersionId = signal<string>('');
  loading = signal(false);
  saving = signal(false);
  activeTab = signal<TabKey>('definition');

  // Create form
  createForm = {
    name: '',
    slug: '',
    description: '',
    category: '',
    operationKind: 'UPDATE',
    implementationType: 'PYTHON_SCRIPT',
    timeoutSeconds: 300,
    idempotent: false,
    initialSourceCode: '# Activity implementation\nimport json\nimport sys\n\ndef main():\n    input_data = json.load(sys.stdin)\n    # TODO: implement activity logic\n    result = {"status": "ok"}\n    json.dump(result, sys.stdout)\n\nif __name__ == "__main__":\n    main()\n',
    inputSchemaJson: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}',
    outputSchemaJson: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}',
  };

  // Executions
  executions = signal<ActivityExecution[]>([]);
  executionsLoading = signal(false);

  // Editor
  draftSourceCode = signal('');

  // Test
  testInput = signal('{}');
  testRunning = signal(false);
  testResult = signal<ActivityExecution | null>(null);

  selectedVersion = computed(() => {
    const vid = this.selectedVersionId();
    return this.versions().find(v => v.id === vid) || null;
  });

  editorLanguage = computed(() => {
    const implType = this.activity()?.implementationType;
    if (implType === 'PYTHON_SCRIPT') return 'python';
    if (implType === 'SHELL_SCRIPT') return 'shell';
    return 'plaintext';
  });

  createFormLanguage = computed(() => {
    if (this.createForm.implementationType === 'PYTHON_SCRIPT') return 'python';
    if (this.createForm.implementationType === 'SHELL_SCRIPT') return 'shell';
    if (this.createForm.implementationType === 'HTTP_WEBHOOK') return 'json';
    return 'plaintext';
  });

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (!id || id === 'new') {
      this.isCreateMode.set(true);
    } else {
      this.loadActivity(id);
    }
  }

  // ── Create Mode ──

  submitCreate(): void {
    if (!this.createForm.name.trim()) return;
    this.saving.set(true);

    const scope = (this.router.url.includes('/provider/activities') || this.router.url.startsWith('/activities')) ? 'COMPONENT' : 'WORKFLOW';
    const input: AutomatedActivityCreateInput = {
      name: this.createForm.name.trim(),
      slug: this.createForm.slug.trim() || undefined,
      description: this.createForm.description.trim() || undefined,
      category: this.createForm.category || undefined,
      operationKind: this.createForm.operationKind,
      implementationType: this.createForm.implementationType,
      scope,
      timeoutSeconds: this.createForm.timeoutSeconds,
      idempotent: this.createForm.idempotent,
    };

    this.activityService.createActivity(input).subscribe({
      next: (created) => {
        this.toast.success(`Activity "${created.name}" created`);
        // Now create version 1 with source code
        const versionInput: ActivityVersionCreateInput = {
          sourceCode: this.createForm.initialSourceCode,
          changelog: 'Initial version',
        };
        try {
          const inputSchema = JSON.parse(this.createForm.inputSchemaJson);
          versionInput.inputSchema = inputSchema;
        } catch { /* skip invalid JSON */ }
        try {
          const outputSchema = JSON.parse(this.createForm.outputSchemaJson);
          versionInput.outputSchema = outputSchema;
        } catch { /* skip invalid JSON */ }

        this.activityService.createVersion(created.id, versionInput).subscribe({
          next: () => {
            this.saving.set(false);
            // Navigate to the new activity's detail view
            const url = this.router.url.split('?')[0];
            const base = url.includes('/provider/activities') ? '/provider/activities' : url.startsWith('/activities') ? '/activities' : '/workflows/activities';
            this.router.navigate([base, created.id]);
          },
          error: () => {
            this.saving.set(false);
            // Activity was created but version failed — navigate anyway
            const url = this.router.url.split('?')[0];
            const base = url.includes('/provider/activities') ? '/provider/activities' : url.startsWith('/activities') ? '/activities' : '/workflows/activities';
            this.router.navigate([base, created.id]);
          },
        });
      },
      error: (err) => {
        this.saving.set(false);
        this.toast.error(err?.message || 'Failed to create activity');
      },
    });
  }

  // ── Edit/View Mode ──

  loadActivity(id: string): void {
    this.loading.set(true);
    this.activityService.getActivity(id).subscribe({
      next: (a) => {
        this.activity.set(a);
        if (a?.versions?.length) {
          const sorted = [...a.versions].sort((x, y) => y.version - x.version);
          this.versions.set(sorted);
          this.selectedVersionId.set(sorted[0].id);
          this.draftSourceCode.set(sorted[0].sourceCode || '');
        }
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  selectVersion(versionId: string): void {
    this.selectedVersionId.set(versionId);
    const v = this.versions().find(ver => ver.id === versionId);
    if (v) this.draftSourceCode.set(v.sourceCode || '');
  }

  goBack(): void {
    const url = this.router.url.split('?')[0];
    const base = url.includes('/provider/activities') ? '/provider/activities' : url.startsWith('/activities') ? '/activities' : '/workflows/activities';
    this.router.navigate([base]);
  }

  createNewVersion(): void {
    const a = this.activity();
    if (!a) return;
    const latestVersion = this.versions()[0];
    const input: ActivityVersionCreateInput = {
      sourceCode: latestVersion?.sourceCode || '',
      inputSchema: latestVersion?.inputSchema || null,
      outputSchema: latestVersion?.outputSchema || null,
      configMutations: latestVersion?.configMutations || null,
      rollbackMutations: latestVersion?.rollbackMutations || null,
      changelog: '',
    };
    this.activityService.createVersion(a.id, input).subscribe({
      next: (v) => {
        this.versions.update(list => [v, ...list]);
        this.selectedVersionId.set(v.id);
        this.draftSourceCode.set(v.sourceCode || '');
        this.toast.success('New version created');
      },
      error: () => this.toast.error('Failed to create version'),
    });
  }

  publishVersion(): void {
    const a = this.activity();
    const v = this.selectedVersion();
    if (!a || !v) return;
    this.activityService.publishVersion(a.id, v.id).subscribe({
      next: (published) => {
        this.versions.update(list =>
          list.map(ver => ver.id === published.id ? published : ver)
        );
        this.toast.success(`Version ${published.version} published`);
      },
      error: () => this.toast.error('Failed to publish version'),
    });
  }

  saveSourceCode(): void {
    const a = this.activity();
    const v = this.selectedVersion();
    if (!a || !v || v.publishedAt) return;
    this.activityService.createVersion(a.id, {
      sourceCode: this.draftSourceCode(),
      inputSchema: v.inputSchema,
      outputSchema: v.outputSchema,
      configMutations: v.configMutations,
      rollbackMutations: v.rollbackMutations,
      changelog: 'Source code update',
    }).subscribe({
      next: (newV) => {
        this.versions.update(list => [newV, ...list]);
        this.selectedVersionId.set(newV.id);
        this.toast.success('Saved as new version');
      },
      error: () => this.toast.error('Failed to save'),
    });
  }

  loadExecutions(): void {
    const a = this.activity();
    if (!a) return;
    this.executionsLoading.set(true);
    this.activityService.listExecutions({ activityId: a.id }).subscribe({
      next: (list) => {
        this.executions.set(list);
        this.executionsLoading.set(false);
      },
      error: () => this.executionsLoading.set(false),
    });
  }

  runTest(): void {
    const a = this.activity();
    const v = this.selectedVersion();
    if (!a || !v) return;

    let inputData: Record<string, unknown> | null = null;
    try {
      const parsed = JSON.parse(this.testInput());
      inputData = typeof parsed === 'object' ? parsed : null;
    } catch {
      this.toast.error('Invalid JSON input');
      return;
    }

    this.testRunning.set(true);
    this.testResult.set(null);
    this.activityService.startExecution(a.id, v.id, null, null, inputData).subscribe({
      next: (exec) => {
        this.testResult.set(exec);
        this.testRunning.set(false);
      },
      error: () => {
        this.testRunning.set(false);
        this.toast.error('Execution failed');
      },
    });
  }

  asMutationArray(mutations: unknown): Record<string, unknown>[] {
    if (Array.isArray(mutations)) return mutations;
    return [];
  }
}
