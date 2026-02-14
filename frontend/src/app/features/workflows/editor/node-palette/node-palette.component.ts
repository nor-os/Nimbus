/**
 * Overview: Node palette — categorized node library with search and drag-to-canvas.
 * Architecture: Left sidebar panel for workflow editor (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms
 * Concepts: Node types, categories, search filter, drag-to-add
 */
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { NodeTypeInfo, WorkflowType } from '@shared/models/workflow.model';

@Component({
  selector: 'nimbus-node-palette',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="node-palette">
      <div class="palette-header">
        <h3>Nodes</h3>
        <input
          type="text"
          class="palette-search"
          placeholder="Search nodes..."
          [ngModel]="searchQuery()"
          (ngModelChange)="searchQuery.set($event)"
        />
      </div>
      <div class="palette-categories">
        @for (cat of categories(); track cat) {
          <div class="category">
            <div class="category-header">{{ cat }}</div>
            @for (node of getNodesForCategory(cat); track node.typeId) {
              <button
                class="palette-node"
                (click)="addNode.emit(node.typeId)"
                [title]="node.description"
              >
                <span class="node-icon" [innerHTML]="node.icon"></span>
                <span class="node-label">{{ node.label }}</span>
              </button>
            }
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .node-palette {
      width: 220px; height: 100%; background: #fff;
      border-right: 1px solid #e2e8f0; overflow-y: auto;
      display: flex; flex-direction: column;
    }
    .palette-header { padding: 12px; border-bottom: 1px solid #e2e8f0; }
    .palette-header h3 { margin: 0 0 8px; font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .palette-search {
      width: 100%; padding: 6px 8px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 6px; color: #1e293b; font-size: 0.75rem; outline: none;
      font-family: inherit;
    }
    .palette-search:focus { border-color: #3b82f6; }
    .palette-categories { flex: 1; padding: 8px 0; }
    .category { margin-bottom: 4px; }
    .category-header {
      padding: 4px 12px; font-size: 0.625rem; font-weight: 700;
      text-transform: uppercase; letter-spacing: 0.08em; color: #94a3b8;
    }
    .palette-node {
      display: flex; align-items: center; gap: 8px; width: 100%;
      padding: 6px 12px; border: none; background: none; color: #374151;
      font-size: 0.8125rem; cursor: pointer; text-align: left;
      transition: background 0.15s;
    }
    .palette-node:hover { background: #f8fafc; color: #1e293b; }
    .node-icon { font-size: 0.875rem; width: 18px; text-align: center; }
  `],
})
export class NodePaletteComponent {
  private _nodeTypes = signal<NodeTypeInfo[]>([]);
  private _workflowType = signal<WorkflowType>('AUTOMATION');

  @Input() set nodeTypes(value: NodeTypeInfo[]) { this._nodeTypes.set(value); }
  @Input() set workflowType(value: WorkflowType) { this._workflowType.set(value); }
  @Output() addNode = new EventEmitter<string>();

  searchQuery = signal('');

  categories = computed(() => {
    const types = this.filteredTypes();
    const cats = new Set(types.map(t => t.category));
    return Array.from(cats).sort();
  });

  filteredTypes = computed(() => {
    const q = this.searchQuery().toLowerCase();
    let types = this._nodeTypes();

    // Hide Deployment category unless editing a DEPLOYMENT workflow
    if (this._workflowType() !== 'DEPLOYMENT') {
      types = types.filter(t => t.category !== 'Deployment');
    }

    if (!q) return types;
    return types.filter(
      t => t.label.toLowerCase().includes(q) || t.description.toLowerCase().includes(q)
    );
  });

  getNodesForCategory(category: string): NodeTypeInfo[] {
    return this.filteredTypes().filter(t => t.category === category);
  }
}
