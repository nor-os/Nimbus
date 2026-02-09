/**
 * Overview: CI template list component -- paginated, filterable browser for CI templates.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, @angular/forms, app/core/services/cmdb.service
 * Concepts: Template listing with CI class filter, pagination, active status, version display
 */
import { Component, inject, signal, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CmdbService } from '@core/services/cmdb.service';
import { CIClass, CITemplate } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-template-list',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="template-list-page">
        <div class="page-header">
          <h1>CI Templates</h1>
          <a
            *nimbusHasPermission="'cmdb:template:create'"
            routerLink="/cmdb/templates/new"
            class="btn btn-primary"
          >
            Create Template
          </a>
        </div>

        <div class="filters">
          <select
            [(ngModel)]="selectedClassId"
            (ngModelChange)="onFilterChange()"
            class="filter-select"
          >
            <option value="">All Classes</option>
            @for (cls of classes(); track cls.id) {
              <option [value]="cls.id">{{ cls.displayName }}</option>
            }
          </select>
        </div>

        <div class="table-container">
          <table class="table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Class</th>
                <th>Version</th>
                <th>Status</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              @for (tpl of templates(); track tpl.id) {
                <tr class="clickable-row" [routerLink]="['/cmdb', 'templates', tpl.id, 'edit']">
                  <td class="name-cell">{{ tpl.name }}</td>
                  <td>{{ tpl.ciClassName }}</td>
                  <td class="version-cell">v{{ tpl.version }}</td>
                  <td>
                    <span
                      class="badge"
                      [class.badge-active]="tpl.isActive"
                      [class.badge-inactive]="!tpl.isActive"
                    >
                      {{ tpl.isActive ? 'Active' : 'Inactive' }}
                    </span>
                  </td>
                  <td>{{ tpl.updatedAt | date: 'medium' }}</td>
                </tr>
              } @empty {
                <tr>
                  <td colspan="5" class="empty-state">No templates found</td>
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
            @if (totalTemplates() > 0) {
              Showing {{ currentOffset() + 1 }}\u2013{{ currentOffset() + templates().length }}
              of {{ totalTemplates() }}
            } @else {
              No items
            }
          </span>
          <button
            class="btn btn-sm"
            [disabled]="currentOffset() + templates().length >= totalTemplates()"
            (click)="nextPage()"
          >Next</button>
        </div>
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .template-list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .btn-primary {
      background: #3b82f6; color: #fff; padding: 0.5rem 1rem;
      border: none; border-radius: 6px; text-decoration: none; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; transition: background 0.15s;
    }
    .btn-primary:hover { background: #2563eb; }
    .filters {
      display: flex; gap: 0.75rem; margin-bottom: 1rem; flex-wrap: wrap;
    }
    .filter-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; font-family: inherit; cursor: pointer;
      min-width: 200px;
    }
    .filter-select:focus { border-color: #3b82f6; outline: none; }
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
    .table tbody tr:hover { background: #f8fafc; }
    .clickable-row { cursor: pointer; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .version-cell {
      font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem;
      color: #64748b;
    }
    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-inactive { background: #fef2f2; color: #dc2626; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }
    .pagination {
      display: flex; align-items: center; justify-content: center;
      gap: 1rem; margin-top: 1rem;
    }
    .btn-sm {
      padding: 0.375rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; background: #fff; cursor: pointer; font-size: 0.8125rem;
      font-family: inherit; transition: background 0.15s;
    }
    .btn-sm:hover { background: #f8fafc; }
    .btn-sm:disabled { opacity: 0.5; cursor: not-allowed; }
    .page-info { color: #64748b; font-size: 0.8125rem; }
  `],
})
export class TemplateListComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private toastService = inject(ToastService);

  templates = signal<CITemplate[]>([]);
  totalTemplates = signal(0);
  currentOffset = signal(0);
  pageSize = 50;
  selectedClassId = '';
  classes = signal<CIClass[]>([]);

  ngOnInit(): void {
    this.loadTemplates();
    this.loadClasses();
  }

  onFilterChange(): void {
    this.currentOffset.set(0);
    this.loadTemplates();
  }

  loadTemplates(): void {
    this.cmdbService.listTemplates({
      ciClassId: this.selectedClassId || undefined,
      offset: this.currentOffset(),
      limit: this.pageSize,
    }).subscribe({
      next: (response) => {
        this.templates.set(response.items);
        this.totalTemplates.set(response.total);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load templates');
      },
    });
  }

  loadClasses(): void {
    this.cmdbService.listClasses(true).subscribe({
      next: (classes) => {
        this.classes.set(classes);
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
