/**
 * Overview: Recursive compartment card for landing zone resource stack — renders compartment header, child nodes, and nested sub-compartments.
 * Architecture: Feature component for LZ resource stack view (Section 7.2)
 * Dependencies: @angular/core
 * Concepts: Compartments are provider-specific containers (Management Groups, Subscriptions, Accounts, etc.).
 *     This component renders recursively for nested compartment hierarchies. Each compartment shows
 *     its child resource nodes and sub-compartments with collapsible body.
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  signal,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { TopologyNode, TopologyCompartment } from '@shared/models/architecture.model';

export interface CompartmentTreeNode {
  compartment: TopologyCompartment;
  nodes: TopologyNode[];
  children: CompartmentTreeNode[];
}

const COMPARTMENT_ICONS: Record<string, string> = {
  management_group: '\u{1F3E2}',
  subscription: '\u{1F4C2}',
  account: '\u{1F4BC}',
  folder: '\u{1F4C1}',
  project: '\u{1F4CB}',
  compartment: '\u{1F4E6}',
  datacenter: '\u{1F3ED}',
  cluster: '\u26D3',
  organization: '\u{1F3DB}',
  ou: '\u{1F4C2}',
  tenancy: '\u{1F3E0}',
  resource_group: '\u{1F4C2}',
  vpc: '\u{1F310}',
  vnet: '\u{1F310}',
  vcn: '\u{1F310}',
};

const NODE_ICONS: Record<string, string> = {
  network: '\u{1F310}',
  compute: '\u2699\uFE0F',
  storage: '\u{1F4BE}',
  security: '\u{1F512}',
  monitoring: '\u{1F4CA}',
  iam: '\u{1F464}',
  database: '\u{1F5C3}\uFE0F',
  dns: '\u{1F310}',
  loadbalancer: '\u2696\uFE0F',
  firewall: '\u{1F6E1}\uFE0F',
  gateway: '\u{1F6AA}',
  container: '\u{1F4E6}',
  default: '\u{1F4CB}',
};

@Component({
  selector: 'nimbus-compartment-card',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="compartment-card" [class.depth-0]="depth === 0" [class.depth-1]="depth === 1" [class.depth-2]="depth >= 2">
      <button class="compartment-header" (click)="toggleExpand()">
        <span class="compartment-icon">{{ getCompartmentIcon() }}</span>
        <span class="compartment-label">{{ treeNode.compartment.label }}</span>
        <span class="resource-count">{{ totalResourceCount() }} resources</span>
        <span class="chevron" [class.expanded]="expanded()">&#9206;</span>
      </button>

      @if (expanded()) {
        <div class="compartment-body">
          @if (treeNode.nodes.length > 0) {
            <div class="node-grid">
              @for (node of treeNode.nodes; track node.id) {
                <button
                  class="resource-card"
                  [class.selected]="selectedNodeId === node.id"
                  (click)="onSelectNode(node.id, $event)"
                >
                  <span class="node-icon">{{ getNodeIcon(node.semanticTypeId) }}</span>
                  <div class="node-info">
                    <span class="node-label">{{ node.label || node.semanticTypeId }}</span>
                    @if (getNodeDescription(node); as desc) {
                      <span class="node-desc">{{ desc }}</span>
                    }
                  </div>
                </button>
              }
            </div>
          }

          @for (child of treeNode.children; track child.compartment.id) {
            <nimbus-compartment-card
              [treeNode]="child"
              [selectedNodeId]="selectedNodeId"
              [depth]="depth + 1"
              (nodeSelected)="nodeSelected.emit($event)"
            />
          }

          @if (treeNode.nodes.length === 0 && treeNode.children.length === 0) {
            <div class="empty-hint">No resources in this compartment.</div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .compartment-card {
      border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px;
      background: #fff; overflow: hidden;
    }
    .depth-0 { border-color: #cbd5e1; }
    .depth-1 { border-color: #e2e8f0; margin-left: 0; }
    .depth-2 { border-color: #f1f5f9; margin-left: 0; }

    .compartment-header {
      display: flex; align-items: center; gap: 8px; width: 100%;
      padding: 10px 14px; background: #f8fafc; border: none;
      cursor: pointer; font-family: inherit; font-size: 0.8125rem;
      text-align: left; transition: background 0.15s;
    }
    .compartment-header:hover { background: #f1f5f9; }
    .compartment-icon { font-size: 1rem; flex-shrink: 0; }
    .compartment-label { font-weight: 600; color: #1e293b; flex: 1; }
    .resource-count {
      font-size: 0.6875rem; color: #94a3b8; white-space: nowrap;
    }
    .chevron { font-size: 0.625rem; color: #94a3b8; transition: transform 0.2s; transform: rotate(180deg); }
    .chevron.expanded { transform: rotate(0deg); }

    .compartment-body { padding: 10px 14px 14px; }

    .node-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 8px; margin-bottom: 8px;
    }

    .resource-card {
      display: flex; align-items: flex-start; gap: 8px;
      padding: 10px 12px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; cursor: pointer; font-family: inherit;
      text-align: left; transition: border-color 0.15s, box-shadow 0.15s;
    }
    .resource-card:hover { border-color: #3b82f6; }
    .resource-card.selected {
      border-color: #3b82f6; background: #eff6ff;
      box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
    }
    .node-icon { font-size: 1.125rem; flex-shrink: 0; margin-top: 1px; }
    .node-info { display: flex; flex-direction: column; min-width: 0; }
    .node-label {
      font-size: 0.75rem; font-weight: 600; color: #1e293b;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .node-desc {
      font-size: 0.625rem; color: #64748b; margin-top: 1px;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }
    .empty-hint { font-size: 0.6875rem; color: #94a3b8; padding: 8px 0; text-align: center; }
  `],
})
export class CompartmentCardComponent {
  @Input({ required: true }) treeNode!: CompartmentTreeNode;
  @Input() selectedNodeId: string | null = null;
  @Input() depth = 0;

  @Output() nodeSelected = new EventEmitter<string | null>();

  expanded = signal(true);

  toggleExpand(): void {
    this.expanded.update(v => !v);
  }

  totalResourceCount(): number {
    let count = this.treeNode.nodes.length;
    for (const child of this.treeNode.children) {
      count += this.countRecursive(child);
    }
    return count;
  }

  private countRecursive(node: CompartmentTreeNode): number {
    let count = node.nodes.length;
    for (const child of node.children) {
      count += this.countRecursive(child);
    }
    return count;
  }

  getCompartmentIcon(): string {
    const typeId = this.treeNode.compartment.semanticTypeId?.toLowerCase() || '';
    const label = this.treeNode.compartment.label.toLowerCase();

    // Try matching by semanticTypeId first
    for (const [key, icon] of Object.entries(COMPARTMENT_ICONS)) {
      if (typeId.includes(key)) return icon;
    }
    // Fallback: match by label text
    for (const [key, icon] of Object.entries(COMPARTMENT_ICONS)) {
      if (label.includes(key.replace('_', ' '))) return icon;
    }
    return '\u{1F4C2}';
  }

  getNodeIcon(semanticTypeId: string): string {
    const id = semanticTypeId.toLowerCase();
    for (const [key, icon] of Object.entries(NODE_ICONS)) {
      if (id.includes(key)) return icon;
    }
    return NODE_ICONS['default'];
  }

  getNodeDescription(node: TopologyNode): string | null {
    const props = node.properties || {};
    return (props['description'] as string) || (props['type'] as string) || null;
  }

  onSelectNode(nodeId: string, event: Event): void {
    event.stopPropagation();
    this.nodeSelected.emit(nodeId);
  }
}
