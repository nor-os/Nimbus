/**
 * Overview: Topology list page with status tabs, search, template toggle, and CRUD actions.
 * Architecture: Feature component for topology management (Section 3.2)
 * Dependencies: @angular/core, @angular/router, @angular/common, @angular/forms, architecture.service
 * Concepts: Topology listing, status filtering, template filtering, permission-gated actions, light theme
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ArchitectureService } from '@core/services/architecture.service';
import { ArchitectureTopology, TopologyStatus } from '@shared/models/architecture.model';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-topology-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Architecture Topologies</h1>
            <p class="page-subtitle">Visual infrastructure topology diagrams with versioning and deployment workflows</p>
          </div>
          <div class="header-actions">
            <button class="btn btn-outline" (click)="onImport()">Import</button>
            <a routerLink="/architecture/new" class="btn btn-primary">+ New Topology</a>
          </div>
        </div>

        <!-- Filters -->
        <div class="filters-bar">
          <div class="status-tabs">
            <button
              class="tab-btn"
              [class.active]="statusFilter() === null"
              (click)="statusFilter.set(null)"
            >All</button>
            <button
              class="tab-btn"
              [class.active]="statusFilter() === 'DRAFT'"
              (click)="statusFilter.set('DRAFT')"
            >Drafts</button>
            <button
              class="tab-btn"
              [class.active]="statusFilter() === 'PUBLISHED'"
              (click)="statusFilter.set('PUBLISHED')"
            >Published</button>
            <button
              class="tab-btn"
              [class.active]="statusFilter() === 'ARCHIVED'"
              (click)="statusFilter.set('ARCHIVED')"
            >Archived</button>
          </div>
          <div class="filter-right">
            <label class="template-toggle">
              <input type="checkbox" [(ngModel)]="templatesOnly" (ngModelChange)="loadTopologies()" />
              Templates Only
            </label>
            <input
              type="text"
              class="search-input"
              placeholder="Search topologies..."
              [(ngModel)]="searchTerm"
              (ngModelChange)="loadTopologies()"
            />
          </div>
        </div>


        <!-- Table -->
        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Version</th>
                <th>Type</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (t of topologies(); track t.id) {
                <tr>
                  <td>
                    <a [routerLink]="['/architecture', t.id]" class="name-link">{{ t.name }}</a>
                  </td>
                  <td>
                    <span class="status-badge" [class]="'badge-' + t.status.toLowerCase()">
                      {{ t.status }}
                    </span>
                  </td>
                  <td>v{{ t.version }}</td>
                  <td>
                    @if (t.isTemplate) {
                      <span class="template-badge">Template</span>
                    }
                    @if (t.isSystem) {
                      <span class="system-badge">System</span>
                    }
                  </td>
                  <td>{{ t.updatedAt | date:'short' }}</td>
                  <td>
                    <div class="action-btns">
                      @if (t.status === 'DRAFT') {
                        <a [routerLink]="['/architecture', t.id, 'edit']" class="action-btn">Edit</a>
                      } @else {
                        <a [routerLink]="['/architecture', t.id]" class="action-btn">View</a>
                      }
                      <button class="action-btn" (click)="onClone(t)">Clone</button>
                      @if (t.status !== 'ARCHIVED') {
                        <button class="action-btn" (click)="onArchive(t)">Archive</button>
                      }
                      <button class="action-btn danger" (click)="onDelete(t)">Delete</button>
                    </div>
                  </td>
                </tr>
              }
              @if (topologies().length === 0) {
                <tr>
                  <td colspan="6" class="empty-cell">No topologies found</td>
                </tr>
              }
            </tbody>
          </table>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .header-actions { display: flex; gap: 8px; }
    .btn {
      padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500;
      cursor: pointer; text-decoration: none; border: none; display: inline-flex;
      align-items: center; font-family: inherit; transition: background 0.15s;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .filters-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
      gap: 16px;
    }
    .status-tabs { display: flex; gap: 4px; }
    .tab-btn {
      padding: 6px 12px;
      border: 1px solid #e2e8f0;
      background: #fff;
      border-radius: 6px;
      font-size: 0.75rem;
      font-weight: 500;
      color: #64748b;
      cursor: pointer;
      font-family: inherit;
      transition: all 0.15s;
    }
    .tab-btn.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .tab-btn:hover:not(.active) { background: #f8fafc; }
    .filter-right { display: flex; align-items: center; gap: 12px; }
    .template-toggle {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8125rem;
      color: #64748b;
      cursor: pointer;
      white-space: nowrap;
    }
    .search-input {
      padding: 6px 12px;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      font-size: 0.8125rem;
      color: #1e293b;
      background: #fff;
      outline: none;
      min-width: 200px;
      font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; }
    .table-container {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      overflow: hidden;
    }
    .table { width: 100%; border-collapse: collapse; }
    .table th {
      padding: 10px 16px;
      text-align: left;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
      border-bottom: 1px solid #e2e8f0;
      background: #fafbfc;
    }
    .table td {
      padding: 12px 16px;
      font-size: 0.8125rem;
      color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .table tr:last-child td { border-bottom: none; }
    .table tr:hover td { background: #fafbfc; }
    .name-link { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .name-link:hover { text-decoration: underline; }
    .status-badge {
      display: inline-block;
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #d1fae5; color: #065f46; }
    .badge-archived { background: #f1f5f9; color: #64748b; }
    .template-badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.625rem;
      font-weight: 600;
      background: #ede9fe;
      color: #6d28d9;
    }
    .system-badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.625rem;
      font-weight: 600;
      background: #f0f9ff;
      color: #0369a1;
      margin-left: 4px;
    }
    .action-btns { display: flex; gap: 8px; }
    .action-btn {
      padding: 4px 8px;
      border: none;
      background: none;
      color: #3b82f6;
      font-size: 0.75rem;
      font-weight: 500;
      cursor: pointer;
      font-family: inherit;
      text-decoration: none;
    }
    .action-btn:hover { text-decoration: underline; }
    .action-btn.danger { color: #ef4444; }
    .empty-cell {
      text-align: center;
      padding: 32px 16px !important;
      color: #94a3b8;
    }
  `],
})
export class TopologyListComponent implements OnInit {
  private architectureService = inject(ArchitectureService);
  private toast = inject(ToastService);
  private confirm = inject(ConfirmService);

  topologies = signal<ArchitectureTopology[]>([]);
  statusFilter = signal<TopologyStatus | null>(null);
  searchTerm = '';
  templatesOnly = false;

  ngOnInit(): void {
    this.loadTopologies();
  }

  loadTopologies(): void {
    this.architectureService.listTopologies({
      status: this.statusFilter() || undefined,
      isTemplate: this.templatesOnly || undefined,
      search: this.searchTerm || undefined,
    }).subscribe({
      next: list => this.topologies.set(list),
      error: err => this.toast.error(err.message || 'Failed to load topologies'),
    });
  }

  onClone(t: ArchitectureTopology): void {
    this.architectureService.cloneTopology(t.id).subscribe({
      next: () => {
        this.toast.success('Topology cloned');
        this.loadTopologies();
      },
      error: err => this.toast.error(err.message || 'Clone failed'),
    });
  }

  async onArchive(t: ArchitectureTopology): Promise<void> {
    const confirmed = await this.confirm.confirm({
      title: 'Archive Topology',
      message: 'Archive this topology?',
    });
    if (!confirmed) return;
    this.architectureService.archiveTopology(t.id).subscribe({
      next: () => {
        this.toast.success('Topology archived');
        this.loadTopologies();
      },
      error: err => this.toast.error(err.message || 'Archive failed'),
    });
  }

  async onDelete(t: ArchitectureTopology): Promise<void> {
    const confirmed = await this.confirm.confirm({
      title: 'Delete Topology',
      message: 'Delete this topology? This action cannot be undone.',
      variant: 'danger',
    });
    if (!confirmed) return;
    this.architectureService.deleteTopology(t.id).subscribe({
      next: () => {
        this.toast.success('Topology deleted');
        this.loadTopologies();
      },
      error: err => this.toast.error(err.message || 'Delete failed'),
    });
  }

  onImport(): void {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = () => {
      const file = input.files?.[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(reader.result as string);
          this.architectureService.importTopology({
            name: data.name || file.name.replace('.json', ''),
            description: data.description,
            graph: data.graph,
            tags: data.tags,
            isTemplate: data.is_template || false,
          }).subscribe({
            next: () => {
              this.toast.success('Topology imported');
              this.loadTopologies();
            },
            error: err => this.toast.error(err.message || 'Import failed'),
          });
        } catch {
          this.toast.error('Invalid JSON file');
        }
      };
      reader.readAsText(file);
    };
    input.click();
  }
}
