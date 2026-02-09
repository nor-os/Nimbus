/**
 * Overview: Node execution panel — side panel showing node input/output/error/duration/attempts.
 * Architecture: Detail panel for individual node execution (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Node execution details, input/output inspection, error display
 */
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { WorkflowNodeExecution } from '@shared/models/workflow.model';

@Component({
  selector: 'nimbus-node-execution-panel',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="node-exec-panel">
      <div class="panel-header">
        <h3>{{ nodeExecution.nodeType }} — {{ nodeExecution.nodeId }}</h3>
        <span class="status-badge" [class]="'status-' + nodeExecution.status">
          {{ nodeExecution.status }}
        </span>
      </div>

      <div class="panel-body">
        <div class="detail-row">
          <label>Attempt</label>
          <span>{{ nodeExecution.attempt }}</span>
        </div>
        @if (nodeExecution.startedAt) {
          <div class="detail-row">
            <label>Started</label>
            <span>{{ nodeExecution.startedAt | date:'medium' }}</span>
          </div>
        }
        @if (nodeExecution.completedAt) {
          <div class="detail-row">
            <label>Completed</label>
            <span>{{ nodeExecution.completedAt | date:'medium' }}</span>
          </div>
        }
        @if (nodeExecution.error) {
          <div class="detail-section error-section">
            <label>Error</label>
            <pre class="json-view error-text">{{ nodeExecution.error }}</pre>
          </div>
        }
        @if (nodeExecution.input) {
          <div class="detail-section">
            <label>Input</label>
            <pre class="json-view">{{ nodeExecution.input | json }}</pre>
          </div>
        }
        @if (nodeExecution.output) {
          <div class="detail-section">
            <label>Output</label>
            <pre class="json-view">{{ nodeExecution.output | json }}</pre>
          </div>
        }
      </div>
    </div>
  `,
  styles: [`
    .node-exec-panel {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-top: 1rem;
    }
    .panel-header {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.75rem 1rem; border-bottom: 1px solid #f1f5f9;
    }
    .panel-header h3 { margin: 0; font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .status-badge { padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem; font-weight: 600; }
    .status-RUNNING { background: #dbeafe; color: #2563eb; }
    .status-COMPLETED { background: #dcfce7; color: #16a34a; }
    .status-FAILED { background: #fef2f2; color: #dc2626; }
    .status-PENDING { background: #f1f5f9; color: #64748b; }
    .status-SKIPPED { background: #fefce8; color: #ca8a04; }
    .panel-body { padding: 0.75rem 1rem; }
    .detail-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.8125rem; }
    .detail-row label { color: #64748b; }
    .detail-row span { color: #1e293b; }
    .detail-section { margin-top: 12px; }
    .detail-section label { display: block; font-size: 0.75rem; color: #64748b; margin-bottom: 4px; }
    .json-view {
      background: #f8fafc; padding: 8px 12px; border-radius: 6px; border: 1px solid #e2e8f0;
      color: #374151; font-size: 0.75rem; overflow-x: auto; max-height: 200px;
      margin: 0;
    }
    .error-section { border-left: 3px solid #dc2626; padding-left: 12px; }
    .error-text { color: #dc2626; }
  `],
})
export class NodeExecutionPanelComponent {
  @Input() nodeExecution!: WorkflowNodeExecution;
}
