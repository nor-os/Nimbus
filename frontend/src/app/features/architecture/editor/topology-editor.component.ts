/**
 * Overview: Topology editor page — three-panel layout with palette, canvas, and properties panel.
 * Architecture: Main editor page for architecture planner (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, architecture services
 * Concepts: Three-panel layout, auto-save draft, read-only for published/archived, light theme
 */
import { Component, OnInit, OnDestroy, ViewChild, inject, signal, computed, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { Subject, debounceTime, takeUntil } from 'rxjs';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ArchitectureService } from '@core/services/architecture.service';
import { SemanticService } from '@core/services/semantic.service';
import { ClusterService } from '@core/services/cluster.service';
import { ToastService } from '@shared/services/toast.service';
import {
  ArchitectureTopology,
  TopologyGraph,
  TopologyCompartment,
  TopologyStackInstance,
  ParameterOverride,
} from '@shared/models/architecture.model';
import { SemanticResourceType, SemanticRelationshipKind } from '@shared/models/semantic.model';
import { ServiceCluster, StackBlueprintParameter } from '@shared/models/cluster.model';
import { ArchitectureCanvasComponent } from './architecture-canvas.component';
import { ComponentPaletteComponent } from './component-palette/component-palette.component';
import { TopologyPropertiesPanelComponent } from './properties-panel/topology-properties-panel.component';
import { ConnectionDialogComponent } from './connection-dialog/connection-dialog.component';
import { ResolutionPreviewComponent } from './resolution-preview/resolution-preview.component';
import { ResolutionPreview } from '@shared/models/architecture.model';

@Component({
  selector: 'nimbus-topology-editor',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    LayoutComponent,
    ArchitectureCanvasComponent,
    ComponentPaletteComponent,
    TopologyPropertiesPanelComponent,
    ConnectionDialogComponent,
    ResolutionPreviewComponent,
  ],
  template: `
    <nimbus-layout>
      <div class="editor-page">
        <!-- Top toolbar -->
        <div class="editor-toolbar">
          <div class="toolbar-left">
            <input
              type="text"
              class="name-input"
              [(ngModel)]="topologyName"
              [disabled]="isReadOnly()"
              placeholder="Topology name..."
            />
            @if (topology()) {
              <span class="status-badge" [class]="'badge-' + topology()!.status.toLowerCase()">
                {{ topology()!.status }}
              </span>
              <span class="version-badge">v{{ topology()!.version }}</span>
            }
          </div>
          <div class="toolbar-right">
            @if (!isReadOnly()) {
              <button class="btn btn-secondary" (click)="onValidate()">Validate</button>
              <button class="btn btn-secondary" (click)="onSave()">Save</button>
              <button class="btn btn-primary" (click)="onPublish()">Publish</button>
            }
            @if (topology()) {
              <button class="btn btn-secondary" (click)="onPreviewResolution()">Preview Resolution</button>
            }
            <button class="btn btn-secondary" (click)="onExport()">Export</button>
          </div>
        </div>

        <!-- Three-panel layout -->
        <div class="editor-body">
          @if (!isReadOnly()) {
            <nimbus-component-palette
              [semanticTypes]="semanticTypes()"
              [availableBlueprints]="blueprints()"
              (addComponent)="onAddComponent($event)"
              (addCompartment)="onAddCompartment()"
              (addCompartmentFromType)="onAddCompartmentFromType($event)"
              (addStack)="onAddStack($event)"
            />
          }

          <nimbus-architecture-canvas
            #canvas
            [graph]="currentGraph()"
            [semanticTypes]="semanticTypes()"
            [blueprints]="blueprints()"
            [readOnly]="isReadOnly()"
            (graphChange)="onGraphChange($event)"
            (nodeSelected)="onNodeSelected($event)"
            (compartmentSelected)="onCompartmentSelected($event)"
            (stackSelected)="onStackSelected($event)"
            (validateRequest)="onValidate()"
          />

          <nimbus-topology-properties-panel
            [selectedNodeId]="selectedNodeId()"
            [selectedType]="selectedType()"
            [nodeProperties]="selectedNodeProperties()"
            [nodeLabel]="selectedNodeLabel()"
            [nodeCount]="nodeCount()"
            [connectionCount]="connectionCount()"
            [compartmentCount]="compartmentCount()"
            [stackCount]="stackCount()"
            [readOnly]="isReadOnly()"
            [selectedCompartment]="selectedCompartmentObj()"
            [compartmentParentOptions]="compartmentParentOptions()"
            [selectedStack]="selectedStackObj()"
            [stackBlueprintParams]="selectedStackParams()"
            (labelChange)="onNodeLabelChange($event)"
            (propertyChange)="onNodePropertyChange($event)"
            (compartmentUpdate)="onCompartmentUpdate($event)"
            (stackLabelChange)="onStackLabelChange($event)"
            (stackOverridesChange)="onStackOverridesChange($event)"
          />
        </div>

        <!-- Validation messages -->
        @if (validationErrors().length > 0) {
          <div class="validation-bar">
            @for (err of validationErrors(); track err.message) {
              <span class="validation-error">{{ err.message }}</span>
            }
          </div>
        }
      </div>

      @if (showResolutionPreview()) {
        <nimbus-resolution-preview
          [preview]="resolutionPreview()"
          (close)="showResolutionPreview.set(false)"
        />
      }
    </nimbus-layout>
  `,
  styles: [`
    .editor-page {
      display: flex;
      flex-direction: column;
      height: calc(100vh - 56px);
      background: #f5f6f8;
    }
    .editor-toolbar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 16px;
      background: #fff;
      border-bottom: 1px solid #e2e8f0;
      min-height: 48px;
    }
    .toolbar-left {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .toolbar-right {
      display: flex;
      align-items: center;
      gap: 8px;
    }
    .name-input {
      padding: 6px 10px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.875rem;
      font-weight: 600;
      color: #1e293b;
      background: #fff;
      min-width: 240px;
      outline: none;
      font-family: inherit;
    }
    .name-input:focus { border-color: #3b82f6; }
    .name-input:disabled { background: #f8fafc; }
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
    .version-badge {
      font-size: 0.6875rem;
      color: #94a3b8;
      font-weight: 500;
    }
    .btn {
      padding: 6px 14px;
      border-radius: 6px;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
      border: none;
      font-family: inherit;
      transition: background 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary {
      background: #fff;
      color: #374151;
      border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .editor-body {
      display: flex;
      flex: 1;
      overflow: hidden;
    }
    .validation-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      padding: 8px 16px;
      background: #fef2f2;
      border-top: 1px solid #fecaca;
    }
    .validation-error {
      font-size: 0.75rem;
      color: #dc2626;
    }
  `],
})
export class TopologyEditorComponent implements OnInit, OnDestroy {
  @ViewChild('canvas') canvas!: ArchitectureCanvasComponent;

  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private architectureService = inject(ArchitectureService);
  private semanticService = inject(SemanticService);
  private clusterService = inject(ClusterService);
  private toast = inject(ToastService);
  private destroy$ = new Subject<void>();
  private autoSave$ = new Subject<void>();

