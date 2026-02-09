/**
 * Overview: Profitability dashboard — aggregated metrics and breakdowns by client, region, service.
 * Architecture: Catalog feature component (Section 8)
 * Dependencies: @angular/core, app/core/services/delivery.service
 * Concepts: Profitability analysis, revenue, cost, margin, estimation aggregation
 */
import {
  Component,
  inject,
  signal,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { DeliveryService } from '@core/services/delivery.service';
import {
  ProfitabilityOverview,
  ProfitabilityByEntity,
} from '@shared/models/delivery.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ToastService } from '@shared/services/toast.service';
import { ClientProfitabilityComponent } from './client-profitability.component';
import { RegionProfitabilityComponent } from './region-profitability.component';

type Tab = 'client' | 'region' | 'service';

@Component({
  selector: 'nimbus-profitability-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    LayoutComponent,
    HasPermissionDirective,
    ClientProfitabilityComponent,
    RegionProfitabilityComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="profitability-page">
        <div class="page-header">
          <h1>Profitability Dashboard</h1>
        </div>

        <!-- Summary Metric Cards -->
        <div class="metric-cards">
          <div class="metric-card">
            <div class="metric-label">
              <span class="metric-icon">$</span>
              Total Revenue
            </div>
            <div class="metric-value">{{ overview().totalRevenue | number:'1.2-2' }}</div>
            <div class="metric-sub">{{ overview().estimationCount }} estimations</div>
          </div>

          <div class="metric-card">
            <div class="metric-label">
              <span class="metric-icon">$</span>
              Total Cost
            </div>
            <div class="metric-value">{{ overview().totalCost | number:'1.2-2' }}</div>
          </div>

          <div class="metric-card">
            <div class="metric-label">
              <span class="metric-icon">$</span>
              Total Margin
            </div>
            <div class="metric-value"
              [class.positive]="overview().totalMargin >= 0"
              [class.negative]="overview().totalMargin < 0"
            >
              {{ overview().totalMargin | number:'1.2-2' }}
            </div>
          </div>

          <div class="metric-card">
            <div class="metric-label">
              <span class="metric-icon">%</span>
              Margin %
            </div>
            <div class="metric-value"
              [class.positive]="overview().marginPercent >= 0"
              [class.negative]="overview().marginPercent < 0"
            >
              {{ overview().marginPercent | number:'1.1-1' }}%
            </div>
          </div>
        </div>

        <!-- Tab Navigation -->
        <div class="tab-bar">
          <button
            class="tab-btn"
            [class.active]="activeTab() === 'client'"
            (click)="switchTab('client')"
          >By Client</button>
          <button
            class="tab-btn"
            [class.active]="activeTab() === 'region'"
            (click)="switchTab('region')"
          >By Region</button>
          <button
            class="tab-btn"
            [class.active]="activeTab() === 'service'"
            (click)="switchTab('service')"
          >By Service</button>
        </div>

        <!-- Tab Content -->
        <div class="tab-content">
          @if (activeTab() === 'client') {
            <nimbus-client-profitability [data]="clientData()" />
          }
          @if (activeTab() === 'region') {
            <nimbus-region-profitability [data]="regionData()" />
          }
          @if (activeTab() === 'service') {
            <div class="table-container">
              <table class="table">
                <thead>
                  <tr>
                    <th>Service Name</th>
                    <th class="num">Revenue</th>
                    <th class="num">Cost</th>
                    <th class="num">Margin</th>
                    <th class="num">Margin %</th>
                    <th class="num"># Estimations</th>
                  </tr>
                </thead>
                <tbody>
                  @for (row of serviceData(); track row.entityId) {
                    <tr>
                      <td class="name-cell">{{ row.entityName }}</td>
                      <td class="num">{{ row.totalRevenue | number:'1.2-2' }}</td>
                      <td class="num">{{ row.totalCost | number:'1.2-2' }}</td>
                      <td class="num">{{ row.marginAmount | number:'1.2-2' }}</td>
                      <td class="num"
                        [class.positive]="row.marginPercent >= 0"
                        [class.negative]="row.marginPercent < 0"
                      >
                        {{ row.marginPercent | number:'1.1-1' }}%
                      </td>
                      <td class="num">{{ row.estimationCount }}</td>
                    </tr>
                  } @empty {
                    <tr>
                      <td colspan="6" class="empty-state">No service profitability data available</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          }
        </div>

        @if (loading()) {
          <div class="loading-overlay">
            <span class="loading-text">Loading profitability data...</span>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .profitability-page { padding: 0; position: relative; }
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }

    /* ── Metric Cards ──────────────────────────────────────────────── */
    .metric-cards {
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .metric-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1.25rem 1.5rem;
    }
    .metric-label {
      display: flex; align-items: center; gap: 0.5rem;
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
      margin-bottom: 0.5rem;
    }
    .metric-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 24px; height: 24px; border-radius: 6px;
      background: #f1f5f9; color: #3b82f6; font-weight: 700; font-size: 0.75rem;
    }
    .metric-value {
      font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .metric-sub {
      font-size: 0.75rem; color: #94a3b8; margin-top: 0.25rem;
    }
    .positive { color: #16a34a; }
    .negative { color: #dc2626; }

    /* ── Tab Bar ───────────────────────────────────────────────────── */
    .tab-bar {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0;
      margin-bottom: 1rem;
    }
    .tab-btn {
      padding: 0.625rem 1.25rem; border: none; background: none;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      cursor: pointer; border-bottom: 2px solid transparent;
      margin-bottom: -2px; transition: color 0.15s, border-color 0.15s;
      font-family: inherit;
    }
    .tab-btn:hover { color: #1e293b; }
    .tab-btn.active {
      color: #3b82f6; border-bottom-color: #3b82f6; font-weight: 600;
    }

    /* ── Tab Content (inline service table) ─────────────────────── */
    .tab-content { min-height: 200px; }
    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .table {
      width: 100%; border-collapse: collapse; font-size: 0.8125rem;
    }
    .table th, .table td {
      padding: 0.75rem 1rem; text-align: left; border-bottom: 1px solid #f1f5f9;
    }
    .table th {
      font-weight: 600; color: #64748b; font-size: 0.75rem;
      text-transform: uppercase; letter-spacing: 0.05em;
    }
    .table th.num, .table td.num { text-align: right; }
    .table tbody tr:hover { background: #f8fafc; }
    .name-cell { font-weight: 500; color: #1e293b; }
    .empty-state { text-align: center; color: #94a3b8; padding: 2rem; }

    /* ── Loading Overlay ───────────────────────────────────────────── */
    .loading-overlay {
      position: absolute; top: 0; left: 0; right: 0; bottom: 0;
      display: flex; align-items: center; justify-content: center;
      background: rgba(255, 255, 255, 0.7); border-radius: 8px; z-index: 10;
    }
    .loading-text {
      font-size: 0.875rem; color: #64748b; font-weight: 500;
    }

    /* ── Responsive ─────────────────────────────────────────────── */
    @media (max-width: 960px) {
      .metric-cards { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 560px) {
      .metric-cards { grid-template-columns: 1fr; }
    }
  `],
})
export class ProfitabilityDashboardComponent implements OnInit {
  private deliveryService = inject(DeliveryService);
  private toastService = inject(ToastService);

  overview = signal<ProfitabilityOverview>({
    totalRevenue: 0,
    totalCost: 0,
    totalMargin: 0,
    marginPercent: 0,
    estimationCount: 0,
  });
  clientData = signal<ProfitabilityByEntity[]>([]);
  regionData = signal<ProfitabilityByEntity[]>([]);
  serviceData = signal<ProfitabilityByEntity[]>([]);
  activeTab = signal<Tab>('client');
  loading = signal(false);

  ngOnInit(): void {
    this.loadData();
  }

  switchTab(tab: Tab): void {
    this.activeTab.set(tab);
  }

  private loadData(): void {
    this.loading.set(true);

    this.deliveryService.getProfitabilityOverview().subscribe({
      next: (data) => this.overview.set(data),
      error: (err) => this.toastService.error(err.message || 'Failed to load profitability overview'),
    });

    this.deliveryService.getProfitabilityByClient().subscribe({
      next: (data) => this.clientData.set(data),
      error: (err) => this.toastService.error(err.message || 'Failed to load client profitability'),
    });

    this.deliveryService.getProfitabilityByRegion().subscribe({
      next: (data) => this.regionData.set(data),
      error: (err) => this.toastService.error(err.message || 'Failed to load region profitability'),
    });

    this.deliveryService.getProfitabilityByService().subscribe({
      next: (data) => {
        this.serviceData.set(data);
        this.loading.set(false);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to load service profitability');
        this.loading.set(false);
      },
    });
  }
}
