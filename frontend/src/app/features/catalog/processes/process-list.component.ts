/**
 * Overview: Process list — hierarchical expandable view of service processes with
 *     inline activity templates showing step counts, required/optional badges.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/forms, @angular/router, app/core/services/delivery.service
 * Concepts: Service processes group activity templates into delivery workflows.
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { DeliveryService } from '@core/services/delivery.service';
import { ServiceProcess, ProcessActivityLink, ActivityTemplate } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ConfirmService } from '@shared/services/confirm.service';

@Component({
  selector: 'nimbus-process-list',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="process-list-page">
        <div class="page-header">
          <h1>Processes</h1>
          <div class="header-actions">
            <button
              *nimbusHasPermission="'catalog:activity:manage'"
              class="btn btn-secondary"
              (click)="createActivity()"
            >
              New Activity Template
            </button>
            <button
              *nimbusHasPermission="'catalog:process:manage'"
              class="btn btn-primary"
              (click)="showCreateForm.set(true)"
            >
              Create Process
            </button>
          </div>
        </div>

        @if (showCreateForm()) {
          <div class="create-form-card">
            <h2 class="form-title">New Process</h2>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label">Name</label>
                <input
                  type="text"
                  [(ngModel)]="newName"
                  placeholder="e.g. Server Onboarding"
                  class="form-input"
                />
              </div>
              <div class="form-group">
                <label class="form-label">Description</label>
                <input
                  type="text"
                  [(ngModel)]="newDescription"
                  placeholder="Optional description"
                  class="form-input"
                />
              </div>
              <div class="form-group form-group-sm">
                <label class="form-label">Sort Order</label>
                <input
                  type="number"
                  [(ngModel)]="newSortOrder"
                  class="form-input"
                  min="0"
                />
              </div>
            </div>
            <div class="form-actions">
              <button
                class="btn btn-primary"
                (click)="createProcess()"
                [disabled]="!newName.trim()"
              >
                Create
              </button>
              <button class="btn btn-secondary" (click)="cancelCreate()">Cancel</button>
            </div>
          </div>
        }

        @if (loading()) {
          <div class="loading-state">Loading processes...</div>
        }

        @for (process of processes(); track process.id) {
          <div class="process-card" [class.expanded]="isExpanded(process.id)">
            <div class="process-header" (click)="toggleExpand(process.id)">
              <span class="expand-icon">{{ isExpanded(process.id) ? '&#9662;' : '&#9656;' }}</span>
              <div class="process-info">
                <span class="process-name">{{ process.name }}</span>
                <span class="process-desc">{{ process.description || '' }}</span>
              </div>
              <span class="badge badge-count">{{ process.activityLinks.length }} {{ process.activityLinks.length === 1 ? 'activity' : 'activities' }}</span>
              <div class="process-actions" (click)="$event.stopPropagation()">
                <button
                  *nimbusHasPermission="'catalog:process:manage'"
                  class="btn-action btn-edit"
                  (click)="openProcess(process)"
                  title="Edit"
                >
                  Edit
                </button>
                <button
                  *nimbusHasPermission="'catalog:process:manage'"
                  class="btn-action btn-delete"
                  (click)="deleteProcess(process)"
                  title="Delete"
                >
                  Delete
                </button>
              </div>
            </div>
            @if (isExpanded(process.id)) {
              <div class="process-body">
                @for (link of sortedLinks(process); track link.id) {
                  <div class="activity-row">
                    <span class="activity-order">{{ link.sortOrder }}</span>
                    <span class="activity-name" (click)="editActivity(link.activityTemplateId)">
                      {{ templateForId(link.activityTemplateId)?.name || 'Unknown template' }}
                    </span>
                    <span class="steps-badge">
                      {{ templateForId(link.activityTemplateId)?.definitions?.length || 0 }} steps
                    </span>
                    <span class="required-badge" [class.required]="link.isRequired" [class.optional]="!link.isRequired">
                      {{ link.isRequired ? 'Required' : 'Optional' }}
                    </span>
                  </div>
                } @empty {
                  <div class="no-activities">No activities linked to this process.</div>
                }
                <a class="add-link" (click)="createActivity()">+ Create Activity Template</a>
              </div>
            }
          </div>
        } @empty {
          @if (!loading()) {
            <div class="empty-card">No processes configured</div>
          }
        }

        @if (total() > 0) {
          <div class="pagination-info">
            Showing {{ processes().length }} of {{ total() }} processes
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .process-list-page { padding: 0; }

    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .header-actions { display: flex; gap: 0.5rem; }

    /* ── Create form card ─────────────────────────────────────────── */

    .create-form-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; margin-bottom: 1.25rem;
    }
    .form-title {
      margin: 0 0 1rem; font-size: 0.9375rem; font-weight: 600; color: #1e293b;
    }
    .form-row {
      display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;
    }
    .form-group { display: flex; flex-direction: column; flex: 1; min-width: 180px; }
    .form-group-sm { flex: 0 0 120px; min-width: 100px; }
    .form-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.375rem;
    }
    .form-input {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; color: #1e293b; font-family: inherit;
      transition: border-color 0.15s;
    }
    .form-input::placeholder { color: #94a3b8; }
    .form-input:focus { border-color: #3b82f6; outline: none; }
    .form-actions { display: flex; gap: 0.5rem; }

    /* ── Process cards ────────────────────────────────────────────── */

    .process-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 0.75rem; overflow: hidden;
      transition: border-color 0.15s;
    }
    .process-card:hover { border-color: #cbd5e1; }
    .process-card.expanded { border-color: #93c5fd; }

    .process-header {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0.75rem 1rem; cursor: pointer;
      transition: background 0.15s;
    }
    .process-header:hover { background: #f8fafc; }

    .expand-icon {
      width: 1rem; flex-shrink: 0; color: #94a3b8;
      font-size: 0.75rem; text-align: center;
    }

    .process-info {
      flex: 1; min-width: 0; display: flex; align-items: center; gap: 0.75rem;
    }
    .process-name {
      font-weight: 600; color: #1e293b; font-size: 0.875rem;
      white-space: nowrap;
    }
    .process-desc {
      color: #64748b; font-size: 0.8125rem;
      white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block; white-space: nowrap; flex-shrink: 0;
    }
    .badge-count { background: #eff6ff; color: #2563eb; }

    .process-actions { display: flex; gap: 0.375rem; align-items: center; flex-shrink: 0; }

    /* ── Expanded body ────────────────────────────────────────────── */

    .process-body {
      border-top: 1px solid #f1f5f9;
      padding: 0.5rem 1rem 0.75rem;
      border-left: 3px solid #3b82f6;
      margin-left: 0;
      background: #fafbfd;
    }

    .activity-row {
      display: flex; align-items: center; gap: 0.75rem;
      padding: 0.375rem 0; font-size: 0.8125rem;
    }
    .activity-row:not(:last-of-type) { border-bottom: 1px solid #f1f5f9; }

    .activity-order {
      width: 1.5rem; text-align: center; color: #94a3b8;
      font-size: 0.75rem; font-weight: 600; flex-shrink: 0;
    }
    .activity-name {
      flex: 1; color: #3b82f6; cursor: pointer; font-weight: 500;
    }
    .activity-name:hover { text-decoration: underline; }

    .steps-badge {
      padding: 0.0625rem 0.375rem; border-radius: 10px;
      font-size: 0.6875rem; font-weight: 500; flex-shrink: 0;
      background: #f1f5f9; color: #64748b;
    }

    .required-badge {
      padding: 0.0625rem 0.375rem; border-radius: 10px;
      font-size: 0.6875rem; font-weight: 600; flex-shrink: 0;
    }
    .required-badge.required { background: #fef3c7; color: #92400e; }
    .required-badge.optional { background: #f1f5f9; color: #64748b; }

    .no-activities {
      color: #94a3b8; font-size: 0.8125rem; padding: 0.75rem 0;
      text-align: center;
    }

    .add-link {
      display: inline-block; color: #3b82f6; font-size: 0.8125rem;
      cursor: pointer; margin-top: 0.5rem; font-weight: 500;
    }
    .add-link:hover { text-decoration: underline; }

    /* ── Empty & loading ──────────────────────────────────────────── */

    .empty-card {
      text-align: center; color: #94a3b8; padding: 2rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .loading-state { text-align: center; color: #64748b; padding: 2rem; font-size: 0.875rem; }

    .pagination-info {
      font-size: 0.75rem; color: #94a3b8; text-align: right; margin-top: 0.75rem;
    }

    /* ── Action buttons ─────────────────────────────────────────────  */

    .btn-action {
      padding: 0.25rem 0.625rem; border-radius: 4px; font-size: 0.75rem;
      font-weight: 500; font-family: inherit; cursor: pointer; border: 1px solid transparent;
      transition: background 0.15s, color 0.15s;
    }
    .btn-action:disabled { opacity: 0.4; cursor: not-allowed; }
    .btn-edit {
      background: #f1f5f9; color: #475569; border-color: #e2e8f0;
    }
    .btn-edit:hover:not(:disabled) { background: #e2e8f0; color: #1e293b; }
    .btn-delete {
      background: #fff; color: #dc2626; border-color: #fecaca;
    }
    .btn-delete:hover:not(:disabled) { background: #fef2f2; }

    /* ── Shared button styles ──────────────────────────────────────── */

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
      padding: 0.5rem 1rem; border: none;
    }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover:not(:disabled) { background: #2563eb; }
    .btn-secondary {
      background: #fff; color: #64748b; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; color: #1e293b; }
  `],
})
export class ProcessListComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);
  private confirmService = inject(ConfirmService);
  private router = inject(Router);

  processes = signal<ServiceProcess[]>([]);
  total = signal(0);
  loading = signal(false);
  showCreateForm = signal(false);

  activityTemplates = signal<ActivityTemplate[]>([]);
  expandedProcessIds = signal<Set<string>>(new Set());

  private activityTemplateMap = computed(() =>
    new Map(this.activityTemplates().map(t => [t.id, t]))
  );

  // Create form fields
  newName = '';
  newDescription = '';
  newSortOrder = 0;

  ngOnInit(): void {
    this.loadProcesses();
    this.loadActivityTemplates();
  }

  loadProcesses(): void {
    this.loading.set(true);
    this.deliveryService.listProcesses({ limit: 100 }).subscribe({
      next: (response) => {
        this.processes.set(response.items);
        this.total.set(response.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load processes');
        this.loading.set(false);
      },
    });
  }

  private loadActivityTemplates(): void {
    this.deliveryService.listActivityTemplates({ limit: 500 }).subscribe({
      next: (response) => {
        this.activityTemplates.set(response.items);
      },
      error: () => {
        // Non-critical — activities just won't have names resolved
      },
    });
  }

  toggleExpand(processId: string): void {
    this.expandedProcessIds.update(ids => {
      const next = new Set(ids);
      if (next.has(processId)) {
        next.delete(processId);
      } else {
        next.add(processId);
      }
      return next;
    });
  }

  isExpanded(processId: string): boolean {
    return this.expandedProcessIds().has(processId);
  }

  sortedLinks(process: ServiceProcess): ProcessActivityLink[] {
    return [...process.activityLinks].sort((a, b) => a.sortOrder - b.sortOrder);
  }

  templateForId(templateId: string): ActivityTemplate | undefined {
    return this.activityTemplateMap().get(templateId);
  }

  editActivity(templateId: string): void {
    this.router.navigate(['/catalog/activities', templateId]);
  }

  createActivity(): void {
    this.router.navigate(['/catalog/activities/new']);
  }

  createProcess(): void {
    const name = this.newName.trim();
    if (!name) return;

    this.deliveryService.createProcess({
      name,
      description: this.newDescription.trim() || null,
      sortOrder: this.newSortOrder,
    }).subscribe({
      next: () => {
        this.toastService.success(`Process "${name}" created`);
        this.cancelCreate();
        this.loadProcesses();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to create process');
      },
    });
  }

  cancelCreate(): void {
    this.showCreateForm.set(false);
    this.newName = '';
    this.newDescription = '';
    this.newSortOrder = 0;
  }

  openProcess(process: ServiceProcess): void {
    this.router.navigate(['/catalog/processes', process.id]);
  }

  async deleteProcess(process: ServiceProcess): Promise<void> {
    const confirmed = await this.confirmService.confirm({
      title: 'Delete Process',
      message: `Are you sure you want to delete "${process.name}"? This action cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!confirmed) return;

    this.deliveryService.deleteProcess(process.id).subscribe({
      next: () => {
        this.toastService.success(`Process "${process.name}" deleted`);
        this.loadProcesses();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete process');
      },
    });
  }
}