  topology = signal<ArchitectureTopology | null>(null);
  semanticTypes = signal<SemanticResourceType[]>([]);
  relationshipKinds = signal<SemanticRelationshipKind[]>([]);
  blueprints = signal<ServiceCluster[]>([]);
  currentGraph = signal<TopologyGraph | null>(null);
  selectedNodeId = signal<string | null>(null);
  selectedCompartmentId = signal<string | null>(null);
  selectedStackId = signal<string | null>(null);
  validationErrors = signal<{ message: string }[]>([]);
  showResolutionPreview = signal(false);
  resolutionPreview = signal<ResolutionPreview | null>(null);
  topologyName = '';

  isReadOnly = computed(() => {
    const t = this.topology();
    return !!t && t.status !== 'DRAFT';
  });

  selectedType = computed(() => {
    const nodeId = this.selectedNodeId();
    if (!nodeId || !this.canvas?.editorService) return null;
    return this.canvas.editorService.getSemanticType(nodeId) || null;
  });

  selectedNodeProperties = computed(() => {
    const nodeId = this.selectedNodeId();
    if (!nodeId || !this.canvas?.editorService) return {};
    return this.canvas.editorService.getNodeProperties(nodeId);
  });

  selectedNodeLabel = computed(() => {
    const nodeId = this.selectedNodeId();
    if (!nodeId) return '';
    const graph = this.currentGraph();
    const node = graph?.nodes.find(n => n.id === nodeId);
    return node?.label || '';
  });

