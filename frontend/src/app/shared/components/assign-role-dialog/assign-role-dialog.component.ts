/**
 * Overview: Dialog for searching and selecting a role to assign, with client-side filtering.
 * Architecture: Shared dialog component for role assignment (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/permission.service, app/shared/services/dialog.service
 * Concepts: Role assignment, search filtering, dialog pattern, Active Directory style
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PermissionService } from '@core/services/permission.service';
import { Role } from '@core/models/permission.model';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';

export interface AssignRoleDialogData {
  excludeIds?: string[];
}

@Component({
  selector: 'nimbus-assign-role-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="assign-dialog">
      <h2>Assign Role</h2>
      <input
        class="search-input"
        placeholder="Search roles..."
        [(ngModel)]="searchQuery"
        (ngModelChange)="onSearch()"
      />
      <div class="role-list">
        @for (role of filteredRoles(); track role.id) {
          <div class="role-row">
            <div class="role-info">
              <span class="role-name">{{ role.name }}</span>
              <span class="badge" [class]="'badge-scope-' + role.scope">{{ role.scope }}</span>
              @if (role.description) {
                <span class="role-desc">{{ role.description }}</span>
              }
            </div>
            <button class="btn btn-sm btn-primary" (click)="onAssign(role)">Assign</button>
          </div>
        } @empty {
          <div class="empty">
            @if (loading()) {
              Loading roles...
            } @else {
              No matching roles
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
    .role-list { max-height: 320px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; }
    .role-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.625rem 0.75rem; border-bottom: 1px solid #f1f5f9;
    }
    .role-row:last-child { border-bottom: none; }
    .role-row:hover { background: #f8fafc; }
    .role-info { display: flex; align-items: center; gap: 0.5rem; flex: 1; min-width: 0; }
    .role-name { font-weight: 500; color: #1e293b; font-size: 0.8125rem; }
    .role-desc { color: #94a3b8; font-size: 0.75rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .badge {
      padding: 0.125rem 0.375rem; border-radius: 12px; font-size: 0.625rem;
      font-weight: 600; text-transform: capitalize; flex-shrink: 0;
    }
    .badge-scope-provider { background: #fef2f2; color: #dc2626; }
    .badge-scope-tenant { background: #dbeafe; color: #1d4ed8; }
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
export class AssignRoleDialogComponent implements OnInit {
  private permissionService = inject(PermissionService);
  private dialogService = inject(DialogService);
  private data = inject<AssignRoleDialogData>(DIALOG_DATA);

  searchQuery = '';
  loading = signal(true);
  private allRoles = signal<Role[]>([]);
  filteredRoles = signal<Role[]>([]);

  ngOnInit(): void {
    this.permissionService.listRoles().subscribe({
      next: (roles) => {
        const excludeSet = new Set(this.data?.excludeIds ?? []);
        const available = roles.filter((r) => !excludeSet.has(r.id));
        this.allRoles.set(available);
        this.filteredRoles.set(available);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  onSearch(): void {
    const q = this.searchQuery.toLowerCase().trim();
    if (!q) {
      this.filteredRoles.set(this.allRoles());
      return;
    }
    this.filteredRoles.set(
      this.allRoles().filter(
        (r) =>
          r.name.toLowerCase().includes(q) ||
          (r.description?.toLowerCase().includes(q) ?? false) ||
          r.scope.toLowerCase().includes(q),
      ),
    );
  }

  onAssign(role: Role): void {
    this.dialogService.close(role);
  }

  onClose(): void {
    this.dialogService.close(undefined);
  }
}
