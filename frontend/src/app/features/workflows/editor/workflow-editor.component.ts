/**
 * Overview: Full workflow editor page — canvas + palette + properties panel + toolbar.
 * Architecture: Main editor page for workflow definitions (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Visual workflow editor, graph editing, save/validate/publish/test
 */
import { Component, OnInit, ViewChild, computed, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { switchMap, of, tap } from 'rxjs';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowDefinition, NodeTypeInfo, ValidationResult, WorkflowType, WorkflowGraph } from '@shared/models/workflow.model';
import { WorkflowCanvasComponent } from './workflow-canvas.component';
import { NodePaletteComponent } from './node-palette/node-palette.component';
import { PropertiesPanelComponent } from './properties-panel/properties-panel.component';
import { ValidationOverlayComponent } from './validation/validation-overlay.component';
import { GraphValidatorService } from './validation/graph-validator.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-workflow-editor',
  standalone: true,
  imports: [
    CommonModule, RouterLink, WorkflowCanvasComponent,
    NodePaletteComponent, PropertiesPanelComponent, ValidationOverlayComponent,
    LayoutComponent,
  ],
  template: `
    <nimbus-layout>
    <div class="editor-layout">
      <!-- Type indicator banner -->
      @if (definition()?.workflowType === 'SYSTEM') {
        <div class="type-banner system-banner">
          &#128274; System Workflow — editable template for system operations
        </div>
      }
      @if (definition()?.workflowType === 'DEPLOYMENT') {
        <div class="type-banner deployment-banner">
          &#128640; Deployment Workflow
          @if (definition()?.sourceTopologyId) {
            — <a [routerLink]="['/architecture', definition()!.sourceTopologyId]" class="banner-link">View Source Topology</a>
          }
        </div>
      }

      <!-- Toolbar -->
      <div class="editor-toolbar">
        <a routerLink="/workflows/definitions" class="back-link">&larr; Back</a>
        <span class="toolbar-title">{{ definition()?.name || 'New Workflow' }}</span>
        <div class="toolbar-actions">
          <button class="btn" (click)="save()" [disabled]="saving()">
            {{ saving() ? 'Saving...' : 'Save' }}
          </button>
          <button class="btn" (click)="validate()">Validate</button>
          @if (definition()?.status === 'DRAFT') {
            <button class="btn btn-success" (click)="publish()">Publish</button>
          }
          <button class="btn" (click)="test()">Test</button>
        </div>
      </div>

      <div class="editor-body">
        <!-- Node Palette (left) -->
        <nimbus-node-palette
          [nodeTypes]="nodeTypes()"
          [workflowType]="definition()?.workflowType ?? 'AUTOMATION'"
          (addNode)="onAddNode($event)"
        />

        <!-- Canvas (center) -->
        <div class="canvas-area">
          <nimbus-workflow-canvas
            #canvas
            [graph]="definition()?.graph ?? null"
            [nodeTypes]="nodeTypes()"
            (nodeSelected)="onNodeSelected($event)"
          />
          <nimbus-validation-overlay [validationResult]="validationResult()" />
        </div>

        <!-- Properties Panel (right) -->
        <nimbus-properties-panel
          [nodeTypes]="nodeTypes()"
          [selectedNode]="selectedNode()"
          [graphContext]="graphContext()"
          [workflowProps]="workflowProps()"
          (configChange)="onConfigChange($event)"
          (workflowNameChange)="onNameChange($event)"
          (workflowDescriptionChange)="onDescriptionChange($event)"
          (timeoutChange)="onTimeoutChange($event)"
        />
      </div>
    </div>
    </nimbus-layout>
  `,
  styles: [`
    :host { display: block; height: 100%; }
    .editor-layout { display: flex; flex-direction: column; height: calc(100vh - 64px); }
    .editor-toolbar {
      display: flex; align-items: center; gap: 12px;
      padding: 8px 16px; background: #fff; border-bottom: 1px solid #e2e8f0;
    }
    .back-link { color: #64748b; text-decoration: none; font-size: 0.8125rem; }
    .back-link:hover { color: #3b82f6; }
    .toolbar-title { flex: 1; color: #1e293b; font-weight: 600; font-size: 0.875rem; }
    .toolbar-actions { display: flex; gap: 8px; }
    .btn {
      padding: 6px 14px; border: 1px solid #e2e8f0; background: #fff;
      color: #1e293b; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      transition: background 0.15s;
    }
    .btn:hover { background: #f8fafc; }
    .btn:disabled { opacity: 0.5; cursor: default; }
    .btn-success { border-color: #16a34a; color: #16a34a; }
    .btn-success:hover { background: #f0fdf4; }
    .type-banner {
      padding: 6px 16px; font-size: 0.75rem; font-weight: 500;
    }
    .system-banner { background: #f3e8ff; color: #7c3aed; }
    .deployment-banner { background: #ecfdf5; color: #059669; }
    .banner-link { color: inherit; text-decoration: underline; }
    .banner-link:hover { opacity: 0.8; }
    .editor-body { display: flex; flex: 1; overflow: hidden; }
    .canvas-area { flex: 1; position: relative; }
  `],
})
export class WorkflowEditorComponent implements OnInit {
  @ViewChild('canvas') canvasRef!: WorkflowCanvasComponent;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private workflowService = inject(WorkflowService);
  private graphValidator = inject(GraphValidatorService);

