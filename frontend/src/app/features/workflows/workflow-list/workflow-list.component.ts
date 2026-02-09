/**
 * Overview: Workflow definitions list — table with status tabs, search, CRUD actions.
 * Architecture: List page for workflow definitions (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Definition listing, status filtering, create/edit/publish/archive/clone/delete
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowDefinition, WorkflowDefinitionStatus } from '@shared/models/workflow.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-workflow-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page-container">
      <div class="page-header">
        <h1>Workflow Definitions</h1>
        <button class="btn btn-primary" [routerLink]="['/workflows/definitions/new']">
          + New Workflow
        </button>
      </div>

      <div class="tabs">
        @for (tab of statusTabs; track tab.value) {
          <button
            class="tab"
            [class.active]="activeTab() === tab.value"
            (click)="setTab(tab.value)"
          >{{ tab.label }}</button>
        }
      </div>

      <div class="search-bar">
        <input
          type="text"
          class="search-input"
          placeholder="Search definitions..."
          [ngModel]="searchQuery()"
          (ngModelChange)="searchQuery.set($event)"
        />
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Version</th>
              <th>Last Modified</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            @for (def of filteredDefinitions(); track def.id) {
              <tr>
                <td>
                  <a [routerLink]="['/workflows/definitions', def.id]" class="def-name">
                    {{ def.name }}
                  </a>
                  @if (def.description) {
                    <div class="def-desc">{{ def.description }}</div>
                  }
                </td>
                <td><span class="status-badge" [class]="'status-' + def.status">{{ def.status }}</span></td>
                <td>v{{ def.version }}</td>
                <td>{{ def.updatedAt | date:'short' }}</td>
                <td class="actions">
                  <button class="btn-sm" [routerLink]="['/workflows/definitions', def.id, 'edit']" title="Edit">&#9998;</button>
                  @if (def.status === 'DRAFT') {
                    <button class="btn-sm btn-success" (click)="publish(def.id)" title="Publish">&#10004;</button>
                  }
                  @if (def.status === 'ACTIVE') {
                    <button class="btn-sm" (click)="archive(def.id)" title="Archive">&#128451;</button>
                  }
                  <button class="btn-sm" (click)="clone(def.id)" title="Clone">&#128203;</button>
                  <button class="btn-sm btn-danger" (click)="remove(def.id)" title="Delete">&#128465;</button>
                </td>
              </tr>
            } @empty {
              <tr><td colspan="5" class="empty-row">No workflow definitions found</td></tr>
            }
          </tbody>
        </table>
      </div>
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn { padding: 0.5rem 1rem; border: none; border-radius: 6px; cursor: pointer; font-size: 0.8125rem; font-weight: 500; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .tabs { display: flex; gap: 4px; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }
    .tab {
      padding: 6px 12px; border: none; background: none; color: #64748b;
      cursor: pointer; font-size: 0.8125rem; border-radius: 4px;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { background: #eff6ff; color: #3b82f6; font-weight: 500; }
    .search-bar { margin-bottom: 1rem; }
    .search-input {
      width: 100%; max-width: 400px; padding: 0.5rem 0.75rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      color: #1e293b; font-size: 0.8125rem; outline: none; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; }
    .table-container { overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .data-table th {
      padding: 0.75rem 1rem; text-align: left; font-size: 0.75rem;
      color: #64748b; border-bottom: 1px solid #f1f5f9; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .data-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f1f5f9; color: #374151; }
    .data-table tbody tr:hover { background: #f8fafc; }
    .def-name { color: #3b82f6; text-decoration: none; font-weight: 500; }
    .def-name:hover { text-decoration: underline; }
    .def-desc { font-size: 0.6875rem; color: #64748b; margin-top: 2px; }
    .status-badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
    }
    .status-DRAFT { background: #f1f5f9; color: #64748b; }
    .status-ACTIVE { background: #dcfce7; color: #16a34a; }
    .status-ARCHIVED { background: #fefce8; color: #ca8a04; }
    .actions { display: flex; gap: 0.25rem; }
    .btn-sm {
      padding: 4px 8px; border: 1px solid #e2e8f0; background: #fff;
      border-radius: 6px; color: #64748b; cursor: pointer; font-size: 0.75rem;
      transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; color: #1e293b; }
    .btn-success:hover { border-color: #16a34a; color: #16a34a; }
    .btn-danger:hover { border-color: #dc2626; color: #dc2626; }
    .empty-row { text-align: center; color: #94a3b8; padding: 2rem !important; }
  `],
})
export class WorkflowListComponent implements OnInit {
  private workflowService = inject(WorkflowService);
  private router = inject(Router);

  definitions = signal<WorkflowDefinition[]>([]);
  activeTab = signal<string | null>(null);
  searchQuery = signal('');
  loading = signal(false);

  statusTabs = [
    { label: 'All', value: null as string | null },
    { label: 'Draft', value: 'DRAFT' },
    { label: 'Active', value: 'ACTIVE' },
    { label: 'Archived', value: 'ARCHIVED' },
  ];

  filteredDefinitions = () => {
    const q = this.searchQuery().toLowerCase();
    let defs = this.definitions();
    if (q) {
      defs = defs.filter(d => d.name.toLowerCase().includes(q));
    }
    return defs;
  };

  ngOnInit(): void {
    this.loadDefinitions();
  }

  setTab(status: string | null): void {
    this.activeTab.set(status);
    this.loadDefinitions();
  }

  loadDefinitions(): void {
    this.loading.set(true);
    const status = this.activeTab() ?? undefined;
    this.workflowService.listDefinitions({ status }).subscribe({
      next: defs => { this.definitions.set(defs); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  publish(id: string): void {
    this.workflowService.publishDefinition(id).subscribe(() => this.loadDefinitions());
  }

  archive(id: string): void {
    this.workflowService.archiveDefinition(id).subscribe(() => this.loadDefinitions());
  }

  clone(id: string): void {
    this.workflowService.cloneDefinition(id).subscribe(() => this.loadDefinitions());
  }

  remove(id: string): void {
    if (confirm('Are you sure you want to delete this workflow definition?')) {
      this.workflowService.deleteDefinition(id).subscribe(() => this.loadDefinitions());
    }
  }
}
