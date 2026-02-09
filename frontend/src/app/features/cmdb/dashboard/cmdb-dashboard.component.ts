/**
 * Overview: CMDB overview dashboard with summary stats, lifecycle bar chart,
 *     CI-by-class breakdown, and recent items quick-access list.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/common, @angular/router, rxjs,
 *     app/core/services/cmdb.service, app/core/services/catalog.service,
 *     app/core/services/tenant-context.service, app/shared/components/layout
 * Concepts: Dashboard aggregation, CSS-based charts, OnPush change detection, signals
 */
import {
  Component,
  inject,
  signal,
  computed,
  OnInit,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { forkJoin, EMPTY, catchError } from 'rxjs';
import { CmdbService } from '@core/services/cmdb.service';
import { CatalogService } from '@core/services/catalog.service';
import { TenantContextService } from '@core/services/tenant-context.service';
import { ConfigurationItem, CIClass } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

/** Lifecycle state with display metadata. */
interface LifecycleBreakdown {
  state: string;
  label: string;
  count: number;
  color: string;
  percent: number;
}

/** CI count grouped by class. */
interface ClassBreakdown {
  classId: string;
  className: string;
  count: number;
  percent: number;
}

@Component({
  selector: 'nimbus-cmdb-dashboard',
  standalone: true,
  imports: [CommonModule, RouterLink, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="cmdb-dashboard">
        <div class="page-header">
          <h1>CMDB Overview</h1>
          <div class="header-actions">
            <a routerLink="/cmdb" class="btn btn-secondary">All CIs</a>
            <a routerLink="/cmdb/create" class="btn btn-primary">Create CI</a>
          </div>
        </div>

        @if (loading()) {
          <div class="loading-state">Loading CMDB data...</div>
        }

        @if (!loading()) {
          <!-- Summary cards -->
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-icon">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <rect x="2" y="3" width="20" height="14" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                </svg>
              </div>
              <div class="stat-body">
                <div class="stat-value">{{ totalCIs() }}</div>
                <div class="stat-label">Configuration Items</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-classes">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M12 2L2 7l10 5 10-5-10-5z" />
                  <path d="M2 17l10 5 10-5" />
                  <path d="M2 12l10 5 10-5" />
                </svg>
              </div>
              <div class="stat-body">
                <div class="stat-value">{{ totalClasses() }}</div>
                <div class="stat-label">CI Classes</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-relationships">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" />
                  <polyline points="15 3 21 3 21 9" />
                  <line x1="10" y1="14" x2="21" y2="3" />
                </svg>
              </div>
              <div class="stat-body">
                <div class="stat-value">{{ totalRelationshipTypes() }}</div>
                <div class="stat-label">Relationship Types</div>
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-icon icon-templates">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="16" y1="13" x2="8" y2="13" />
                  <line x1="16" y1="17" x2="8" y2="17" />
                  <polyline points="10 9 9 9 8 9" />
                </svg>
              </div>
              <div class="stat-body">
                <div class="stat-value">{{ totalTemplates() }}</div>
                <div class="stat-label">Templates</div>
              </div>
            </div>
          </div>

          <!-- Charts row -->
          <div class="charts-row">
            <!-- Lifecycle state breakdown -->
            <div class="chart-card">
              <div class="chart-header">
                <h2>CI Lifecycle States</h2>
                <span class="chart-subtitle">Distribution across all CIs</span>
              </div>
              <div class="lifecycle-chart">
                @for (item of lifecycleBreakdown(); track item.state) {
                  <div class="bar-row">
                    <div class="bar-label">
                      <span
                        class="state-dot"
                        [style.background]="item.color"
                      ></span>
                      {{ item.label }}
                    </div>
                    <div class="bar-track">
                      <div
                        class="bar-fill"
                        [style.width.%]="item.percent"
                        [style.background]="item.color"
                      ></div>
                    </div>
                    <div class="bar-value">{{ item.count }}</div>
                  </div>
                } @empty {
                  <div class="empty-chart">No data available</div>
                }
              </div>
            </div>

            <!-- CI by class (top 10) -->
            <div class="chart-card">
              <div class="chart-header">
                <h2>CIs by Class</h2>
                <span class="chart-subtitle">Top 10 classes</span>
              </div>
              <div class="class-chart">
                @for (item of classBreakdown(); track item.classId) {
                  <div class="hbar-row">
                    <div class="hbar-label" [title]="item.className">
                      {{ item.className }}
                    </div>
                    <div class="hbar-track">
                      <div
                        class="hbar-fill"
                        [style.width.%]="item.percent"
                      ></div>
                      <span class="hbar-count">{{ item.count }}</span>
                    </div>
                  </div>
                } @empty {
                  <div class="empty-chart">No data available</div>
                }
              </div>
            </div>
          </div>

          <!-- Quick links row -->
          <div class="quick-links-row">
            <!-- Recent CIs -->
            <div class="chart-card recent-card">
              <div class="chart-header">
                <h2>Recent Configuration Items</h2>
                <a routerLink="/cmdb" class="view-all-link">View all</a>
              </div>
              <div class="recent-list">
                @for (ci of recentCIs(); track ci.id) {
                  <a class="recent-item" [routerLink]="['/cmdb', ci.id]">
                    <div class="recent-item-main">
                      <span class="recent-name">{{ ci.name }}</span>
                      <span class="recent-class">{{ ci.ciClassName }}</span>
                    </div>
                    <div class="recent-item-meta">
                      <span
                        class="lifecycle-badge"
                        [class.badge-planned]="ci.lifecycleState === 'planned'"
                        [class.badge-active]="ci.lifecycleState === 'active'"
                        [class.badge-maintenance]="ci.lifecycleState === 'maintenance'"
                        [class.badge-retired]="ci.lifecycleState === 'retired'"
                      >
                        {{ ci.lifecycleState | titlecase }}
                      </span>
                      <span class="recent-date">
                        {{ ci.updatedAt | date: 'shortDate' }}
                      </span>
                    </div>
                  </a>
                } @empty {
                  <div class="empty-chart">No configuration items yet</div>
                }
              </div>
            </div>

            <!-- Navigation shortcuts -->
            <div class="chart-card nav-card">
              <div class="chart-header">
                <h2>Quick Navigation</h2>
              </div>
              <div class="nav-grid">
                <a routerLink="/cmdb" class="nav-tile">
                  <div class="nav-tile-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <rect x="2" y="3" width="20" height="14" rx="2" />
                      <path d="M8 21h8M12 17v4" />
                    </svg>
                  </div>
                  <span>All CIs</span>
                </a>
                <a routerLink="/cmdb/classes" class="nav-tile">
                  <div class="nav-tile-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M12 2L2 7l10 5 10-5-10-5z" />
                      <path d="M2 17l10 5 10-5" />
                      <path d="M2 12l10 5 10-5" />
                    </svg>
                  </div>
                  <span>Classes</span>
                </a>
                <a routerLink="/cmdb/compartments" class="nav-tile">
                  <div class="nav-tile-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
                    </svg>
                  </div>
                  <span>Compartments</span>
                </a>
                <a routerLink="/cmdb/create" class="nav-tile">
                  <div class="nav-tile-icon icon-create">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="8" x2="12" y2="16" />
                      <line x1="8" y1="12" x2="16" y2="12" />
                    </svg>
                  </div>
                  <span>Create CI</span>
                </a>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .cmdb-dashboard { padding: 0; }

    /* ── Page header ───────────────────────────────────────────────── */
    .page-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1.5rem;
    }
    .page-header h1 {
      margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b;
    }
    .header-actions { display: flex; gap: 0.5rem; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; border: none; text-decoration: none;
      display: inline-flex; align-items: center;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-secondary {
      background: #fff; color: #374151; border: 1px solid #e2e8f0;
    }
    .btn-secondary:hover { background: #f8fafc; }

    .loading-state {
      padding: 4rem; text-align: center; color: #64748b;
      font-size: 0.875rem;
    }

    /* ── Summary stat cards ────────────────────────────────────────── */
    .stats-grid {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    @media (max-width: 1100px) {
      .stats-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 600px) {
      .stats-grid { grid-template-columns: 1fr; }
    }

    .stat-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
      padding: 1.25rem; display: flex; align-items: center; gap: 1rem;
      transition: box-shadow 0.15s;
    }
    .stat-card:hover {
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    }

    .stat-icon {
      width: 44px; height: 44px; border-radius: 10px;
      background: rgba(59, 130, 246, 0.1); color: #3b82f6;
      display: flex; align-items: center; justify-content: center;
      flex-shrink: 0;
    }
    .stat-icon svg { width: 22px; height: 22px; }
    .stat-icon.icon-classes { background: rgba(139, 92, 246, 0.1); color: #8b5cf6; }
    .stat-icon.icon-relationships { background: rgba(16, 185, 129, 0.1); color: #10b981; }
    .stat-icon.icon-templates { background: rgba(245, 158, 11, 0.1); color: #f59e0b; }

    .stat-body { min-width: 0; }
    .stat-value { font-size: 1.75rem; font-weight: 700; color: #1e293b; line-height: 1.2; }
    .stat-label { font-size: 0.8125rem; color: #64748b; margin-top: 0.125rem; }

    /* ── Charts row ────────────────────────────────────────────────── */
    .charts-row {
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 1rem; margin-bottom: 1.5rem;
    }
    @media (max-width: 900px) {
      .charts-row { grid-template-columns: 1fr; }
    }

    .chart-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
      padding: 1.25rem;
    }
    .chart-header {
      display: flex; justify-content: space-between; align-items: baseline;
      margin-bottom: 1rem;
    }
    .chart-header h2 {
      margin: 0; font-size: 0.9375rem; font-weight: 600; color: #1e293b;
    }
    .chart-subtitle {
      font-size: 0.75rem; color: #94a3b8;
    }
    .view-all-link {
      font-size: 0.75rem; color: #3b82f6; text-decoration: none;
      font-weight: 500;
    }
    .view-all-link:hover { text-decoration: underline; }

    .empty-chart {
      padding: 2rem; text-align: center; color: #94a3b8; font-size: 0.8125rem;
    }

    /* ── Lifecycle bar chart ───────────────────────────────────────── */
    .lifecycle-chart { display: flex; flex-direction: column; gap: 0.625rem; }

    .bar-row {
      display: flex; align-items: center; gap: 0.75rem;
    }
    .bar-label {
      width: 110px; flex-shrink: 0; font-size: 0.8125rem;
      color: #475569; display: flex; align-items: center; gap: 0.5rem;
    }
    .state-dot {
      width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    }
    .bar-track {
      flex: 1; height: 24px; background: #f1f5f9; border-radius: 4px;
      overflow: hidden;
    }
    .bar-fill {
      height: 100%; border-radius: 4px; transition: width 0.4s ease;
      min-width: 2px;
    }
    .bar-value {
      width: 40px; text-align: right; font-size: 0.8125rem;
      font-weight: 600; color: #1e293b; flex-shrink: 0;
    }

    /* ── Horizontal bar chart (CI by class) ────────────────────────── */
    .class-chart { display: flex; flex-direction: column; gap: 0.5rem; }

    .hbar-row {
      display: flex; align-items: center; gap: 0.75rem;
    }
    .hbar-label {
      width: 120px; flex-shrink: 0; font-size: 0.75rem;
      color: #475569; overflow: hidden; text-overflow: ellipsis;
      white-space: nowrap;
    }
    .hbar-track {
      flex: 1; height: 22px; background: #f1f5f9; border-radius: 4px;
      overflow: hidden; position: relative;
    }
    .hbar-fill {
      height: 100%; border-radius: 4px; background: #3b82f6;
      transition: width 0.4s ease; min-width: 2px;
    }
    .hbar-count {
      position: absolute; right: 8px; top: 50%; transform: translateY(-50%);
      font-size: 0.6875rem; font-weight: 600; color: #1e293b;
    }

    /* ── Quick links row ───────────────────────────────────────────── */
    .quick-links-row {
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 1rem;
    }
    @media (max-width: 900px) {
      .quick-links-row { grid-template-columns: 1fr; }
    }

    /* ── Recent CIs ────────────────────────────────────────────────── */
    .recent-list { display: flex; flex-direction: column; }
    .recent-item {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.625rem 0; border-bottom: 1px solid #f1f5f9;
      text-decoration: none; color: inherit; transition: background 0.1s;
      margin: 0 -1.25rem; padding-left: 1.25rem; padding-right: 1.25rem;
    }
    .recent-item:last-child { border-bottom: none; }
    .recent-item:hover { background: #f8fafc; }
    .recent-item-main { display: flex; flex-direction: column; gap: 0.125rem; min-width: 0; }
    .recent-name {
      font-size: 0.8125rem; font-weight: 500; color: #1e293b;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .recent-class { font-size: 0.6875rem; color: #94a3b8; }
    .recent-item-meta { display: flex; align-items: center; gap: 0.75rem; flex-shrink: 0; }
    .recent-date { font-size: 0.6875rem; color: #94a3b8; }

    .lifecycle-badge {
      padding: 0.0625rem 0.5rem; border-radius: 12px; font-size: 0.625rem;
      font-weight: 600; display: inline-block; line-height: 1.6;
    }
    .badge-planned { background: #f1f5f9; color: #64748b; }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-maintenance { background: #fef9c3; color: #a16207; }
    .badge-retired { background: #fef2f2; color: #dc2626; }

    /* ── Nav grid ──────────────────────────────────────────────────── */
    .nav-grid {
      display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem;
    }
    .nav-tile {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; gap: 0.5rem; padding: 1.25rem 0.75rem;
      border: 1px solid #e2e8f0; border-radius: 8px; text-decoration: none;
      color: #475569; font-size: 0.8125rem; font-weight: 500;
      transition: background 0.15s, border-color 0.15s;
    }
    .nav-tile:hover {
      background: #f8fafc; border-color: #3b82f6;
      color: #3b82f6;
    }
    .nav-tile-icon {
      width: 36px; height: 36px; display: flex; align-items: center;
      justify-content: center; color: #94a3b8;
    }
    .nav-tile:hover .nav-tile-icon { color: #3b82f6; }
    .nav-tile-icon svg { width: 24px; height: 24px; }
    .nav-tile-icon.icon-create { color: #3b82f6; }
  `],
})
export class CmdbDashboardComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private catalogService = inject(CatalogService);
  private tenantContext = inject(TenantContextService);

  /** Raw data signals. */
  allCIs = signal<ConfigurationItem[]>([]);
  totalCIs = signal(0);
  classes = signal<CIClass[]>([]);
  totalRelationshipTypes = signal(0);
  totalTemplates = signal(0);
  loading = signal(true);

  /** Computed stats. */
  totalClasses = computed(() => this.classes().length);

  recentCIs = computed(() => {
    const items = [...this.allCIs()];
    items.sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime());
    return items.slice(0, 5);
  });

  lifecycleBreakdown = computed<LifecycleBreakdown[]>(() => {
    const cis = this.allCIs();
    const total = cis.length || 1;
    const stateConfig: Record<string, { label: string; color: string }> = {
      planned: { label: 'Planned', color: '#94a3b8' },
      active: { label: 'Active', color: '#22c55e' },
      maintenance: { label: 'Maintenance', color: '#eab308' },
      retired: { label: 'Retired', color: '#ef4444' },
    };

    return Object.entries(stateConfig).map(([state, cfg]) => {
      const count = cis.filter((ci) => ci.lifecycleState === state).length;
      return {
        state,
        label: cfg.label,
        count,
        color: cfg.color,
        percent: Math.round((count / total) * 100),
      };
    });
  });

  classBreakdown = computed<ClassBreakdown[]>(() => {
    const cis = this.allCIs();
    const classMap = this.classes();
    if (cis.length === 0) return [];

    // Count CIs per class
    const countMap = new Map<string, number>();
    for (const ci of cis) {
      countMap.set(ci.ciClassId, (countMap.get(ci.ciClassId) ?? 0) + 1);
    }

    // Build sorted list (top 10)
    const maxCount = Math.max(...countMap.values(), 1);
    return Array.from(countMap.entries())
      .map(([classId, count]) => {
        const cls = classMap.find((c) => c.id === classId);
        return {
          classId,
          className: cls?.displayName ?? classId,
          count,
          percent: Math.round((count / maxCount) * 100),
        };
      })
      .sort((a, b) => b.count - a.count)
      .slice(0, 10);
  });

  ngOnInit(): void {
    this.loadDashboardData();
  }

  private loadDashboardData(): void {
    this.loading.set(true);

    forkJoin({
      cis: this.cmdbService.listCIs({ limit: 1000 }).pipe(catchError(() => EMPTY)),
      classes: this.cmdbService.listClasses().pipe(catchError(() => EMPTY)),
      relationshipTypes: this.cmdbService.listRelationshipTypes().pipe(catchError(() => EMPTY)),
      templates: this.cmdbService.listTemplates({ limit: 1 }).pipe(catchError(() => EMPTY)),
    }).subscribe({
      next: (data) => {
        if (data.cis) {
          this.allCIs.set(data.cis.items);
          this.totalCIs.set(data.cis.total);
        }
        if (data.classes) {
          this.classes.set(data.classes as CIClass[]);
        }
        if (data.relationshipTypes) {
          this.totalRelationshipTypes.set((data.relationshipTypes as unknown[]).length);
        }
        if (data.templates) {
          this.totalTemplates.set((data.templates as { total: number }).total);
        }
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }
}
