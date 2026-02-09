/**
 * Overview: Force-directed graph visualization of CI relationships using Canvas 2D API.
 * Architecture: CMDB feature component (Section 8) — renders graph traversal data as
 *     interactive node-link diagrams with physics-based layout, zoom, and pan.
 * Dependencies: @angular/core, @angular/router, app/core/services/cmdb.service,
 *     app/core/services/tenant-context.service, app/shared/models/cmdb.model
 * Concepts: Force-directed layout, Canvas 2D rendering, CI graph traversal, impact analysis,
 *     node repulsion, edge attraction, zoom/pan transforms, SSR-safe afterNextRender
 */
import {
  Component,
  ChangeDetectionStrategy,
  inject,
  signal,
  computed,
  ElementRef,
  viewChild,
  OnDestroy,
  afterNextRender,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import { CmdbService } from '@core/services/cmdb.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { GraphNode } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

// ── Internal types ──────────────────────────────────────────────────

/** A positioned node in the force simulation. */
interface SimNode {
  id: string;
  name: string;
  ciClass: string;
  depth: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  radius: number;
  color: string;
  pinned: boolean;
}

/** An edge between two simulation nodes. */
interface SimEdge {
  source: SimNode;
  target: SimNode;
}

// ── Color palette by CI class ───────────────────────────────────────

const CLASS_COLORS: Record<string, string> = {
  VirtualMachine: '#3b82f6',
  Container: '#8b5cf6',
  Database: '#f59e0b',
  Network: '#10b981',
  LoadBalancer: '#ec4899',
  Storage: '#6366f1',
  Application: '#06b6d4',
  Service: '#14b8a6',
  Firewall: '#ef4444',
  Cluster: '#a855f7',
};

const DEFAULT_COLORS = [
  '#0ea5e9', '#d946ef', '#f97316', '#84cc16', '#e11d48',
  '#2dd4bf', '#a3e635', '#fb923c', '#c084fc', '#38bdf8',
];

function colorForClass(ciClass: string): string {
  if (CLASS_COLORS[ciClass]) return CLASS_COLORS[ciClass];
  // Deterministic fallback based on hash of class name
  let hash = 0;
  for (let i = 0; i < ciClass.length; i++) {
    hash = ((hash << 5) - hash + ciClass.charCodeAt(i)) | 0;
  }
  return DEFAULT_COLORS[Math.abs(hash) % DEFAULT_COLORS.length];
}

// ── Force simulation constants ──────────────────────────────────────

const REPULSION_STRENGTH = 5000;
const ATTRACTION_STRENGTH = 0.005;
const EDGE_REST_LENGTH = 160;
const DAMPING = 0.85;
const MIN_VELOCITY = 0.01;
const NODE_RADIUS = 24;
const ROOT_NODE_RADIUS = 32;
const LABEL_FONT = '11px -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';

@Component({
  selector: 'nimbus-graph-view',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="graph-view-page">
        <div class="page-header">
          <button class="back-btn" (click)="goBack()">&larr; Back to detail</button>
          <div class="title-row">
            <h1>Relationship Graph</h1>
            @if (rootNode(); as root) {
              <span class="badge root-badge">{{ root.name }}</span>
              <span class="badge class-badge">{{ root.ciClass }}</span>
            }
          </div>
        </div>

        <div class="controls-bar">
          <div class="control-group">
            <label class="control-label">Mode</label>
            <select class="control-select" [value]="mode()" (change)="onModeChange($event)">
              <option value="graph">Graph Traversal</option>
              <option value="impact">Impact Analysis</option>
            </select>
          </div>
          <div class="control-group">
            <label class="control-label">Max Depth</label>
            <select class="control-select" [value]="maxDepth()" (change)="onDepthChange($event)">
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
              <option value="5">5</option>
            </select>
          </div>
          <button class="btn btn-sm btn-secondary" (click)="resetView()">Reset View</button>
          <button class="btn btn-sm btn-secondary" (click)="reloadGraph()">Reload</button>
        </div>

        @if (loading()) {
          <div class="loading">Loading graph data...</div>
        }

        @if (!loading() && errorMsg()) {
          <div class="error-state">{{ errorMsg() }}</div>
        }

        @if (!loading() && !errorMsg() && nodes().length === 0) {
          <div class="empty-state">No related configuration items found.</div>
        }

        <div class="canvas-wrapper" [class.hidden]="loading() || nodes().length === 0">
          <canvas #graphCanvas
            (mousedown)="onMouseDown($event)"
            (mousemove)="onMouseMove($event)"
            (mouseup)="onMouseUp()"
            (mouseleave)="onMouseUp()"
            (wheel)="onWheel($event)"
            (dblclick)="onDoubleClick($event)"
          ></canvas>

          @if (hoveredNode(); as hovered) {
            <div class="tooltip"
              [style.left.px]="tooltipX()"
              [style.top.px]="tooltipY()"
            >
              <div class="tooltip-name">{{ hovered.name }}</div>
              <div class="tooltip-class">Class: {{ hovered.ciClass }}</div>
              <div class="tooltip-depth">Depth: {{ hovered.depth }}</div>
              <div class="tooltip-hint">Double-click to navigate</div>
            </div>
          }
        </div>

        @if (nodes().length > 0) {
          <div class="legend">
            @for (entry of legendEntries(); track entry.ciClass) {
              <div class="legend-item">
                <span class="legend-dot" [style.background]="entry.color"></span>
                <span class="legend-label">{{ entry.ciClass }}</span>
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .graph-view-page { padding: 0; }

    .loading, .empty-state, .error-state {
      padding: 3rem; text-align: center; color: #64748b;
    }
    .error-state { color: #dc2626; }

    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; padding: 0; margin-bottom: 0.75rem; font-family: inherit;
    }
    .back-btn:hover { text-decoration: underline; }

    .page-header { margin-bottom: 1rem; }
    .title-row {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.375rem;
    }
    .title-row h1 {
      font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0;
    }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .root-badge { background: #dbeafe; color: #1d4ed8; }
    .class-badge { background: #f0fdf4; color: #16a34a; }

    .controls-bar {
      display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;
      padding: 0.75rem 1rem; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; flex-wrap: wrap;
    }
    .control-group { display: flex; align-items: center; gap: 0.5rem; }
    .control-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .control-select {
      padding: 0.375rem 0.625rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; font-family: inherit; cursor: pointer;
    }
    .control-select:focus { border-color: #3b82f6; outline: none; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; text-decoration: none; display: inline-block;
    }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-secondary {
      background: #f1f5f9; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #e2e8f0; }

    .canvas-wrapper {
      position: relative;
      background: #fafbfc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
      min-height: 500px;
    }
    .canvas-wrapper.hidden { display: none; }
    .canvas-wrapper canvas {
      display: block; width: 100%; height: 500px; cursor: grab;
    }
    .canvas-wrapper canvas:active { cursor: grabbing; }

    .tooltip {
      position: absolute;
      background: #1e293b;
      color: #fff;
      padding: 0.5rem 0.75rem;
      border-radius: 6px;
      font-size: 0.75rem;
      pointer-events: none;
      z-index: 10;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      max-width: 220px;
      white-space: nowrap;
    }
    .tooltip-name { font-weight: 600; margin-bottom: 0.125rem; }
    .tooltip-class { color: #94a3b8; }
    .tooltip-depth { color: #94a3b8; }
    .tooltip-hint {
      color: #64748b; font-size: 0.6875rem; margin-top: 0.25rem;
      border-top: 1px solid #334155; padding-top: 0.25rem;
    }

    .legend {
      display: flex; flex-wrap: wrap; gap: 0.75rem;
      margin-top: 0.75rem; padding: 0.5rem 0;
    }
    .legend-item { display: flex; align-items: center; gap: 0.375rem; }
    .legend-dot {
      width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0;
    }
    .legend-label { font-size: 0.75rem; color: #64748b; }
  `],
})
export class GraphViewComponent implements OnDestroy {
  private cmdbService = inject(CmdbService);
  private tenantContext = inject(TenantContextService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  // ── Template refs ──────────────────────────────────────────────────
  private canvasRef = viewChild.required<ElementRef<HTMLCanvasElement>>('graphCanvas');

  // ── Reactive state ─────────────────────────────────────────────────
  loading = signal(true);
  errorMsg = signal('');
  mode = signal<'graph' | 'impact'>('graph');
  maxDepth = signal(3);
  nodes = signal<SimNode[]>([]);
  edges = signal<SimEdge[]>([]);
  hoveredNode = signal<SimNode | null>(null);
  tooltipX = signal(0);
  tooltipY = signal(0);

  /** The root CI from the graph data (depth === 0). */
  rootNode = computed(() => this.nodes().find((n) => n.depth === 0) ?? null);

  /** Unique CI classes for the legend. */
  legendEntries = computed(() => {
    const seen = new Map<string, string>();
    for (const n of this.nodes()) {
      if (!seen.has(n.ciClass)) {
        seen.set(n.ciClass, n.color);
      }
    }
    return Array.from(seen.entries()).map(([ciClass, color]) => ({ ciClass, color }));
  });

  // ── Canvas / interaction state (not signals — mutated in rAF) ─────
  private ctx: CanvasRenderingContext2D | null = null;
  private canvasWidth = 0;
  private canvasHeight = 0;
  private dpr = 1;
  private animFrameId = 0;
  private isSimulating = true;
  private stableFrames = 0;

  // Transform (pan + zoom)
  private panX = 0;
  private panY = 0;
  private zoom = 1;

  // Drag state
  private isDragging = false;
  private isPanning = false;
  private dragNode: SimNode | null = null;
  private lastMouseX = 0;
  private lastMouseY = 0;

  private ciId = '';
  private resizeObserver: ResizeObserver | null = null;

  constructor() {
    afterNextRender(() => {
      this.ciId = this.route.snapshot.paramMap.get('id') ?? '';
      if (!this.ciId) {
        this.loading.set(false);
        this.errorMsg.set('No CI ID provided.');
        return;
      }
      this.setupCanvas();
      this.loadGraph();
    });
  }

  ngOnDestroy(): void {
    if (this.animFrameId) cancelAnimationFrame(this.animFrameId);
    this.resizeObserver?.disconnect();
  }

  // ── Public methods bound to template ───────────────────────────────

  goBack(): void {
    this.router.navigate(['/cmdb', this.ciId]);
  }

  onModeChange(event: Event): void {
    const value = (event.target as HTMLSelectElement).value as 'graph' | 'impact';
    this.mode.set(value);
    this.reloadGraph();
  }

  onDepthChange(event: Event): void {
    const value = parseInt((event.target as HTMLSelectElement).value, 10);
    this.maxDepth.set(value);
    this.reloadGraph();
  }

  resetView(): void {
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.centerGraph();
  }

  reloadGraph(): void {
    this.loadGraph();
  }

  // ── Mouse interaction ──────────────────────────────────────────────

  onMouseDown(event: MouseEvent): void {
    const [wx, wy] = this.screenToWorld(event.offsetX, event.offsetY);
    const hit = this.hitTest(wx, wy);

    if (hit) {
      this.isDragging = true;
      this.dragNode = hit;
      hit.pinned = true;
    } else {
      this.isPanning = true;
    }
    this.lastMouseX = event.offsetX;
    this.lastMouseY = event.offsetY;
  }

  onMouseMove(event: MouseEvent): void {
    if (this.isDragging && this.dragNode) {
      const [wx, wy] = this.screenToWorld(event.offsetX, event.offsetY);
      this.dragNode.x = wx;
      this.dragNode.y = wy;
      this.dragNode.vx = 0;
      this.dragNode.vy = 0;
      this.wakeSimulation();
    } else if (this.isPanning) {
      const dx = event.offsetX - this.lastMouseX;
      const dy = event.offsetY - this.lastMouseY;
      this.panX += dx;
      this.panY += dy;
      this.lastMouseX = event.offsetX;
      this.lastMouseY = event.offsetY;
      this.renderFrame();
    } else {
      // Hover detection
      const [wx, wy] = this.screenToWorld(event.offsetX, event.offsetY);
      const hit = this.hitTest(wx, wy);
      this.hoveredNode.set(hit);
      if (hit) {
        this.tooltipX.set(event.offsetX + 14);
        this.tooltipY.set(event.offsetY - 10);
      }
    }
  }

  onMouseUp(): void {
    if (this.dragNode) {
      this.dragNode.pinned = false;
      this.dragNode = null;
    }
    this.isDragging = false;
    this.isPanning = false;
  }

  onWheel(event: WheelEvent): void {
    event.preventDefault();
    const scaleFactor = event.deltaY < 0 ? 1.1 : 0.9;
    const newZoom = Math.max(0.1, Math.min(5, this.zoom * scaleFactor));

    // Zoom towards mouse position
    const mx = event.offsetX;
    const my = event.offsetY;
    this.panX = mx - (mx - this.panX) * (newZoom / this.zoom);
    this.panY = my - (my - this.panY) * (newZoom / this.zoom);
    this.zoom = newZoom;
    this.renderFrame();
  }

  onDoubleClick(event: MouseEvent): void {
    const [wx, wy] = this.screenToWorld(event.offsetX, event.offsetY);
    const hit = this.hitTest(wx, wy);
    if (hit) {
      this.router.navigate(['/cmdb', hit.id]);
    }
  }

  // ── Canvas setup ──────────────────────────────────────────────────

  private setupCanvas(): void {
    const canvas = this.canvasRef().nativeElement;
    this.ctx = canvas.getContext('2d');
    this.dpr = window.devicePixelRatio || 1;
    this.resizeCanvas();

    this.resizeObserver = new ResizeObserver(() => this.resizeCanvas());
    this.resizeObserver.observe(canvas.parentElement!);
  }

  private resizeCanvas(): void {
    const canvas = this.canvasRef().nativeElement;
    const parent = canvas.parentElement!;
    const rect = parent.getBoundingClientRect();
    this.canvasWidth = rect.width;
    this.canvasHeight = Math.max(rect.height, 500);

    canvas.width = this.canvasWidth * this.dpr;
    canvas.height = this.canvasHeight * this.dpr;
    canvas.style.width = `${this.canvasWidth}px`;
    canvas.style.height = `${this.canvasHeight}px`;

    if (this.ctx) {
      this.ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    }
    this.renderFrame();
  }

  // ── Data loading ──────────────────────────────────────────────────

  private loadGraph(): void {
    this.loading.set(true);
    this.errorMsg.set('');

    const depth = this.maxDepth();
    const graph$ = this.mode() === 'impact'
      ? this.cmdbService.getCIImpact(this.ciId, 'downstream', depth)
      : this.cmdbService.getCIGraph(this.ciId, { maxDepth: depth });

    const relationships$ = this.cmdbService.getCIRelationships(this.ciId);

    forkJoin([graph$, relationships$]).subscribe({
      next: ([graphNodes, relationships]) => {
        this.buildSimulation(graphNodes, relationships);
        this.loading.set(false);
      },
      error: (err) => {
        this.errorMsg.set(err.message || 'Failed to load graph data.');
        this.loading.set(false);
      },
    });
  }

  // ── Build simulation from graph data ──────────────────────────────

  private buildSimulation(
    graphNodes: GraphNode[],
    relationships: Array<{ sourceCiId: string; targetCiId: string }>,
  ): void {
    if (this.animFrameId) {
      cancelAnimationFrame(this.animFrameId);
      this.animFrameId = 0;
    }

    if (graphNodes.length === 0) {
      this.nodes.set([]);
      this.edges.set([]);
      return;
    }

    // Build sim nodes with initial positions in a radial layout
    const cx = this.canvasWidth / 2;
    const cy = this.canvasHeight / 2;
    const nodeMap = new Map<string, SimNode>();

    const simNodes: SimNode[] = graphNodes.map((gn, i) => {
      const isRoot = gn.depth === 0;
      const angle = (2 * Math.PI * i) / graphNodes.length;
      const spreadRadius = 80 + gn.depth * 100;
      const node: SimNode = {
        id: gn.ciId,
        name: gn.name,
        ciClass: gn.ciClass,
        depth: gn.depth,
        x: isRoot ? cx : cx + Math.cos(angle) * spreadRadius + (Math.random() - 0.5) * 40,
        y: isRoot ? cy : cy + Math.sin(angle) * spreadRadius + (Math.random() - 0.5) * 40,
        vx: 0,
        vy: 0,
        radius: isRoot ? ROOT_NODE_RADIUS : NODE_RADIUS,
        color: colorForClass(gn.ciClass),
        pinned: false,
      };
      nodeMap.set(gn.ciId, node);
      return node;
    });

    // Build edges from relationships where both endpoints exist in graph
    const simEdges: SimEdge[] = [];
    const edgeSet = new Set<string>();

    for (const rel of relationships) {
      const source = nodeMap.get(rel.sourceCiId);
      const target = nodeMap.get(rel.targetCiId);
      if (source && target && source !== target) {
        const key = [source.id, target.id].sort().join('|');
        if (!edgeSet.has(key)) {
          edgeSet.add(key);
          simEdges.push({ source, target });
        }
      }
    }

    // If relationships did not produce edges, infer from path adjacency
    if (simEdges.length === 0 && graphNodes.length > 1) {
      for (const gn of graphNodes) {
        if (gn.path.length >= 2) {
          const parentId = gn.path[gn.path.length - 2];
          const parent = nodeMap.get(parentId);
          const child = nodeMap.get(gn.ciId);
          if (parent && child && parent !== child) {
            const key = [parent.id, child.id].sort().join('|');
            if (!edgeSet.has(key)) {
              edgeSet.add(key);
              simEdges.push({ source: parent, target: child });
            }
          }
        }
      }
    }

    this.nodes.set(simNodes);
    this.edges.set(simEdges);

    // Reset view and start simulation
    this.zoom = 1;
    this.panX = 0;
    this.panY = 0;
    this.isSimulating = true;
    this.stableFrames = 0;
    this.startSimulation();
  }

  // ── Force simulation loop ─────────────────────────────────────────

  private startSimulation(): void {
    const tick = () => {
      if (this.isSimulating) {
        this.simulateStep();
      }
      this.renderFrame();
      this.animFrameId = requestAnimationFrame(tick);
    };
    this.animFrameId = requestAnimationFrame(tick);
  }

  private wakeSimulation(): void {
    this.isSimulating = true;
    this.stableFrames = 0;
  }

  private simulateStep(): void {
    const allNodes = this.nodes();
    const allEdges = this.edges();
    if (allNodes.length === 0) return;

    // Repulsion (all pairs)
    for (let i = 0; i < allNodes.length; i++) {
      for (let j = i + 1; j < allNodes.length; j++) {
        const a = allNodes[i];
        const b = allNodes[j];
        let dx = b.x - a.x;
        let dy = b.y - a.y;
        let dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 1) {
          dx = (Math.random() - 0.5) * 2;
          dy = (Math.random() - 0.5) * 2;
          dist = 1;
        }
        const force = REPULSION_STRENGTH / (dist * dist);
        const fx = (dx / dist) * force;
        const fy = (dy / dist) * force;
        if (!a.pinned) { a.vx -= fx; a.vy -= fy; }
        if (!b.pinned) { b.vx += fx; b.vy += fy; }
      }
    }

    // Attraction along edges
    for (const edge of allEdges) {
      const { source, target } = edge;
      const dx = target.x - source.x;
      const dy = target.y - source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) continue;
      const displacement = dist - EDGE_REST_LENGTH;
      const force = displacement * ATTRACTION_STRENGTH;
      const fx = (dx / dist) * force;
      const fy = (dy / dist) * force;
      if (!source.pinned) { source.vx += fx; source.vy += fy; }
      if (!target.pinned) { target.vx -= fx; target.vy -= fy; }
    }

    // Center gravity — gently pull nodes towards canvas center
    const cx = this.canvasWidth / 2;
    const cy = this.canvasHeight / 2;
    for (const node of allNodes) {
      if (!node.pinned) {
        node.vx += (cx - node.x) * 0.0001;
        node.vy += (cy - node.y) * 0.0001;
      }
    }

    // Apply velocities with damping
    let maxVelocity = 0;
    for (const node of allNodes) {
      if (node.pinned) continue;
      node.vx *= DAMPING;
      node.vy *= DAMPING;
      node.x += node.vx;
      node.y += node.vy;
      const v = Math.abs(node.vx) + Math.abs(node.vy);
      if (v > maxVelocity) maxVelocity = v;
    }

    // Check for stability
    if (maxVelocity < MIN_VELOCITY) {
      this.stableFrames++;
      if (this.stableFrames > 60) {
        this.isSimulating = false;
      }
    } else {
      this.stableFrames = 0;
    }
  }

  // ── Rendering ─────────────────────────────────────────────────────

  private renderFrame(): void {
    const ctx = this.ctx;
    if (!ctx) return;

    const w = this.canvasWidth;
    const h = this.canvasHeight;

    ctx.save();
    ctx.setTransform(this.dpr, 0, 0, this.dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    // Apply pan and zoom
    ctx.translate(this.panX, this.panY);
    ctx.scale(this.zoom, this.zoom);

    // Draw edges
    const allEdges = this.edges();
    ctx.strokeStyle = '#cbd5e1';
    ctx.lineWidth = 1.5 / this.zoom;
    for (const edge of allEdges) {
      ctx.beginPath();
      ctx.moveTo(edge.source.x, edge.source.y);
      ctx.lineTo(edge.target.x, edge.target.y);
      ctx.stroke();
    }

    // Draw edge arrows (direction indicator)
    ctx.fillStyle = '#94a3b8';
    for (const edge of allEdges) {
      const dx = edge.target.x - edge.source.x;
      const dy = edge.target.y - edge.source.y;
      const dist = Math.sqrt(dx * dx + dy * dy);
      if (dist < 1) continue;
      const nx = dx / dist;
      const ny = dy / dist;
      // Arrow at midpoint
      const mx = (edge.source.x + edge.target.x) / 2;
      const my = (edge.source.y + edge.target.y) / 2;
      const arrowSize = 6 / this.zoom;
      ctx.beginPath();
      ctx.moveTo(mx + nx * arrowSize, my + ny * arrowSize);
      ctx.lineTo(mx - nx * arrowSize / 2 + ny * arrowSize / 2, my - ny * arrowSize / 2 - nx * arrowSize / 2);
      ctx.lineTo(mx - nx * arrowSize / 2 - ny * arrowSize / 2, my - ny * arrowSize / 2 + nx * arrowSize / 2);
      ctx.closePath();
      ctx.fill();
    }

    // Draw nodes
    const allNodes = this.nodes();
    const hovered = this.hoveredNode();

    for (const node of allNodes) {
      const isHovered = hovered === node;
      const r = node.radius;

      // Shadow
      ctx.shadowColor = 'rgba(0, 0, 0, 0.12)';
      ctx.shadowBlur = isHovered ? 12 : 6;
      ctx.shadowOffsetY = 2;

      // Fill circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, r, 0, Math.PI * 2);
      ctx.fillStyle = node.color;
      ctx.fill();

      // Reset shadow
      ctx.shadowColor = 'transparent';
      ctx.shadowBlur = 0;
      ctx.shadowOffsetY = 0;

      // Hover ring
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 3, 0, Math.PI * 2);
        ctx.strokeStyle = node.color;
        ctx.lineWidth = 2.5 / this.zoom;
        ctx.stroke();
      }

      // Root node ring
      if (node.depth === 0) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 2, 0, Math.PI * 2);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3 / this.zoom;
        ctx.stroke();
        ctx.beginPath();
        ctx.arc(node.x, node.y, r + 5, 0, Math.PI * 2);
        ctx.strokeStyle = node.color;
        ctx.lineWidth = 2 / this.zoom;
        ctx.stroke();
      }

      // Depth number inside node
      ctx.fillStyle = '#fff';
      ctx.font = `bold ${Math.round(11 / Math.max(this.zoom, 0.5))}px -apple-system, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(node.depth), node.x, node.y);

      // Label below node
      ctx.fillStyle = '#1e293b';
      ctx.font = LABEL_FONT;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      const label = node.name.length > 18 ? node.name.substring(0, 16) + '...' : node.name;
      ctx.fillText(label, node.x, node.y + r + 6);
    }

    ctx.restore();
  }

  // ── Coordinate transforms ─────────────────────────────────────────

  private screenToWorld(sx: number, sy: number): [number, number] {
    const wx = (sx - this.panX) / this.zoom;
    const wy = (sy - this.panY) / this.zoom;
    return [wx, wy];
  }

  private hitTest(wx: number, wy: number): SimNode | null {
    // Search in reverse so top-rendered nodes are hit first
    const allNodes = this.nodes();
    for (let i = allNodes.length - 1; i >= 0; i--) {
      const n = allNodes[i];
      const dx = wx - n.x;
      const dy = wy - n.y;
      if (dx * dx + dy * dy <= n.radius * n.radius) {
        return n;
      }
    }
    return null;
  }

  private centerGraph(): void {
    const allNodes = this.nodes();
    if (allNodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    for (const n of allNodes) {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    }

    const graphW = maxX - minX + 100;
    const graphH = maxY - minY + 100;
    const graphCx = (minX + maxX) / 2;
    const graphCy = (minY + maxY) / 2;

    this.zoom = Math.min(
      this.canvasWidth / graphW,
      this.canvasHeight / graphH,
      1.5,
    );
    this.panX = this.canvasWidth / 2 - graphCx * this.zoom;
    this.panY = this.canvasHeight / 2 - graphCy * this.zoom;
    this.renderFrame();
  }
}
