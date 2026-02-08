/**
 * Overview: Audit log detail panel with taxonomy fields, request context, diff viewer, and trace button.
 * Architecture: Feature component for audit detail view (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Audit detail, value diff, trace linking, request context, event taxonomy
 */
import { Component, input, output, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditLog } from '@shared/models/audit.model';

@Component({
  selector: 'nimbus-audit-detail',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (entry(); as log) {
      <div class="detail-panel">
        <div class="detail-header">
          <h3>Audit Entry</h3>
          <button class="close-btn" (click)="closed.emit()">&times;</button>
        </div>

        <div class="detail-body">
          <div class="field">
            <span class="label">ID</span>
            <span class="value mono">{{ log.id }}</span>
          </div>
          <div class="field">
            <span class="label">Timestamp</span>
            <span class="value">{{ log.created_at | date: 'medium' }}</span>
          </div>
          @if (log.event_type) {
            <div class="field">
              <span class="label">Event Type</span>
              <span class="value">
                <span class="event-badge">{{ log.event_type }}</span>
              </span>
            </div>
          }
          @if (log.event_category) {
            <div class="field">
              <span class="label">Category</span>
              <span class="value">
                <span class="cat-badge" [class]="'cat-' + log.event_category.toLowerCase()">{{ log.event_category }}</span>
              </span>
            </div>
          }
          <div class="field">
            <span class="label">Action</span>
            <span class="value">
              <span class="badge" [class]="'badge-' + log.action.toLowerCase()">{{ log.action }}</span>
            </span>
          </div>
          <div class="field">
            <span class="label">Priority</span>
            <span class="value">
              <span class="priority" [class]="'priority-' + log.priority.toLowerCase()">{{ log.priority }}</span>
            </span>
          </div>
          <div class="field">
            <span class="label">Actor</span>
            <span class="value">{{ log.actor_email || '\u2014' }}</span>
          </div>
          @if (log.actor_type) {
            <div class="field">
              <span class="label">Actor Type</span>
              <span class="value">{{ log.actor_type }}</span>
            </div>
          }
          <div class="field">
            <span class="label">Actor IP</span>
            <span class="value mono">{{ log.actor_ip || '\u2014' }}</span>
          </div>
          @if (log.impersonator_id) {
            <div class="field">
              <span class="label">Impersonator</span>
              <span class="value mono">{{ log.impersonator_id }}</span>
            </div>
          }
          <div class="field">
            <span class="label">Resource</span>
            <span class="value">{{ log.resource_type || '\u2014' }} / {{ log.resource_id || '\u2014' }}</span>
          </div>
          <div class="field">
            <span class="label">Resource Name</span>
            <span class="value">{{ log.resource_name || '\u2014' }}</span>
          </div>

          <!-- Request Context -->
          @if (log.request_method || log.request_path || log.response_status || log.user_agent) {
            <div class="section-divider">Request Context</div>
            @if (log.request_method) {
              <div class="field">
                <span class="label">Method</span>
                <span class="value mono">{{ log.request_method }}</span>
              </div>
            }
            @if (log.request_path) {
              <div class="field">
                <span class="label">Path</span>
                <span class="value mono">{{ log.request_path }}</span>
              </div>
            }
            @if (log.response_status) {
              <div class="field">
                <span class="label">Status</span>
                <span class="value">
                  <span class="status-code" [class.status-ok]="log.response_status < 400" [class.status-err]="log.response_status >= 400">
                    {{ log.response_status }}
                  </span>
                </span>
              </div>
            }
            @if (log.user_agent) {
              <div class="field">
                <span class="label">User Agent</span>
                <span class="value small">{{ log.user_agent }}</span>
              </div>
            }
          }

          @if (log.trace_id) {
            <div class="field">
              <span class="label">Trace ID</span>
              <span class="value mono clickable" (click)="traceClicked.emit(log.trace_id!)">{{ log.trace_id }}</span>
            </div>
            <button class="show-trace-btn" (click)="showTraceClicked.emit(log.trace_id!)">
              Show Full Trace
            </button>
          }
          <div class="field">
            <span class="label">Hash</span>
            <span class="value mono small">{{ log.hash || '\u2014' }}</span>
          </div>

          <!-- Diff Viewer for old/new values -->
          @if (log.old_values || log.new_values) {
            <div class="diff-section">
              <h4>Changes</h4>
              <div class="diff-container">
                @if (log.old_values) {
                  <div class="diff-col">
                    <div class="diff-col-header old">Old Values</div>
                    @for (key of diffKeys(); track key) {
                      <div class="diff-row" [class.changed]="isKeyChanged(key)">
                        <span class="diff-key">{{ key }}:</span>
                        <span class="diff-val">{{ getOldValue(key) }}</span>
                      </div>
                    }
                  </div>
                }
                @if (log.new_values) {
                  <div class="diff-col">
                    <div class="diff-col-header new">New Values</div>
                    @for (key of diffKeys(); track key) {
                      <div class="diff-row" [class.changed]="isKeyChanged(key)">
                        <span class="diff-key">{{ key }}:</span>
                        <span class="diff-val">{{ getNewValue(key) }}</span>
                      </div>
                    }
                  </div>
                }
              </div>
            </div>
          }

          @if (log.request_body) {
            <div class="values-section">
              <h4 class="collapsible" (click)="showRequestBody = !showRequestBody">
                Request Body {{ showRequestBody ? '\u25B4' : '\u25BE' }}
              </h4>
              @if (showRequestBody) {
                <pre class="json-block">{{ log.request_body | json }}</pre>
              }
            </div>
          }

          @if (log.response_body) {
            <div class="values-section">
              <h4 class="collapsible" (click)="showResponseBody = !showResponseBody">
                Response Body {{ showResponseBody ? '\u25B4' : '\u25BE' }}
              </h4>
              @if (showResponseBody) {
                <pre class="json-block">{{ log.response_body | json }}</pre>
              }
            </div>
          }

          @if (log.metadata) {
            <div class="values-section">
              <h4>Metadata</h4>
              <pre class="json-block">{{ log.metadata | json }}</pre>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [`
    .detail-panel {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden;
    }
    .detail-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem; border-bottom: 1px solid #f1f5f9;
    }
    .detail-header h3 { margin: 0; font-size: 1rem; font-weight: 600; color: #1e293b; }
    .close-btn {
      background: none; border: none; font-size: 1.25rem; color: #64748b;
      cursor: pointer; padding: 0 0.25rem;
    }
    .close-btn:hover { color: #1e293b; }
    .detail-body { padding: 1rem; }
    .field {
      display: flex; gap: 0.75rem; padding: 0.375rem 0;
      border-bottom: 1px solid #f8fafc; font-size: 0.8125rem;
    }
    .label { color: #64748b; min-width: 110px; font-weight: 500; flex-shrink: 0; }
    .value { color: #1e293b; word-break: break-all; }
    .mono { font-family: monospace; font-size: 0.75rem; }
    .small { font-size: 0.6875rem; }
    .clickable { color: #3b82f6; cursor: pointer; text-decoration: underline; }
    .clickable:hover { color: #2563eb; }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 600; text-transform: uppercase;
      background: #f1f5f9; color: #475569;
    }
    .badge-create { background: #dcfce7; color: #16a34a; }
    .badge-update { background: #fef3c7; color: #d97706; }
    .badge-delete { background: #fef2f2; color: #dc2626; }
    .badge-login { background: #dbeafe; color: #2563eb; }
    .badge-logout { background: #e0e7ff; color: #4f46e5; }
    .badge-permission_change { background: #fae8ff; color: #a855f7; }
    .badge-impersonate { background: #fff7ed; color: #ea580c; }
    .badge-override { background: #fef2f2; color: #dc2626; }
    .event-badge {
      font-family: monospace; font-size: 0.75rem; background: #f0fdf4;
      color: #16a34a; padding: 0.125rem 0.5rem; border-radius: 6px;
    }
    .cat-badge {
      padding: 0.125rem 0.5rem; border-radius: 4px;
      font-size: 0.6875rem; font-weight: 600; color: #fff;
    }
    .cat-api { background: #60a5fa; }
    .cat-auth { background: #818cf8; }
    .cat-data { background: #34d399; }
    .cat-permission { background: #f472b6; }
    .cat-system { background: #94a3b8; }
    .cat-security { background: #f87171; }
    .cat-tenant { background: #fbbf24; }
    .cat-user { background: #a78bfa; }
    .priority { font-size: 0.6875rem; font-weight: 600; }
    .priority-debug { color: #94a3b8; }
    .priority-info { color: #3b82f6; }
    .priority-warn { color: #f59e0b; }
    .priority-err { color: #dc2626; }
    .priority-critical { color: #dc2626; font-weight: 800; }
    .section-divider {
      margin-top: 0.75rem; padding: 0.375rem 0; font-size: 0.75rem;
      font-weight: 600; color: #64748b; text-transform: uppercase;
      letter-spacing: 0.05em; border-top: 1px solid #e2e8f0;
    }
    .status-code { font-weight: 600; font-family: monospace; }
    .status-ok { color: #16a34a; }
    .status-err { color: #dc2626; }
    .show-trace-btn {
      margin: 0.5rem 0; padding: 0.375rem 0.75rem; background: #eff6ff;
      border: 1px solid #bfdbfe; border-radius: 6px; color: #1d4ed8;
      font-size: 0.8125rem; font-weight: 500; cursor: pointer; font-family: inherit;
    }
    .show-trace-btn:hover { background: #dbeafe; }
    .diff-section { margin-top: 1rem; }
    .diff-section h4 { margin: 0 0 0.5rem; font-size: 0.8125rem; font-weight: 600; color: #475569; }
    .diff-container { display: flex; gap: 0.5rem; }
    .diff-col { flex: 1; min-width: 0; }
    .diff-col-header {
      font-size: 0.6875rem; font-weight: 600; padding: 0.25rem 0.5rem;
      border-radius: 4px 4px 0 0;
    }
    .diff-col-header.old { background: #fef2f2; color: #dc2626; }
    .diff-col-header.new { background: #f0fdf4; color: #16a34a; }
    .diff-row {
      padding: 0.125rem 0.5rem; font-size: 0.75rem; font-family: monospace;
      border-bottom: 1px solid #f8fafc;
    }
    .diff-row.changed { background: #fffbeb; }
    .diff-key { color: #64748b; }
    .diff-val { color: #1e293b; margin-left: 0.25rem; }
    .values-section { margin-top: 1rem; }
    .values-section h4 { margin: 0 0 0.5rem; font-size: 0.8125rem; font-weight: 600; color: #475569; }
    .collapsible { cursor: pointer; user-select: none; }
    .collapsible:hover { color: #3b82f6; }
    .json-block {
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px;
      padding: 0.75rem; font-size: 0.75rem; font-family: monospace;
      overflow-x: auto; max-height: 200px; white-space: pre-wrap; word-break: break-all;
    }
  `],
})
export class AuditDetailComponent {
  entry = input<AuditLog | null>(null);
  closed = output<void>();
  traceClicked = output<string>();
  showTraceClicked = output<string>();

  showRequestBody = false;
  showResponseBody = false;

  diffKeys = computed(() => {
    const log = this.entry();
    if (!log) return [];
    const keys = new Set<string>();
    if (log.old_values) Object.keys(log.old_values).forEach(k => keys.add(k));
    if (log.new_values) Object.keys(log.new_values).forEach(k => keys.add(k));
    return Array.from(keys).sort();
  });

  isKeyChanged(key: string): boolean {
    const log = this.entry();
    if (!log) return false;
    const oldVal = log.old_values?.[key];
    const newVal = log.new_values?.[key];
    return JSON.stringify(oldVal) !== JSON.stringify(newVal);
  }

  getOldValue(key: string): string {
    const val = this.entry()?.old_values?.[key];
    return val !== undefined ? String(val) : '\u2014';
  }

  getNewValue(key: string): string {
    const val = this.entry()?.new_values?.[key];
    return val !== undefined ? String(val) : '\u2014';
  }
}
