/**
 * Overview: Thin wrapper around DialogService for confirmation prompts.
 * Architecture: Shared service for confirm dialogs (Section 3.2)
 * Dependencies: @angular/core, app/shared/services/dialog.service, app/shared/components/confirm-dialog
 * Concepts: Confirmation dialogs, promise-based API
 */
import { Injectable, inject } from '@angular/core';
import { DialogService } from './dialog.service';
import {
  ConfirmDialogComponent,
  ConfirmDialogData,
} from '@shared/components/confirm-dialog/confirm-dialog.component';

@Injectable({ providedIn: 'root' })
export class ConfirmService {
  private dialogService = inject(DialogService);

  confirm(opts: ConfirmDialogData): Promise<boolean> {
    return this.dialogService.open<boolean>(ConfirmDialogComponent, opts).then(
      (result) => !!result,
    );
  }
}
