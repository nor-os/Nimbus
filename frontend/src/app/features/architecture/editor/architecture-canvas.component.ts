/**
 * Overview: Architecture canvas wrapper — hosts Rete container, toolbar, keyboard shortcuts,
 *     right-click context menu, and clipboard operations.
 * Architecture: Main canvas component for visual architecture editor (Section 3.2)
 * Dependencies: @angular/core, rete-editor.service, @shared/models/architecture.model
 * Concepts: Canvas hosting, keyboard shortcuts, context menu, clipboard, minimap, zoom controls
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
import { ArchitectureEditorService } from './rete/architecture-editor.service';
import { CompartmentOverlayComponent } from './rete/compartment-overlay.component';
import { StackNodeComponent } from './rete/stack-node.component';
import { TopologyGraph, TopologyCompartment, TopologyStackInstance } from '@shared/models/architecture.model';
import { SemanticResourceType } from '@shared/models/semantic.model';
import { ServiceCluster } from '@shared/models/cluster.model';

interface ContextMenuItem {
  label: string;
  icon: string;
  shortcut?: string;
  action: () => void;
  disabled?: boolean;
  separator?: boolean;
}

@Component({
  selector: 'nimbus-architecture-canvas',
  standalone: true,
  imports: [CommonModule, CompartmentOverlayComponent, StackNodeComponent],
  providers: [ArchitectureEditorService],
  template: `
    <div class="canvas-container"
      (keydown)="onKeyDown($event)"
      tabindex="0"
      (mousedown)="onCanvasMouseDown($event)"
      (contextmenu)="onContextMenu($event)"
    >
      <div class="canvas-toolbar">
        <button class="toolbar-btn" (click)="zoomToFit()" title="Zoom to fit">&#8689;</button>
        <button class="toolbar-btn" (click)="toggleMinimap()" title="Toggle minimap">&#9635;</button>
        @if (!readOnly) {
          <button class="toolbar-btn" (click)="validate()" title="Validate graph">&#10003;</button>
        }
      </div>

      <!-- Compartment overlays -->
      @for (comp of editorService.getCompartments(); track comp.id) {
        <nimbus-compartment-overlay
          [compartment]="comp"
          [selected]="editorService.selectedCompartmentId() === comp.id"
          [readOnly]="readOnly"
          (select)="onCompartmentSelected($event)"
          (remove)="onCompartmentRemoved($event)"
          (resize)="onCompartmentResized($event)"
          (move)="onCompartmentMoved($event)"
        />
      }

      <!-- Stack nodes -->
      @for (stack of editorService.getStacks(); track stack.id) {
        <nimbus-stack-node
          [stack]="stack"
          [blueprintName]="getBlueprintName(stack.blueprintId)"
          [selected]="editorService.selectedStackId() === stack.id"
          [readOnly]="readOnly"
          (select)="onStackSelected($event)"
          (remove)="onStackRemoved($event)"
          (move)="onStackMoved($event)"
        />
      }

      <div #canvasContainer class="rete-container"></div>

      <!-- Context menu — stopPropagation prevents canvas mousedown from destroying it before click fires -->
      @if (contextMenu()) {
        <div class="context-menu"
          [style.left.px]="contextMenu()!.x"
          [style.top.px]="contextMenu()!.y"
          (mousedown)="$event.stopPropagation()"
          (click)="$event.stopPropagation()"
        >
          @for (item of contextMenuItems(); track item.label) {
            @if (item.separator) {
              <div class="context-menu-separator"></div>
            }
            <button
              class="context-menu-item"
              [class.disabled]="item.disabled"
              [disabled]="item.disabled"
              (click)="onContextMenuAction(item)"
            >
              <span class="cm-icon">{{ item.icon }}</span>
              <span class="cm-label">{{ item.label }}</span>
              @if (item.shortcut) {
                <span class="cm-shortcut">{{ item.shortcut }}</span>
              }
            </button>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    :host { display: block; flex: 1; min-width: 0; overflow: hidden; }
    .canvas-container {
      position: relative;
      width: 100%;
      height: 100%;
      background: #f8fafc;
      outline: none;
      background-image: radial-gradient(circle, #e2e8f0 1px, transparent 1px);
      background-size: 24px 24px;
    }
    .rete-container { width: 100%; height: 100%; }
    .canvas-toolbar {
      position: absolute;
      top: 12px;
      right: 12px;
      z-index: 10;
      display: flex;
      gap: 4px;
    }
    .toolbar-btn {
      width: 32px;
      height: 32px;
      border: 1px solid #e2e8f0;
      background: #fff;
      color: #64748b;
      border-radius: 6px;
      cursor: pointer;
      font-size: 1rem;
      display: flex;
      align-items: center;
      justify-content: center;
      box-shadow: 0 1px 3px rgba(0,0,0,0.06);
      transition: background 0.15s, color 0.15s;
    }
    .toolbar-btn:hover { background: #f8fafc; color: #3b82f6; }

    /* Context menu */
    .context-menu {
      position: absolute;
      z-index: 100;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.12), 0 1px 4px rgba(0,0,0,0.06);
      padding: 4px 0;
      min-width: 200px;
      font-size: 0.8125rem;
    }
    .context-menu-item {
      display: flex;
      align-items: center;
      gap: 8px;
      width: 100%;
      padding: 7px 12px;
      border: none;
      background: transparent;
      color: #374151;
      cursor: pointer;
      font-size: 0.8125rem;
      font-family: inherit;
      text-align: left;
      transition: background 0.1s;
    }
    .context-menu-item:hover:not(.disabled) { background: #f1f5f9; }
    .context-menu-item.disabled {
      color: #cbd5e1;
      cursor: default;
    }
    .cm-icon {
      width: 16px;
      text-align: center;
      font-size: 0.875rem;
      flex-shrink: 0;
    }
    .cm-label { flex: 1; }
    .cm-shortcut {
      color: #94a3b8;
      font-size: 0.6875rem;
      margin-left: 16px;
      white-space: nowrap;
    }
    .context-menu-separator {
      height: 1px;
      background: #e2e8f0;
      margin: 4px 0;
    }
  `],
})
export class ArchitectureCanvasComponent implements OnInit, OnChanges, OnDestroy {
  @ViewChild('canvasContainer', { static: true }) containerRef!: ElementRef<HTMLElement>;

  @Input() graph: TopologyGraph | null = null;
  @Input() semanticTypes: SemanticResourceType[] = [];
  @Input() blueprints: ServiceCluster[] = [];
  @Input() readOnly = false;

  @Output() graphChange = new EventEmitter<TopologyGraph>();
  @Output() nodeSelected = new EventEmitter<string | null>();
  @Output() compartmentSelected = new EventEmitter<string | null>();
  @Output() stackSelected = new EventEmitter<string | null>();
  @Output() validateRequest = new EventEmitter<void>();

  private injector = inject(Injector);
  editorService = inject(ArchitectureEditorService);
  showMinimap = signal(true);
  contextMenu = signal<{ x: number; y: number } | null>(null);
  contextMenuItems = signal<ContextMenuItem[]>([]);
  private initialized = false;

  constructor() {
    effect(() => {
      const nodeId = this.editorService.selectedNodeId();
      this.nodeSelected.emit(nodeId);
    });
  }

  async ngOnInit(): Promise<void> {
    this.editorService.setSemanticTypes(this.semanticTypes);
    await this.editorService.initialize(this.containerRef.nativeElement, this.injector);
    this.initialized = true;

    if (this.graph) {
      await this.editorService.loadGraph(this.graph);
    }
  }

  async ngOnChanges(changes: SimpleChanges): Promise<void> {
    if (!this.initialized) return;

    if (changes['semanticTypes'] && this.semanticTypes) {
      this.editorService.setSemanticTypes(this.semanticTypes);
    }

    if (changes['graph'] && this.graph) {
      this.editorService.setSemanticTypes(this.semanticTypes);
      await this.editorService.loadGraph(this.graph);
    }
  }

  ngOnDestroy(): void {
    this.editorService.destroy();
  }

  // ── Keyboard Shortcuts ──────────────────────────────────────────

  onKeyDown(event: KeyboardEvent): void {
    // Close context menu on any key press
    this.closeContextMenu();

    if (this.readOnly) return;

    const ctrl = event.ctrlKey || event.metaKey;

    if (event.key === 'Delete' || event.key === 'Backspace') {
      this.deleteSelected();
      event.preventDefault();
    } else if (ctrl && event.key === 'c') {
      this.editorService.copySelected();
      event.preventDefault();
    } else if (ctrl && event.key === 'x') {
      this.editorService.cutSelected().then(() => this.emitGraphChange());
      event.preventDefault();
    } else if (ctrl && event.key === 'v') {
      this.editorService.pasteFromClipboard().then(() => this.emitGraphChange());
      event.preventDefault();
    } else if (ctrl && event.key === 'd') {
      this.editorService.duplicateSelected().then(() => this.emitGraphChange());
      event.preventDefault();
    } else if (ctrl && event.key === 'a') {
      // Prevent browser select-all inside the canvas
      event.preventDefault();
    }
  }

  /** Close context menu when clicking anywhere outside */
  @HostListener('document:click')
  onDocumentClick(): void {
    this.closeContextMenu();
  }

  /** Close context menu on Escape */
  @HostListener('document:keydown.escape')
  onEscape(): void {
    this.closeContextMenu();
  }

  // ── Context Menu ──────────────────────────────────────────────

  onContextMenu(event: MouseEvent): void {
    event.preventDefault();
    event.stopPropagation();

    if (this.readOnly) return;

    const rect = (event.currentTarget as HTMLElement).getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    const hasSelectedNode = !!this.editorService.selectedNodeId();
    const hasSelectedCompartment = !!this.editorService.selectedCompartmentId();
    const hasSelectedStack = !!this.editorService.selectedStackId();
    const hasClipboard = !!this.editorService.clipboard();
    const hasSelection = hasSelectedNode || hasSelectedCompartment || hasSelectedStack;

    const items: ContextMenuItem[] = [];

    if (hasSelectedNode) {
      items.push(
        { label: 'Copy', icon: '\u2398', shortcut: 'Ctrl+C', action: () => this.editorService.copySelected() },
        { label: 'Cut', icon: '\u2702', shortcut: 'Ctrl+X', action: () => this.editorService.cutSelected().then(() => this.emitGraphChange()) },
        { label: 'Duplicate', icon: '\u29C9', shortcut: 'Ctrl+D', action: () => this.editorService.duplicateSelected().then(() => this.emitGraphChange()) },
        { label: 'Delete', icon: '\u2715', shortcut: 'Del', action: () => this.deleteSelected(), separator: true },
      );
    }

    if (hasSelectedCompartment) {
      items.push(
        { label: 'Delete Compartment', icon: '\u2715', shortcut: 'Del', action: () => this.deleteSelected(), separator: true },
      );
    }

    if (hasSelectedStack) {
      items.push(
        { label: 'Delete Stack', icon: '\u2715', shortcut: 'Del', action: () => this.deleteSelected(), separator: true },
      );
    }

    items.push(
      { label: 'Paste', icon: '\u2398', shortcut: 'Ctrl+V', action: () => this.editorService.pasteFromClipboard().then(() => this.emitGraphChange()), disabled: !hasClipboard },
    );

    if (!hasSelection) {
      items.push(
        { label: '', icon: '', action: () => {}, separator: true },
        { label: 'Zoom to Fit', icon: '\u21F1', action: () => this.zoomToFit() },
        { label: 'Validate', icon: '\u2713', action: () => this.validate() },
      );
    }

    this.contextMenuItems.set(items);
    this.contextMenu.set({ x, y });
  }

  onContextMenuAction(item: ContextMenuItem): void {
    if (item.disabled) return;
    this.closeContextMenu();
    item.action();
  }

  private closeContextMenu(): void {
    this.contextMenu.set(null);
  }

  // ── Canvas Operations ─────────────────────────────────────────

  private async deleteSelected(): Promise<void> {
    const nodeId = this.editorService.selectedNodeId();
    const compId = this.editorService.selectedCompartmentId();
    const stackId = this.editorService.selectedStackId();

    if (nodeId) {
      await this.editorService.removeSelected();
    } else if (compId) {
      this.editorService.removeCompartment(compId);
      this.editorService.selectCompartment(null);
    } else if (stackId) {
      this.editorService.removeStack(stackId);
      this.editorService.selectStack(null);
    }
    this.emitGraphChange();
  }

  async addNode(semanticTypeId: string, position?: { x: number; y: number }): Promise<void> {
    const pos = position || { x: 300 + Math.random() * 200, y: 200 + Math.random() * 200 };
    await this.editorService.addNode(semanticTypeId, pos);
    this.emitGraphChange();
  }

  zoomToFit(): void {
    this.editorService.zoomToFit();
  }

  toggleMinimap(): void {
    this.showMinimap.update(v => !v);
  }

  validate(): void {
    this.validateRequest.emit();
  }

  getGraph(): TopologyGraph {
    return this.editorService.serializeGraph();
  }

  // ── Compartment Handlers ─────────────────────────────────────

  addCompartment(compartment: TopologyCompartment): void {
    this.editorService.addCompartment(compartment);
    this.emitGraphChange();
  }

  onCompartmentSelected(id: string): void {
    this.editorService.selectCompartment(id);
    this.compartmentSelected.emit(id);
  }

  onCompartmentRemoved(id: string): void {
    this.editorService.removeCompartment(id);
    this.emitGraphChange();
  }

  onCompartmentResized(event: { id: string; width: number; height: number }): void {
    this.editorService.updateCompartment(event.id, {
      size: { width: event.width, height: event.height },
    });
    this.emitGraphChange();
  }

  onCompartmentMoved(event: { id: string; x: number; y: number }): void {
    this.editorService.updateCompartment(event.id, {
      position: { x: event.x, y: event.y },
    });
    this.emitGraphChange();
  }

  // ── Stack Handlers ───────────────────────────────────────────

  addStackInstance(stack: TopologyStackInstance): void {
    this.editorService.addStack(stack);
    this.emitGraphChange();
  }

  onStackSelected(id: string): void {
    this.editorService.selectStack(id);
    this.stackSelected.emit(id);
  }

  onStackRemoved(id: string): void {
    this.editorService.removeStack(id);
    this.emitGraphChange();
  }

  onStackMoved(event: { id: string; x: number; y: number }): void {
    this.editorService.updateStack(event.id, {
      position: { x: event.x, y: event.y },
    });
    this.emitGraphChange();
  }

  getBlueprintName(blueprintId: string): string | null {
    const bp = this.blueprints.find(b => b.id === blueprintId);
    return bp?.name || null;
  }

  onCanvasMouseDown(event: MouseEvent): void {
    // Close context menu on left-click
    if (event.button === 0) {
      this.closeContextMenu();
    }
    // Only clear selection when clicking directly on the canvas background
    if (event.target === this.containerRef.nativeElement.parentElement) {
      this.editorService.clearSelection();
    }
  }

  private emitGraphChange(): void {
    this.graphChange.emit(this.editorService.serializeGraph());
  }
}
