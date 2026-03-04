/**
 * Overview: Provider-level workflow template list — table view matching definitions list design.
 * Architecture: Feature component for template management (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Workflow templates, deployment/stack lifecycle templates, table list
 */
import { Component, OnInit, inject, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowDefinition, WorkflowType } from '@shared/models/workflow.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-workflow-template-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page-container">
      <div class="page-header">
        <h1>Workflow Templates</h1>
        <p class="page-subtitle">Default workflow templates for component and stack lifecycle operations.</p>
      </div>

      <!-- Type filter tabs -->
      <div class="type-tabs">
        @for (tab of typeTabs; track tab.value) {
          <button
            class="type-tab"
            [class.active]="activeTypeTab() === tab.value"
            (click)="setTypeTab(tab.value)"
          >{{ tab.label }}</button>
        }
      </div>

      <div class="search-bar">
        <input
          type="text"
          class="search-input"
          placeholder="Search templates..."
          [ngModel]="searchQuery()"
          (ngModelChange)="searchQuery.set($event)"
        />
      </div>

      @if (loading()) {
        <div class="loading-state">Loading templates...</div>
      }

      @if (!loading()) {
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Type</th>
                <th>Status</th>
                <th>Version</th>
                <th>Nodes</th>
                <th>Last Modified</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              @for (tpl of filteredTemplates(); track tpl.id) {
                <tr>
                  <td>
                    <a class="def-name" (click)="editTemplate(tpl.id)">
                      <span class="wf-icon" [class]="'type-icon-' + tpl.workflowType">{{ typeIcon(tpl.workflowType) }}</span>
                      {{ tpl.name }}
                    </a>
                    @if (tpl.description) {
                      <div class="def-desc">{{ tpl.description }}</div>
                    }
                  </td>
                  <td><span class="type-badge" [class]="'type-' + tpl.workflowType">{{ tpl.workflowType }}</span></td>
                  <td><span class="status-badge" [class]="'status-' + tpl.status">{{ tpl.status }}</span></td>
                  <td>v{{ tpl.version }}</td>
                  <td>{{ tpl.graph?.nodes?.length || 0 }}</td>
                  <td>{{ tpl.updatedAt | date:'short' }}</td>
                  <td class="actions">
                    <button class="btn-sm" (click)="editTemplate(tpl.id)" title="Edit">&#x270E;</button>
                    <button class="btn-sm" (click)="clone(tpl.id)" title="Clone to Tenant">&#x2398; Clone</button>
                  </td>
                </tr>
              } @empty {
                <tr><td colspan="7" class="empty-row">No workflow templates found</td></tr>
              }
            </tbody>
          </table>
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { margin-bottom: 1.5rem; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .page-subtitle { font-size: 14px; color: #64748b; margin: 4px 0 0; }

    .type-tabs { display: flex; gap: 4px; margin-bottom: 0.75rem; }
    .type-tab {
      padding: 6px 14px; border: 1px solid #e2e8f0; background: #fff; color: #64748b;
      cursor: pointer; font-size: 0.75rem; border-radius: 16px; font-weight: 500;
      font-family: inherit; transition: all 0.15s;
    }
    .type-tab:hover { border-color: #94a3b8; color: #374151; }
    .type-tab.active { background: #3b82f6; border-color: #3b82f6; color: #fff; }

    .search-bar { margin-bottom: 1rem; }
    .search-input {
      width: 100%; max-width: 400px; padding: 0.5rem 0.75rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 6px;
      color: #1e293b; font-size: 0.8125rem; outline: none; font-family: inherit;
    }
    .search-input:focus { border-color: #3b82f6; }

    .loading-state {
      text-align: center; padding: 48px 24px; color: #64748b; font-size: 15px;
      background: #fff; border-radius: 8px; border: 1px solid #e2e8f0;
    }

    .table-container { overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
    .data-table th {
      padding: 0.75rem 1rem; text-align: left; font-size: 0.75rem;
      color: #64748b; border-bottom: 1px solid #f1f5f9; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .data-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f1f5f9; color: #374151; }
    .data-table tbody tr:hover { background: #f8fafc; }

    .def-name { color: #3b82f6; text-decoration: none; font-weight: 500; cursor: pointer; }
    .def-name:hover { text-decoration: underline; }
    .def-desc { font-size: 0.6875rem; color: #64748b; margin-top: 2px; }

    .wf-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 22px; height: 22px; border-radius: 4px; font-size: 0.75rem;
      margin-right: 6px; vertical-align: middle;
    }
    .type-icon-DEPLOYMENT { background: #ecfdf5; color: #059669; }
    .type-icon-STACK { background: #fef3c7; color: #d97706; }

    .type-badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.625rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.03em;
    }
    .type-DEPLOYMENT { background: #ecfdf5; color: #059669; }
    .type-STACK { background: #fef3c7; color: #d97706; }

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

    .empty-row { text-align: center; color: #94a3b8; padding: 2rem !important; }
  `],
})
export class WorkflowTemplateListComponent implements OnInit {
  private workflowService = inject(WorkflowService);
  private router = inject(Router);

  private templates = signal<WorkflowDefinition[]>([]);
  loading = signal(false);
  searchQuery = signal('');
  activeTypeTab = signal<WorkflowType | null>(null);

  typeTabs: { label: string; value: WorkflowType | null }[] = [
    { label: 'All', value: null },
    { label: 'Deployment', value: 'DEPLOYMENT' },
    { label: 'Stack', value: 'STACK' },
  ];

  filteredTemplates = computed(() => {
    const q = this.searchQuery().toLowerCase();
    const type = this.activeTypeTab();
    let tpls = this.templates();
    if (type) {
      tpls = tpls.filter(t => t.workflowType === type);
    }
    if (q) {
      tpls = tpls.filter(t => t.name.toLowerCase().includes(q) || t.description?.toLowerCase().includes(q));
    }
    return tpls;
  });

  ngOnInit(): void {
    this.loadTemplates();
  }

  setTypeTab(type: WorkflowType | null): void {
    this.activeTypeTab.set(type);
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.workflowService.listTemplates().subscribe({
      next: tpls => { this.templates.set(tpls); this.loading.set(false); },
      error: () => this.loading.set(false),
    });
  }

  editTemplate(id: string): void {
    this.router.navigate(['/provider/templates', id, 'edit']);
  }

  clone(id: string): void {
    this.workflowService.cloneDefinition(id).subscribe(() => this.loadTemplates());
  }

  typeIcon(type: WorkflowType): string {
    switch (type) {
      case 'DEPLOYMENT': return '\u25B6';  // ▶
      case 'STACK': return '\u25A6';       // ▦
      default: return '\u25C7';            // ◇
    }
  }
}
