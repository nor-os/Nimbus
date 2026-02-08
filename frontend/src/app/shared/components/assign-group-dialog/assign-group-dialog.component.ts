/**
 * Overview: Dialog for searching and selecting a group to assign, with client-side filtering.
 * Architecture: Shared dialog component for group assignment (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/permission.service, app/shared/services/dialog.service
 * Concepts: Group assignment, search filtering, dialog pattern, Active Directory style
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { Group } from '@core/models/permission.model';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';

export interface AssignGroupDialogData {
  excludeIds?: string[];
}

@Component({
  selector: 'nimbus-assign-group-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="assign-dialog">
      <h2>Add to Group</h2>
      <input
        class="search-input"
        placeholder="Search groups..."
        [(ngModel)]="searchQuery"
        (ngModelChange)="onSearch()"
      />
      <div class="group-list">
        @for (group of filteredGroups(); track group.id) {
          <div class="group-row">
            <div class="group-info">
              <span class="group-name">{{ group.name }}</span>
              @if (group.description) {
                <span class="group-desc">{{ group.description }}</span>
              }
            </div>
            <button class="btn btn-sm btn-primary" (click)="onAssign(group)">Add</button>
          </div>
        } @empty {
          <div class="empty">
            @if (loading()) {
              Loading groups...
            } @else {
              No matching groups
            }
          </div>
        }
      </div>
      <div class="dialog-footer">
        <button class="btn btn-cancel" (click)="onClose()">Cancel</button>
      </div>
    </div>
  `,
  styles: [`
    .assign-dialog { padding: 1.5rem; }
    h2 { margin: 0 0 1rem 0; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .search-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; box-sizing: border-box;
      font-family: inherit; margin-bottom: 0.75rem;
    }
    .search-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .group-list { max-height: 320px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; }
    .group-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.625rem 0.75rem; border-bottom: 1px solid #f1f5f9;
    }
    .group-row:last-child { border-bottom: none; }
    .group-row:hover { background: #f8fafc; }
    .group-info { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; min-width: 0; }
    .group-name { font-weight: 500; color: #1e293b; font-size: 0.8125rem; }
    .group-desc { color: #94a3b8; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .empty { padding: 1.5rem; text-align: center; color: #94a3b8; font-size: 0.8125rem; }
    .dialog-footer { display: flex; justify-content: flex-end; margin-top: 1rem; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; transition: background 0.15s;
    }
    .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.75rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-cancel { background: #fff; color: #374151; border: 1px solid #e2e8f0; padding: 0.5rem 1.25rem; }
    .btn-cancel:hover { background: #f8fafc; }
  `],
})
export class AssignGroupDialogComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private dialogService = inject(DialogService);
  private data = inject<AssignGroupDialogData>(DIALOG_DATA);

  searchQuery = '';
  loading = signal(true);
  private allGroups = signal<Group[]>([]);
  filteredGroups = signal<Group[]>([]);

  ngOnInit(): void {
    this.permissionService.listGroups().subscribe({
      next: (groups) => {
        const excludeSet = new Set(this.data?.excludeIds ?? []);
        const available = groups.filter((g) => !excludeSet.has(g.id));
        this.allGroups.set(available);
        this.filteredGroups.set(available);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onSearch(): void {
    const q = this.searchQuery.toLowerCase().trim();
    if (!q) {
      this.filteredGroups.set(this.allGroups());
      return;
    }
    this.filteredGroups.set(
      this.allGroups().filter(
        (g) =>
          g.name.toLowerCase().includes(q) ||
          (g.description?.toLowerCase().includes(q) ?? false),
      ),
    );
  }

  onAssign(group: Group): void {
    this.dialogService.close(group);
  }

  onClose(): void {
    this.dialogService.close(undefined);
  }
}
