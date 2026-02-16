/**
 * Overview: Recursive tree node component that renders a single row in the landing zone hierarchy tree editor.
 * Architecture: Presentational component for hierarchy visualization (Section 5 — Landing Zones)
 * Dependencies: CommonModule, FormsModule, HierarchyNode, HierarchyLevelDef from landing-zone.model
 * Concepts: Recursive rendering, expand/collapse, inline editing, depth-based indentation
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
import { FormsModule } from '@angular/forms';
import {
  HierarchyNode,
  HierarchyLevelDef,
} from '@shared/models/landing-zone.model';

@Component({
  selector: 'nimbus-hierarchy-tree-node',
  standalone: true,
  imports: [CommonModule, FormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (node) {
      <div
        class="tree-row"
        [class.selected]="selectedId === node.id"
        [style.paddingLeft.px]="depth * 24"
        (click)="nodeSelected.emit(node.id)"
      >
        <!-- Expand / collapse chevron -->
        <button
          class="chevron-btn"
          [class.invisible]="!children || children.length === 0"
          (click)="toggleExpand($event)"
        >
          @if (expanded()) {
            <span class="chevron">&#9660;</span>
          } @else {
            <span class="chevron">&#9654;</span>
          }
        </button>

        <!-- Icon label from level def -->
        <span class="icon-label">
          @if (levelDef) {
            {{ levelDef.icon }}
          } @else {
            folder
          }
        </span>

        <!-- Node label (inline editable when selected and not readOnly) -->
        @if (selectedId === node.id && !readOnly) {
          <input
            class="label-input"
            type="text"
            [ngModel]="node.label"
            (ngModelChange)="node.label = $event"
            (click)="$event.stopPropagation()"
          />
        } @else {
          <span class="node-label">{{ node.label }}</span>
        }

        <!-- Type badge -->
        @if (levelDef) {
          <span class="badge type-badge">{{ levelDef.label }}</span>
        }

        <!-- CIDR badge -->
        @if (node.properties.ipam?.cidr) {
          <span class="badge cidr-badge">{{ node.properties.ipam!.cidr }}</span>
        }

        <!-- Tag count badge -->
        @if (node.properties.tagPolicies && node.properties.tagPolicies.length > 0) {
          <span class="badge tag-badge">{{ node.properties.tagPolicies.length }} tags</span>
        }

        <!-- Validation error indicator -->
        @if (nodeErrors.length > 0) {
          <span class="badge error-badge" [title]="nodeErrors.join(', ')">{{ nodeErrors.length }} err</span>
        }

        <!-- Hover action buttons -->
        <span class="hover-actions">
          <button
            class="action-btn add-btn"
            title="Add child node"
            [disabled]="readOnly || !hasAllowedChildren"
            (click)="onAddChild($event)"
          >+</button>
          <button
            class="action-btn delete-btn"
            title="Delete node"
            [disabled]="readOnly"
            (click)="onDelete($event)"
          >&times;</button>
        </span>
      </div>

      <!-- Recursive children -->
      @if (expanded() && children && children.length > 0) {
        @for (child of children; track child.id) {
          <nimbus-hierarchy-tree-node
            [node]="child"
            [depth]="depth + 1"
            [selectedId]="selectedId"
            [children]="getChildNodes(child.id)"
            [levelDefs]="levelDefs"
            [readOnly]="readOnly"
            [validationErrors]="validationErrors"
            (nodeSelected)="nodeSelected.emit($event)"
            (addChild)="addChild.emit($event)"
            (deleteNode)="deleteNode.emit($event)"
          />
        }
      }
    }
  `,
  styles: [`
    :host {
      display: block;
    }

    .tree-row {
      display: flex;
      align-items: center;
      gap: 6px;
      height: 36px;
      padding-right: 8px;
      border-left: 3px solid transparent;
      cursor: pointer;
      transition: background-color 0.15s ease;
    }

    .tree-row:hover {
      background-color: #f8fafc;
    }

    .tree-row.selected {
      background-color: #eff6ff;
      border-left-color: #3b82f6;
    }

    .chevron-btn {
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: none;
      background: none;
      cursor: pointer;
      color: #64748b;
      font-size: 10px;
      padding: 0;
      flex-shrink: 0;
    }

    .chevron-btn.invisible {
      visibility: hidden;
    }

    .chevron-btn:hover {
      color: #1e293b;
    }

    .icon-label {
      font-size: 12px;
      color: #64748b;
      flex-shrink: 0;
      min-width: 48px;
      font-weight: 500;
    }

    .node-label {
      font-size: 14px;
      color: #1e293b;
      font-weight: 500;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .label-input {
      font-size: 14px;
      color: #1e293b;
      font-weight: 500;
      border: 1px solid #3b82f6;
      border-radius: 4px;
      padding: 2px 6px;
      outline: none;
      background: #fff;
      min-width: 120px;
    }

    .badge {
      font-size: 11px;
      padding: 1px 8px;
      border-radius: 10px;
      font-weight: 500;
      white-space: nowrap;
      flex-shrink: 0;
    }

    .type-badge {
      background-color: #e0f2fe;
      color: #0369a1;
    }

    .cidr-badge {
      background-color: #f0fdf4;
      color: #15803d;
      font-family: monospace;
    }

    .tag-badge {
      background-color: #fef3c7;
      color: #92400e;
    }

    .error-badge {
      background-color: #fee2e2;
      color: #dc2626;
    }

    .hover-actions {
      margin-left: auto;
      display: flex;
      gap: 4px;
      opacity: 0;
      transition: opacity 0.15s ease;
    }

    .tree-row:hover .hover-actions {
      opacity: 1;
    }

    .action-btn {
      width: 24px;
      height: 24px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid #e2e8f0;
      border-radius: 4px;
      background: #fff;
      cursor: pointer;
      font-size: 14px;
      color: #64748b;
      padding: 0;
      line-height: 1;
    }

    .action-btn:hover:not(:disabled) {
      background: #f1f5f9;
      color: #1e293b;
    }

    .action-btn:disabled {
      opacity: 0.4;
      cursor: not-allowed;
    }

    .add-btn {
      color: #3b82f6;
    }

    .delete-btn {
      color: #ef4444;
    }
  `],
})
export class HierarchyTreeNodeComponent {
  @Input({ required: true }) node!: HierarchyNode;
  @Input() depth = 0;
  @Input() selectedId: string | null = null;
  @Input() children: HierarchyNode[] = [];
  @Input() levelDefs: Map<string, HierarchyLevelDef> = new Map();
  @Input() readOnly = false;
  @Input() validationErrors: Map<string, string[]> = new Map();

  @Output() nodeSelected = new EventEmitter<string>();
  @Output() addChild = new EventEmitter<string>();
  @Output() deleteNode = new EventEmitter<string>();

  expanded = signal(true);

  /** All hierarchy nodes for resolving grandchildren — set via parent container */
  @Input() allNodes: HierarchyNode[] = [];

  get levelDef(): HierarchyLevelDef | undefined {
    return this.levelDefs.get(this.node?.typeId);
  }

  get nodeErrors(): string[] {
    return this.validationErrors.get(this.node?.id) || [];
  }

  get hasAllowedChildren(): boolean {
    const def = this.levelDef;
    return !!def && def.allowedChildren.length > 0;
  }

  toggleExpand(event: Event): void {
    event.stopPropagation();
    this.expanded.set(!this.expanded());
  }

  onAddChild(event: Event): void {
    event.stopPropagation();
    this.addChild.emit(this.node.id);
  }

  onDelete(event: Event): void {
    event.stopPropagation();
    this.deleteNode.emit(this.node.id);
  }

  getChildNodes(parentId: string): HierarchyNode[] {
    return this.allNodes.filter(n => n.parentId === parentId);
  }
}
