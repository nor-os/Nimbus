/**
 * Overview: Main dashboard showing current tenant overview and key metrics.
 * Architecture: Feature component for authenticated landing page (Section 3.2)
 * Dependencies: @angular/core
 * Concepts: Dashboard, authenticated view, tenant context
 */
import { Component, inject, signal, effect } from '@angular/core';
import { CommonModule } from '@angular/common';
import { EMPTY, catchError } from 'rxjs';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { AuthService } from '@core/auth/auth.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { TenantService } from '@core/services/tenant.service';
import { PermissionCheckService } from '@core/services/permission-check.service';
import { TenantStats } from '@core/models/tenant.model';
import { QuotaCardComponent } from '../tenants/tenant-dashboard/components/quota-card/quota-card.component';

@Component({
  selector: 'nimbus-dashboard',
  standalone: true,
  imports: [CommonModule, LayoutComponent, QuotaCardComponent],
  template: `
    <nimbus-layout>
      <div class="dashboard">
        <div class="page-header">
          <h1>Dashboard</h1>
          @if (authService.currentUser(); as user) {
            <p class="subtitle">Welcome back, {{ user.display_name ?? user.email }}</p>
          }
        </div>

        @if (stats()) {
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-value">{{ stats()!.total_users }}</div>
              <div class="stat-label">Users</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats()!.total_compartments }}</div>
              <div class="stat-label">Compartments</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats()!.total_children }}</div>
              <div class="stat-label">Child Tenants</div>
            </div>
          </div>

          @if (stats()!.quotas.length) {
            <section class="section">
              <h2>Quota Usage</h2>
              <div class="quota-grid">
                @for (quota of stats()!.quotas; track quota.id) {
                  <nimbus-quota-card [quota]="quota" />
                }
              </div>
            </section>
          }
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .dashboard { padding: 0; }

    .page-header { margin-bottom: 1.5rem; }
    .page-header h1 {
      margin: 0;
      font-size: 1.5rem;
      font-weight: 700;
      color: #1e293b;
    }
    .subtitle {
      margin: 0.25rem 0 0;
      color: #64748b;
      font-size: 0.875rem;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }
    .stat-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1.25rem;
      text-align: center;
    }
    .stat-value { font-size: 2rem; font-weight: 700; color: #3b82f6; }
    .stat-label { font-size: 0.8125rem; color: #64748b; margin-top: 0.25rem; }

    .section { margin-bottom: 2rem; }
    .section h2 {
      font-size: 1.0625rem;
      font-weight: 600;
      color: #1e293b;
      margin-bottom: 1rem;
    }

    .quota-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
      gap: 1rem;
    }
  `],
})
export class DashboardComponent {
  authService = inject(AuthService);
  tenantContext = inject(TenantContextService);
  private tenantService = inject(TenantService);
  private permissionCheck = inject(PermissionCheckService);

  stats = signal<TenantStats | null>(null);

  constructor() {
    // Reactively load stats when tenant context becomes available and user has permission
    effect(() => {
      const tenantId = this.tenantContext.currentTenantId();
      const canRead = this.permissionCheck.hasPermission('settings:tenant:read');
      if (tenantId && canRead) {
        this.tenantService.getTenantStats(tenantId).pipe(
          catchError(() => EMPTY),
        ).subscribe((s) => this.stats.set(s));
      }
    });
  }
}
