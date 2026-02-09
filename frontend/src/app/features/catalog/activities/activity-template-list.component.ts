/**
 * Overview: Activity template listing — view and manage process step templates.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/delivery.service
 * Concepts: Activity templates, process steps, effort estimation
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { DeliveryService } from '@core/services/delivery.service';
import { ActivityTemplate } from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-activity-template-list',
  standalone: true,
  imports: [CommonModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="activity-list-page">
        <div class="page-header">
          <h1>Activity Templates</h1>
          <button
            *nimbusHasPermission="'catalog:activity:manage'"
            class="btn btn-primary"
            (click)="createTemplate()"
          >
            Create Template
          </button>
        </div>

        @if (loading()) {
          <div class="loading">Loading activity templates...</div>
        }

        @if (!loading()) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Version</th>
                  <th># of Steps</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                @for (template of templates(); track template.id) {
                  <tr class="clickable-row" (click)="goToEditor(template.id)">
                    <td class="name-cell">{{ template.name }}</td>
                    <td class="desc-cell">{{ template.description || '\u2014' }}</td>
                    <td>{{ template.version }}</td>
                    <td>{{ template.definitions.length }}</td>
                    <td class="actions-cell" (click)="$event.stopPropagation()">
                      <button
                        *nimbusHasPermission="'catalog:activity:manage'"
                        class="btn btn-sm"
                        (click)="cloneTemplate(template)"
                        title="Clone template"
                      >
                        Clone
                      </button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="5" class="empty-state">No activity templates found</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>

          <div class="pagination">
            <button
              class="btn btn-sm"
              [disabled]="currentOffset() === 0"
              (click)="prevPage()"
            >Previous</button>
            <span class="page-info">
              @if (total() > 0) {
                Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + templates().length }}
                of {{ total() }}
              } @else {
                No items
              }
            </span>
            <button
              class="btn btn-sm"
              [disabled]="currentOffset() + templates().length >= total()"
              (click)="nextPage()"
            >Next</button>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .activity-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    .loading {
      padding: 2rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }

    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table tbody tr { color: #334155; }
    .table tbody tr:hover { background: #f8fafc; }
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .desc-cell {
      max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .actions-cell { width: 100px; }

    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }

    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .page-info { color: #64748b; font-size: 0.8125rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; text-decoration: none;
    }
    .btn-primary:hover { background: #2563eb; }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer;
      font-size: 0.8125rem; font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
  `],
})
export class ActivityTemplateListComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private router = inject(Router);
  private toastService = inject(ToastService);

  templates = signal<ActivityTemplate[]>([]);
  total = signal(0);
  currentOffset = signal(0);
  loading = signal(false);
  pageSize = 50;

  ngOnInit(): void {
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.loading.set(true);
    this.deliveryService.listActivityTemplates({
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.templates.set(response.items);
        this.total.set(response.total);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.toastService.error(err.message || 'Failed to load activity templates');
      },
    });
  }

  createTemplate(): void {
    this.router.navigate(['/catalog', 'activities', 'new']);
  }

  goToEditor(id: string): void {
    this.router.navigate(['/catalog', 'activities', id]);
  }

  cloneTemplate(template: ActivityTemplate): void {
    this.deliveryService.cloneActivityTemplate(template.id).subscribe({
      next: (cloned) => {
        this.toastService.success(`Template "${template.name}" cloned as "${cloned.name}"`);
        this.loadTemplates();
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to clone template');
      },
    });
  }

  prevPage(): void {
    this.currentOffset.update((v) => Math.max(0, v - this.pageSize));
    this.loadTemplates();
  }

  nextPage(): void {
    this.currentOffset.update((v) => v + this.pageSize);
    this.loadTemplates();
  }
}