  definition = signal<WorkflowDefinition | null>(null);
  nodeTypes = signal<NodeTypeInfo[]>([]);
  validationResult = signal<ValidationResult | null>(null);
  saving = signal(false);
  selectedNode = signal<{ id: string; type: string; config: Record<string, unknown> } | null>(null);

  workflowProps = signal<{ name: string; description: string; timeoutSeconds: number } | null>(null);
  private _graphVersion = signal(0);

  graphContext = computed(() => {
    // Re-compute when graph version changes (node selection, graph edits)
    this._graphVersion();
    if (!this.canvasRef) return null;
    const graph = this.canvasRef.getGraph();
    return { nodes: graph.nodes, connections: graph.connections };
  });

  private workflowName = '';
  private workflowDescription = '';
  private timeoutSeconds = 3600;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');

    // Load nodeTypes FIRST, then the definition — the canvas needs type info
    // (ports, categories, icons) before it can render the graph correctly.
    this.workflowService.getNodeTypes().pipe(
      tap(types => this.nodeTypes.set(types)),
      switchMap(() => id ? this.workflowService.getDefinition(id) : of(null)),
    ).subscribe(d => {
      if (d) {
        this.definition.set(d);
        this.workflowName = d.name;
        this.workflowDescription = d.description || '';
        this.timeoutSeconds = d.timeoutSeconds;
        this.workflowProps.set({
          name: d.name,
          description: d.description || '',
          timeoutSeconds: d.timeoutSeconds,
        });
      }
    });
  }

  onAddNode(typeId: string): void {
    this.canvasRef?.addNode(typeId, { x: 300, y: 200 });
  }

  onNodeSelected(nodeId: string | null): void {
    if (nodeId && this.canvasRef) {
      const type = this.canvasRef.editorService.getNodeType(nodeId);
      const config = this.canvasRef.editorService.getNodeConfig(nodeId);
      this.selectedNode.set(type ? { id: nodeId, type, config: config || {} } : null);
      this._graphVersion.update(v => v + 1);
    } else {
      this.selectedNode.set(null);
    }
  }

  onConfigChange(config: Record<string, unknown>): void {
    const node = this.selectedNode();
    if (node && this.canvasRef) {
      this.canvasRef.editorService.updateNodeConfig(node.id, config);
    }
  }

  onNameChange(name: string): void { this.workflowName = name; }
  onDescriptionChange(desc: string): void { this.workflowDescription = desc; }
  onTimeoutChange(timeout: number): void { this.timeoutSeconds = timeout; }

  save(): void {
    const def = this.definition();
    const graph = this.canvasRef?.getGraph();
    this.saving.set(true);

    const input = {
      name: this.workflowName,
      description: this.workflowDescription || undefined,
      graph: graph as any,
      timeoutSeconds: this.timeoutSeconds,
    };

    if (def) {
      this.workflowService.updateDefinition(def.id, input).subscribe({
        next: updated => { if (updated) this.definition.set(updated); this.saving.set(false); },
        error: () => this.saving.set(false),
      });
    } else {
      this.workflowService.createDefinition({ ...input, name: this.workflowName || 'Untitled' }).subscribe({
        next: created => {
          this.definition.set(created);
          this.router.navigate(['/workflows/definitions', created.id, 'edit'], { replaceUrl: true });
          this.saving.set(false);
        },
        error: () => this.saving.set(false),
      });
    }
  }

  validate(): void {
    const graph = this.canvasRef?.getGraph();
    if (graph) {
      const result = this.graphValidator.validate(graph);
      this.validationResult.set(result);
    }
  }

  publish(): void {
    const def = this.definition();
    if (def) {
      this.workflowService.publishDefinition(def.id).subscribe(updated => {
        this.definition.set(updated);
      });
    }
  }

  test(): void {
    const def = this.definition();
    if (def) {
      this.workflowService.startExecution({
        definitionId: def.id,
        isTest: true,
      }).subscribe(exec => {
        this.router.navigate(['/workflows/executions', exec.id]);
      });
    }
  }
}
