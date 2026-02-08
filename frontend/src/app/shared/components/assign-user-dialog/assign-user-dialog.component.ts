/**
 * Overview: Dialog for searching and selecting a user to add as group member, with server-side search.
 * Architecture: Shared dialog component for user assignment (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/forms, app/core/services/user.service, app/shared/services/dialog.service
 * Concepts: User assignment, server-side search, debounced input, dialog pattern
 */
import { Component, inject, signal, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subject, debounceTime, distinctUntilChanged, switchMap, of } from 'rxjs';
import { UserService } from '@core/services/user.service';
import { User } from '@core/models/user.model';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';

export interface AssignUserDialogData {
  excludeIds?: string[];
}

@Component({
  selector: 'nimbus-assign-user-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="assign-dialog">
      <h2>Add Member</h2>
      <input
        class="search-input"
        placeholder="Search users by email or name..."
        [(ngModel)]="searchQuery"
        (ngModelChange)="onSearch($event)"
      />
      <div class="user-list">
        @for (user of users(); track user.id) {
          <div class="user-row">
            <div class="user-info">
              <span class="user-email">{{ user.email }}</span>
              @if (user.display_name) {
                <span class="user-name">{{ user.display_name }}</span>
              }
            </div>
            <button class="btn btn-sm btn-primary" (click)="onSelect(user)">Add</button>
          </div>
        } @empty {
          <div class="empty">
            @if (searching()) {
              Searching...
            } @else if (searchQuery.length >= 2) {
              No matching users
            } @else {
              Type at least 2 characters to search
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
    .user-list { max-height: 320px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 6px; }
    .user-row {
      display: flex; align-items: center; justify-content: space-between;
      padding: 0.625rem 0.75rem; border-bottom: 1px solid #f1f5f9;
    }
    .user-row:last-child { border-bottom: none; }
    .user-row:hover { background: #f8fafc; }
    .user-info { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; min-width: 0; }
    .user-email { font-weight: 500; color: #1e293b; font-size: 0.8125rem; }
    .user-name { color: #94a3b8; font-size: 0.75rem; }
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
export class AssignUserDialogComponent implements OnInit, OnDestroy {
  private userService = inject(UserService);
  private dialogService = inject(DialogService);
  private data = inject<AssignUserDialogData>(DIALOG_DATA);

  searchQuery = '';
  searching = signal(false);
  users = signal<User[]>([]);
  private search$ = new Subject<string>();

  ngOnInit(): void {
    const excludeSet = new Set(this.data?.excludeIds ?? []);

    this.search$
      .pipe(
        debounceTime(300),
        distinctUntilChanged(),
        switchMap((query) => {
          if (!query || query.length < 2) {
            this.searching.set(false);
            return of(null);
          }
          this.searching.set(true);
          return this.userService.listUsers(0, 20, query);
        }),
      )
      .subscribe((result) => {
        this.searching.set(false);
        if (!result) {
          this.users.set([]);
          return;
        }
        this.users.set(result.items.filter((u) => !excludeSet.has(u.id)));
      });
  }

  ngOnDestroy(): void {
    this.search$.complete();
  }

  onSearch(query: string): void {
    this.search$.next(query);
  }

  onSelect(user: User): void {
    this.dialogService.close(user);
  }

  onClose(): void {
    this.dialogService.close(undefined);
  }
}
