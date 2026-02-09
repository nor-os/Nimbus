/**
 * Overview: Hierarchical tree view of compartments with CRUD operations and drag-drop CI assignment.
 * Architecture: Feature component for CMDB compartment management (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, rxjs, CmdbService
 * Concepts: Tree navigation, compartment hierarchy, cloud provider info, CI organization
 */
import { Component, inject, signal, computed, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { CmdbService } from '@core/services/cmdb.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { CompartmentNode, CompartmentCreateInput, CompartmentUpdateInput } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-compartment-tree',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
    <div class="compartment-tree-container">
      <div class="tree-header">
        <h2>Compartments</h2>
        <button class="btn btn-primary btn-sm" (click)="openCreateDialog()">
          + New Compartment
        </button>
      </div>

      @if (loading()) {
        <div class="loading-state">Loading compartment tree...</div>
      }

      @if (!loading() && tree().length === 0) {
        <div class="empty-state">
          <p>No compartments found.</p>
          <p class="hint">Create a compartment to organize your configuration items.</p>
        </div>
      }

      @if (!loading() && tree().length > 0) {
        <div class="tree-view">
          @for (node of tree(); track node.id) {
            <ng-container
              *ngTemplateOutlet="treeNode; context: { $implicit: node, depth: 0 }"
            ></ng-container>
          }
        </div>
      }

      <ng-template #treeNode let-node let-depth="depth">
        <div
          class="tree-item"
          [style.padding-left.rem]="1 + depth * 1.25"
          [class.selected]="selectedId() === node.id"
          (click)="selectNode(node)"
        >
          <button
            class="expand-btn"
            [class.hidden]="!node.children?.length"
            [class.expanded]="isExpanded(node.id)"
            (click)="toggleExpand(node.id); $event.stopPropagation()"
          >
            &#9206;
          </button>
          <span class="node-icon">&#128193;</span>
          <span class="node-name">{{ node.name }}</span>
          @if (node.providerType) {
            <span class="provider-badge">{{ node.providerType }}</span>
          }
          @if (node.cloudId) {
            <span class="cloud-id-badge" [title]="node.cloudId">&#9729;</span>
          }
          <div class="node-actions">
            <button class="action-btn" title="Add child" (click)="openCreateDialog(node.id); $event.stopPropagation()">+</button>
            <button class="action-btn" title="Edit" (click)="openEditDialog(node); $event.stopPropagation()">&#9998;</button>
            <button class="action-btn danger" title="Delete" (click)="confirmDelete(node); $event.stopPropagation()">&#10005;</button>
          </div>
        </div>
        @if (isExpanded(node.id) && node.children?.length) {
          @for (child of node.children; track child.id) {
            <ng-container
              *ngTemplateOutlet="treeNode; context: { $implicit: child, depth: depth + 1 }"
            ></ng-container>
          }
        }
      </ng-template>

      <!-- Create/Edit Dialog -->
      @if (showDialog()) {
        <div class="dialog-backdrop" (click)="closeDialog()">
          <div class="dialog" (click)="$event.stopPropagation()">
            <h3>{{ editingNode() ? 'Edit' : 'Create' }} Compartment</h3>
            <div class="form-group">
              <label for="comp-name">Name</label>
              <input
                id="comp-name"
                type="text"
                [(ngModel)]="formName"
                placeholder="Compartment name"
              />
            </div>
            <div class="form-group">
              <label for="comp-desc">Description</label>
              <textarea
                id="comp-desc"
                [(ngModel)]="formDescription"
                placeholder="Optional description"
                rows="2"
              ></textarea>
            </div>
            <div class="form-group">
              <label for="comp-cloud">Cloud ID</label>
              <input
                id="comp-cloud"
                type="text"
                [(ngModel)]="formCloudId"
                placeholder="e.g. vpc-abc123"
              />
            </div>
            <div class="form-group">
              <label for="comp-provider">Provider Type</label>
              <input
                id="comp-provider"
                type="text"
                [(ngModel)]="formProviderType"
                placeholder="e.g. AWS, Proxmox"
              />
            </div>
            <div class="dialog-actions">
              <button class="btn btn-secondary" (click)="closeDialog()">Cancel</button>
              <button class="btn btn-primary" (click)="saveCompartment()" [disabled]="!formName.trim()">
                {{ editingNode() ? 'Save' : 'Create' }}
              </button>
            </div>
          </div>
        </div>
      }

      @if (error()) {
        <div class="error-bar">{{ error() }}</div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .compartment-tree-container {
      display: flex;
      flex-direction: column;
      height: 100%;
    }

    .tree-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 1rem 1.5rem;
      border-bottom: 1px solid #e2e8f0;
    }

    .tree-header h2 {
      margin: 0;
      font-size: 1.125rem;
      font-weight: 600;
      color: #1e293b;
    }

    .tree-view {
      flex: 1;
      overflow-y: auto;
      padding: 0.5rem 0;
    }

    .tree-item {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      padding: 0.5rem 1rem;
      cursor: pointer;
      transition: background 0.15s;
      min-height: 2.25rem;
    }

    .tree-item:hover {
      background: #f8fafc;
    }

    .tree-item.selected {
      background: #eff6ff;
      border-right: 2px solid #3b82f6;
    }

    .expand-btn {
      width: 1.25rem;
      height: 1.25rem;
      display: flex;
      align-items: center;
      justify-content: center;
      border: none;
      background: none;
      color: #94a3b8;
      font-size: 0.625rem;
      cursor: pointer;
      transition: transform 0.2s;
      transform: rotate(180deg);
      flex-shrink: 0;
    }

    .expand-btn.expanded {
      transform: rotate(0deg);
    }

    .expand-btn.hidden {
      visibility: hidden;
    }

    .node-icon {
      font-size: 0.875rem;
      flex-shrink: 0;
    }

    .node-name {
      flex: 1;
      font-size: 0.8125rem;
      color: #1e293b;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .provider-badge {
      font-size: 0.625rem;
      padding: 0.125rem 0.375rem;
      border-radius: 3px;
      background: #dbeafe;
      color: #2563eb;
      font-weight: 600;
      text-transform: uppercase;
      flex-shrink: 0;
    }

    .cloud-id-badge {
      font-size: 0.75rem;
      color: #94a3b8;
      flex-shrink: 0;
    }

    .node-actions {
      display: none;
      gap: 0.25rem;
      flex-shrink: 0;
    }

    .tree-item:hover .node-actions {
      display: flex;
    }

    .action-btn {
      width: 1.25rem;
      height: 1.25rem;
      border: none;
      background: #f1f5f9;
      border-radius: 3px;
      color: #64748b;
      font-size: 0.625rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .action-btn:hover {
      background: #e2e8f0;
      color: #1e293b;
    }

    .action-btn.danger:hover {
      background: #fef2f2;
      color: #dc2626;
    }

    .loading-state,
    .empty-state {
      padding: 2rem 1.5rem;
      text-align: center;
      color: #94a3b8;
      font-size: 0.875rem;
    }

    .empty-state .hint {
      font-size: 0.75rem;
      margin-top: 0.5rem;
      opacity: 0.7;
    }

    .error-bar {
      padding: 0.75rem 1rem;
      background: #fef2f2;
      border-top: 1px solid #fecaca;
      color: #dc2626;
      font-size: 0.8125rem;
    }

    /* ── Dialog ──────────────────────────────────────────── */

    .dialog-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.4);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .dialog {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.5rem;
      width: 100%;
      max-width: 28rem;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
    }

    .dialog h3 {
      margin: 0 0 1rem;
      font-size: 1rem;
      font-weight: 600;
      color: #1e293b;
    }

    .form-group {
      margin-bottom: 0.75rem;
    }

    .form-group label {
      display: block;
      font-size: 0.75rem;
      font-weight: 500;
      color: #64748b;
      margin-bottom: 0.25rem;
    }

    .form-group input,
    .form-group textarea {
      width: 100%;
      padding: 0.5rem 0.75rem;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      background: #fff;
      color: #1e293b;
      font-size: 0.8125rem;
      font-family: inherit;
    }

    .form-group input:focus,
    .form-group textarea:focus {
      outline: none;
      border-color: #3b82f6;
    }

    .dialog-actions {
      display: flex;
      justify-content: flex-end;
      gap: 0.5rem;
      margin-top: 1rem;
    }

    .btn {
      padding: 0.4375rem 1rem;
      border-radius: 6px;
      border: none;
      font-size: 0.8125rem;
      font-weight: 500;
      cursor: pointer;
    }

    .btn-primary {
      background: #3b82f6;
      color: #fff;
    }

    .btn-primary:hover:not(:disabled) {
      background: #2563eb;
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: default;
    }

    .btn-secondary {
      background: #fff;
      color: #374151;
      border: 1px solid #e2e8f0;
    }

    .btn-secondary:hover {
      background: #f8fafc;
    }

    .btn-sm {
      padding: 0.3125rem 0.75rem;
      font-size: 0.75rem;
    }
  `],
})
export class CompartmentTreeComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private tenantContext = inject(TenantContextService);
  private router = inject(Router);

  tree = signal<CompartmentNode[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);
  selectedId = signal<string | null>(null);
  expandedNodes = signal<Set<string>>(new Set());

  // Dialog state
  showDialog = signal(false);
  editingNode = signal<CompartmentNode | null>(null);
  parentIdForCreate = signal<string | null>(null);

  formName = '';
  formDescription = '';
  formCloudId = '';
  formProviderType = '';

  totalNodes = computed(() => this.countNodes(this.tree()));

  ngOnInit(): void {
    this.loadTree();
  }

  loadTree(): void {
    this.loading.set(true);
    this.error.set(null);
    this.cmdbService.getCompartmentTree().subscribe({
      next: (nodes) => {
        this.tree.set(nodes);
        this.loading.set(false);
        // Auto-expand first level
        const expanded = new Set<string>();
        for (const node of nodes) {
          if (node.children?.length) {
            expanded.add(node.id);
          }
        }
        this.expandedNodes.set(expanded);
      },
      error: (err) => {
        this.error.set(err.message || 'Failed to load compartments');
        this.loading.set(false);
      },
    });
  }

  selectNode(node: CompartmentNode): void {
    this.selectedId.set(node.id);
  }

  toggleExpand(id: string): void {
    const current = this.expandedNodes();
    const next = new Set(current);
    if (next.has(id)) {
      next.delete(id);
    } else {
      next.add(id);
    }
    this.expandedNodes.set(next);
  }

  isExpanded(id: string): boolean {
    return this.expandedNodes().has(id);
  }

  openCreateDialog(parentId?: string): void {
    this.editingNode.set(null);
    this.parentIdForCreate.set(parentId ?? null);
    this.formName = '';
    this.formDescription = '';
    this.formCloudId = '';
    this.formProviderType = '';
    this.showDialog.set(true);
  }

  openEditDialog(node: CompartmentNode): void {
    this.editingNode.set(node);
    this.parentIdForCreate.set(null);
    this.formName = node.name;
    this.formDescription = node.description ?? '';
    this.formCloudId = node.cloudId ?? '';
    this.formProviderType = node.providerType ?? '';
    this.showDialog.set(true);
  }

  closeDialog(): void {
    this.showDialog.set(false);
    this.editingNode.set(null);
  }

  saveCompartment(): void {
    const editing = this.editingNode();
    if (editing) {
      const input: CompartmentUpdateInput = {
        name: this.formName.trim(),
        description: this.formDescription.trim() || null,
        cloudId: this.formCloudId.trim() || null,
        providerType: this.formProviderType.trim() || null,
      };
      this.cmdbService.updateCompartment(editing.id, input).subscribe({
        next: () => {
          this.closeDialog();
          this.loadTree();
        },
        error: (err) => this.error.set(err.message || 'Failed to update'),
      });
    } else {
      const input: CompartmentCreateInput = {
        name: this.formName.trim(),
        description: this.formDescription.trim() || null,
        parentId: this.parentIdForCreate() ?? undefined,
        cloudId: this.formCloudId.trim() || null,
        providerType: this.formProviderType.trim() || null,
      };
      this.cmdbService.createCompartment(input).subscribe({
        next: () => {
          this.closeDialog();
          this.loadTree();
        },
        error: (err) => this.error.set(err.message || 'Failed to create'),
      });
    }
  }

  confirmDelete(node: CompartmentNode): void {
    if (!confirm(`Delete compartment "${node.name}"? This will also remove all child compartments.`)) {
      return;
    }
    this.cmdbService.deleteCompartment(node.id).subscribe({
      next: () => this.loadTree(),
      error: (err) => this.error.set(err.message || 'Failed to delete'),
    });
  }

  private countNodes(nodes: CompartmentNode[]): number {
    let count = nodes.length;
    for (const n of nodes) {
      if (n.children?.length) {
        count += this.countNodes(n.children);
      }
    }
    return count;
  }
}
