/**
 * Overview: Component editor — create/edit Pulumi Python scripts with Monaco, schema builders, and resolver bindings.
 * Architecture: Feature component for component authoring (Section 11)
 * Dependencies: @angular/core, @angular/router, ComponentService, SemanticService, MonacoEditorComponent, SearchableSelectComponent
 * Concepts: Full component editor with code, structured input/output schema builder, visual resolver bindings,
 *     version history with restore, publish workflow. Language locked to Python. Provider auto-selected.
 */
import { Component as NgComponent, OnInit, inject, signal, computed, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { ComponentService } from '@core/services/component.service';
import { SemanticService } from '@core/services/semantic.service';
import { WorkflowService } from '@core/services/workflow.service';
import { AutomatedActivityService } from '@core/services/automated-activity.service';
import { AutomatedActivity } from '@shared/models/automated-activity.model';
import {
  Component as ComponentModel,
  ComponentCreateInput,
  ComponentOperation,
  ComponentOperationCreateInput,
  ComponentVersion,
  EstimatedDowntime,
} from '@shared/models/component.model';
import { WorkflowDefinition } from '@shared/models/workflow.model';
import { forkJoin, of, catchError } from 'rxjs';
import { ToastService } from '@shared/services/toast.service';

type EditorTab = 'workflows' | 'activities' | 'versions';
type ComponentMode = 'provider' | 'tenant';

const EXAMPLE_CODE = `"""
Example Pulumi component for provisioning a virtual machine.
Modify this template to define your infrastructure resource.
"""

import pulumi
from pulumi import Input, Output

# Component inputs are injected as variables:
#   name: str           - resolved resource name
#   ip_address: str     - resolved IP from IPAM
#   image_id: str       - resolved OS image reference

def create_resource(args: dict) -> dict:
    """Create the infrastructure resource.

    Args:
        args: Resolved input parameters (after resolver pre-processing)

    Returns:
        Dictionary of output values to store in CMDB
    """
    resource_name = args.get("name", "unnamed")

    # TODO: Replace with actual Pulumi resource creation
    # Example:
    # vm = compute.VirtualMachine(
    #     resource_name,
    #     name=args["name"],
    #     image=args["image_id"],
    #     ip_address=args["ip_address"],
    #     ...
    # )

    return {
        "resource_id": f"placeholder-{resource_name}",
        "status": "created",
    }
`;

@NgComponent({
  selector: 'nimbus-component-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <!-- Header -->
        <div class="page-header">
          <button class="back-btn" (click)="router.navigate([basePath()])">&larr; {{ isProviderMode() ? 'Provider Components' : 'Components' }}</button>
          <div class="header-row">
            <div class="header-title">
              <h1>{{ isNew() ? 'New Component' : component()?.displayName || 'Component' }}</h1>
              @if (component(); as c) {
                <div class="header-badges">
                  <span class="badge lang-python">Python</span>
                  <span class="badge" [class.published]="c.isPublished" [class.draft]="!c.isPublished">
                    {{ c.isPublished ? 'Published v' + (c.version - 1) : 'Draft' }}
                  </span>
                </div>
              }
            </div>
            <div class="header-actions">
              <button class="btn btn-outline" (click)="onCancel()">Cancel</button>
              <button class="btn btn-secondary" (click)="save()" [disabled]="saving()">
                {{ saving() ? 'Saving...' : 'Save Draft' }}
              </button>
              @if (!isNew() && component()) {
                <button class="btn btn-primary" (click)="showPublishDialog.set(true)">Publish</button>
              }
            </div>
          </div>
        </div>

        <!-- Form Fields -->
        <div class="form-section">
          <div class="form-row">
            <div class="form-group">
              <label>Name (slug)</label>
              <input type="text" [(ngModel)]="form.name" placeholder="my-component" />
            </div>
            <div class="form-group">
              <label>Display Name</label>
              <input type="text" [(ngModel)]="form.displayName" placeholder="My Component" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>Provider</label>
              <nimbus-searchable-select
                [options]="providerOptions()"
                [(ngModel)]="providerId"
                placeholder="Select provider..."
              />
            </div>
            <div class="form-group">
              <label>Semantic Type</label>
              <nimbus-searchable-select
                [options]="semanticTypeOptions()"
                [(ngModel)]="form.semanticTypeId"
                placeholder="Select semantic type..."
              />
            </div>
          </div>
          <div class="form-group" style="margin-bottom: 0;">
            <label>Description</label>
            <input type="text" [(ngModel)]="form.description" placeholder="Brief description" />
          </div>
        </div>

        <!-- Tabs -->
        <div class="tabs">
          <button class="tab" [class.active]="activeTab() === 'workflows'" (click)="activeTab.set('workflows'); loadOperations()">
            Workflows ({{ allWorkflowOps().length }})
          </button>
          <button class="tab" [class.active]="activeTab() === 'activities'" (click)="activeTab.set('activities'); loadOperations()">
            Activities ({{ allActivities().length }})
          </button>
          @if (!isNew()) {
            <button class="tab" [class.active]="activeTab() === 'versions'" (click)="activeTab.set('versions'); loadVersions()">
              Versions ({{ versions().length }})
            </button>
          }
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          <!-- ── Workflows Tab ─────────────────────────── -->
          @if (activeTab() === 'workflows') {
            <div class="operations-builder">
              @if (deploymentOps().length === 0 && day2Ops().length === 0) {
                <div class="deploy-init-banner">
                  <p>No workflows found. Initialize standard deployment operations for this component.</p>
                  <button class="btn btn-primary" (click)="initDeploymentOps()" [disabled]="deployInitializing()">
                    {{ deployInitializing() ? 'Initializing...' : 'Initialize Deployment Operations' }}
                  </button>
                </div>
              }

              <!-- All workflow-backed operations (deployment + day-2) -->
              @for (op of allWorkflowOps(); track op.id) {
                @if (editingOpId() !== op.id) {
                  <div class="operation-card" [class.expanded]="expandedOpId() === op.id">
                    <div class="operation-header" (click)="toggleOperationExpand(op)">
                      <div class="operation-title">
                        <span class="expand-icon">{{ expandedOpId() === op.id ? '&#9660;' : '&#9654;' }}</span>
                        <span class="operation-name">{{ op.displayName }}</span>
                        <span class="badge badge-kind">{{ op.operationCategory === 'DEPLOYMENT' ? 'Deployment' : 'Day-2' }}</span>
                        @if (op.operationKind) {
                          <span class="badge badge-kind">{{ op.operationKind }}</span>
                        }
                        @if (op.isDestructive) {
                          <span class="badge badge-destructive">Destructive</span>
                        }
                        @if (op.requiresApproval) {
                          <span class="badge badge-approval">Approval</span>
                        }
                        @if (op.estimatedDowntime && op.estimatedDowntime !== 'NONE') {
                          <span class="badge badge-downtime">~{{ parseDowntimeMinutes(op.estimatedDowntime) }} min</span>
                        }
                      </div>
                      <div class="operation-actions" (click)="$event.stopPropagation()">
                        <button class="btn btn-sm btn-secondary" (click)="editOperation(op)">Edit</button>
                        <button class="btn btn-sm btn-danger" (click)="deleteOperation(op)">Delete</button>
                      </div>
                    </div>

                    <!-- Collapsed summary: always show workflow info + template status -->
                    <div class="wf-summary">
                      @if (getWorkflowForOp(op); as wf) {
                        <div class="wf-summary-row">
                          <span class="wf-summary-name">{{ wf.name }}</span>
                          <span class="badge" [class.published]="wf.status === 'ACTIVE'" [class.draft]="wf.status === 'DRAFT'">{{ wf.status }}</span>
                          <span class="wf-version">v{{ wf.version }}</span>
                          @if (wf.templateSourceId && wf.version <= 1) {
                            <span class="badge badge-default">Default</span>
                          } @else if (wf.templateSourceId) {
                            <span class="badge badge-customized">Customized</span>
                          }
                        </div>
                      } @else {
                        <span class="wf-summary-name wf-missing">{{ workflowsLoaded() ? 'Workflow not found' : 'Loading...' }}</span>
                      }
                    </div>

                    <!-- Expanded workflow detail -->
                    @if (expandedOpId() === op.id) {
                      <div class="workflow-detail">
                        @if (getWorkflowForOp(op); as wf) {
                          <div class="workflow-detail-header">
                            <h4>{{ wf.name }}</h4>
                            <div class="workflow-detail-actions">
                              @if (wf.templateSourceId) {
                                <button class="btn btn-sm" (click)="resetDeployWorkflow(op)">Reset to Template</button>
                              }
                              <button class="btn btn-sm btn-secondary" (click)="editWorkflow(wf.id)">Open in Editor</button>
                            </div>
                          </div>
                          @if (wf.description) {
                            <p class="workflow-detail-desc">{{ wf.description }}</p>
                          }
                          <div class="workflow-detail-meta">
                            <div class="meta-item">
                              <span class="meta-label">Status</span>
                              <span class="badge" [class.published]="wf.status === 'ACTIVE'" [class.draft]="wf.status === 'DRAFT'">{{ wf.status }}</span>
                            </div>
                            <div class="meta-item">
                              <span class="meta-label">Type</span>
                              <span>{{ wf.workflowType }}</span>
                            </div>
                            <div class="meta-item">
                              <span class="meta-label">Version</span>
                              <span>v{{ wf.version }}</span>
                            </div>
                            @if (wf.graph) {
                              <div class="meta-item">
                                <span class="meta-label">Nodes</span>
                                <span>{{ wf.graph!.nodes.length || 0 }}</span>
                              </div>
                            }
                            <div class="meta-item">
                              <span class="meta-label">Timeout</span>
                              <span>{{ wf.timeoutSeconds }}s</span>
                            </div>
                          </div>
                          @if (wf.graph?.nodes?.length) {
                            <div class="workflow-node-list">
                              <span class="meta-label">Node Pipeline</span>
                              <div class="node-pipeline">
                                @for (node of wf.graph!.nodes; track node.id; let last = $last) {
                                  <span class="pipeline-node">{{ node.label || node.type }}</span>
                                  @if (!last) {
                                    <span class="pipeline-arrow">&rarr;</span>
                                  }
                                }
                              </div>
                            </div>
                          }
                        } @else {
                          <div class="workflow-loading">{{ workflowsLoaded() ? 'Workflow not found — this operation references a deleted or missing workflow.' : 'Loading workflow...' }}</div>
                        }
                      </div>
                    }
                  </div>
                }

                <!-- Inline edit form (shown when editing this op) -->
                @if (editingOpId() === op.id) {
                  <ng-container *ngTemplateOutlet="opFormTpl; context: { isEdit: true }"></ng-container>
                }
              }

              <!-- Add workflow button -->
              <div class="add-op-row">
                <button class="btn btn-sm" (click)="showOpForm.set(true); resetOpForm()">+ Add Workflow</button>
                <button class="btn btn-sm btn-secondary" style="margin-left: 0.5rem;" (click)="createBlankWorkflow()">+ Create Blank Workflow</button>
              </div>

              <!-- New operation form (at bottom, only for new) -->
              @if (showOpForm() && !editingOpId()) {
                <ng-container *ngTemplateOutlet="opFormTpl; context: { isEdit: false }"></ng-container>
              }
              <!-- Shared form template -->
              <ng-template #opFormTpl let-isEdit="isEdit">
                <div class="operation-form">
                  <h4>{{ isEdit ? 'Edit Operation' : 'Link Workflow to Component' }}</h4>
                  <div class="form-group">
                    <label>Display Name</label>
                    <input type="text" [(ngModel)]="opForm.displayName" placeholder="e.g. Extend Disk" />
                  </div>
                  <div class="form-group">
                    <label>Description</label>
                    <input type="text" [(ngModel)]="opForm.description" placeholder="What this operation does" />
                  </div>
                  <div class="form-row">
                    <div class="form-group">
                      <label>Workflow Definition</label>
                      @if (isEdit) {
                        <input type="text" [value]="getWorkflowName(opForm.workflowDefinitionId)" disabled />
                      } @else {
                        <select [(ngModel)]="opForm.workflowDefinitionId">
                          <option value="">-- Select existing workflow --</option>
                          @for (wf of workflowDefinitions(); track wf.id) {
                            <option [value]="wf.id">{{ wf.name }}</option>
                          }
                        </select>
                      }
                    </div>
                    <div class="form-group">
                      <label>Estimated Downtime (minutes)</label>
                      <input type="number" [(ngModel)]="opForm.downtimeMinutes" min="0" placeholder="0" />
                    </div>
                  </div>
                  <div class="form-actions">
                    <button class="btn btn-secondary" (click)="cancelOpForm()">Cancel</button>
                    <button class="btn btn-primary" (click)="saveOperation()" [disabled]="opSaving()">
                      {{ opSaving() ? 'Saving...' : (isEdit ? 'Update' : 'Create') }}
                    </button>
                  </div>
                </div>
              </ng-template>
            </div>
          }

          <!-- ── Activities Tab ─────────────────────────── -->
          @if (activeTab() === 'activities') {
            <div class="operations-builder">
              @if (allActivities().length === 0) {
                <div class="empty-schema">No activities linked to this component yet. Initialize deployment operations to create standard activities.</div>
              }

              <div class="activity-list-inline">
                @for (act of allActivities(); track act.id) {
                  <div class="activity-card-inline">
                    <div class="activity-card-header-inline">
                      <div class="activity-card-title-inline">
                        <span class="activity-card-name">{{ act.name }}</span>
                        <span class="badge badge-kind">{{ act.isComponentActivity ? 'Component' : 'Template' }}</span>
                        <span class="badge badge-kind">{{ act.operationKind }}</span>
                        @if (act.isMandatory) {
                          <span class="badge badge-mandatory-sm">Mandatory</span>
                        }
                        @if (act.templateActivityId && act.forkedAtVersion !== null) {
                          @if (isActivityCustomized(act)) {
                            <span class="badge badge-customized">Customized</span>
                          } @else {
                            <span class="badge badge-default">Default</span>
                          }
                          <span class="wf-version">from template v{{ act.forkedAtVersion }}</span>
                        }
                      </div>
                      <div class="activity-card-actions-inline">
                        <button class="btn btn-sm btn-secondary" (click)="editActivity(act.id)">Edit</button>
                      </div>
                    </div>
                    <div class="activity-card-slug">{{ act.slug }}</div>
                  </div>
                }
              </div>

              <div class="add-op-row">
                <button class="btn btn-sm" (click)="createDay2Activity()">+ New Activity</button>
              </div>
            </div>
          }

          <!-- ── Versions Tab ────────────────────────────── -->
          @if (activeTab() === 'versions') {
            <div class="version-list">
              @if (versions().length === 0) {
                <p class="empty-msg">No published versions yet. Publish this component to create a version snapshot.</p>
              }
              @for (v of versions(); track v.id) {
                <div class="version-card">
                  <div class="version-header">
                    <span class="version-number">v{{ v.version }}</span>
                    <span class="version-date">{{ v.publishedAt | date:'medium' }}</span>
                    <button class="btn btn-sm btn-secondary" (click)="restoreVersion(v)">Restore</button>
                  </div>
                  @if (v.changelog) {
                    <div class="version-changelog">{{ v.changelog }}</div>
                  }
                </div>
              }
            </div>
          }
        </div>

        <!-- Publish Dialog -->
        @if (showPublishDialog()) {
          <div class="dialog-overlay" (click)="showPublishDialog.set(false)">
            <div class="dialog" (click)="$event.stopPropagation()">
              <h3>Publish Component</h3>
              <p>This will create an immutable version snapshot (v{{ component()?.version }}).</p>
              <label>Changelog</label>
              <textarea rows="4" [(ngModel)]="publishChangelog" placeholder="What changed in this version?"></textarea>
              <div class="dialog-actions">
                <button class="btn btn-secondary" (click)="showPublishDialog.set(false)">Cancel</button>
                <button class="btn btn-primary" (click)="publish()">Publish</button>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { margin-bottom: 1.5rem; }
    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.875rem; padding: 0; text-align: left; margin-bottom: 0.5rem;
    }
    .back-btn:hover { text-decoration: underline; }
    .header-row { display: flex; justify-content: space-between; align-items: center; }
    .header-title { display: flex; align-items: center; gap: 0.75rem; }
    .header-title h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .header-badges { display: flex; gap: 0.5rem; }
    .badge {
      font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.5rem; border-radius: 4px;
      text-transform: uppercase;
    }
    .lang-python { background: #fef3c7; color: #92400e; }
    .badge.published { background: #dcfce7; color: #166534; }
    .badge.draft { background: #f1f5f9; color: #64748b; }
    .header-actions { display: flex; gap: 0.5rem; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; cursor: pointer; border: none; font-weight: 500; transition: background 0.15s; }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.8125rem; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-secondary { background: #f1f5f9; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-danger { background: #fee2e2; color: #991b1b; }
    .btn-danger:hover { background: #fecaca; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }

    .form-section { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1.25rem; margin-bottom: 1rem; }
    .form-row { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .form-group { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; }
    .form-group.flex-2 { flex: 2; }
    .form-group label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .form-group input, .form-group select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.875rem; color: #1e293b; background: #fff;
    }
    .form-group input:focus, .form-group select:focus {
      outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,0.1);
    }

    .tabs { display: flex; gap: 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 1rem; }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.875rem; color: #64748b; font-weight: 500; border-bottom: 2px solid transparent;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .tab-content { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem; min-height: 300px; }

    .empty-schema { color: #94a3b8; font-size: 0.875rem; padding: 1.5rem; text-align: center; }

    /* ── Version list ────────────────────────── */
    .version-list { display: flex; flex-direction: column; gap: 0.5rem; }
    .empty-msg { color: #64748b; font-size: 0.875rem; }
    .version-card { padding: 0.75rem; background: #f8fafc; border-radius: 6px; border: 1px solid #e2e8f0; }
    .version-header { display: flex; justify-content: space-between; align-items: center; gap: 0.75rem; }
    .version-number { font-weight: 600; color: #1e293b; }
    .version-date { font-size: 0.75rem; color: #94a3b8; flex: 1; }
    .version-changelog { font-size: 0.8125rem; color: #374151; margin-top: 0.375rem; }

    /* ── Operations ──────────────────────────── */
    .operations-builder { display: flex; flex-direction: column; gap: 0.75rem; }
    .operation-card {
      padding: 0.75rem 1rem; background: #f8fafc; border-radius: 6px;
      border: 1px solid #e2e8f0;
    }
    .operation-card { cursor: pointer; transition: border-color 0.15s; }
    .operation-card:hover { border-color: #cbd5e1; }
    .operation-card.expanded { border-color: #3b82f6; cursor: default; }
    .operation-header { display: flex; justify-content: space-between; align-items: center; cursor: pointer; }
    .operation-title { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .expand-icon { font-size: 0.625rem; color: #94a3b8; width: 0.75rem; flex-shrink: 0; }
    .operation-name { font-weight: 600; color: #1e293b; font-size: 0.9375rem; }
    .op-name-badge { background: #f1f5f9; color: #64748b; font-family: monospace; font-size: 0.75rem; }
    .badge-destructive { background: #fef2f2; color: #dc2626; }
    .badge-approval { background: #eff6ff; color: #2563eb; }
    .badge-downtime { background: #fffbeb; color: #d97706; }
    .operation-actions { display: flex; gap: 0.375rem; align-items: center; }
    .btn-link { background: none; border: none; color: #3b82f6; cursor: pointer; font-size: 0.8125rem; padding: 0.375rem 0.5rem; }
    .btn-link:hover { text-decoration: underline; }
    .operation-desc { font-size: 0.8125rem; color: #64748b; margin-top: 0.375rem; }
    .operation-meta { display: flex; gap: 1.5rem; font-size: 0.75rem; color: #94a3b8; margin-top: 0.375rem; }
    .operation-meta strong { color: #475569; }
    .operation-form {
      background: #fff; border: 1px solid #3b82f6; border-radius: 8px;
      padding: 1.25rem; display: flex; flex-direction: column; gap: 0.75rem;
    }
    .operation-form h4 { margin: 0; font-size: 1rem; color: #1e293b; }
    .form-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 0.25rem; }

    /* ── Workflow detail (expanded operation) ── */
    .workflow-detail {
      margin-top: 0.75rem; padding-top: 0.75rem; border-top: 1px solid #e2e8f0;
    }
    .workflow-loading { font-size: 0.8125rem; color: #94a3b8; padding: 0.5rem 0; }
    .workflow-detail-header { display: flex; justify-content: space-between; align-items: center; }
    .workflow-detail-header h4 { margin: 0; font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
    .workflow-detail-actions { display: flex; gap: 0.375rem; }
    .workflow-detail-desc { font-size: 0.8125rem; color: #64748b; margin: 0.25rem 0 0.5rem; }
    .workflow-detail-meta { display: flex; flex-wrap: wrap; gap: 1rem; margin-top: 0.5rem; }
    .meta-item { display: flex; flex-direction: column; gap: 0.125rem; }
    .meta-label { font-size: 0.6875rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; }
    .meta-item span:not(.meta-label):not(.badge) { font-size: 0.8125rem; color: #1e293b; }
    .workflow-node-list { margin-top: 0.75rem; }
    .node-pipeline {
      display: flex; flex-wrap: wrap; align-items: center; gap: 0.375rem; margin-top: 0.375rem;
    }
    .pipeline-node {
      display: inline-block; padding: 0.25rem 0.625rem; background: #eff6ff; color: #1e40af;
      border-radius: 4px; font-size: 0.75rem; font-weight: 500;
    }
    .pipeline-arrow { color: #94a3b8; font-size: 0.75rem; }

    /* ── Deployment Operations ──────────────── */
    .section-divider { margin-bottom: 0.75rem; }
    .section-divider h3 { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 0.25rem; }
    .deploy-init-banner {
      text-align: center; padding: 1.5rem; background: #f0f7ff; border: 1px dashed #93c5fd;
      border-radius: 8px; margin-bottom: 1rem;
    }
    .deploy-init-banner p { color: #475569; font-size: 0.875rem; margin: 0 0 0.75rem; }
    .deploy-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 0.75rem; margin-bottom: 0.5rem;
    }
    .deploy-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 0.875rem; display: flex; flex-direction: column; gap: 0.5rem;
      transition: border-color 0.15s;
    }
    .deploy-card:hover { border-color: #cbd5e1; }
    .deploy-card-header { display: flex; justify-content: space-between; align-items: flex-start; }
    .deploy-card-title { display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap; }
    .deploy-name { font-weight: 600; color: #1e293b; font-size: 0.9375rem; }
    .badge-kind {
      background: #eff6ff; color: #1e40af; font-size: 0.625rem; font-weight: 600;
      padding: 0.125rem 0.375rem; border-radius: 3px; text-transform: uppercase;
    }
    .deploy-card-body { display: flex; flex-direction: column; gap: 0.25rem; }
    .deploy-meta-row { display: flex; justify-content: space-between; align-items: center; font-size: 0.8125rem; }
    .deploy-wf-name { color: #475569; font-weight: 500; }
    .text-green { color: #16a34a; }
    .text-amber { color: #d97706; }
    .deploy-card-actions {
      display: flex; gap: 0.375rem; margin-top: 0.25rem; padding-top: 0.5rem; border-top: 1px solid #f1f5f9;
      flex-wrap: wrap;
    }
    /* ── Activity Cards (Inline) ──────────────── */
    .activity-list-inline { display: flex; flex-direction: column; gap: 0.5rem; }
    .activity-card-inline {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 0.75rem;
      transition: border-color 0.15s;
    }
    .activity-card-inline:hover { border-color: #cbd5e1; }
    .activity-card-header-inline {
      display: flex; justify-content: space-between; align-items: center;
    }
    .activity-card-title-inline {
      display: flex; align-items: center; gap: 0.375rem; flex-wrap: wrap;
    }
    .activity-card-actions-inline { display: flex; gap: 0.375rem; align-items: center; }
    .activity-card-name { font-weight: 600; font-size: 0.8125rem; color: #1e293b; }
    .activity-card-slug { font-size: 0.6875rem; color: #94a3b8; font-family: monospace; margin-top: 0.125rem; }
    .badge-mandatory-sm { background: #fef2f2; color: #991b1b; font-size: 0.5625rem; padding: 1px 4px; }
    .badge-forked-sm { background: #f0f7ff; color: #1e40af; font-size: 0.5625rem; padding: 1px 4px; }
    .badge-default { background: #f1f5f9; color: #64748b; font-size: 0.625rem; padding: 2px 6px; }
    .badge-customized { background: #fef3c7; color: #92400e; font-size: 0.625rem; padding: 2px 6px; }
    .add-op-row { margin-top: 0.75rem; }
    .wf-summary { margin-top: 0.375rem; }
    .wf-summary-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
    .wf-summary-name { font-size: 0.8125rem; color: #475569; font-weight: 500; }
    .wf-missing { color: #dc2626; font-style: italic; }
    .wf-version { font-size: 0.75rem; color: #94a3b8; }
    .btn-upgrade { background: #fef3c7; color: #92400e; border: 1px solid #fbbf24; }
    .btn-upgrade:hover { background: #fde68a; }

    .empty-msg { color: #64748b; font-size: 0.875rem; }
    /* ── Dialog ──────────────────────────────── */
    .dialog-overlay {
      position: fixed; inset: 0; background: rgba(0,0,0,0.3); display: flex;
      align-items: center; justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 8px; padding: 1.5rem; max-width: 480px; width: 100%;
      box-shadow: 0 20px 60px rgba(0,0,0,0.2);
    }
    .dialog h3 { font-size: 1.125rem; color: #1e293b; margin: 0 0 0.5rem; }
    .dialog p { font-size: 0.875rem; color: #64748b; margin: 0 0 1rem; }
    .dialog label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; display: block; margin-bottom: 0.25rem; }
    .dialog textarea {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.875rem; resize: vertical; box-sizing: border-box;
    }
    .dialog-actions { display: flex; justify-content: flex-end; gap: 0.5rem; margin-top: 1rem; }
  `],
})
export class ComponentEditorComponent implements OnInit {
  router = inject(Router);
  private route = inject(ActivatedRoute);
  private componentService = inject(ComponentService);
  private semanticService = inject(SemanticService);
  private workflowService = inject(WorkflowService);
  private activityService = inject(AutomatedActivityService);
  private toastService = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  component = signal<ComponentModel | null>(null);
  loading = signal(false);
  saving = signal(false);
  activeTab = signal<EditorTab>('workflows');
  showPublishDialog = signal(false);
  publishChangelog = '';
  versions = signal<ComponentVersion[]>([]);
  operations = signal<ComponentOperation[]>([]);
  workflowDefinitions = signal<{ id: string; name: string }[]>([]);
  showOpForm = signal(false);
  editingOpId = signal<string | null>(null);
  opSaving = signal(false);
  expandedOpId = signal<string | null>(null);
  editorVisible = signal(false);
  deployInitializing = signal(false);

  // Computed: split operations by category
  deploymentOps = computed(() => this.operations().filter(op => op.operationCategory === 'DEPLOYMENT'));
  day2Ops = computed(() => this.operations().filter(op => op.operationCategory !== 'DEPLOYMENT'));
  allWorkflowOps = computed(() => [...this.deploymentOps(), ...this.day2Ops()]);

  // Activity signals
  deploymentActivities = signal<AutomatedActivity[]>([]);
  day2Activities = signal<AutomatedActivity[]>([]);
  allActivities = computed(() => [...this.deploymentActivities(), ...this.day2Activities()]);

  // Pre-loaded workflow definitions keyed by ID (for showing template info on all cards)
  workflowMap = signal<Map<string, WorkflowDefinition>>(new Map());
  workflowsLoaded = signal(false);

  // Track which activities have been customized (versions > 1 means user made changes)
  customizedActivityIds = signal<Set<string>>(new Set());

  // Dropdown options
  semanticTypeOptions = signal<SelectOption[]>([]);
  providerOptions = signal<SelectOption[]>([]);
  providerId = '';

  isProviderMode = computed(() => (this.route.snapshot.data['mode'] as ComponentMode) === 'provider');
  basePath = computed(() => this.isProviderMode() ? '/provider/components' : '/components');

  form = {
    name: '',
    displayName: '',
    description: '',
    semanticTypeId: '',
    code: EXAMPLE_CODE,
  };

  opForm = {
    displayName: '',
    description: '',
    workflowDefinitionId: '',
    downtimeMinutes: 0,
  };

  isNew = computed(() => !this.route.snapshot.params['id']);

  ngOnInit(): void {
    const id = this.route.snapshot.params['id'];
    this.loadSemanticTypes();
    this.loadProvider();

    if (id) {
      this.loadComponent(id);
    } else {
      // Trigger editor visibility after a tick so Monaco gets a real DOM size
      setTimeout(() => {
        this.editorVisible.set(true);
        this.cdr.markForCheck();
      }, 50);
    }
  }

  private loadSemanticTypes(): void {
    this.semanticService.listTypes({ limit: 500, infrastructureOnly: true }).subscribe({
      next: (result) => {
        this.semanticTypeOptions.set(
          result.items.map(t => ({ value: t.id, label: `${t.displayName} (${t.category?.name || t.name})` }))
        );
        this.cdr.markForCheck();
      },
    });
  }

  private loadProvider(): void {
    this.semanticService.listProviders().subscribe({
      next: (providers) => {
        this.providerOptions.set(
          providers.map(p => ({ value: p.id, label: p.displayName || p.name }))
        );
        // Auto-select first provider for new components if only one exists
        if (this.isNew() && providers.length === 1) {
          this.providerId = providers[0].id;
        }
        this.cdr.markForCheck();
      },
    });
  }

  private loadComponent(id: string): void {
    this.loading.set(true);
    this.componentService.getComponent(id, this.isProviderMode()).subscribe({
      next: (c) => {
        this.component.set(c);
        this.form.name = c.name;
        this.form.displayName = c.displayName;
        this.form.description = c.description || '';
        this.form.semanticTypeId = c.semanticTypeId;
        this.form.code = c.code || EXAMPLE_CODE;
        this.providerId = c.providerId;
        this.versions.set(c.versions || []);
        this.operations.set(c.operations || []);
        this.loadComponentActivities();
        this.loadComponentWorkflows(c.operations || []);

        this.loading.set(false);
        // Show editor after data loads
        setTimeout(() => {
          this.editorVisible.set(true);
          this.cdr.markForCheck();
        }, 50);
        this.cdr.markForCheck();
      },
      error: () => this.loading.set(false),
    });
  }

  private loadComponentActivities(): void {
    const comp = this.component();
    if (!comp) return;
    // Load activities that have component_id set to this component
    this.activityService.listActivities({ componentId: comp.id, limit: 200 }).subscribe({
      next: (list) => {
        // Only update signals if we actually found per-component activities;
        // otherwise leave existing data (from fallback loaders) untouched
        if (list.length > 0) {
          this.deploymentActivities.set(list.filter(a => a.operationKind === 'CREATE' || a.operationKind === 'DELETE' || a.operationKind === 'RESTORE'));
          this.day2Activities.set(list.filter(a => a.operationKind !== 'CREATE' && a.operationKind !== 'DELETE' && a.operationKind !== 'RESTORE'));
          this.trackActivityCustomization(list);
          this.cdr.markForCheck();
        }
      },
    });
  }

  /** Track which forked activities have been customized (have more than 1 version) */
  private trackActivityCustomization(activities: AutomatedActivity[]): void {
    const ids = new Set(this.customizedActivityIds());
    for (const act of activities) {
      if (act.templateActivityId && act.versions && act.versions.length > 1) {
        ids.add(act.id);
      }
    }
    this.customizedActivityIds.set(ids);
  }

  /** Check if a forked activity has been customized (has multiple versions) */
  isActivityCustomized(act: AutomatedActivity): boolean {
    if (this.customizedActivityIds().has(act.id)) return true;
    if (act.versions && act.versions.length > 1) return true;
    return false;
  }

  /** Pre-load all WorkflowDefinition objects for the component's operations */
  private loadComponentWorkflows(ops: ComponentOperation[]): void {
    const wfIds = [...new Set(ops.map(o => o.workflowDefinitionId).filter(Boolean))];
    if (wfIds.length === 0) {
      this.workflowsLoaded.set(true);
      return;
    }

    // Wrap each fetch in catchError so missing/deleted workflows don't break forkJoin
    const fetches = wfIds.map(id =>
      this.workflowService.getDefinition(id).pipe(catchError(() => of(null)))
    );
    forkJoin(fetches).subscribe({
      next: (workflows) => {
        const map = new Map<string, WorkflowDefinition>();
        for (const wf of workflows) {
          if (wf) map.set(wf.id, wf);
        }
        this.workflowMap.set(map);
        this.workflowsLoaded.set(true);

        // If no component activities were loaded yet, extract activity references
        // from workflow graph nodes and load them
        if (this.allActivities().length === 0) {
          this.loadActivitiesFromWorkflowGraphs(workflows.filter(Boolean) as WorkflowDefinition[]);
        }

        this.cdr.markForCheck();
      },
    });
  }

  /** Fallback: extract activity IDs/slugs from workflow graph nodes, or load system deployment activities */
  private loadActivitiesFromWorkflowGraphs(workflows: WorkflowDefinition[]): void {
    const activityIds = new Set<string>();
    for (const wf of workflows) {
      if (!wf.graph?.nodes) continue;
      for (const node of wf.graph.nodes) {
        const actId = node.config?.['activity_id'] as string;
        if (actId) activityIds.add(actId);
      }
    }

    if (activityIds.size > 0) {
      const fetches = [...activityIds].map(id =>
        this.activityService.getActivity(id).pipe(catchError(() => of(null)))
      );
      forkJoin(fetches).subscribe({
        next: (activities) => {
          const valid = activities.filter(Boolean) as AutomatedActivity[];
          if (valid.length > 0) {
            this.deploymentActivities.set(valid.filter(a => a.operationKind === 'CREATE' || a.operationKind === 'DELETE' || a.operationKind === 'RESTORE'));
            this.day2Activities.set(valid.filter(a => a.operationKind !== 'CREATE' && a.operationKind !== 'DELETE' && a.operationKind !== 'RESTORE'));
            this.trackActivityCustomization(valid);
            this.cdr.markForCheck();
          } else {
            this.loadSystemDeploymentActivities();
          }
        },
      });
    } else {
      // No activity IDs in graphs — load system deployment activities as fallback
      this.loadSystemDeploymentActivities();
    }
  }

  /** Load system deployment activities when no per-component activities exist */
  private loadSystemDeploymentActivities(): void {
    if (this.deploymentOps().length === 0) return;
    // Load all deployment-type activities (system defaults, no componentId filter)
    this.activityService.listActivities({ isComponentActivity: false, limit: 50 }).subscribe({
      next: (list) => {
        if (list.length > 0) {
          this.deploymentActivities.set(list);
          this.cdr.markForCheck();
        }
      },
    });
  }

  /** Get the pre-loaded workflow for an operation */
  getWorkflowForOp(op: ComponentOperation): WorkflowDefinition | null {
    return this.workflowMap().get(op.workflowDefinitionId) ?? null;
  }

  editActivity(activityId: string): void {
    const comp = this.component();
    if (!comp) return;
    this.router.navigate([this.basePath(), comp.id, 'activities', activityId]);
  }

  createDay2Activity(): void {
    const comp = this.component();
    if (!comp) return;
    this.router.navigate([this.basePath(), comp.id, 'activities', 'new'], {
      queryParams: { componentId: comp.id, isComponentActivity: true },
    });
  }

  createBlankWorkflow(): void {
    const comp = this.component();
    if (!comp) return;
    const returnTo = `${this.basePath()}/${comp.id}/edit`;
    this.router.navigate(['/workflows', 'definitions', 'new'], {
      queryParams: {
        returnTo,
        componentId: comp.id,
        applicableSemanticTypeId: comp.semanticTypeId,
        applicableProviderId: comp.providerId,
      },
    });
  }

  loadVersions(): void {
    const comp = this.component();
    if (!comp) return;
    this.componentService.getVersionHistory(comp.id).subscribe({
      next: (v) => {
        this.versions.set(v);
        this.cdr.markForCheck();
      },
    });
  }

  // ── Operations ───────────────────────────────────────────────────

  loadOperations(): void {
    const comp = this.component();
    if (!comp) return;
    // Load operations from the component's embedded list first
    this.operations.set(comp.operations || []);
    // Only re-fetch workflows and activities if not already loaded
    if (!this.workflowsLoaded()) {
      this.loadComponentWorkflows(comp.operations || []);
      this.loadComponentActivities();
    }
    // Load workflow definitions filtered by applicability (semantic type + provider)
    this.loadApplicableWorkflows();
  }

  resetOpForm(): void {
    this.editingOpId.set(null);
    this.opForm = { displayName: '', description: '', workflowDefinitionId: '', downtimeMinutes: 0 };
    if (this.workflowDefinitions().length === 0) {
      this.loadApplicableWorkflows();
    }
  }

  editOperation(op: ComponentOperation): void {
    this.showOpForm.set(false);
    this.editingOpId.set(op.id);
    this.opForm = {
      displayName: op.displayName,
      description: op.description || '',
      workflowDefinitionId: op.workflowDefinitionId,
      downtimeMinutes: this.parseDowntimeMinutes(op.estimatedDowntime),
    };
    if (this.workflowDefinitions().length === 0) {
      this.loadApplicableWorkflows();
    }
  }

  getWorkflowName(id: string): string {
    const wf = this.workflowDefinitions().find(w => w.id === id);
    return wf?.name || '(linked workflow)';
  }

  parseDowntimeMinutes(downtime: EstimatedDowntime | string): number {
    if (!downtime || downtime === 'NONE') return 0;
    if (downtime === 'BRIEF') return 5;
    if (downtime === 'EXTENDED') return 30;
    const n = parseInt(downtime as string, 10);
    return isNaN(n) ? 0 : n;
  }

  private minutesToDowntime(minutes: number): EstimatedDowntime {
    if (minutes <= 0) return 'NONE';
    if (minutes <= 5) return 'BRIEF';
    return 'EXTENDED';
  }

  private toSlug(displayName: string): string {
    return displayName.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
  }

  private loadApplicableWorkflows(): void {
    const comp = this.component();
    if (comp?.semanticTypeId && comp?.providerId) {
      this.workflowService.listOperationWorkflows(comp.semanticTypeId, comp.providerId).subscribe({
        next: (defs) => {
          this.workflowDefinitions.set(defs.map(d => ({ id: d.id, name: d.name })));
          this.cdr.markForCheck();
        },
      });
    } else {
      // Fallback: load all active workflows
      this.workflowService.listDefinitions({ status: 'ACTIVE', limit: 500 }).subscribe({
        next: (defs) => {
          this.workflowDefinitions.set(defs.map(d => ({ id: d.id, name: d.name })));
          this.cdr.markForCheck();
        },
      });
    }
  }

  cancelOpForm(): void {
    this.showOpForm.set(false);
    this.editingOpId.set(null);
  }

  toggleOperationExpand(op: ComponentOperation): void {
    if (this.expandedOpId() === op.id) {
      this.expandedOpId.set(null);
      return;
    }
    this.expandedOpId.set(op.id);
  }

  editWorkflow(workflowDefinitionId: string): void {
    const comp = this.component();
    const returnTo = comp ? `${this.basePath()}/${comp.id}/edit` : undefined;
    this.router.navigate(['/workflows', 'definitions', workflowDefinitionId, 'edit'], {
      queryParams: returnTo ? { returnTo } : undefined,
    });
  }

  saveOperation(): void {
    const comp = this.component();
    if (!comp) return;
    if (!this.opForm.displayName || !this.opForm.workflowDefinitionId) {
      this.toastService.error('Display name and workflow are required');
      return;
    }

    this.opSaving.set(true);
    const providerMode = this.isProviderMode();
    const downtime = this.minutesToDowntime(this.opForm.downtimeMinutes);

    if (this.editingOpId()) {
      this.componentService.updateOperation(this.editingOpId()!, {
        displayName: this.opForm.displayName,
        name: this.toSlug(this.opForm.displayName),
        description: this.opForm.description || undefined,
        estimatedDowntime: downtime,
      }, providerMode).subscribe({
        next: (updated) => {
          this.operations.update(ops => ops.map(o => o.id === updated.id ? updated : o));
          this.editingOpId.set(null);
          this.opSaving.set(false);
          this.toastService.success('Operation updated');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.opSaving.set(false);
          this.toastService.error('Failed: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    } else {
      const input: ComponentOperationCreateInput = {
        name: this.toSlug(this.opForm.displayName),
        displayName: this.opForm.displayName,
        workflowDefinitionId: this.opForm.workflowDefinitionId,
        description: this.opForm.description || undefined,
        estimatedDowntime: downtime,
      };
      this.componentService.createOperation(comp.id, input, providerMode).subscribe({
        next: (created) => {
          this.operations.update(ops => [...ops, created]);
          this.showOpForm.set(false);
          this.opSaving.set(false);
          this.toastService.success('Operation created');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.opSaving.set(false);
          this.toastService.error('Failed: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    }
  }

  deleteOperation(op: ComponentOperation): void {
    if (!confirm(`Delete operation "${op.displayName}"?`)) return;
    this.componentService.deleteOperation(op.id, this.isProviderMode()).subscribe({
      next: () => {
        this.operations.update(ops => ops.filter(o => o.id !== op.id));
        this.toastService.success('Operation deleted');
        this.cdr.markForCheck();
      },
      error: (err) => this.toastService.error('Failed: ' + err.message),
    });
  }

  initDeploymentOps(): void {
    const comp = this.component();
    if (!comp) return;
    this.deployInitializing.set(true);
    this.componentService.initializeDeploymentOperations(comp.id, this.isProviderMode()).subscribe({
      next: (ops) => {
        this.operations.update(existing => [...existing, ...ops]);
        this.deployInitializing.set(false);
        this.toastService.success('Deployment operations initialized');
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.deployInitializing.set(false);
        this.toastService.error('Failed: ' + err.message);
        this.cdr.markForCheck();
      },
    });
  }

  resetDeployWorkflow(op: ComponentOperation): void {
    if (!confirm(`Reset "${op.displayName}" workflow to the default template? Any customizations will be lost.`)) return;
    this.componentService.resetDeploymentWorkflow(op.id, this.isProviderMode()).subscribe({
      next: (updated) => {
        this.operations.update(ops => ops.map(o => o.id === updated.id ? updated : o));
        this.toastService.success(`${op.displayName} workflow reset to default`);
        this.cdr.markForCheck();
      },
      error: (err) => this.toastService.error('Failed: ' + err.message),
    });
  }

  getSchemaFieldCount(schema: Record<string, unknown>): number {
    const props = schema['properties'] as Record<string, unknown> | undefined;
    return props ? Object.keys(props).length : 0;
  }

  // ── Version restore ───────────────────────────────────────────────

  restoreVersion(v: ComponentVersion): void {
    if (!confirm(`Restore code from v${v.version}? Current draft will be overwritten.`)) return;
    this.form.code = v.code;

    // Force Monaco to re-render with new code
    this.editorVisible.set(false);
    setTimeout(() => {
      this.editorVisible.set(true);
      this.cdr.markForCheck();
    }, 50);

    this.activeTab.set('workflows');
    this.toastService.success(`Restored from v${v.version}. Save to persist.`);
    this.cdr.markForCheck();
  }

  // ── Cancel / Save / Publish ──────────────────────────────────────

  onCancel(): void {
    this.router.navigate([this.basePath()]);
  }

  save(): void {
    this.saving.set(true);
    const comp = this.component();
    const providerMode = this.isProviderMode();

    if (comp) {
      this.componentService.updateComponent(comp.id, {
        name: this.form.name,
        displayName: this.form.displayName,
        description: this.form.description || undefined,
        code: this.form.code,
        language: 'python',
      }, providerMode).subscribe({
        next: (updated) => {
          this.component.set(updated);
          this.saving.set(false);
          this.toastService.success('Component saved');
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error('Failed to save: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    } else {
      if (!this.providerId) {
        this.saving.set(false);
        this.toastService.error('No provider available. Create a provider first.');
        return;
      }
      const input: ComponentCreateInput = {
        name: this.form.name,
        displayName: this.form.displayName,
        providerId: this.providerId,
        semanticTypeId: this.form.semanticTypeId,
        language: 'python',
        description: this.form.description || undefined,
        code: this.form.code,
      };
      this.componentService.createComponent(input, providerMode).subscribe({
        next: (created) => {
          this.component.set(created);
          this.saving.set(false);
          this.toastService.success('Component created');
          this.router.navigate([this.basePath(), created.id, 'edit']);
          this.cdr.markForCheck();
        },
        error: (err) => {
          this.saving.set(false);
          this.toastService.error('Failed to create: ' + err.message);
          this.cdr.markForCheck();
        },
      });
    }
  }

  publish(): void {
    const comp = this.component();
    if (!comp) return;

    this.componentService.publishComponent(comp.id, this.publishChangelog, this.isProviderMode()).subscribe({
      next: (updated) => {
        this.component.set(updated);
        this.versions.set(updated.versions || []);
        this.showPublishDialog.set(false);
        this.publishChangelog = '';
        this.toastService.success('Component published');
        this.cdr.markForCheck();
      },
      error: (err) => {
        this.toastService.error('Failed to publish: ' + err.message);
      },
    });
  }

  confirmDelete(): void {
    const comp = this.component();
    if (!comp) return;
    if (!confirm('Are you sure you want to delete this component?')) return;

    this.componentService.deleteComponent(comp.id, this.isProviderMode()).subscribe({
      next: () => {
        this.toastService.success('Component deleted');
        this.router.navigate([this.basePath()]);
      },
    });
  }
}
