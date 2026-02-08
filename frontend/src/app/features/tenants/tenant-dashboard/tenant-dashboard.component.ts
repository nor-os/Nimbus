/**
 * Overview: Tenant dashboard showing overview cards, quota usage, hierarchy, and quick actions.
 * Architecture: Feature component for tenant overview (Section 3.2)
 * Dependencies: @angular/core, @angular/router, app/core/services/tenant.service
 * Concepts: Multi-tenancy, tenant dashboard, quota monitoring
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TenantService } from '@core/services/tenant.service';
import { TenantDetail, TenantHierarchy, TenantStats } from '@core/models/tenant.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { QuotaCardComponent } from './components/quota-card/quota-card.component';
import { TenantTreeComponent } from './components/tenant-tree/tenant-tree.component';

@Component({
  selector: 'nimbus-tenant-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent, QuotaCardComponent, TenantTreeComponent],
  template: `
    <nimbus-layout>
      <div class="tenant-dashboard">
        @if (tenant()) {
          <div class="page-header">
            <div>
              <h1>{{ tenant()!.name }}</h1>
              <span class="level-badge" [class]="'level-' + tenant()!.level">
                {{ getLevelLabel(tenant()!.level) }}
              </span>
            </div>
            <div class="header-actions">
              <a [routerLink]="['/tenants', tenant()!.id, 'settings']" class="btn btn-secondary">Settings</a>
            </div>
          </div>

          <div class="stats-cards">
            <div class="stat-card">
              <div class="stat-value">{{ stats()?.total_users ?? 0 }}</div>
              <div class="stat-label">Users</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats()?.total_compartments ?? 0 }}</div>
              <div class="stat-label">Compartments</div>
            </div>
            <div class="stat-card">
              <div class="stat-value">{{ stats()?.total_children ?? 0 }}</div>
              <div class="stat-label">Child Tenants</div>
            </div>
          </div>

          @if (stats()?.quotas?.length) {
            <section class="section">
              <h2>Quotas</h2>
              <div class="quota-grid">
                @for (quota of stats()!.quotas; track quota.id) {
                  <nimbus-quota-card [quota]="quota" />
                }
              </div>
            </section>
          }

          @if (hierarchy()) {
            <section class="section">
              <h2>Hierarchy</h2>
              <nimbus-tenant-tree [nodes]="[hierarchy()!]" />
            </section>
          }

          <section class="section">
            <h2>Quick Actions</h2>
            <div class="action-buttons">
              <a routerLink="/tenants/create" [queryParams]="{ parent: tenant()!.id }" class="btn btn-outline">
                Create Child Tenant
              </a>
              <a [routerLink]="['/tenants', tenant()!.id, 'settings']" class="btn btn-outline">
                Manage Settings
              </a>
            </div>
          </section>
        } @else {
          <p class="loading">Loading tenant...</p>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .tenant-dashboard { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0 0 0.375rem; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .level-badge {
      font-size: 0.6875rem; font-weight: 600; padding: 0.125rem 0.5rem; border-radius: 12px;
    }
    .level-0 { background: #dbeafe; color: #1d4ed8; }
    .level-1 { background: #f3e8ff; color: #7c3aed; }
    .level-2 { background: #dcfce7; color: #16a34a; }
    .header-actions { display: flex; gap: 0.5rem; }
    .stats-cards {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
      gap: 1rem; margin-bottom: 2rem;
    }
    .stat-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem; text-align: center;
    }
    .stat-value { font-size: 2rem; font-weight: 700; color: #3b82f6; }
    .stat-label { font-size: 0.8125rem; color: #64748b; margin-top: 0.25rem; }
    .section { margin-bottom: 2rem; }
    .section h2 { font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin-bottom: 1rem; }
    .quota-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 1rem;
    }
    .action-buttons { display: flex; gap: 0.75rem; flex-wrap: wrap; }
    .btn-secondary {
      padding: 0.375rem 0.875rem; border: 1px solid #e2e8f0; border-radius: 6px;
      text-decoration: none; color: #374151; font-size: 0.8125rem; font-weight: 500;
      background: #fff; transition: background 0.15s;
    }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-outline {
      padding: 0.5rem 1rem; border: 1px solid #3b82f6; border-radius: 6px;
      text-decoration: none; color: #3b82f6; font-size: 0.8125rem; font-weight: 500;
      background: transparent; transition: background 0.15s;
    }
    .btn-outline:hover { background: #eff6ff; }
    .loading { color: #94a3b8; text-align: center; padding: 2rem; }
  `],
})
export class TenantDashboardComponent implements OnInit {
  private tenantService = inject(TenantService);
  private route = inject(ActivatedRoute);

  tenant = signal<TenantDetail | null>(null);
  stats = signal<TenantStats | null>(null);
  hierarchy = signal<TenantHierarchy | null>(null);

  ngOnInit(): void {
    const id = this.route.snapshot.params['id'];
    if (!id) return;

    this.tenantService.getTenant(id).subscribe({
      next: (t) => this.tenant.set(t),
    });

    this.tenantService.getTenantStats(id).subscribe({
      next: (s) => this.stats.set(s),
    });

    this.tenantService.getTenantHierarchy(id).subscribe({
      next: (h) => this.hierarchy.set(h),
    });
  }

  getLevelLabel(level: number): string {
    return ['Provider', 'Tenant', 'Sub-tenant'][level] ?? `Level ${level}`;
  }
}
