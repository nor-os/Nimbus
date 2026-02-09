/**
 * Overview: Workflow execution list — table with status filters and execution details.
 * Architecture: List page for workflow executions (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Execution listing, status filtering, execution monitoring
 */
import { Component, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowExecution } from '@shared/models/workflow.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-execution-list',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page-container">
      <div class="page-header">
        <h1>Workflow Executions</h1>
      </div>

      <div class="tabs">
        @for (tab of statusTabs; track tab.value) {
          <button class="tab" [class.active]="activeTab() === tab.value" (click)="setTab(tab.value)">
            {{ tab.label }}
          </button>
        }
      </div>

      <div class="table-container">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Status</th>
              <th>Version</th>
              <th>Started By</th>
              <th>Started At</th>
              <th>Duration</th>
              <th>Test</th>
            </tr>
          </thead>
          <tbody>
            @for (exec of executions(); track exec.id) {
              <tr>
                <td>
                  <a [routerLink]="['/workflows/executions', exec.id]" class="exec-link">
                    {{ exec.id | slice:0:8 }}...
                  </a>
                </td>
                <td>
                  <span class="status-badge" [class]="'status-' + exec.status">
                    {{ exec.status }}
                  </span>
                </td>
                <td>v{{ exec.definitionVersion }}</td>
                <td>{{ exec.startedBy | slice:0:8 }}...</td>
                <td>{{ exec.startedAt | date:'short' }}</td>
                <td>{{ getDuration(exec) }}</td>
                <td>{{ exec.isTest ? 'Yes' : '' }}</td>
              </tr>
            } @empty {
              <tr><td colspan="7" class="empty-row">No executions found</td></tr>
            }
          </tbody>
        </table>
      </div>
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; }
    .page-header { margin-bottom: 1.5rem; }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .tabs { display: flex; gap: 4px; margin-bottom: 1rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; }
    .tab {
      padding: 6px 12px; border: none; background: none; color: #64748b;
      cursor: pointer; font-size: 0.8125rem; border-radius: 4px;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { background: #eff6ff; color: #3b82f6; font-weight: 500; }
    .table-container { overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; }
    .data-table { width: 100%; border-collapse: collapse; font-size: 0.8125rem; }
    .data-table th {
      padding: 0.75rem 1rem; text-align: left; font-size: 0.75rem;
      color: #64748b; border-bottom: 1px solid #f1f5f9; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .data-table td { padding: 0.75rem 1rem; border-bottom: 1px solid #f1f5f9; color: #374151; }
    .data-table tbody tr:hover { background: #f8fafc; }
    .exec-link { color: #3b82f6; text-decoration: none; font-family: monospace; }
    .exec-link:hover { text-decoration: underline; }
    .status-badge { padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .status-PENDING { background: #f1f5f9; color: #64748b; }
    .status-RUNNING { background: #dbeafe; color: #2563eb; }
    .status-COMPLETED { background: #dcfce7; color: #16a34a; }
    .status-FAILED { background: #fef2f2; color: #dc2626; }
    .status-CANCELLED { background: #fefce8; color: #ca8a04; }
    .empty-row { text-align: center; color: #94a3b8; padding: 2rem !important; }
  `],
})
export class ExecutionListComponent implements OnInit {
  private workflowService = inject(WorkflowService);

  executions = signal<WorkflowExecution[]>([]);
  activeTab = signal<string | null>(null);

  statusTabs = [
    { label: 'All', value: null as string | null },
    { label: 'Running', value: 'RUNNING' },
    { label: 'Completed', value: 'COMPLETED' },
    { label: 'Failed', value: 'FAILED' },
    { label: 'Cancelled', value: 'CANCELLED' },
  ];

  ngOnInit(): void {
    this.loadExecutions();
  }

  setTab(status: string | null): void {
    this.activeTab.set(status);
    this.loadExecutions();
  }

  loadExecutions(): void {
    const status = this.activeTab() ?? undefined;
    this.workflowService.listExecutions({ status }).subscribe(execs => this.executions.set(execs));
  }

  getDuration(exec: WorkflowExecution): string {
    if (!exec.completedAt) return exec.status === 'RUNNING' ? 'In progress' : '-';
    const start = new Date(exec.startedAt).getTime();
    const end = new Date(exec.completedAt).getTime();
    const seconds = Math.round((end - start) / 1000);
    if (seconds < 60) return `${seconds}s`;
    return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  }
}
