/**
 * Overview: Topology detail view with read-only canvas, properties, export, and version history tabs.
 * Architecture: Detail page for architecture planner (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common, architecture services
 * Concepts: Read-only topology view, version history, export, clone/edit actions, light theme
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ArchitectureService } from '@core/services/architecture.service';
import { SemanticService } from '@core/services/semantic.service';
import { WorkflowService } from '@core/services/workflow.service';
import { ArchitectureTopology, TopologyGraph } from '@shared/models/architecture.model';
import { SemanticResourceType } from '@shared/models/semantic.model';
import { WorkflowDefinition } from '@shared/models/workflow.model';
import { ArchitectureCanvasComponent } from '../editor/architecture-canvas.component';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-topology-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent, ArchitectureCanvasComponent, FormsModule],
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (topology()) {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/architecture" class="breadcrumb-link">Architecture Topologies</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ topology()!.name }}</span>
              </div>
              <h1 class="page-title">
                {{ topology()!.name }}
                <span class="status-badge" [class]="'badge-' + topology()!.status.toLowerCase()">
                  {{ topology()!.status }}
                </span>
                <span class="version-badge">v{{ topology()!.version }}</span>
              </h1>
              @if (topology()?.description) {
                <p class="page-subtitle">{{ topology()!.description }}</p>
              }
            </div>
            <div class="header-actions">
              <button class="btn btn-secondary" (click)="onClone()">Clone</button>
              @if (topology()!.status !== 'ARCHIVED') {
                <button class="btn btn-secondary" (click)="onArchive()">Archive</button>
              }
              @if (topology()!.status === 'PUBLISHED') {
                <button class="btn btn-primary" (click)="onEditDraft()">Edit (New Draft)</button>
                <button class="btn btn-deploy" (click)="showGenerateDialog.set(true)">Generate Deployment Workflow</button>
              }
              <button class="btn btn-secondary" (click)="onExport()">Export</button>
            </div>
          </div>

          <!-- Tabs -->
          <div class="tabs">
            <button
              class="tab" [class.active]="activeTab() === 'canvas'"
              (click)="activeTab.set('canvas')"
            >Canvas</button>
            <button
              class="tab" [class.active]="activeTab() === 'properties'"
              (click)="activeTab.set('properties')"
            >Properties</button>
            <button
              class="tab" [class.active]="activeTab() === 'versions'"
              (click)="activeTab.set('versions'); loadVersions()"
            >Versions</button>
            <button
              class="tab" [class.active]="activeTab() === 'workflows'"
              (click)="activeTab.set('workflows'); loadLinkedWorkflows()"
            >Deployment Workflows</button>
          </div>

          <div class="tab-content">
            @switch (activeTab()) {
              @case ('canvas') {
                <div class="canvas-wrapper">
                  <nimbus-architecture-canvas
                    [graph]="currentGraph()"
                    [semanticTypes]="semanticTypes()"
                    [readOnly]="true"
                  />
                </div>
              }
              @case ('properties') {
                <div class="properties-tab">
                  @if (topology()?.description) {
                    <div class="prop-section">
                      <h3>Description</h3>
                      <p>{{ topology()!.description }}</p>
                    </div>
                  }
                  @if (topology()?.tags?.length) {
                    <div class="prop-section">
                      <h3>Tags</h3>
                      <div class="tag-list">
                        @for (tag of topology()!.tags || []; track tag) {
                          <span class="tag">{{ tag }}</span>
                        }
                      </div>
                    </div>
                  }
                  <div class="prop-section">
                    <h3>Metadata</h3>
                    <div class="meta-grid">
                      <div class="meta-item">
                        <span class="meta-label">Created</span>
                        <span class="meta-value">{{ topology()!.createdAt | date:'medium' }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">Updated</span>
                        <span class="meta-value">{{ topology()!.updatedAt | date:'medium' }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">Nodes</span>
                        <span class="meta-value">{{ currentGraph()?.nodes?.length || 0 }}</span>
                      </div>
                      <div class="meta-item">
                        <span class="meta-label">Connections</span>
                        <span class="meta-value">{{ currentGraph()?.connections?.length || 0 }}</span>
                      </div>
                    </div>
                  </div>
                </div>
              }
              @case ('versions') {
                <div class="versions-tab">
                  <table class="table">
                    <thead>
                      <tr>
                        <th>Version</th>
                        <th>Status</th>
                        <th>Updated</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      @for (v of versions(); track v.id) {
                        <tr>
                          <td>v{{ v.version }}</td>
                          <td>
                            <span class="status-badge" [class]="'badge-' + v.status.toLowerCase()">
                              {{ v.status }}
                            </span>
                          </td>
                          <td>{{ v.updatedAt | date:'short' }}</td>
                          <td>
                            <a [routerLink]="['/architecture', v.id]" class="action-btn">View</a>
                          </td>
                        </tr>
                      }
                    </tbody>
                  </table>
                </div>
              }
              @case ('workflows') {
                <div class="workflows-tab">
                  @if (linkedWorkflows().length) {
                    <table class="table">
                      <thead>
                        <tr>
                          <th>Name</th>
                          <th>Status</th>
                          <th>Version</th>
                          <th>Updated</th>
                          <th>Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        @for (w of linkedWorkflows(); track w.id) {
                          <tr>
                            <td>{{ w.name }}</td>
                            <td>
                              <span class="status-badge" [class]="'badge-' + w.status.toLowerCase()">
                                {{ w.status }}
                              </span>
                            </td>
                            <td>v{{ w.version }}</td>
                            <td>{{ w.updatedAt | date:'short' }}</td>
                            <td>
                              <a [routerLink]="['/workflows/definitions', w.id, 'edit']" class="action-btn">Edit</a>
                            </td>
                          </tr>
                        }
                      </tbody>
                    </table>
                  } @else {
                    <div class="empty-state">
                      <p>No deployment workflows linked to this topology.</p>
                      @if (topology()?.status === 'PUBLISHED') {
                        <button class="btn btn-deploy" (click)="showGenerateDialog.set(true)">
                          Generate Deployment Workflow
                        </button>
                      }
                    </div>
                  }
                </div>
              }
            }
          </div>

          <!-- Generate Deployment Workflow Dialog -->
          @if (showGenerateDialog()) {
            <div class="dialog-backdrop" (click)="showGenerateDialog.set(false)">
              <div class="dialog" (click)="$event.stopPropagation()">
                <h3>Generate Deployment Workflow</h3>
                <p class="dialog-desc">Create a deployment workflow from this topology. The workflow will be generated as a DRAFT.</p>
                <label class="checkbox-label">
                  <input type="checkbox" [checked]="genApprovalGates()" (change)="genApprovalGates.set(!genApprovalGates())" />
                  Add approval gates before each deployment group
                </label>
                <label class="checkbox-label">
                  <input type="checkbox" [checked]="genNotifications()" (change)="genNotifications.set(!genNotifications())" />
                  Add notifications after each deployment group
                </label>
                <div class="dialog-actions">
                  <button class="btn btn-secondary" (click)="showGenerateDialog.set(false)">Cancel</button>
                  <button class="btn btn-deploy" (click)="onGenerateWorkflow()" [disabled]="generating()">
                    {{ generating() ? 'Generating...' : 'Generate' }}
                  </button>
                </div>
              </div>
            </div>
          }
        } @else {
          <div class="loading">Loading...</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .breadcrumb { font-size: 0.8rem; color: #64748b; margin-bottom: 2px; }
    .breadcrumb-link { color: #3b82f6; text-decoration: none; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { margin: 0 4px; }
    .header-actions { display: flex; gap: 8px; }
    .status-badge {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #d1fae5; color: #065f46; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .version-badge { font-size: 0.75rem; color: #94a3b8; }
    .btn {
      padding: 8px 16px;
      border-radius: 8px;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      text-decoration: none;
      border: none;
      font-family: inherit;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary { background: #fff; color: #374151; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .tabs {
      display: flex;
      gap: 4px;
      margin-bottom: 16px;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 0;
    }
    .tab {
      padding: 8px 16px;
      border: none;
      background: none;
      font-size: 0.8125rem;
      font-weight: 500;
      color: #64748b;
      cursor: pointer;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;
      font-family: inherit;
    }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab:hover:not(.active) { color: #1e293b; }
    .tab-content { min-height: 400px; }
    .canvas-wrapper {
      height: 500px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .properties-tab {
      background: #fff;
      padding: 20px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .prop-section { margin-bottom: 20px; }
    .prop-section h3 {
      margin: 0 0 8px;
      font-size: 0.8125rem;
      font-weight: 600;
      color: #1e293b;
    }
    .prop-section p { margin: 0; font-size: 0.8125rem; color: #374151; }
    .tag-list { display: flex; gap: 6px; flex-wrap: wrap; }
    .tag {
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.6875rem;
      background: #f0f4ff;
      color: #3b82f6;
      font-weight: 500;
    }
    .meta-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 12px;
    }
    .meta-item {
      display: flex;
      flex-direction: column;
      gap: 2px;
    }
    .meta-label { font-size: 0.6875rem; color: #94a3b8; font-weight: 600; text-transform: uppercase; }
    .meta-value { font-size: 0.8125rem; color: #374151; }
    .versions-tab {
      background: #fff;
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
    .action-btn {
      color: #3b82f6;
      text-decoration: none;
      font-size: 0.75rem;
      font-weight: 500;
    }
    .action-btn:hover { text-decoration: underline; }
    .btn-deploy { background: #059669; color: #fff; }
    .btn-deploy:hover { background: #047857; }
    .btn-deploy:disabled { opacity: 0.5; cursor: default; }
    .workflows-tab {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .empty-state {
      padding: 32px;
      text-align: center;
      color: #94a3b8;
    }
    .empty-state p { margin-bottom: 12px; }
    .dialog-backdrop {
      position: fixed; top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.3); display: flex; align-items: center;
      justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 12px; padding: 24px;
      width: 420px; max-width: 90vw;
    }
    .dialog h3 { margin: 0 0 8px; font-size: 1rem; font-weight: 700; color: #1e293b; }
    .dialog-desc { font-size: 0.8125rem; color: #64748b; margin-bottom: 16px; }
    .checkbox-label {
      display: flex; align-items: center; gap: 8px;
      font-size: 0.8125rem; color: #374151; margin-bottom: 8px; cursor: pointer;
    }
    .dialog-actions {
      display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;
    }
    .loading { padding: 48px; text-align: center; color: #94a3b8; }
  `],
})
export class TopologyDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private architectureService = inject(ArchitectureService);
  private semanticService = inject(SemanticService);
  private workflowService = inject(WorkflowService);
  private toast = inject(ToastService);

  topology = signal<ArchitectureTopology | null>(null);
  semanticTypes = signal<SemanticResourceType[]>([]);
  currentGraph = signal<TopologyGraph | null>(null);
  versions = signal<ArchitectureTopology[]>([]);
  linkedWorkflows = signal<WorkflowDefinition[]>([]);
  activeTab = signal<'canvas' | 'properties' | 'versions' | 'workflows'>('canvas');

  // Generate dialog state
  showGenerateDialog = signal(false);
  genApprovalGates = signal(false);
  genNotifications = signal(false);
  generating = signal(false);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id')!;

    this.architectureService.getTopology(id).subscribe(t => {
      if (t) {
        this.topology.set(t);
        this.currentGraph.set(t.graph as TopologyGraph || { nodes: [], connections: [] });
      }
    });

    this.semanticService.listTypes({ limit: 500 }).subscribe(result => {
      this.semanticTypes.set(result.items || []);
    });
  }

  loadVersions(): void {
    const t = this.topology();
    if (!t) return;
    this.architectureService.getTopologyVersions(t.name).subscribe(v => {
      this.versions.set(v);
    });
  }

  onClone(): void {
    const t = this.topology();
    if (!t) return;
    this.architectureService.cloneTopology(t.id).subscribe({
      next: cloned => {
        this.toast.success('Topology cloned');
        this.router.navigate(['/architecture', cloned.id, 'edit']);
      },
      error: err => this.toast.error(err.message || 'Clone failed'),
    });
  }

  onArchive(): void {
    const t = this.topology();
    if (!t) return;
    this.architectureService.archiveTopology(t.id).subscribe({
      next: archived => {
        this.topology.set(archived);
        this.toast.success('Topology archived');
      },
      error: err => this.toast.error(err.message || 'Archive failed'),
    });
  }

  onEditDraft(): void {
    const t = this.topology();
    if (!t) return;
    this.architectureService.cloneTopology(t.id).subscribe({
      next: draft => {
        this.router.navigate(['/architecture', draft.id, 'edit']);
      },
      error: err => this.toast.error(err.message || 'Failed to create draft'),
    });
  }

  onExport(): void {
    const t = this.topology();
    if (!t) return;
    this.architectureService.exportTopology(t.id, 'json').subscribe({
      next: result => {
        const blob = new Blob([JSON.stringify(result.data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${t.name}.json`;
        a.click();
        URL.revokeObjectURL(url);
      },
      error: err => this.toast.error(err.message || 'Export failed'),
    });
  }

  loadLinkedWorkflows(): void {
    const t = this.topology();
    if (!t) return;
    this.workflowService.getDeploymentWorkflowsForTopology(t.id).subscribe({
      next: workflows => this.linkedWorkflows.set(workflows),
      error: () => this.linkedWorkflows.set([]),
    });
  }

  onGenerateWorkflow(): void {
    const t = this.topology();
    if (!t) return;
    this.generating.set(true);
    this.workflowService.generateDeploymentWorkflow({
      topologyId: t.id,
      addApprovalGates: this.genApprovalGates(),
      addNotifications: this.genNotifications(),
    }).subscribe({
      next: def => {
        this.showGenerateDialog.set(false);
        this.generating.set(false);
        this.toast.success('Deployment workflow generated');
        this.router.navigate(['/workflows/definitions', def.id, 'edit']);
      },
      error: err => {
        this.generating.set(false);
        this.toast.error(err.message || 'Generation failed');
      },
    });
  }
}
