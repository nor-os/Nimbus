/**
 * Overview: Event type list — displays system and custom event types with CRUD for custom ones.
 * Architecture: Feature component for event type management (Section 11.6)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/event.service
 * Concepts: Event type catalog, system vs custom types, category filtering
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { EventService } from '@core/services/event.service';
import { EventType, EventTypeCreateInput } from '@shared/models/event.model';

@Component({
  selector: 'nimbus-event-type-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div>
            <h1 class="page-title">Event Types</h1>
            <p class="page-subtitle">System and custom event types that can trigger subscriptions</p>
          </div>
          <button class="btn btn-primary" (click)="showCreateForm = !showCreateForm">
            {{ showCreateForm ? 'Cancel' : '+ New Event Type' }}
          </button>
        </div>

        <!-- Create form -->
        @if (showCreateForm) {
          <div class="card form-card">
            <h3 class="card-title">Create Custom Event Type</h3>
            <div class="form-row">
              <div class="form-group">
                <label>Name</label>
                <input type="text" [(ngModel)]="newType.name" placeholder="e.g. custom.deployment.ready" class="form-input" />
              </div>
              <div class="form-group">
                <label>Category</label>
                <select [(ngModel)]="newType.category" class="form-input">
                  @for (cat of categories; track cat) {
                    <option [value]="cat">{{ cat }}</option>
                  }
                </select>
              </div>
            </div>
            <div class="form-group">
              <label>Description</label>
              <input type="text" [(ngModel)]="newType.description" placeholder="What triggers this event?" class="form-input" />
            </div>
            <button class="btn btn-primary" (click)="createType()" [disabled]="!newType.name">Create</button>
          </div>
        }

        <!-- Filters -->
        <div class="filter-bar">
          <select [(ngModel)]="selectedCategory" (ngModelChange)="load()" class="form-input filter-select">
            <option value="">All Categories</option>
            @for (cat of categories; track cat) {
              <option [value]="cat">{{ cat }}</option>
            }
          </select>
          <input
            type="text"
            [(ngModel)]="searchQuery"
            (ngModelChange)="load()"
            placeholder="Search event types..."
            class="form-input filter-search"
          />
        </div>

        <!-- Table -->
        @if (loading()) {
          <div class="loading">Loading event types...</div>
        } @else {
          <div class="card">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Category</th>
                  <th>Description</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (et of eventTypes(); track et.id) {
                  <tr>
                    <td class="font-mono text-sm">{{ et.name }}</td>
                    <td><span class="badge badge-category">{{ et.category }}</span></td>
                    <td class="text-muted">{{ et.description || '—' }}</td>
                    <td>
                      @if (et.isSystem) {
                        <span class="badge badge-system">System</span>
                      } @else {
                        <span class="badge badge-custom">Custom</span>
                      }
                    </td>
                    <td>
                      <span class="badge" [class.badge-active]="et.isActive" [class.badge-inactive]="!et.isActive">
                        {{ et.isActive ? 'Active' : 'Inactive' }}
                      </span>
                    </td>
                    <td>
                      @if (!et.isSystem) {
                        <button class="btn btn-sm btn-danger" (click)="deleteType(et.id)">Delete</button>
                      }
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="6" class="text-center text-muted">No event types found</td>
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

    .filter-bar { display: flex; gap: 0.75rem; margin-bottom: 1rem; }
    .filter-select { width: 200px; }
    .filter-search { flex: 1; }

    .data-table { width: 100%; border-collapse: collapse; }
    .data-table th { text-align: left; padding: 0.625rem 0.75rem; font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; border-bottom: 2px solid #e2e8f0; }
    .data-table td { padding: 0.625rem 0.75rem; font-size: 0.875rem; color: #334155; border-bottom: 1px solid #f1f5f9; }

    .font-mono { font-family: 'SF Mono', 'Fira Code', monospace; }
    .text-sm { font-size: 0.8125rem; }
    .text-muted { color: #64748b; }
    .text-center { text-align: center; }

    .badge { display: inline-block; padding: 0.125rem 0.5rem; border-radius: 4px; font-size: 0.75rem; font-weight: 500; }
    .badge-system { background: #eff6ff; color: #2563eb; }
    .badge-custom { background: #f0fdf4; color: #16a34a; }
    .badge-category { background: #f8fafc; color: #475569; border: 1px solid #e2e8f0; }
    .badge-active { background: #f0fdf4; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }

    .btn { padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; border: none; transition: background 0.15s; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-sm { padding: 0.25rem 0.5rem; font-size: 0.75rem; }
    .btn-danger { background: #fee2e2; color: #dc2626; }
    .btn-danger:hover { background: #fecaca; }

    .loading { padding: 2rem; text-align: center; color: #64748b; }
  `],
})
export class EventTypeListComponent implements OnInit {
  private eventService = inject(EventService);

  eventTypes = signal<EventType[]>([]);
  loading = signal(true);
  showCreateForm = false;
  selectedCategory = '';
  searchQuery = '';

  categories = [
    'AUTHENTICATION', 'APPROVAL', 'DEPLOYMENT', 'ENVIRONMENT',
    'CMDB', 'AUTOMATION', 'WORKFLOW', 'CUSTOM',
  ];

  newType: EventTypeCreateInput = { name: '', description: '', category: 'CUSTOM' };

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.eventService.listEventTypes({
      category: this.selectedCategory || undefined,
      search: this.searchQuery || undefined,
    }).subscribe({
      next: (types) => {
        this.eventTypes.set(types);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  createType(): void {
    this.eventService.createEventType(this.newType).subscribe({
      next: () => {
        this.showCreateForm = false;
        this.newType = { name: '', description: '', category: 'CUSTOM' };
        this.load();
      },
    });
  }

  deleteType(id: string): void {
    if (confirm('Delete this event type?')) {
      this.eventService.deleteEventType(id).subscribe({
        next: () => this.load(),
      });
    }
  }
}
