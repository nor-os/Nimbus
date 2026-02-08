/**
 * Overview: Progress bar card showing quota usage with color-coded status.
 * Architecture: Shared tenant dashboard component (Section 3.2)
 * Dependencies: @angular/core, @angular/common
 * Concepts: Quotas, resource limits, visual indicators
 */
import { Component, Input, computed, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TenantQuota } from '@core/models/tenant.model';

@Component({
  selector: 'nimbus-quota-card',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="quota-card">
      <div class="quota-header">
        <span class="quota-name">{{ formatQuotaType(quota.quota_type) }}</span>
        <span class="quota-badge" [class]="'badge-' + quota.enforcement">
          {{ quota.enforcement }}
        </span>
      </div>
      <div class="quota-bar">
        <div
          class="quota-fill"
          [style.width.%]="percentage()"
          [class]="colorClass()"
        ></div>
      </div>
      <div class="quota-info">
        {{ quota.current_usage }} / {{ quota.limit_value }}
        <span class="quota-pct">({{ percentage() }}%)</span>
      </div>
    </div>
  `,
  styles: [`
    .quota-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; min-width: 200px;
    }
    .quota-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 0.625rem;
    }
    .quota-name { font-weight: 600; font-size: 0.8125rem; color: #1e293b; }
    .quota-badge {
      font-size: 0.5625rem; padding: 0.125rem 0.375rem; border-radius: 8px;
      text-transform: uppercase; font-weight: 700; letter-spacing: 0.05em;
    }
    .badge-hard { background: #fef2f2; color: #dc2626; }
    .badge-soft { background: #fffbeb; color: #d97706; }
    .quota-bar {
      height: 6px; background: #f1f5f9; border-radius: 3px; overflow: hidden;
      margin-bottom: 0.5rem;
    }
    .quota-fill {
      height: 100%; border-radius: 3px; transition: width 0.3s ease;
    }
    .color-green { background: #22c55e; }
    .color-yellow { background: #f59e0b; }
    .color-red { background: #ef4444; }
    .quota-info { font-size: 0.75rem; color: #64748b; }
    .quota-pct { color: #94a3b8; }
  `],
})
export class QuotaCardComponent {
  @Input({ required: true }) quota!: TenantQuota;

  percentage = computed(() => {
    if (this.quota.limit_value === 0) return 0;
    return Math.min(100, Math.round((this.quota.current_usage / this.quota.limit_value) * 100));
  });

  colorClass = computed(() => {
    const pct = this.percentage();
    if (pct >= 90) return 'color-red';
    if (pct >= 70) return 'color-yellow';
    return 'color-green';
  });

  formatQuotaType(type: string): string {
    return type
      .replace('max_', '')
      .split('_')
      .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
      .join(' ');
  }
}
