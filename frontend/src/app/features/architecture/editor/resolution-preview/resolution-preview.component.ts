/**
 * Overview: Resolution preview — shows deployment order and per-stack parameter resolution status.
 * Architecture: Dialog/panel for parameter resolution preview (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Deployment order groups, resolved vs unresolved parameters, source badges
 */
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ResolutionPreview, StackResolution, ResolvedParameter } from '@shared/models/architecture.model';

@Component({
  selector: 'nimbus-resolution-preview',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="resolution-overlay" (click)="close.emit()">
      <div class="resolution-panel" (click)="$event.stopPropagation()">
        <div class="panel-header">
          <h3>Resolution Preview</h3>
          <button class="close-btn" (click)="close.emit()">&times;</button>
        </div>

        @if (preview) {
          <div class="summary-bar" [class.complete]="preview.allComplete" [class.incomplete]="!preview.allComplete">
            @if (preview.allComplete) {
              <span>All parameters resolved</span>
            } @else {
              <span>{{ preview.totalUnresolved }} unresolved required parameter(s)</span>
            }
          </div>

          <!-- Deployment Order -->
          @if (preview.deploymentOrder.length > 0) {
            <div class="section">
              <div class="section-title">Deployment Order</div>
              <div class="deployment-groups">
                @for (group of preview.deploymentOrder; track $index) {
                  <div class="deploy-group">
                    <span class="group-number">{{ $index + 1 }}</span>
                    <span class="group-stacks">
                      @for (sid of group; track sid) {
                        <span class="stack-chip">{{ getStackLabel(sid) }}</span>
                        @if (!$last) { <span class="stack-sep">,</span> }
                      }
                    </span>
                  </div>
                }
              </div>
            </div>
          }

          <!-- Per-Stack Details -->
          @for (stack of preview.stacks; track stack.stackId) {
            <div class="section">
              <div class="stack-header" [class.incomplete]="!stack.isComplete">
                <span class="stack-name">{{ stack.stackLabel }}</span>
                @if (stack.isComplete) {
                  <span class="status-chip complete">Complete</span>
                } @else {
                  <span class="status-chip incomplete">{{ stack.unresolvedCount }} unresolved</span>
                }
              </div>
              <table class="param-table">
                <thead>
                  <tr>
                    <th>Parameter</th>
                    <th>Value</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  @for (param of stack.parameters; track param.name) {
                    <tr [class.unresolved]="param.source === 'unresolved' && param.isRequired">
                      <td class="param-name">
                        {{ param.displayName }}
                        @if (param.isRequired) { <span class="req">*</span> }
                      </td>
                      <td class="param-value">
                        @if (param.source === 'unresolved') {
                          <span class="no-value">-</span>
                        } @else {
                          {{ formatValue(param.value) }}
                        }
                      </td>
                      <td>
                        <span class="source-badge" [class]="'source-' + param.source">
                          {{ formatSource(param.source) }}
                        </span>
                        @if (param.tagKey) {
                          <span class="tag-key">{{ param.tagKey }}</span>
                        }
                      </td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }

          @if (preview.stacks.length === 0) {
            <div class="empty-state">No stacks in this topology</div>
          }
        } @else {
          <div class="loading">Loading resolution preview...</div>
        }
      </div>
    </div>
  `,
  styles: [`
    .resolution-overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0, 0, 0, 0.3);
      z-index: 1000;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .resolution-panel {
      background: #fff;
      border-radius: 12px;
      width: 700px;
      max-height: 80vh;
      overflow-y: auto;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
    }
    .panel-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px 20px;
      border-bottom: 1px solid #e2e8f0;
    }
    .panel-header h3 {
      margin: 0;
      font-size: 1rem;
      font-weight: 600;
      color: #1e293b;
    }
    .close-btn {
      width: 28px;
      height: 28px;
      border: none;
      background: none;
      font-size: 1.25rem;
      color: #94a3b8;
      cursor: pointer;
      border-radius: 6px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    .close-btn:hover { background: #f1f5f9; color: #64748b; }
    .summary-bar {
      padding: 10px 20px;
      font-size: 0.8125rem;
      font-weight: 500;
    }
    .summary-bar.complete { background: #f0fdf4; color: #166534; }
    .summary-bar.incomplete { background: #fef2f2; color: #991b1b; }
    .section {
      padding: 12px 20px;
      border-bottom: 1px solid #f1f5f9;
    }
    .section:last-child { border-bottom: none; }
    .section-title {
      font-size: 0.6875rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: #64748b;
      margin-bottom: 8px;
    }
    .deployment-groups { display: flex; flex-direction: column; gap: 6px; }
    .deploy-group { display: flex; align-items: center; gap: 8px; }
    .group-number {
      width: 22px;
      height: 22px;
      border-radius: 50%;
      background: #dbeafe;
      color: #2563eb;
      font-size: 0.6875rem;
      font-weight: 700;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .stack-chip {
      padding: 2px 8px;
      background: #f1f5f9;
      border-radius: 4px;
      font-size: 0.75rem;
      color: #374151;
    }
    .stack-sep { color: #94a3b8; }
    .stack-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 8px;
    }
    .stack-name {
      font-size: 0.875rem;
      font-weight: 600;
      color: #1e293b;
    }
    .status-chip {
      padding: 2px 8px;
      border-radius: 12px;
      font-size: 0.6875rem;
      font-weight: 600;
    }
    .status-chip.complete { background: #d1fae5; color: #065f46; }
    .status-chip.incomplete { background: #fee2e2; color: #991b1b; }
    .param-table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.75rem;
    }
    .param-table th {
      text-align: left;
      padding: 4px 8px;
      font-weight: 600;
      color: #64748b;
      border-bottom: 1px solid #e2e8f0;
    }
    .param-table td {
      padding: 4px 8px;
      color: #374151;
      border-bottom: 1px solid #f8fafc;
    }
    .param-table tr.unresolved td { background: #fef2f2; }
    .param-name { font-weight: 500; }
    .req { color: #dc2626; }
    .param-value { font-family: monospace; font-size: 0.6875rem; }
    .no-value { color: #dc2626; font-style: italic; }
    .source-badge {
      padding: 1px 6px;
      border-radius: 4px;
      font-size: 0.625rem;
      font-weight: 600;
      text-transform: uppercase;
    }
    .source-explicit { background: #dbeafe; color: #2563eb; }
    .source-tag_ref { background: #fef3c7; color: #92400e; }
    .source-compartment_default { background: #ede9fe; color: #7c3aed; }
    .source-blueprint_default { background: #f1f5f9; color: #64748b; }
    .source-unresolved { background: #fee2e2; color: #991b1b; }
    .tag-key {
      margin-left: 4px;
      font-size: 0.625rem;
      color: #92400e;
      font-family: monospace;
    }
    .empty-state, .loading {
      padding: 32px 20px;
      text-align: center;
      font-size: 0.8125rem;
      color: #94a3b8;
    }
  `],
})
export class ResolutionPreviewComponent {
  @Input() preview: ResolutionPreview | null = null;

  @Output() close = new EventEmitter<void>();

  getStackLabel(stackId: string): string {
    const stack = this.preview?.stacks.find(s => s.stackId === stackId);
    return stack?.stackLabel || stackId;
  }

  formatValue(value: unknown): string {
    if (value === null || value === undefined) return '(none)';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  formatSource(source: string): string {
    const labels: Record<string, string> = {
      explicit: 'Explicit',
      tag_ref: 'Tag',
      compartment_default: 'Compartment',
      blueprint_default: 'Default',
      unresolved: 'Unresolved',
    };
    return labels[source] || source;
  }
}
