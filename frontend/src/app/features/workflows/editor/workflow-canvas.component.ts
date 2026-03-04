/**
 * Overview: Workflow canvas wrapper — hosts Rete container, keyboard shortcuts, minimap toggle, context menu.
 * Architecture: Main canvas component for visual workflow editor (Section 3.2)
 * Dependencies: @angular/core, rete-editor.service
 * Concepts: Canvas hosting, keyboard shortcuts, minimap, zoom controls, right-click context menu
 */
import {
  Component,
  ElementRef,
  EventEmitter,
  HostListener,
  Injector,
  Input,
  OnChanges,
  OnDestroy,
  OnInit,
  Output,
  SimpleChanges,
  ViewChild,
  effect,
  inject,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReteEditorService } from './rete/rete-editor.service';
import { WorkflowGraph, NodeTypeInfo } from '@shared/models/workflow.model';

interface ContextMenuItem {
  label: string;
  icon: string;
  action: () => void;
  visible: boolean;
}

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
      <div #canvasContainer class="rete-container" (contextmenu)="onContextMenu($event)"></div>

      <!-- Context menu -->
      @if (contextMenu()) {
        <div
          class="context-menu"
          [style.left.px]="contextMenu()!.x"
          [style.top.px]="contextMenu()!.y"
        >
          @for (item of contextMenu()!.items; track item.label) {
            @if (item.visible) {
              <button class="context-menu-item" (click)="item.action(); closeContextMenu()">
                <span class="context-menu-icon">{{ item.icon }}</span>
                {{ item.label }}
              </button>
            }
          }
        </div>
      }
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

    .context-menu {
      position: absolute; z-index: 100;
      background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 4px 0;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
      min-width: 180px;
    }
    .context-menu-item {
      display: flex; align-items: center; gap: 8px;
      width: 100%; padding: 8px 14px; border: none;
      background: none; cursor: pointer; font-size: 0.85rem;
      color: #334155; text-align: left;
      transition: background 0.1s;
    }
    .context-menu-item:hover { background: #f1f5f9; }
    .context-menu-icon { font-size: 1rem; width: 18px; text-align: center; }
  `],
})
export class WorkflowCanvasComponent implements OnInit, OnChanges, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) containerRef!: ElementRef<HTMLElement>;

  @Input() graph: WorkflowGraph | null = null;
  @Input() nodeTypes: NodeTypeInfo[] = [];
  @Input() readOnly = false;

  @Output() graphChange = new EventEmitter<WorkflowGraph>();
  @Output() nodeSelected = new EventEmitter<string | null>();
  @Output() editActivity = new EventEmitter<string>();

  private injector = inject(Injector);
  editorService = inject(ReteEditorService);
  showMinimap = signal(true);
  contextMenu = signal<{ x: number; y: number; items: ContextMenuItem[]; nodeId: string | null } | null>(null);
  private initialized = false;

  constructor() {
    // Propagate Rete selection changes (left-click) to parent
    effect(() => {
      const nodeId = this.editorService.selectedNodeId();
      this.nodeSelected.emit(nodeId);
    });
  }

  async ngOnInit(): Promise<void> {
    this.editorService.setNodeTypes(this.nodeTypes);
    await this.editorService.initialize(this.containerRef.nativeElement, this.injector);
    this.initialized = true;

    if (this.graph) {
      await this.editorService.loadGraph(this.graph);
    }
  }

  async ngOnChanges(changes: SimpleChanges): Promise<void> {
    if (!this.initialized) return;

    if (changes['nodeTypes'] && this.nodeTypes) {
      this.editorService.setNodeTypes(this.nodeTypes);
    }

    if (changes['graph'] && this.graph) {
      this.editorService.setNodeTypes(this.nodeTypes);
      await this.editorService.loadGraph(this.graph);
    }
  }

  ngOnDestroy(): void {
    this.editorService.destroy();
  }

  onKeyDown(event: KeyboardEvent): void {
    if (event.key === 'Escape') {
      this.closeContextMenu();
      return;
    }

    if (this.readOnly) return;

    if (event.key === 'Delete' || event.key === 'Backspace') {
      this.editorService.removeSelected();
      event.preventDefault();
    }
  }

  @HostListener('document:click')
  onDocumentClick(): void {
    this.closeContextMenu();
  }

  onContextMenu(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();

    // Find which Rete node was right-clicked by walking up the DOM
    const nodeId = this.findNodeIdFromEvent(event);
    const nodeType = nodeId ? this.editorService.getNodeType(nodeId) : null;
    const isActivityNode = nodeType === 'activity';

    // Position relative to canvas container
    const containerRect = this.containerRef.nativeElement.parentElement!.getBoundingClientRect();
    const x = event.clientX - containerRect.left;
    const y = event.clientY - containerRect.top;

    const items: ContextMenuItem[] = [
      {
        label: 'View Properties',
        icon: '\u2699',
        action: () => {
          if (nodeId) {
            this.editorService.selectedNodeId.set(nodeId);
            this.nodeSelected.emit(nodeId);
          }
        },
        visible: !!nodeId,
      },
      {
        label: 'Edit Activity',
        icon: '\u270E',
        action: () => {
          if (nodeId) {
            const config = this.editorService.getNodeConfig(nodeId);
            const activityId = config?.['activity_id'] as string;
            if (activityId) {
              this.editActivity.emit(activityId);
            }
          }
        },
        visible: isActivityNode,
      },
      {
        label: 'Delete Node',
        icon: '\u2716',
        action: () => {
          if (nodeId && !this.readOnly) {
            this.editorService.selectedNodeId.set(nodeId);
            this.editorService.removeSelected();
            this.emitGraphChange();
          }
        },
        visible: !!nodeId && !this.readOnly,
      },
    ];

    // Only show menu if there are visible items
    if (items.some(i => i.visible)) {
      this.contextMenu.set({ x, y, items, nodeId });
    }
  }

  closeContextMenu(): void {
    this.contextMenu.set(null);
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

  private findNodeIdFromEvent(event: MouseEvent): string | null {
    let el = event.target as HTMLElement | null;
    while (el) {
      // Rete.js wraps each node in an element with a data-node-id attribute
      const nodeId = el.getAttribute?.('data-node-id');
      if (nodeId) return nodeId;

      // Also check for the rete-node class which wraps the node view
      if (el.classList?.contains('node')) {
        // The node view ID is on the parent container managed by the area plugin
        const parent = el.closest('[data-node-id]');
        if (parent) return parent.getAttribute('data-node-id');
      }

      // Stop at canvas container
      if (el === this.containerRef.nativeElement) break;
      el = el.parentElement;
    }
    return null;
  }
}