  nodeCount = computed(() => this.currentGraph()?.nodes.length || 0);
  connectionCount = computed(() => this.currentGraph()?.connections.length || 0);
  compartmentCount = computed(() => this.currentGraph()?.compartments?.length || 0);
  stackCount = computed(() => this.currentGraph()?.stacks?.length || 0);

  selectedCompartmentObj = computed(() => {
    const id = this.selectedCompartmentId();
    if (!id || !this.canvas?.editorService) return null;
    return this.canvas.editorService.getCompartment(id) || null;
  });

  compartmentParentOptions = computed(() => {
    const selectedId = this.selectedCompartmentId();
    if (!this.canvas?.editorService) return [];
    return this.canvas.editorService.getCompartments()
      .filter(c => c.id !== selectedId)
      .map(c => ({ id: c.id, label: c.label }));
  });

  selectedStackObj = computed(() => {
    const id = this.selectedStackId();
    if (!id || !this.canvas?.editorService) return null;
    return this.canvas.editorService.getStack(id) || null;
  });

  selectedStackParams = computed((): StackBlueprintParameter[] => {
    const stack = this.selectedStackObj();
    if (!stack) return [];
    const bp = this.blueprints().find(b => b.id === stack.blueprintId);
    return bp?.parameters || [];
  });

  ngOnInit(): void {
    // Load semantic types — infrastructure categories only (not application/services)
    const INFRA_CATEGORIES = new Set([
      'compute', 'network', 'storage', 'database', 'security', 'monitoring',
    ]);
    this.semanticService.listTypes({ limit: 500 }).subscribe(result => {
      const infraTypes = (result.items || []).filter(
        t => INFRA_CATEGORIES.has(t.category?.name ?? ''),
      );
      this.semanticTypes.set(infraTypes);
    });

    this.semanticService.listRelationshipKinds().subscribe(kinds => {
      this.relationshipKinds.set(kinds);
    });

    // Load blueprints for stack palette
    this.clusterService.listClusters({ limit: 200 }).subscribe(result => {
      this.blueprints.set(result.items || []);
    });

    // Load topology if editing
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.architectureService.getTopology(id).subscribe(t => {
        if (t) {
          this.topology.set(t);
          this.topologyName = t.name;
          this.currentGraph.set(t.graph as TopologyGraph || { nodes: [], connections: [] });
        }
      });
    }

