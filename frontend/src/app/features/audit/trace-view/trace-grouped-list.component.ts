/**
 * Overview: Grouped list view for trace events, organized by event category.
 * Architecture: Feature component for trace visualization (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/shared/models/audit.model
 * Concepts: Trace grouping, category headers, expandable details
 */
import { Component, input, output, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditLog } from '@shared/models/audit.model';

@Component({
  selector: 'nimbus-trace-grouped-list',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="grouped-container">
      @for (group of groups(); track group.category) {
        <div class="category-group">
          <div class="category-header">
            <span class="cat-badge" [style.background]="getCategoryColor(group.category)">
              {{ group.category }}
            </span>
            <span class="cat-count">{{ group.events.length }} event(s)</span>
          </div>
          @for (evt of group.events; track evt.id) {
            <div
              class="event-row"
              [class.selected]="selectedId() === evt.id"
              (click)="selectEvent.emit(evt.id)"
            >
              <div class="event-main">
                <span class="event-type">{{ evt.event_type || evt.action }}</span>
                <span class="event-time">{{ getRelativeTime(evt) }}</span>
              </div>
              @if (evt.resource_name || evt.resource_type) {
                <div class="event-resource">
                  {{ evt.resource_type }} {{ evt.resource_name ? '/ ' + evt.resource_name : '' }}
                </div>
              }
              @if (expandedId() === evt.id) {
                <div class="event-detail">
                  <div class="detail-field">
                    <span class="detail-label">Actor:</span>
                    {{ evt.actor_email || '\u2014' }}
                  </div>
                  @if (evt.old_values) {
                    <div class="detail-field">
                      <span class="detail-label">Old:</span>
                      <pre class="detail-json">{{ evt.old_values | json }}</pre>
                    </div>
                  }
                  @if (evt.new_values) {
                    <div class="detail-field">
                      <span class="detail-label">New:</span>
                      <pre class="detail-json">{{ evt.new_values | json }}</pre>
                    </div>
                  }
                </div>
              }
              <button class="expand-btn" (click)="toggleExpand(evt.id); $event.stopPropagation()">
                {{ expandedId() === evt.id ? 'Collapse' : 'Details' }}
              </button>
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .grouped-container { display: flex; flex-direction: column; gap: 0.75rem; }
    .category-group { }
    .category-header {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.375rem 0; border-bottom: 1px solid #e2e8f0;
    }
    .cat-badge {
      padding: 0.125rem 0.5rem; border-radius: 4px;
      font-size: 0.6875rem; font-weight: 600; color: #fff;
    }
    .cat-count { font-size: 0.75rem; color: #64748b; }
    .event-row {
      padding: 0.5rem 0.5rem 0.5rem 1rem;
      border-bottom: 1px solid #f8fafc; cursor: pointer;
      position: relative;
    }
    .event-row:hover { background: #f8fafc; }
    .event-row.selected { background: #eff6ff; }
    .event-main {
      display: flex; justify-content: space-between; align-items: center;
    }
    .event-type { font-size: 0.8125rem; font-weight: 500; color: #1e293b; }
    .event-time { font-size: 0.6875rem; color: #94a3b8; font-family: monospace; }
    .event-resource { font-size: 0.75rem; color: #64748b; margin-top: 0.125rem; }
    .event-detail {
      margin-top: 0.5rem; padding: 0.5rem; background: #f8fafc;
      border-radius: 6px; font-size: 0.75rem;
    }
    .detail-field { margin-bottom: 0.25rem; }
    .detail-label { font-weight: 600; color: #475569; }
    .detail-json {
      margin: 0.25rem 0 0; font-family: monospace; font-size: 0.6875rem;
      white-space: pre-wrap; word-break: break-all; max-height: 120px; overflow-y: auto;
    }
    .expand-btn {
      position: absolute; top: 0.5rem; right: 0.5rem;
      background: none; border: none; cursor: pointer;
      font-size: 0.6875rem; color: #3b82f6; font-family: inherit;
      padding: 0.125rem 0.375rem;
    }
    .expand-btn:hover { text-decoration: underline; }
  `],
})
export class TraceGroupedListComponent {
  events = input<AuditLog[]>([]);
  selectedId = input<string | null>(null);

  selectEvent = output<string>();
  expandedId = signal<string | null>(null);

  private categoryColors: Record<string, string> = {
    API: '#60a5fa',
    AUTH: '#818cf8',
    DATA: '#34d399',
    PERMISSION: '#f472b6',
    SYSTEM: '#94a3b8',
    SECURITY: '#f87171',
    TENANT: '#fbbf24',
    USER: '#a78bfa',
  };

  private traceStartTime = computed(() => {
    const evts = this.events();
    if (evts.length === 0) return 0;
    return Math.min(...evts.map(e => new Date(e.created_at).getTime()));
  });

  groups = computed(() => {
    const evts = this.events();
    const map = new Map<string, AuditLog[]>();
    for (const e of evts) {
      const cat = e.event_category || 'SYSTEM';
      if (!map.has(cat)) map.set(cat, []);
      map.get(cat)!.push(e);
    }
    return Array.from(map.entries()).map(([category, events]) => ({
      category,
      events: events.sort((a, b) =>
        new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
      ),
    }));
  });

  getCategoryColor(cat: string): string {
    return this.categoryColors[cat] || '#94a3b8';
  }

  getRelativeTime(evt: AuditLog): string {
    const start = this.traceStartTime();
    const t = new Date(evt.created_at).getTime();
    return `+${Math.round(t - start)}ms`;
  }

  toggleExpand(id: string): void {
    this.expandedId.update(v => v === id ? null : id);
  }
}
