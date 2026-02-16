/**
 * Overview: Container component that manages the full landing zone hierarchy tree of nodes.
 * Architecture: Smart container for hierarchy tree editor (Section 5 — Landing Zones)
 * Dependencies: HierarchyTreeNodeComponent, HierarchyNode, HierarchyLevelDef, LandingZoneHierarchy from landing-zone.model
 * Concepts: Flat-to-tree conversion, node CRUD, parent-child relationships
 */

import {
  ChangeDetectionStrategy,
  Component,
  EventEmitter,
  Input,
  Output,
  signal,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  HierarchyNode,
  HierarchyLevelDef,
  LandingZoneHierarchy,
} from '@shared/models/landing-zone.model';
import { HierarchyTreeNodeComponent } from './hierarchy-tree-node.component';

@Component({
  selector: 'nimbus-hierarchy-tree',
  standalone: true,
  imports: [CommonModule, HierarchyTreeNodeComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="tree-container">
      @if (hierarchy && hierarchy.nodes.length > 0) {
        <div class="tree-scroll">
          @for (root of rootNodes; track root.id) {
            <nimbus-hierarchy-tree-node
              [node]="root"
              [depth]="0"
              [selectedId]="selectedNodeId()"
              [children]="getChildren(root.id)"
              [allNodes]="hierarchy!.nodes"
              [levelDefs]="levelDefs"
              [readOnly]="readOnly"
              [validationErrors]="validationErrors"
              (nodeSelected)="onNodeSelected($event)"
              (addChild)="onAddChild($event)"
              (deleteNode)="onDeleteNode($event)"
            />
          }
        </div>
      } @else {
        <div class="empty-state">
          <span class="empty-icon">account_tree</span>
          <p class="empty-text">Click a level from the palette to start building your hierarchy</p>
        </div>
      }
    </div>
  `,
  styles: [`
    :host {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .tree-container {
      display: flex;
      flex-direction: column;
      flex: 1;
      min-height: 0;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }

    .tree-scroll {
      flex: 1;
      overflow-y: auto;
      padding: 8px 0;
    }

    .empty-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      flex: 1;
      padding: 48px 24px;
      text-align: center;
    }

    .empty-icon {
      font-size: 16px;
      color: #94a3b8;
      margin-bottom: 12px;
      font-weight: 500;
    }

    .empty-text {
      font-size: 14px;
      color: #94a3b8;
      margin: 0;
      max-width: 280px;
      line-height: 1.5;
    }
  `],
})
export class HierarchyTreeComponent {
  @Input() hierarchy: LandingZoneHierarchy | null = null;
  @Input() providerName = '';
  @Input() readOnly = false;
  @Input() levelDefs: Map<string, HierarchyLevelDef> = new Map();
  @Input() validationErrors: Map<string, string[]> = new Map();

  @Output() nodeSelected = new EventEmitter<string | null>();
  @Output() hierarchyChange = new EventEmitter<LandingZoneHierarchy>();

  selectedNodeId = signal<string | null>(null);

  /** Root nodes: nodes with no parent */
  get rootNodes(): HierarchyNode[] {
    if (!this.hierarchy) return [];
    return this.hierarchy.nodes.filter(n => n.parentId === null);
  }

  /** Get direct children for a given parent ID */
  getChildren(parentId: string): HierarchyNode[] {
    if (!this.hierarchy) return [];
    return this.hierarchy.nodes.filter(n => n.parentId === parentId);
  }

  /** Toggle selection: deselect if clicking the same node, otherwise select */
  onNodeSelected(nodeId: string): void {
    if (this.selectedNodeId() === nodeId) {
      this.selectedNodeId.set(null);
      this.nodeSelected.emit(null);
    } else {
      this.selectedNodeId.set(nodeId);
      this.nodeSelected.emit(nodeId);
    }
  }

  /** Create a new child node under the given parent */
  onAddChild(parentId: string): void {
    if (!this.hierarchy) return;

    const parentNode = this.hierarchy.nodes.find(n => n.id === parentId);
    if (!parentNode) return;

    const parentDef = this.levelDefs.get(parentNode.typeId);
    if (!parentDef || parentDef.allowedChildren.length === 0) return;

    // Use the first allowed child type
    const childTypeId = parentDef.allowedChildren[0];
    const childDef = this.levelDefs.get(childTypeId);

    const newNode: HierarchyNode = {
      id: crypto.randomUUID(),
      parentId,
      typeId: childTypeId,
      label: childDef ? `New ${childDef.label}` : 'New Node',
      properties: {},
    };

    const updatedHierarchy: LandingZoneHierarchy = {
      nodes: [...this.hierarchy.nodes, newNode],
    };

    this.hierarchyChange.emit(updatedHierarchy);
  }

  /** Remove a node and all its descendants */
  onDeleteNode(nodeId: string): void {
    if (!this.hierarchy) return;

    // Collect the node and all descendants via BFS
    const idsToRemove = new Set<string>();
    const queue = [nodeId];

    while (queue.length > 0) {
      const currentId = queue.shift()!;
      idsToRemove.add(currentId);
      for (const node of this.hierarchy.nodes) {
        if (node.parentId === currentId && !idsToRemove.has(node.id)) {
          queue.push(node.id);
        }
      }
    }

    const updatedHierarchy: LandingZoneHierarchy = {
      nodes: this.hierarchy.nodes.filter(n => !idsToRemove.has(n.id)),
    };

    // Clear selection if deleted node was selected
    if (this.selectedNodeId() && idsToRemove.has(this.selectedNodeId()!)) {
      this.selectedNodeId.set(null);
      this.nodeSelected.emit(null);
    }

    this.hierarchyChange.emit(updatedHierarchy);
  }
}
