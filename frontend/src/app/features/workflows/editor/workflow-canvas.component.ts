/**
 * Overview: Workflow canvas wrapper — hosts Rete container, keyboard shortcuts, minimap toggle.
 * Architecture: Main canvas component for visual workflow editor (Section 3.2)
 * Dependencies: @angular/core, rete-editor.service
 * Concepts: Canvas hosting, keyboard shortcuts, minimap, zoom controls
 */
import {
  Component,
  ElementRef,
  EventEmitter,
  Injector,
  Input,
  OnDestroy,
  OnInit,
  Output,
  ViewChild,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReteEditorService } from './rete/rete-editor.service';
import { WorkflowGraph, NodeTypeInfo } from '@shared/models/workflow.model';

@Component({
  selector: 'nimbus-workflow-canvas',
  standalone: true,
  imports: [CommonModule],
  providers: [ReteEditorService],
  template: `
    <div class="canvas-container" (keydown)="onKeyDown($event)" tabindex="0">
      <div class="canvas-toolbar">
        <button class="toolbar-btn" (click)="zoomToFit()" title="Zoom to fit">&#8689;</button>
        <button class="toolbar-btn" (click)="toggleMinimap()" title="Toggle minimap">&#9635;</button>
      </div>
      <div #canvasContainer class="rete-container"></div>
    </div>
  `,
  styles: [`
    .canvas-container {
      position: relative; width: 100%; height: 100%;
      background: #f8fafc; outline: none;
      background-image: radial-gradient(circle, #e2e8f0 1px, transparent 1px);
      background-size: 24px 24px;
    }
    .rete-container { width: 100%; height: 100%; }
    .canvas-toolbar {
      position: absolute; top: 12px; right: 12px; z-index: 10;
      display: flex; gap: 4px;
    }
    .toolbar-btn {
      width: 32px; height: 32px; border: 1px solid #e2e8f0;
      background: #fff; color: #64748b; border-radius: 6px;
      cursor: pointer; font-size: 1rem; display: flex;
      align-items: center; justify-content: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
      transition: background 0.15s, color 0.15s;
    }
    .toolbar-btn:hover { background: #f8fafc; color: #3b82f6; }
  `],
})
export class WorkflowCanvasComponent implements OnInit, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) containerRef!: ElementRef<HTMLElement>;

  @Input() graph: WorkflowGraph | null = null;
  @Input() nodeTypes: NodeTypeInfo[] = [];
  @Input() readOnly = false;

  @Output() graphChange = new EventEmitter<WorkflowGraph>();
  @Output() nodeSelected = new EventEmitter<string | null>();

  private injector = inject(Injector);
  editorService = inject(ReteEditorService);
  showMinimap = signal(true);

  async ngOnInit(): Promise<void> {
    this.editorService.setNodeTypes(this.nodeTypes);
    await this.editorService.initialize(this.containerRef.nativeElement, this.injector);

    if (this.graph) {
      await this.editorService.loadGraph(this.graph);
    }
  }

  ngOnDestroy(): void {
    this.editorService.destroy();
  }

  onKeyDown(event: KeyboardEvent): void {
    if (this.readOnly) return;

    if (event.key === 'Delete' || event.key === 'Backspace') {
      this.editorService.removeSelected();
      event.preventDefault();
    }
  }

  async addNode(typeId: string, position: { x: number; y: number }): Promise<void> {
    await this.editorService.addNode(typeId, position);
    this.emitGraphChange();
  }

  zoomToFit(): void {
    this.editorService.zoomToFit();
  }

  toggleMinimap(): void {
    this.showMinimap.update(v => !v);
  }

  getGraph(): WorkflowGraph {
    return this.editorService.serializeGraph();
  }

  private emitGraphChange(): void {
    this.graphChange.emit(this.editorService.serializeGraph());
  }
}
