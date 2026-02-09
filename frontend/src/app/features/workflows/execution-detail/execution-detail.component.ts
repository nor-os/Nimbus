/**
 * Overview: Execution detail — read-only canvas with node status overlay and auto-refresh polling.
 * Architecture: Execution monitoring page (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, workflow.service
 * Concepts: Execution monitoring, node status overlay, auto-refresh, cancel action
 */
import { Component, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { WorkflowService } from '@core/services/workflow.service';
import { WorkflowExecution, WorkflowNodeExecution } from '@shared/models/workflow.model';
import { NodeExecutionPanelComponent } from './node-execution-panel.component';
import { LayoutComponent } from '@shared/components/layout/layout.component';

@Component({
  selector: 'nimbus-execution-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, NodeExecutionPanelComponent, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="page-container">
      @if (execution()) {
        <div class="page-header">
          <div class="header-left">
            <a routerLink="/workflows/executions" class="back-link">&larr; Back</a>
            <h1>Execution {{ execution()!.id | slice:0:8 }}...</h1>
            <span class="status-badge" [class]="'status-' + execution()!.status">
              {{ execution()!.status }}
            </span>
            @if (execution()!.isTest) {
              <span class="test-badge">TEST</span>
            }
          </div>
          <div class="header-actions">
            @if (execution()!.status === 'RUNNING' || execution()!.status === 'PENDING') {
              <button class="btn btn-danger" (click)="cancel()">Cancel</button>
            }
            @if (execution()!.status === 'FAILED') {
              <button class="btn btn-primary" (click)="retry()">Retry</button>
            }
          </div>
        </div>

        <div class="detail-grid">
          <div class="detail-item">
            <label>Definition Version</label>
            <span>v{{ execution()!.definitionVersion }}</span>
          </div>
          <div class="detail-item">
            <label>Started At</label>
            <span>{{ execution()!.startedAt | date:'medium' }}</span>
          </div>
          <div class="detail-item">
            <label>Completed At</label>
            <span>{{ execution()!.completedAt ? (execution()!.completedAt | date:'medium') : '-' }}</span>
          </div>
          @if (execution()!.error) {
            <div class="detail-item error-item">
              <label>Error</label>
              <span>{{ execution()!.error }}</span>
            </div>
          }
        </div>

        <div class="node-executions">
          <h2>Node Executions</h2>
          <div class="node-list">
            @for (ne of execution()!.nodeExecutions; track ne.id) {
              <button
                class="node-exec-card"
                [class]="'ne-status-' + ne.status"
                [class.selected]="selectedNodeExec()?.id === ne.id"
                (click)="selectNodeExec(ne)"
              >
                <span class="ne-type">{{ ne.nodeType }}</span>
                <span class="ne-id">{{ ne.nodeId }}</span>
                <span class="ne-status-badge">{{ ne.status }}</span>
              </button>
            } @empty {
              <p class="empty">No node executions yet</p>
            }
          </div>
        </div>

        @if (selectedNodeExec()) {
          <nimbus-node-execution-panel [nodeExecution]="selectedNodeExec()!" />
        }
      } @else {
        <div class="loading">Loading...</div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .header-left { display: flex; align-items: center; gap: 12px; }
    .back-link { color: #64748b; text-decoration: none; font-size: 0.8125rem; }
    .back-link:hover { color: #3b82f6; }
    h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .status-badge { padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .status-PENDING { background: #f1f5f9; color: #64748b; }
    .status-RUNNING { background: #dbeafe; color: #2563eb; }
    .status-COMPLETED { background: #dcfce7; color: #16a34a; }
    .status-FAILED { background: #fef2f2; color: #dc2626; }
    .status-CANCELLED { background: #fefce8; color: #ca8a04; }
    .test-badge { padding: 0.125rem 0.5rem; background: #f3e8ff; color: #7c3aed; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .btn {
      padding: 6px 14px; border: 1px solid #e2e8f0; background: #fff;
      color: #1e293b; border-radius: 6px; cursor: pointer; font-size: 0.8125rem;
      transition: background 0.15s;
    }
    .btn:hover { background: #f8fafc; }
    .btn-primary { border-color: #3b82f6; background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-danger { border-color: #fecaca; color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; }
    .detail-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin-bottom: 1.5rem; }
    .detail-item { background: #fff; padding: 0.75rem 1rem; border-radius: 8px; border: 1px solid #e2e8f0; }
    .detail-item label { display: block; font-size: 0.6875rem; color: #64748b; margin-bottom: 2px; }
    .detail-item span { color: #1e293b; font-size: 0.8125rem; }
    .error-item { border-color: #fecaca; }
    .error-item span { color: #dc2626; }
    h2 { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 12px; }
    .node-list { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 1rem; }
    .node-exec-card {
      padding: 8px 12px; border: 1px solid #e2e8f0; background: #fff;
      border-radius: 8px; cursor: pointer; text-align: left;
      display: flex; flex-direction: column; gap: 2px; min-width: 140px;
      transition: border-color 0.15s;
    }
    .node-exec-card:hover { border-color: #cbd5e1; }
    .node-exec-card.selected { border-color: #3b82f6; background: #eff6ff; }
    .ne-type { font-size: 0.8125rem; color: #1e293b; font-weight: 500; }
    .ne-id { font-size: 0.625rem; color: #64748b; font-family: monospace; }
    .ne-status-badge { font-size: 0.6875rem; font-weight: 600; }
    .ne-status-RUNNING .ne-status-badge { color: #2563eb; }
    .ne-status-COMPLETED .ne-status-badge { color: #16a34a; }
    .ne-status-FAILED .ne-status-badge { color: #dc2626; }
    .ne-status-PENDING .ne-status-badge { color: #64748b; }
    .ne-status-SKIPPED .ne-status-badge { color: #ca8a04; }
    .empty { color: #94a3b8; font-size: 0.8125rem; }
    .loading { color: #94a3b8; text-align: center; padding: 3rem; }
  `],
})
export class ExecutionDetailComponent implements OnInit, OnDestroy {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private workflowService = inject(WorkflowService);

  execution = signal<WorkflowExecution | null>(null);
  selectedNodeExec = signal<WorkflowNodeExecution | null>(null);
  private pollInterval: any = null;

  ngOnInit(): void {
    this.loadExecution();

    // Auto-refresh for running executions (5s polling)
    this.pollInterval = setInterval(() => {
      const exec = this.execution();
      if (exec && (exec.status === 'RUNNING' || exec.status === 'PENDING')) {
        this.loadExecution();
      }
    }, 5000);
  }

  ngOnDestroy(): void {
    if (this.pollInterval) clearInterval(this.pollInterval);
  }

  loadExecution(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.workflowService.getExecution(id).subscribe(e => this.execution.set(e));
    }
  }

  selectNodeExec(ne: WorkflowNodeExecution): void {
    this.selectedNodeExec.set(ne);
  }

  cancel(): void {
    const exec = this.execution();
    if (exec) {
      this.workflowService.cancelExecution(exec.id).subscribe(e => this.execution.set(e));
    }
  }

  retry(): void {
    const exec = this.execution();
    if (exec) {
      this.workflowService.retryExecution(exec.id).subscribe(newExec => {
        this.router.navigate(['/workflows/executions', newExec.id]);
      });
    }
  }
}
