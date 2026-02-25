/**
 * Overview: Event subscription list — manage subscriptions with handler type selection.
 * Architecture: Feature component for event subscription management (Section 11.6)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/event.service
 * Concepts: Subscription management, handler configuration, filter expressions
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { EventService } from '@core/services/event.service';
import {
  EventType,
  EventSubscription,
  EventSubscriptionCreateInput,
  EventHandlerType,
} from '@shared/models/event.model';

@Component({
  selector: 'nimbus-event-subscription-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Event Subscriptions</h1>
            <p class="page-subtitle">Define what happens when events fire</p>
          </div>
          <button class="btn btn-primary" (click)="showCreateForm = !showCreateForm">
            {{ showCreateForm ? 'Cancel' : '+ New Subscription' }}
          </button>
        </div>

        <!-- Create form -->
        @if (showCreateForm) {
          <div class="card form-card">
            <h3 class="card-title">Create Subscription</h3>
            <div class="form-row">
              <div class="form-group">
                <label>Event Type</label>
                <select [(ngModel)]="newSub.eventTypeId" class="form-input">
                  <option value="">Select event type...</option>
                  @for (et of eventTypes(); track et.id) {
                    <option [value]="et.id">{{ et.name }}</option>
                  }
                </select>
              </div>
              <div class="form-group">
                <label>Name</label>
                <input type="text" [(ngModel)]="newSub.name" placeholder="Subscription name" class="form-input" />
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label>Handler Type</label>
                <select [(ngModel)]="newSub.handlerType" class="form-input">
                  @for (ht of handlerTypes; track ht) {
                    <option [value]="ht">{{ ht }}</option>
                  }
                </select>
              </div>
              <div class="form-group">
                <label>Priority</label>
                <input type="number" [(ngModel)]="newSub.priority" class="form-input" min="0" max="1000" />
              </div>
            </div>
            <div class="form-group">
              <label>Filter Expression (optional)</label>
              <input type="text" [(ngModel)]="newSub.filterExpression" placeholder="e.g. $payload.status == 'DEPLOYED'" class="form-input" />
            </div>
            <div class="form-group">
              <label>Handler Config (JSON)</label>
              <textarea [(ngModel)]="handlerConfigJson" rows="3" class="form-input font-mono" placeholder='{"workflow_definition_id": "..."}'></textarea>
            </div>
            <button class="btn btn-primary" (click)="createSubscription()" [disabled]="!newSub.eventTypeId || !newSub.name">Create</button>
          </div>
        }

        <!-- Table -->
        @if (loading()) {
          <div class="loading">Loading subscriptions...</div>
        } @else {
          <div class="card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Event Type</th>
                  <th>Handler</th>
                  <th>Filter</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (sub of subscriptions(); track sub.id) {
                  <tr>
                    <td>{{ sub.name }}</td>
                    <td class="font-mono text-sm">{{ getEventTypeName(sub.eventTypeId) }}</td>
                    <td><span class="badge badge-handler">{{ sub.handlerType }}</span></td>
                    <td class="font-mono text-sm text-muted">{{ sub.filterExpression || '—' }}</td>
                    <td>{{ sub.priority }}</td>
                    <td>
                      <span class="badge" [class.badge-active]="sub.isActive" [class.badge-inactive]="!sub.isActive">
                        {{ sub.isActive ? 'Active' : 'Inactive' }}
                      </span>
                      @if (sub.isSystem) {
                        <span class="badge badge-system">System</span>
                      }
                    </td>
                    <td>
                      @if (!sub.isSystem) {
                        <button class="btn btn-sm btn-toggle" (click)="toggleActive(sub)">
                          {{ sub.isActive ? 'Disable' : 'Enable' }}
                        </button>
                        <button class="btn btn-sm btn-danger" (click)="deleteSubscription(sub.id)">Delete</button>
                      }
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="7" class="text-center text-muted">No subscriptions found</td>
                  </tr>
                }
              </tbody>
            </table>
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
    .card-title { font-size: 1rem; font-weight: 600; color: #1e293b; margin: 0 0 1rem; }
    .form-card { margin-bottom: 1.5rem; }

    .form-row { display: flex; gap: 1rem; margin-bottom: 0.75rem; }
    .form-group { flex: 1; display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.75rem; }
    .form-group label { font-size: 0.75rem; font-weight: 600; color: #475569; text-transform: uppercase; letter-spacing: 0.05em; }
    .form-input { padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px; font-size: 0.875rem; color: #1e293b; background: #fff; }
    .form-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.1); }

    textarea.form-input { resize: vertical; }

    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th { text-align: left; padding: 0.625rem 0.75rem; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 2px solid #e2e8f0; }
    .data-table td { padding: 0.625rem 0.75rem; font-size: 0.875rem; color: #334155; border-bottom: 1px solid #f1f5f9; }

    .font-mono { font-family: 'SF Mono', 'Fira Code', monospace; }
    .text-sm { font-size: 0.8125rem; }
    .text-muted { color: #64748b; }
    .text-center { text-align: center; }

    .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; margin-right: 0.25rem; }
    .badge-system { background: #eff6ff; color: #2563eb; }
    .badge-handler { background: #faf5ff; color: #7c3aed; }
    .badge-active { background: #f0fdf4; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; border: none; transition: background 0.15s; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; margin-right: 0.25rem; }
    .btn-danger { background: #fee2e2; color: #dc2626; }
    .btn-danger:hover { background: #fecaca; }
    .btn-toggle { background: #f1f5f9; color: #475569; }
    .btn-toggle:hover { background: #e2e8f0; }

    .loading { padding: 2rem; text-align: center; color: #64748b; }
  `],
})
export class EventSubscriptionListComponent implements OnInit {
  private eventService = inject(EventService);

  subscriptions = signal<EventSubscription[]>([]);
  eventTypes = signal<EventType[]>([]);
  loading = signal(true);
  showCreateForm = false;

  handlerTypes: EventHandlerType[] = ['WORKFLOW', 'ACTIVITY', 'NOTIFICATION', 'WEBHOOK', 'INTERNAL'];
  handlerConfigJson = '{}';

  newSub: EventSubscriptionCreateInput = {
    eventTypeId: '',
    name: '',
    handlerType: 'WORKFLOW',
    handlerConfig: {},
    filterExpression: '',
    priority: 100,
    isActive: true,
  };

  private eventTypeMap = new Map<string, string>();

  ngOnInit(): void {
    this.loadEventTypes();
    this.load();
  }

  loadEventTypes(): void {
    this.eventService.listEventTypes().subscribe({
      next: (types) => {
        this.eventTypes.set(types);
        this.eventTypeMap.clear();
        for (const et of types) {
          this.eventTypeMap.set(et.id, et.name);
        }
      },
    });
  }

  load(): void {
    this.loading.set(true);
    this.eventService.listSubscriptions().subscribe({
      next: (subs) => {
        this.subscriptions.set(subs);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  getEventTypeName(id: string): string {
    return this.eventTypeMap.get(id) || id;
  }

  createSubscription(): void {
    try {
      this.newSub.handlerConfig = JSON.parse(this.handlerConfigJson);
    } catch {
      alert('Invalid JSON in handler config');
      return;
    }

    this.eventService.createSubscription(this.newSub).subscribe({
      next: () => {
        this.showCreateForm = false;
        this.newSub = {
          eventTypeId: '', name: '', handlerType: 'WORKFLOW',
          handlerConfig: {}, filterExpression: '', priority: 100, isActive: true,
        };
        this.handlerConfigJson = '{}';
        this.load();
      },
    });
  }

  toggleActive(sub: EventSubscription): void {
    this.eventService.updateSubscription(sub.id, { isActive: !sub.isActive }).subscribe({
      next: () => this.load(),
    });
  }

  deleteSubscription(id: string): void {
    if (confirm('Delete this subscription?')) {
      this.eventService.deleteSubscription(id).subscribe({
        next: () => this.load(),
      });
    }
  }
}
