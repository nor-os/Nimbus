/**
 * Overview: Horizontal waterfall timeline for trace events, color-coded by event category.
 * Architecture: Feature component for trace visualization (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/shared/models/audit.model
 * Concepts: Trace timeline, waterfall chart, event category coloring
 */
import { Component, input, output, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AuditLog } from '@shared/models/audit.model';

const CATEGORY_COLORS: Record<string, string> = {
  API: '#60a5fa',
  AUTH: '#818cf8',
  DATA: '#34d399',
  PERMISSION: '#f472b6',
  SYSTEM: '#94a3b8',
  SECURITY: '#f87171',
  TENANT: '#fbbf24',
  USER: '#a78bfa',
};

@Component({
  selector: 'nimbus-trace-timeline',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="timeline-container">
      @for (bar of bars(); track bar.id) {
        <div
          class="timeline-row"
          [class.selected]="selectedId() === bar.id"
          (click)="selectEvent.emit(bar.id)"
          (mouseenter)="hoveredId = bar.id"
          (mouseleave)="hoveredId = null"
        >
          <div class="row-label" [title]="bar.eventType">
            {{ bar.eventType }}
            <span class="row-offset">+{{ bar.offsetMs }}ms</span>
          </div>
          <div class="row-track">
            <div
              class="bar"
              [style.left.%]="bar.leftPct"
              [style.width.%]="bar.widthPct"
              [style.background]="bar.color"
            ></div>
          </div>
          @if (hoveredId === bar.id) {
            <div class="tooltip">
              {{ bar.eventType }} &mdash; {{ bar.offsetMs }}ms from start
            </div>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .timeline-container { display: flex; flex-direction: column; gap: 2px; }
    .timeline-row {
      display: flex; align-items: center; gap: 0.5rem;
      padding: 0.25rem 0; cursor: pointer; position: relative;
      border-radius: 4px;
    }
    .timeline-row:hover { background: #f8fafc; }
    .timeline-row.selected { background: #eff6ff; }
    .row-label {
      width: 180px; flex-shrink: 0; font-size: 0.75rem; color: #334155;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .row-offset { color: #94a3b8; margin-left: 0.25rem; }
    .row-track {
      flex: 1; height: 18px; background: #f1f5f9; border-radius: 3px;
      position: relative; overflow: hidden;
    }
    .bar {
      position: absolute; top: 2px; bottom: 2px; border-radius: 2px;
      min-width: 4px; transition: opacity 0.1s;
    }
    .bar:hover { opacity: 0.85; }
    .tooltip {
      position: absolute; top: -28px; left: 180px; z-index: 10;
      background: #1e293b; color: #fff; padding: 0.25rem 0.5rem;
      border-radius: 4px; font-size: 0.6875rem; white-space: nowrap;
      pointer-events: none;
    }
  `],
})
export class TraceTimelineComponent {
  events = input<AuditLog[]>([]);
  selectedId = input<string | null>(null);

  selectEvent = output<string>();

  hoveredId: string | null = null;

  bars = computed(() => {
    const evts = this.events();
    if (evts.length === 0) return [];

    const times = evts.map(e => new Date(e.created_at).getTime());
    const minTime = Math.min(...times);
    const maxTime = Math.max(...times);
    const totalSpan = Math.max(maxTime - minTime, 1);

    return evts.map((e, i) => {
      const t = times[i];
      const offsetMs = t - minTime;
      const leftPct = (offsetMs / totalSpan) * 100;
      const widthPct = Math.max(2, (1 / evts.length) * 80);

      return {
        id: e.id,
        eventType: e.event_type || e.action,
        offsetMs: Math.round(offsetMs),
        leftPct: Math.min(leftPct, 100 - widthPct),
        widthPct,
        color: CATEGORY_COLORS[e.event_category || 'SYSTEM'] || '#94a3b8',
      };
    });
  });
}
