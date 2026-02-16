/**
 * Overview: Resource stack view for landing zone designer — replaces Rete.js canvas with structured, hierarchical resource cards.
 * Architecture: Feature component for LZ resource stack view (Section 7.2)
 * Dependencies: @angular/core, CompartmentCardComponent, architecture.model
 * Concepts: Landing zones use provider-specific resources (Proxmox bridges, Azure VNets, AWS VPCs).
 *     This component renders them as auto-organized cards in two view modes:
 *     - Flat mode: groups nodes by semanticTypeId category (network, compute, storage, etc.)
 *     - Hierarchy mode: renders compartment tree with nested resources inside each compartment
 *     View mode is auto-selected based on whether compartments exist in the graph.
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  computed,
  signal,
  effect,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopologyGraph, TopologyNode, TopologyCompartment } from '@shared/models/architecture.model';
import { CompartmentCardComponent, CompartmentTreeNode } from './compartment-card.component';

interface ResourceCategory {
  key: string;
  label: string;
  icon: string;
  nodes: TopologyNode[];
}

const CATEGORY_CONFIG: Record<string, { label: string; icon: string; order: number }> = {
  network: { label: 'Network', icon: '\u{1F310}', order: 1 },
  compute: { label: 'Compute', icon: '\u2699\uFE0F', order: 2 },
  storage: { label: 'Storage', icon: '\u{1F4BE}', order: 3 },
  security: { label: 'Security', icon: '\u{1F512}', order: 4 },
  firewall: { label: 'Security', icon: '\u{1F6E1}\uFE0F', order: 4 },
  iam: { label: 'Identity & Access', icon: '\u{1F464}', order: 5 },
  monitoring: { label: 'Monitoring', icon: '\u{1F4CA}', order: 6 },
  database: { label: 'Database', icon: '\u{1F5C3}\uFE0F', order: 7 },
  dns: { label: 'DNS', icon: '\u{1F310}', order: 8 },
  loadbalancer: { label: 'Load Balancing', icon: '\u2696\uFE0F', order: 9 },
  gateway: { label: 'Gateway', icon: '\u{1F6AA}', order: 10 },
  container: { label: 'Containers', icon: '\u{1F4E6}', order: 11 },
};

@Component({
  selector: 'nimbus-resource-stack',
  standalone: true,
  imports: [CommonModule, CompartmentCardComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="resource-stack">
      @if (!graph || (graph.nodes.length === 0 && (!graph.compartments || graph.compartments.length === 0))) {
        <div class="empty-state">
          <div class="empty-icon">\u{1F4CB}</div>
          <h3 class="empty-title">No resources yet</h3>
          <p class="empty-desc">Select a blueprint from the left panel to load a pre-built resource stack.</p>
        </div>
      } @else {
        <!-- View mode indicator -->
        <div class="stack-header">
          <span class="view-mode-badge">
            {{ viewMode() === 'hierarchy' ? 'Hierarchy View' : 'Flat View' }}
          </span>
          <span class="resource-summary">
            {{ graph.nodes.length }} resources
            @if (graph.compartments && graph.compartments.length > 0) {
              &middot; {{ graph.compartments.length }} compartments
            }
            @if (graph.connections && graph.connections.length > 0) {
              &middot; {{ graph.connections.length }} connections
            }
          </span>
        </div>

        @if (viewMode() === 'flat') {
          <!-- Flat mode: group by category -->
          @for (cat of categories(); track cat.key) {
            <div class="category-section">
              <button class="category-header" (click)="toggleCategory(cat.key)">
                <span class="cat-icon">{{ cat.icon }}</span>
                <span class="cat-label">{{ cat.label }}</span>
                <span class="cat-count">{{ cat.nodes.length }}</span>
                <span class="chevron" [class.expanded]="isCategoryExpanded(cat.key)">&#9206;</span>
              </button>
              @if (isCategoryExpanded(cat.key)) {
                <div class="category-body">
                  @for (node of cat.nodes; track node.id) {
                    <button
                      class="resource-card"
                      [class.selected]="selectedNodeId() === node.id"
                      (click)="onSelectNode(node.id)"
                    >
                      <span class="node-icon">{{ cat.icon }}</span>
                      <div class="node-info">
                        <span class="node-label">{{ node.label || node.semanticTypeId }}</span>
                        @if (getNodeDescription(node); as desc) {
                          <span class="node-desc">{{ desc }}</span>
                        }
                      </div>
                      @if (getNodeProperties(node).length > 0 && selectedNodeId() === node.id) {
                        <div class="node-props">
                          @for (prop of getNodeProperties(node); track prop.key) {
                            <div class="prop-row">
                              <span class="prop-key">{{ prop.key }}</span>
                              <span class="prop-val">{{ prop.value }}</span>
                            </div>
                          }
                        </div>
                      }
                    </button>
                  }
                </div>
              }
            </div>
          }
        } @else {
          <!-- Hierarchy mode: render compartment tree -->
          <div class="hierarchy-view">
            @for (rootNode of hierarchyRoots(); track rootNode.compartment.id) {
              <nimbus-compartment-card
                [treeNode]="rootNode"
                [selectedNodeId]="selectedNodeId()"
                [depth]="0"
                (nodeSelected)="onSelectNode($event)"
              />
            }

            <!-- Orphan nodes (not in any compartment) -->
            @if (orphanNodes().length > 0) {
              <div class="orphan-section">
                <div class="orphan-header">Unassigned Resources</div>
                <div class="node-grid">
                  @for (node of orphanNodes(); track node.id) {
                    <button
                      class="resource-card"
                      [class.selected]="selectedNodeId() === node.id"
                      (click)="onSelectNode(node.id)"
                    >
                      <span class="node-icon">{{ getNodeCategoryIcon(node.semanticTypeId) }}</span>
                      <div class="node-info">
                        <span class="node-label">{{ node.label || node.semanticTypeId }}</span>
                        @if (getNodeDescription(node); as desc) {
                          <span class="node-desc">{{ desc }}</span>
                        }
                      </div>
                    </button>
                  }
                </div>
              </div>
            }
          </div>
        }
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex; flex: 1; min-width: 0; overflow: hidden;
    }
    .resource-stack {
      flex: 1; overflow-y: auto; padding: 16px; background: #f5f6f8;
    }

    /* ---- Empty state ---- */
    .empty-state {
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      padding: 60px 20px; text-align: center;
    }
    .empty-icon { font-size: 3rem; margin-bottom: 12px; opacity: 0.5; }
    .empty-title { margin: 0 0 6px; font-size: 1rem; font-weight: 600; color: #64748b; }
    .empty-desc { margin: 0; font-size: 0.8125rem; color: #94a3b8; max-width: 320px; }

    /* ---- Stack header ---- */
    .stack-header {
      display: flex; align-items: center; gap: 10px; margin-bottom: 14px;
    }
    .view-mode-badge {
      padding: 3px 10px; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #dbeafe; color: #1d4ed8;
    }
    .resource-summary { font-size: 0.75rem; color: #64748b; }

    /* ---- Category sections (flat mode) ---- */
    .category-section {
      margin-bottom: 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; overflow: hidden;
    }
    .category-header {
      display: flex; align-items: center; gap: 8px; width: 100%;
      padding: 10px 14px; background: #fff; border: none; cursor: pointer;
      font-family: inherit; font-size: 0.8125rem; text-align: left;
      transition: background 0.15s;
    }
    .category-header:hover { background: #f8fafc; }
    .cat-icon { font-size: 1rem; flex-shrink: 0; }
    .cat-label { font-weight: 600; color: #1e293b; flex: 1; }
    .cat-count {
      background: #f1f5f9; color: #475569; padding: 1px 7px; border-radius: 10px;
      font-size: 0.6875rem; font-weight: 600;
    }
    .chevron { font-size: 0.625rem; color: #94a3b8; transition: transform 0.2s; transform: rotate(180deg); }
    .chevron.expanded { transform: rotate(0deg); }

    .category-body { padding: 0 14px 14px; }

    /* ---- Resource cards ---- */
    .resource-card {
      display: flex; align-items: flex-start; gap: 10px; width: 100%;
      padding: 10px 12px; margin-bottom: 6px; background: #f8fafc;
      border: 1px solid #e2e8f0; border-radius: 6px; cursor: pointer;
      font-family: inherit; text-align: left;
      transition: border-color 0.15s, box-shadow 0.15s;
    }
    .resource-card:last-child { margin-bottom: 0; }
    .resource-card:hover { border-color: #3b82f6; }
    .resource-card.selected {
      border-color: #3b82f6; background: #eff6ff;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .node-icon { font-size: 1.125rem; flex-shrink: 0; margin-top: 1px; }
    .node-info { display: flex; flex-direction: column; flex: 1; min-width: 0; }
    .node-label {
      font-size: 0.8125rem; font-weight: 600; color: #1e293b;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .node-desc {
      font-size: 0.6875rem; color: #64748b; margin-top: 1px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    /* ---- Inline properties (expanded on selection) ---- */
    .node-props {
      width: 100%; margin-top: 6px; padding-top: 6px; border-top: 1px solid #e2e8f0;
    }
    .prop-row {
      display: flex; justify-content: space-between; align-items: center;
      padding: 2px 0; font-size: 0.6875rem;
    }
    .prop-key { color: #64748b; }
    .prop-val { color: #1e293b; font-weight: 500; font-family: 'Cascadia Code', 'Fira Code', monospace; font-size: 0.625rem; }

    /* ---- Hierarchy mode ---- */
    .hierarchy-view { }

    .node-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 8px;
    }
    .node-grid .resource-card { margin-bottom: 0; }

    .orphan-section {
      margin-top: 12px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px; padding: 14px; overflow: hidden;
    }
    .orphan-header {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 10px;
    }
  `],
})
export class ResourceStackComponent {
  @Input() graph: TopologyGraph | null = null;
  @Input() providerName = '';
  @Input() readOnly = false;

  @Output() nodeSelected = new EventEmitter<string | null>();
  @Output() graphChange = new EventEmitter<TopologyGraph>();

  selectedNodeId = signal<string | null>(null);
  private expandedCategories = signal<Set<string>>(new Set());

  // Auto-select view mode based on compartments
  viewMode = computed((): 'flat' | 'hierarchy' => {
    const g = this.graph;
    if (!g) return 'flat';
    return (g.compartments && g.compartments.length > 0) ? 'hierarchy' : 'flat';
  });

  // Flat mode: group nodes by category
  categories = computed((): ResourceCategory[] => {
    const g = this.graph;
    if (!g) return [];

    const groupMap = new Map<string, TopologyNode[]>();
    for (const node of g.nodes) {
      const catKey = this.getCategoryKey(node.semanticTypeId);
      if (!groupMap.has(catKey)) groupMap.set(catKey, []);
      groupMap.get(catKey)!.push(node);
    }

    const result: ResourceCategory[] = [];
    for (const [key, nodes] of groupMap) {
      const config = CATEGORY_CONFIG[key] || { label: this.capitalize(key), icon: '\u{1F4CB}', order: 99 };
      result.push({ key, label: config.label, icon: config.icon, nodes });
    }

    result.sort((a, b) => {
      const oa = CATEGORY_CONFIG[a.key]?.order ?? 99;
      const ob = CATEGORY_CONFIG[b.key]?.order ?? 99;
      return oa - ob;
    });

    return result;
  });

  // Hierarchy mode: build compartment tree
  hierarchyRoots = computed((): CompartmentTreeNode[] => {
    const g = this.graph;
    if (!g || !g.compartments) return [];

    const compartments = g.compartments;
    const nodes = g.nodes;

    // Build lookup
    const compMap = new Map<string, TopologyCompartment>();
    for (const c of compartments) compMap.set(c.id, c);

    // Group nodes by compartmentId
    const nodesByComp = new Map<string, TopologyNode[]>();
    for (const node of nodes) {
      const cid = node.compartmentId || '__none__';
      if (!nodesByComp.has(cid)) nodesByComp.set(cid, []);
      nodesByComp.get(cid)!.push(node);
    }

    // Build tree nodes
    const treeMap = new Map<string, CompartmentTreeNode>();
    for (const c of compartments) {
      treeMap.set(c.id, {
        compartment: c,
        nodes: nodesByComp.get(c.id) || [],
        children: [],
      });
    }

    // Link children to parents
    const roots: CompartmentTreeNode[] = [];
    for (const c of compartments) {
      const treeNode = treeMap.get(c.id)!;
      if (c.parentCompartmentId && treeMap.has(c.parentCompartmentId)) {
        treeMap.get(c.parentCompartmentId)!.children.push(treeNode);
      } else {
        roots.push(treeNode);
      }
    }

    return roots;
  });

  // Nodes not assigned to any compartment (in hierarchy mode)
  orphanNodes = computed((): TopologyNode[] => {
    const g = this.graph;
    if (!g || !g.compartments || g.compartments.length === 0) return [];

    const compartmentIds = new Set(g.compartments.map(c => c.id));
    return g.nodes.filter(n => !n.compartmentId || !compartmentIds.has(n.compartmentId));
  });

  constructor() {
    // Auto-expand all categories on initial load
    effect(() => {
      const cats = this.categories();
      if (cats.length > 0 && this.expandedCategories().size === 0) {
        this.expandedCategories.set(new Set(cats.map(c => c.key)));
      }
    });
  }

  toggleCategory(key: string): void {
    this.expandedCategories.update(set => {
      const next = new Set(set);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }

  isCategoryExpanded(key: string): boolean {
    return this.expandedCategories().has(key);
  }

  onSelectNode(nodeId: string | null): void {
    const current = this.selectedNodeId();
    const newId = current === nodeId ? null : nodeId;
    this.selectedNodeId.set(newId);
    this.nodeSelected.emit(newId);
  }

  getNodeDescription(node: TopologyNode): string | null {
    const props = node.properties || {};
    return (props['description'] as string) || (props['type'] as string) || null;
  }

  getNodeProperties(node: TopologyNode): { key: string; value: string }[] {
    const props = node.properties || {};
    const result: { key: string; value: string }[] = [];
    for (const [key, value] of Object.entries(props)) {
      if (key === 'description' || value === null || value === undefined || value === '') continue;
      result.push({ key, value: String(value) });
    }
    return result.slice(0, 6); // Limit to 6 properties inline
  }

  getNodeCategoryIcon(semanticTypeId: string): string {
    const key = this.getCategoryKey(semanticTypeId);
    return CATEGORY_CONFIG[key]?.icon || '\u{1F4CB}';
  }

  private getCategoryKey(semanticTypeId: string): string {
    const id = semanticTypeId.toLowerCase();
    // Try direct match or partial match
    for (const key of Object.keys(CATEGORY_CONFIG)) {
      if (id === key || id.includes(key)) return key;
    }
    return id;
  }

  private capitalize(s: string): string {
    return s.charAt(0).toUpperCase() + s.slice(1);
  }
}
