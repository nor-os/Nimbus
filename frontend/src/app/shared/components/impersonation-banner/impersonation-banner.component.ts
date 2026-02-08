/**
 * Overview: Amber banner shown during impersonation with countdown and session controls.
 * Architecture: Shared layout component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, app/core/services/impersonation.service
 * Concepts: Impersonation awareness, session lifecycle, countdown timer
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ImpersonationService } from '@core/services/impersonation.service';

@Component({
  selector: 'nimbus-impersonation-banner',
  standalone: true,
  imports: [CommonModule],
  template: `
    @if (impersonationService.isImpersonating()) {
      <div class="impersonation-banner">
        <span class="banner-icon">&#9888;</span>
        <span class="banner-text">
          Impersonating user &mdash; {{ impersonationService.remainingTime() }} remaining
        </span>
        <div class="banner-actions">
          <button class="banner-btn banner-btn-extend" (click)="extend()">
            Extend
          </button>
          <button class="banner-btn banner-btn-end" (click)="endSession()">
            End Session
          </button>
        </div>
      </div>
    }
  `,
  styles: [`
    .impersonation-banner {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      padding: 0.5rem 1.5rem;
      background: linear-gradient(90deg, #f59e0b, #d97706);
      color: #fff;
      font-size: 0.8125rem;
      font-weight: 500;
      z-index: 100;
    }
    .banner-icon {
      font-size: 1rem;
    }
    .banner-text {
      flex: 1;
    }
    .banner-actions {
      display: flex;
      gap: 0.5rem;
    }
    .banner-btn {
      padding: 0.25rem 0.75rem;
      border: 1px solid rgba(255, 255, 255, 0.4);
      border-radius: 4px;
      background: rgba(255, 255, 255, 0.15);
      color: #fff;
      font-size: 0.75rem;
      font-weight: 600;
      cursor: pointer;
      font-family: inherit;
      transition: background 0.15s;
    }
    .banner-btn:hover {
      background: rgba(255, 255, 255, 0.25);
    }
    .banner-btn-end {
      background: rgba(220, 38, 38, 0.3);
      border-color: rgba(220, 38, 38, 0.5);
    }
    .banner-btn-end:hover {
      background: rgba(220, 38, 38, 0.5);
    }
  `],
})
export class ImpersonationBannerComponent {
  impersonationService = inject(ImpersonationService);

  extend(): void {
    const info = this.impersonationService.currentImpersonation();
    if (info?.session_id) {
      this.impersonationService.extendSession(info.session_id, 30).subscribe();
    }
  }

  endSession(): void {
    const info = this.impersonationService.currentImpersonation();
    if (info?.session_id) {
      this.impersonationService.endSession(info.session_id).subscribe({
        next: () => window.location.reload(),
      });
    }
  }
}
