/**
 * Overview: Fixed bottom-right toast stack renderer with enter/exit animations.
 * Architecture: Shared layout component for toast notifications (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/shared/services/toast.service
 * Concepts: Toast notifications, CSS animations, auto-dismiss
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-toast-host',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="toast-stack">
      @for (toast of toastService.toasts(); track toast.id) {
        <div class="toast" [class]="'toast-' + toast.type">
          <span class="toast-icon">
            @switch (toast.type) {
              @case ('success') { &#10003; }
              @case ('error') { &#10007; }
              @case ('info') { &#8505; }
            }
          </span>
          <span class="toast-message">{{ toast.message }}</span>
          <button class="toast-close" (click)="toastService.dismiss(toast.id)">&times;</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-stack {
      position: fixed; bottom: 1.25rem; right: 1.25rem; z-index: 200;
      display: flex; flex-direction: column; gap: 0.5rem;
      max-width: 380px; width: 100%;
    }
    .toast {
      display: flex; align-items: center; gap: 0.625rem;
      padding: 0.75rem 1rem; border-radius: 8px;
      font-size: 0.8125rem; font-weight: 500;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
      animation: toastIn 0.2s ease-out;
    }
    .toast-success { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
    .toast-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
    .toast-info { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
    .toast-icon { font-size: 1rem; flex-shrink: 0; }
    .toast-message { flex: 1; line-height: 1.4; }
    .toast-close {
      background: none; border: none; cursor: pointer; font-size: 1.125rem;
      color: inherit; opacity: 0.6; padding: 0 0.25rem; line-height: 1;
      font-family: inherit;
    }
    .toast-close:hover { opacity: 1; }
    @keyframes toastIn {
      from { opacity: 0; transform: translateX(20px); }
      to { opacity: 1; transform: translateX(0); }
    }
  `],
})
export class ToastHostComponent {
  toastService = inject(ToastService);
}
