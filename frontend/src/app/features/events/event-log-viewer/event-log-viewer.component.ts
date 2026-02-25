/**
 * Overview: Event log viewer — searchable event log with delivery status drill-down.
 * Architecture: Feature component for event observability (Section 11.6)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/event.service
 * Concepts: Event log, delivery tracking, observability, searchable list
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { EventService } from '@core/services/event.service';
import { EventLogEntry } from '@shared/models/event.model';

@Component({
  selector: 'nimbus-event-log-viewer',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Event Log</h1>
            <p class="page-subtitle">Audit trail of all emitted events and their delivery status</p>
          </div>
          <button class="btn btn-secondary" (click)="load()">Refresh</button>
        </div>

        <!-- Filters -->
        <div class="filter-bar">
          <input
            type="text"
            [(ngModel)]="filterTypeName"
            (ngModelChange)="load()"
            placeholder="Filter by event type name..."
            class="form-input filter-search"
          />
          <input
            type="text"
            [(ngModel)]="filterSource"
            (ngModelChange)="load()"
            placeholder="Filter by source..."
            class="form-input filter-source"
          />
        </div>

        @if (loading()) {
          <div class="loading">Loading event log...</div>
        } @else {
          <div class="card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Time</th>
                  <th>Event Type</th>
                  <th>Source</th>
                  <th>Trace ID</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (entry of entries(); track entry.id) {
                  <tr [class.expanded-row]="selectedEntry()?.id === entry.id">
                    <td class="text-sm">{{ formatDate(entry.emittedAt) }}</td>
                    <td class="font-mono text-sm">{{ entry.eventTypeName }}</td>
                    <td class="text-sm">{{ entry.source }}</td>
                    <td class="font-mono text-sm text-muted">{{ entry.traceId || '—' }}</td>
                    <td>
                      <button class="btn btn-sm btn-toggle" (click)="toggleDetails(entry)">
                        {{ selectedEntry()?.id === entry.id ? 'Hide' : 'Details' }}
                      </button>
                    </td>
                  </tr>
                  @if (selectedEntry()?.id === entry.id) {
                    <tr class="detail-row">
                      <td colspan="5">
                        <div class="detail-panel">
                          <div class="detail-section">
                            <h4>Payload</h4>
                            <pre class="payload-json">{{ formatJson(entry.payload) }}</pre>
                          </div>
                          @if (selectedEntry()!.deliveries.length) {
                            <div class="detail-section">
                              <h4>Deliveries ({{ selectedEntry()!.deliveries.length }})</h4>
                              <table class="data-table delivery-table">
                                <thead>
                                  <tr>
                                    <th>Subscription</th>
                                    <th>Status</th>
                                    <th>Attempts</th>
                                    <th>Error</th>
                                    <th>Delivered At</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  @for (d of selectedEntry()!.deliveries; track d.id) {
                                    <tr>
                                      <td class="font-mono text-sm">{{ d.subscriptionId | slice:0:8 }}...</td>
                                      <td>
                                        <span class="badge" [class]="'badge-' + d.status.toLowerCase()">{{ d.status }}</span>
                                      </td>
                                      <td>{{ d.attempts }}</td>
                                      <td class="text-sm text-error">{{ d.error || '—' }}</td>
                                      <td class="text-sm">{{ d.deliveredAt ? formatDate(d.deliveredAt) : '—' }}</td>
                                    </tr>
                                  }
                                </tbody>
                              </table>
                            </div>
                          } @else {
                            <div class="detail-section">
                              <p class="text-muted">No deliveries for this event</p>
                            </div>
                          }
                        </div>
                      </td>
                    </tr>
                  }
                } @empty {
                  <tr>
                    <td colspan="5" class="text-center text-muted">No events found</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <!-- Pagination -->
          <div class="pagination">
            <button class="btn btn-sm btn-toggle" [disabled]="currentOffset === 0" (click)="prevPage()">Previous</button>
            <span class="text-sm text-muted">Showing {{ currentOffset + 1 }} - {{ currentOffset + entries().length }}</span>
            <button class="btn btn-sm btn-toggle" [disabled]="entries().length < pageSize" (click)="nextPage()">Next</button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 1.5rem; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 0.25rem 0 0; }

    .card { background: #fff; border-radius: 8px; border: 1px solid #e2e8f0; padding: 1rem; margin-bottom: 1rem; }

    .filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
    .filter-search { flex: 1; }
    .filter-source { width: 200px; }
    .form-input { padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; color: #1e293b; background: #fff; }
    .form-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }

    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th { text-align: left; padding: 0.625rem 0.75rem; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 2px solid #e2e8f0; }
    .data-table td { padding: 0.625rem 0.75rem; font-size: 0.875rem; color: #334155; border-bottom: 1px solid #f1f5f9; }

    .expanded-row td { background: #f8fafc; }
    .detail-row td { background: #f8fafc; padding: 0; border-bottom: 2px solid #e2e8f0; }
    .detail-panel { padding: 1rem; }
    .detail-section { margin-bottom: 1rem; }
    .detail-section h4 { font-size: 0.875rem; font-weight: 600; color: #1e293b; margin: 0 0 0.5rem; }

    .payload-json { background: #f1f5f9; padding: 0.75rem; border-radius: 6px; font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.75rem; color: #334155; overflow-x: auto; white-space: pre-wrap; word-break: break-word; margin: 0; }

    .delivery-table { margin-top: 0.5rem; }
    .delivery-table th { border-bottom: 1px solid #e2e8f0; }

    .font-mono { font-family: 'SF Mono', 'Fira Code', monospace; }
    .text-sm { font-size: 0.8125rem; }
    .text-muted { color: #64748b; }
    .text-error { color: #dc2626; }
    .text-center { text-align: center; }

    .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
    .badge-delivered { background: #f0fdf4; color: #16a34a; }
    .badge-pending { background: #fffbeb; color: #d97706; }
    .badge-processing { background: #eff6ff; color: #2563eb; }
    .badge-failed { background: #fef2f2; color: #dc2626; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; border: none; transition: background 0.15s; }
    .btn-secondary { background: #f1f5f9; color: #475569; }
    .btn-secondary:hover { background: #e2e8f0; }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
    .btn-toggle { background: #f1f5f9; color: #475569; }
    .btn-toggle:hover { background: #e2e8f0; }
    .btn-toggle:disabled { opacity: 0.5; cursor: not-allowed; }

    .pagination { display: flex; justify-content: center; align-items: center; gap: 1rem; margin-top: 1rem; }

    .loading { padding: 2rem; text-align: center; color: #64748b; }
  `],
})
export class EventLogViewerComponent implements OnInit {
  private eventService = inject(EventService);

  entries = signal<EventLogEntry[]>([]);
  selectedEntry = signal<EventLogEntry | null>(null);
  loading = signal(true);

  filterTypeName = '';
  filterSource = '';
  currentOffset = 0;
  pageSize = 25;

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.eventService.listEventLog({
      eventTypeName: this.filterTypeName || undefined,
      source: this.filterSource || undefined,
      offset: this.currentOffset,
      limit: this.pageSize,
    }).subscribe({
      next: (entries) => {
        this.entries.set(entries);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  toggleDetails(entry: EventLogEntry): void {
    if (this.selectedEntry()?.id === entry.id) {
      this.selectedEntry.set(null);
      return;
    }

    // Load with deliveries
    this.eventService.getEventLogEntry(entry.id).subscribe({
      next: (full) => this.selectedEntry.set(full),
    });
  }

  formatDate(iso: string): string {
    return new Date(iso).toLocaleString();
  }

  formatJson(obj: Record<string, unknown>): string {
    return JSON.stringify(obj, null, 2);
  }

  prevPage(): void {
    this.currentOffset = Math.max(0, this.currentOffset - this.pageSize);
    this.load();
  }

  nextPage(): void {
    this.currentOffset += this.pageSize;
    this.load();
  }
}
