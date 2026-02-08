/**
 * Overview: Styled confirmation dialog with danger/info variants replacing browser confirm().
 * Architecture: Shared component for user confirmation prompts (Section 3.2)
 * Dependencies: @angular/core, app/shared/services/dialog.service
 * Concepts: Confirmation dialogs, danger actions, user consent
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DIALOG_DATA, DialogService } from '@shared/services/dialog.service';

export interface ConfirmDialogData {
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'danger' | 'info';
}

@Component({
  selector: 'nimbus-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="confirm-dialog">
      <h2 class="confirm-title">{{ data.title }}</h2>
      <p class="confirm-message">{{ data.message }}</p>
      <div class="confirm-actions">
        <button class="btn btn-cancel" (click)="onCancel()">
          {{ data.cancelLabel || 'Cancel' }}
        </button>
        <button
          class="btn"
          [class.btn-danger]="data.variant === 'danger'"
          [class.btn-primary]="data.variant !== 'danger'"
          (click)="onConfirm()"
        >
          {{ data.confirmLabel || 'Confirm' }}
        </button>
      </div>
    </div>
  `,
  styles: [`
    .confirm-dialog { padding: 1.5rem; }
    .confirm-title {
      margin: 0 0 0.75rem 0; font-size: 1.125rem; font-weight: 600; color: #1e293b;
    }
    .confirm-message {
      margin: 0 0 1.5rem 0; font-size: 0.875rem; color: #64748b; line-height: 1.5;
    }
    .confirm-actions { display: flex; justify-content: flex-end; gap: 0.75rem; }
    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1.25rem;
      transition: background 0.15s;
    }
    .btn-cancel {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-cancel:hover { background: #f8fafc; }
    .btn-danger { background: #dc2626; color: #fff; border: none; }
    .btn-danger:hover { background: #b91c1c; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
  `],
})
export class ConfirmDialogComponent {
  data = inject<ConfirmDialogData>(DIALOG_DATA);
  private dialogService = inject(DialogService);

  onConfirm(): void {
    this.dialogService.close(true);
  }

  onCancel(): void {
    this.dialogService.close(false);
  }
}
