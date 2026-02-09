/**
 * Overview: Custom Rete.js node rendering component with icon, label, ports, and status indicator.
 * Architecture: Visual node component for workflow canvas (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Node rendering, port visualization, status indicators
 */
import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'nimbus-custom-node',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="workflow-node" [class]="'node-' + nodeType" [class.selected]="selected">
      <div class="node-header">
        <span class="node-icon" [innerHTML]="icon"></span>
        <span class="node-label">{{ label }}</span>
        <span class="node-status" *ngIf="status" [class]="'status-' + status"></span>
      </div>
      <div class="node-ports">
        <div class="input-ports">
          <div class="port input-port" *ngFor="let port of inputPorts">
            <span class="port-dot"></span>
            <span class="port-label">{{ port }}</span>
          </div>
        </div>
        <div class="output-ports">
          <div class="port output-port" *ngFor="let port of outputPorts">
            <span class="port-label">{{ port }}</span>
            <span class="port-dot"></span>
          </div>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .workflow-node {
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 8px;
      min-width: 160px;
      font-size: 0.8125rem;
      box-shadow: 0 2px 8px rgba(0,0,0,0.3);
      transition: border-color 0.15s;
    }
    .workflow-node.selected { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.3); }
    .node-header {
      display: flex; align-items: center; gap: 6px;
      padding: 8px 12px; border-bottom: 1px solid #334155;
      background: rgba(255,255,255,0.03); border-radius: 8px 8px 0 0;
    }
    .node-icon { font-size: 1rem; }
    .node-label { font-weight: 500; color: #e2e8f0; flex: 1; }
    .node-status {
      width: 8px; height: 8px; border-radius: 50%;
    }
    .status-RUNNING { background: #3b82f6; animation: pulse 1.5s infinite; }
    .status-COMPLETED { background: #22c55e; }
    .status-FAILED { background: #ef4444; }
    .status-PENDING { background: #6b7280; }
    .status-SKIPPED { background: #eab308; }
    .node-ports { padding: 8px 0; display: flex; justify-content: space-between; }
    .input-ports, .output-ports { display: flex; flex-direction: column; gap: 4px; }
    .output-ports { align-items: flex-end; }
    .port { display: flex; align-items: center; gap: 4px; padding: 2px 8px; }
    .port-dot {
      width: 10px; height: 10px; border-radius: 50%;
      background: #475569; border: 2px solid #64748b;
    }
    .port-label { color: #94a3b8; font-size: 0.6875rem; }
    @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
  `],
})
export class CustomNodeComponent {
  @Input() label = '';
  @Input() icon = '';
  @Input() nodeType = '';
  @Input() selected = false;
  @Input() status = '';
  @Input() inputPorts: string[] = [];
  @Input() outputPorts: string[] = [];
}
