/**
 * Overview: Modal dialog for requesting user impersonation with mode selection and password re-entry.
 * Architecture: Feature component for impersonation request (Section 3.2)
 * Dependencies: @angular/core, @angular/forms, @angular/common
 * Concepts: Impersonation request, mode selection, password re-authentication
 */
import { Component, inject, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ImpersonationService } from '@core/services/impersonation.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { ToastService } from '@shared/services/toast.service';
import { ImpersonationMode } from '@core/models/impersonation.model';

@Component({
  selector: 'nimbus-impersonation-request-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule],
  template: `
    <div class="dialog-overlay" (click)="close()">
      <div class="dialog" (click)="$event.stopPropagation()">
        <div class="dialog-header">
          <h2>Request Impersonation</h2>
          <button class="close-btn" (click)="close()">&times;</button>
        </div>

        <div class="dialog-body">
          <div class="field">
            <label>Target User</label>
            <span class="field-value">{{ targetEmail }}</span>
          </div>

          <div class="field">
            <label>Mode</label>
            <div class="mode-toggle">
              <button
                class="mode-btn"
                [class.active]="mode === 'STANDARD'"
                (click)="mode = 'STANDARD'"
              >Standard</button>
              <button
                class="mode-btn"
                [class.active]="mode === 'OVERRIDE'"
                (click)="mode = 'OVERRIDE'"
              >Override</button>
            </div>
            <p class="mode-desc">
              @if (mode === 'STANDARD') {
                Act as this user via temporary token. Their account is unaffected.
              } @else {
                Deactivate user and set temporary password for direct login. User is restored when session ends.
              }
            </p>
          </div>

          <div class="field">
            <label for="reason">Reason</label>
            <textarea
              id="reason"
              class="form-input"
              [(ngModel)]="reason"
              placeholder="Explain why impersonation is needed (min 10 chars)..."
              rows="3"
            ></textarea>
          </div>

          <div class="field">
            <label for="password">Your Password</label>
            <input
              id="password"
              type="password"
              class="form-input"
              [(ngModel)]="password"
              placeholder="Re-enter your password to confirm"
            />
          </div>

          @if (errorMsg()) {
            <div class="error-msg">{{ errorMsg() }}</div>
          }
        </div>

        <div class="dialog-footer">
          <button class="btn btn-secondary" (click)="close()">Cancel</button>
          <button
            class="btn btn-primary"
            [disabled]="submitting() || reason.length < 10 || !password"
            (click)="submit()"
          >
            {{ submitting() ? 'Requesting...' : 'Request Impersonation' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [`
    .dialog-overlay {
      position: fixed; inset: 0; background: rgba(0, 0, 0, 0.5);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 8px; width: 480px; max-width: 90vw;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }
    .dialog-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem 1.25rem; border-bottom: 1px solid #e2e8f0;
    }
    .dialog-header h2 { margin: 0; font-size: 1.125rem; font-weight: 600; }
    .close-btn {
      background: none; border: none; font-size: 1.25rem; color: #64748b;
      cursor: pointer; padding: 0.25rem;
    }
    .dialog-body { padding: 1.25rem; }
    .field { margin-bottom: 1rem; }
    .field label {
      display: block; font-size: 0.8125rem; font-weight: 600; color: #374151;
      margin-bottom: 0.375rem;
    }
    .field-value { font-size: 0.8125rem; color: #1e293b; }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0;
      border-radius: 6px; font-size: 0.8125rem; font-family: inherit;
      box-sizing: border-box;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1); }
    .mode-toggle { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; }
    .mode-btn {
      flex: 1; padding: 0.5rem; border: 1px solid #e2e8f0; border-radius: 6px;
      background: #fff; font-size: 0.8125rem; font-weight: 500; cursor: pointer;
      font-family: inherit; transition: all 0.15s;
    }
    .mode-btn.active { background: #3b82f6; color: #fff; border-color: #3b82f6; }
    .mode-desc { font-size: 0.75rem; color: #64748b; margin: 0; }
    .error-msg {
      background: #fef2f2; color: #dc2626; padding: 0.5rem 0.75rem;
      border-radius: 6px; font-size: 0.8125rem; border: 1px solid #fecaca;
    }
    .dialog-footer {
      display: flex; justify-content: flex-end; gap: 0.5rem;
      padding: 1rem 1.25rem; border-top: 1px solid #e2e8f0;
    }
    .btn {
      padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.8125rem;
      font-weight: 500; cursor: pointer; font-family: inherit; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #f1f5f9; color: #374151; }
    .btn-secondary:hover { background: #e2e8f0; }
  `],
})
export class ImpersonationRequestDialogComponent {
  private impersonationService = inject(ImpersonationService);
  private tenantContext = inject(TenantContextService);
  private toastService = inject(ToastService);

  targetUserId = '';
  targetEmail = '';
  mode: ImpersonationMode = 'STANDARD';
  reason = '';
  password = '';
  submitting = signal(false);
  errorMsg = signal('');

  private resolveDialog: ((result: boolean) => void) | null = null;

  open(userId: string, email: string): Promise<boolean> {
    this.targetUserId = userId;
    this.targetEmail = email;
    this.mode = 'STANDARD';
    this.reason = '';
    this.password = '';
    this.errorMsg.set('');
    return new Promise((resolve) => {
      this.resolveDialog = resolve;
    });
  }

  submit(): void {
    const tenantId = this.tenantContext.currentTenantId();
    if (!tenantId) {
      this.errorMsg.set('No tenant context');
      return;
    }

    this.submitting.set(true);
    this.errorMsg.set('');

    this.impersonationService
      .requestImpersonation({
        target_user_id: this.targetUserId,
        tenant_id: tenantId,
        mode: this.mode,
        reason: this.reason,
        password: this.password,
      })
      .subscribe({
        next: (session) => {
          this.submitting.set(false);
          this.toastService.success(
            session.status === 'PENDING_APPROVAL'
              ? 'Impersonation request submitted for approval'
              : 'Impersonation session started',
          );
          this.resolveDialog?.(true);
        },
        error: (err) => {
          this.submitting.set(false);
          this.errorMsg.set(err.error?.detail?.error?.message || 'Request failed');
        },
      });
  }

  close(): void {
    this.resolveDialog?.(false);
  }
}
