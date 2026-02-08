/**
 * Overview: Container component for trace visualization with timeline/grouped-list toggle.
 * Architecture: Feature component for trace viewing (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/core/services/audit.service
 * Concepts: Trace visualization, timeline/list toggle, event detail panel
 */
import { Component, input, signal, effect, inject, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditService } from '@core/services/audit.service';
import { AuditLog } from '@shared/models/audit.model';
import { TraceTimelineComponent } from './trace-timeline.component';
import { TraceGroupedListComponent } from './trace-grouped-list.component';

type ViewMode = 'timeline' | 'grouped';

@Component({
  selector: 'nimbus-trace-view',
  standalone: true,
  imports: [CommonModule, TraceTimelineComponent, TraceGroupedListComponent],
  template: `
    <div class="trace-view">
      <div class="trace-toolbar">
        <div class="trace-info">
          <span class="trace-label">Trace</span>
          <code class="trace-id">{{ traceId() }}</code>
          <span class="trace-meta">{{ events().length }} event(s)</span>
          @if (totalDuration() > 0) {
            <span class="trace-meta">{{ totalDuration() }}ms</span>
          }
        </div>
        <div class="view-toggle">
          <button
            class="toggle-btn"
            [class.active]="viewMode() === 'timeline'"
            (click)="viewMode.set('timeline')"
          >Timeline</button>
          <button
            class="toggle-btn"
            [class.active]="viewMode() === 'grouped'"
            (click)="viewMode.set('grouped')"
          >Grouped</button>
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading trace...</div>
      } @else if (events().length === 0) {
        <div class="empty">No events found for this trace</div>
      } @else {
        @if (viewMode() === 'timeline') {
          <nimbus-trace-timeline
            [events]="events()"
            [selectedId]="selectedEventId()"
            (selectEvent)="selectEvent($event)"
          />
        } @else {
          <nimbus-trace-grouped-list
            [events]="events()"
            [selectedId]="selectedEventId()"
            (selectEvent)="selectEvent($event)"
          />
        }

        @if (selectedEvent(); as evt) {
          <div class="selected-detail">
            <div class="detail-header">
              <h4>{{ evt.event_type || evt.action }}</h4>
              <button class="close-btn" (click)="selectedEventId.set(null)">&times;</button>
            </div>
            <div class="detail-fields">
              <div class="df"><span class="dl">Category:</span> {{ evt.event_category || '\u2014' }}</div>
              <div class="df"><span class="dl">Actor:</span> {{ evt.actor_email || '\u2014' }}</div>
              <div class="df"><span class="dl">Resource:</span> {{ evt.resource_type || '' }} {{ evt.resource_name ? '/ ' + evt.resource_name : '' }}</div>
              <div class="df"><span class="dl">Priority:</span> {{ evt.priority }}</div>
              <div class="df"><span class="dl">Time:</span> {{ evt.created_at | date: 'medium' }}</div>
              @if (evt.request_method) {
                <div class="df"><span class="dl">Request:</span> {{ evt.request_method }} {{ evt.request_path }}</div>
              }
              @if (evt.response_status) {
                <div class="df"><span class="dl">Status:</span> {{ evt.response_status }}</div>
              }
            </div>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .trace-view {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem; display: flex; flex-direction: column; gap: 0.75rem;
    }
    .trace-toolbar {
      display: flex; justify-content: space-between; align-items: center;
      padding-bottom: 0.5rem; border-bottom: 1px solid #f1f5f9;
    }
    .trace-info { display: flex; align-items: center; gap: 0.5rem; }
    .trace-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; }
    .trace-id {
      font-family: monospace; font-size: 0.75rem; color: #1d4ed8;
      background: #eff6ff; padding: 0.125rem 0.375rem; border-radius: 4px;
    }
    .trace-meta { font-size: 0.75rem; color: #94a3b8; }
    .view-toggle { display: flex; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden; }
    .toggle-btn {
      padding: 0.25rem 0.625rem; border: none; background: #fff;
      cursor: pointer; font-size: 0.75rem; font-family: inherit; color: #475569;
    }
    .toggle-btn:hover { background: #f8fafc; }
    .toggle-btn.active { background: #3b82f6; color: #fff; }
    .loading, .empty {
      padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.875rem;
    }
    .selected-detail {
      margin-top: 0.5rem; padding: 0.75rem; background: #f8fafc;
      border: 1px solid #e2e8f0; border-radius: 6px;
    }
    .detail-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.5rem;
    }
    .detail-header h4 { margin: 0; font-size: 0.875rem; font-weight: 600; color: #1e293b; }
    .close-btn {
      background: none; border: none; font-size: 1rem; color: #64748b;
      cursor: pointer; padding: 0;
    }
    .detail-fields { display: flex; flex-direction: column; gap: 0.25rem; }
    .df { font-size: 0.8125rem; color: #334155; }
    .dl { font-weight: 500; color: #64748b; display: inline-block; min-width: 80px; }
  `],
})
export class TraceViewComponent {
  traceId = input.required<string>();

  private auditService = inject(AuditService);

  events = signal<AuditLog[]>([]);
  loading = signal(false);
  viewMode = signal<ViewMode>('timeline');
  selectedEventId = signal<string | null>(null);

  selectedEvent = computed(() => {
    const id = this.selectedEventId();
    if (!id) return null;
    return this.events().find(e => e.id === id) || null;
  });

  totalDuration = computed(() => {
    const evts = this.events();
    if (evts.length < 2) return 0;
    const times = evts.map(e => new Date(e.created_at).getTime());
    return Math.round(Math.max(...times) - Math.min(...times));
  });

  constructor() {
    effect(() => {
      const tid = this.traceId();
      if (tid) this.loadTrace(tid);
    });
  }

  selectEvent(id: string): void {
    this.selectedEventId.set(id);
  }

  private loadTrace(traceId: string): void {
    this.loading.set(true);
    this.auditService.getLogsByTrace(traceId).subscribe({
      next: (logs) => {
        this.events.set(logs);
        this.loading.set(false);
      },
      error: () => {
        this.events.set([]);
        this.loading.set(false);
      },
    });
  }
}