    // Auto-save debounced
    this.autoSave$.pipe(
      debounceTime(2000),
      takeUntil(this.destroy$),
    ).subscribe(() => this.saveQuietly());
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }

  onAddComponent(semanticTypeId: string): void {
    this.canvas?.addNode(semanticTypeId);
  }

  onGraphChange(graph: TopologyGraph): void {
    this.currentGraph.set(graph);
    if (!this.isReadOnly()) {
      this.autoSave$.next();
    }
  }

  onNodeSelected(nodeId: string | null): void {
    this.selectedNodeId.set(nodeId);
    this.selectedCompartmentId.set(null);
    this.selectedStackId.set(null);
  }

  onNodeLabelChange(label: string): void {
    const nodeId = this.selectedNodeId();
    if (nodeId && this.canvas?.editorService) {
      this.canvas.editorService.updateNodeLabel(nodeId, label);
    }
  }

  onNodePropertyChange(event: { name: string; value: unknown }): void {
    const nodeId = this.selectedNodeId();
    if (nodeId && this.canvas?.editorService) {
      const props = { ...this.canvas.editorService.getNodeProperties(nodeId) };
      props[event.name] = event.value;
      this.canvas.editorService.updateNodeProperties(nodeId, props);
    }
  }

  onSave(): void {
    const graph = this.canvas?.getGraph();
    if (!graph) return;

    const t = this.topology();
    if (t) {
      this.architectureService.updateTopology(t.id, {
        name: this.topologyName,
        graph: graph as any,
      }).subscribe({
        next: updated => {
          if (updated) this.topology.set(updated);
          this.toast.success('Topology saved');
        },
        error: err => this.toast.error(err.message || 'Save failed'),
      });
    } else {
      this.architectureService.createTopology({
        name: this.topologyName || 'Untitled Topology',
        graph: graph as any,
      }).subscribe({
        next: created => {
          this.topology.set(created);
          this.router.navigate(['/architecture', created.id, 'edit']);
          this.toast.success('Topology created');
        },
        error: err => this.toast.error(err.message || 'Create failed'),
      });
    }
  }

  onPublish(): void {
    const t = this.topology();
    if (!t) {
      this.toast.error('Save the topology first');
      return;
    }
    this.architectureService.publishTopology(t.id).subscribe({
      next: published => {
        this.topology.set(published);
        this.toast.success('Topology published');
      },
      error: err => this.toast.error(err.message || 'Publish failed'),
    });
  }

  onValidate(): void {
    const graph = this.canvas?.getGraph();
    if (!graph) return;
    this.architectureService.validateGraph(graph as any).subscribe({
      next: result => {
        this.validationErrors.set(result.errors);
        if (result.valid) {
          this.toast.success('Topology is valid');
        } else {
          this.toast.error(`${result.errors.length} validation error(s)`);
        }
      },
      error: err => this.toast.error(err.message || 'Validation failed'),
    });
  }

  onExport(): void {
    const t = this.topology();
    if (!t) {
      this.toast.error('Save the topology first');
      return;
    }
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

  // ── Compartment Handlers ───────────────────────────────────────

  onAddCompartment(): void {
    const id = `comp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    const compartment: TopologyCompartment = {
      id,
      label: 'New Compartment',
      position: { x: 100 + Math.random() * 100, y: 80 + Math.random() * 100 },
      size: { width: 400, height: 300 },
      defaults: {},
      properties: {},
    };
    this.canvas?.addCompartment(compartment);
  }

  onAddCompartmentFromType(semanticTypeId: string): void {
    const type = this.semanticTypes().find(t => t.id === semanticTypeId);
    const id = `comp_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    const compartment: TopologyCompartment = {
      id,
      label: type?.displayName || 'Compartment',
      semanticTypeId,
      position: { x: 100 + Math.random() * 100, y: 80 + Math.random() * 100 },
      size: { width: 400, height: 300 },
      defaults: {},
      properties: {},
    };
    this.canvas?.addCompartment(compartment);
  }

  onCompartmentSelected(id: string | null): void {
    this.selectedCompartmentId.set(id);
    this.selectedNodeId.set(null);
    this.selectedStackId.set(null);
  }

  onCompartmentUpdate(event: { id: string; updates: Partial<TopologyCompartment> }): void {
    if (this.canvas?.editorService) {
      this.canvas.editorService.updateCompartment(event.id, event.updates);
      this.onGraphChange(this.canvas.getGraph());
    }
  }

  // ── Stack Handlers ────────────────────────────────────────────

  onAddStack(blueprintId: string): void {
    const bp = this.blueprints().find(b => b.id === blueprintId);
    const id = `stack_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 6)}`;
    const stack: TopologyStackInstance = {
      id,
      blueprintId,
      label: bp?.name || 'Stack',
      position: { x: 200 + Math.random() * 200, y: 150 + Math.random() * 150 },
      parameterOverrides: {},
      dependsOn: [],
      tags: {},
    };
    this.canvas?.addStackInstance(stack);
  }

  onStackSelected(id: string | null): void {
    this.selectedStackId.set(id);
    this.selectedNodeId.set(null);
    this.selectedCompartmentId.set(null);
  }

  onStackLabelChange(event: { id: string; label: string }): void {
    if (this.canvas?.editorService) {
      this.canvas.editorService.updateStack(event.id, { label: event.label });
      this.onGraphChange(this.canvas.getGraph());
    }
  }

  onStackOverridesChange(event: { id: string; overrides: Record<string, ParameterOverride> }): void {
    if (this.canvas?.editorService) {
      this.canvas.editorService.updateStack(event.id, { parameterOverrides: event.overrides });
      this.onGraphChange(this.canvas.getGraph());
    }
  }

  // ── Resolution Preview ────────────────────────────────────────

  onPreviewResolution(): void {
    const t = this.topology();
    if (!t) return;

    this.showResolutionPreview.set(true);
    this.resolutionPreview.set(null);

    this.architectureService.previewResolution(t.id).subscribe({
      next: preview => this.resolutionPreview.set(preview),
      error: err => {
        this.toast.error(err.message || 'Resolution preview failed');
        this.showResolutionPreview.set(false);
      },
    });
  }

  private saveQuietly(): void {
    const t = this.topology();
    const graph = this.canvas?.getGraph();
    if (!t || !graph || this.isReadOnly()) return;

    this.architectureService.updateTopology(t.id, {
      name: this.topologyName,
      graph: graph as any,
    }).subscribe({
      next: updated => {
        if (updated) this.topology.set(updated);
      },
    });
  }
}
