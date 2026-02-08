/**
 * Overview: Renders a breadcrumb navigation trail with clickable links.
 * Architecture: Shared UI component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/shared/services/breadcrumb.service
 * Concepts: Breadcrumb navigation, route-aware rendering, hash-based routing
 */
import { Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { BreadcrumbService } from '../../services/breadcrumb.service';

@Component({
  selector: 'nimbus-breadcrumb',
  standalone: true,
  imports: [CommonModule, RouterLink],
  template: `
    @if (breadcrumbService.breadcrumbs().length > 0) {
      <nav class="breadcrumb-bar" aria-label="Breadcrumb">
        @for (crumb of breadcrumbService.breadcrumbs(); track crumb.url; let last = $last) {
          @if (!last) {
            <a [routerLink]="crumb.url" class="breadcrumb-link">{{ crumb.label }}</a>
            <span class="breadcrumb-separator">/</span>
          } @else {
            <span class="breadcrumb-current">{{ crumb.label }}</span>
          }
        }
      </nav>
    }
  `,
  styles: [`
    .breadcrumb-bar {
      display: flex;
      align-items: center;
      gap: 0.375rem;
      padding-bottom: 0.75rem;
      font-size: 0.8125rem;
      line-height: 1;
    }
    .breadcrumb-link {
      color: #6b7280;
      text-decoration: none;
      transition: color 0.15s ease;
    }
    .breadcrumb-link:hover {
      color: #3b82f6;
    }
    .breadcrumb-separator {
      color: #d1d5db;
      user-select: none;
    }
    .breadcrumb-current {
      color: #374151;
      font-weight: 500;
    }
  `],
})
export class BreadcrumbComponent {
  readonly breadcrumbService = inject(BreadcrumbService);
}
