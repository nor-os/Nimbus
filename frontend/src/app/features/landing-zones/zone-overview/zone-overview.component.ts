/**
 * Overview: Read-only zone overview panel shown when no hierarchy node is selected in the landing zone designer.
 * Architecture: Feature component for landing zone summary display (Section 7.2)
 * Dependencies: @angular/core, @angular/common, landing-zone.model
 * Concepts: Hierarchy stats by level, region listing, zone-level tag policies, validation summary.
 */
import {
  Component,
  Input,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  LandingZoneHierarchy,
  HierarchyLevelDef,
  LandingZoneValidation,
  LandingZoneRegion,
  LandingZoneTagPolicy,
} from '@shared/models/landing-zone.model';

interface LevelStat {
  typeId: string;
  label: string;
  icon: string;
  count: number;
}

@Component({
  selector: 'nimbus-zone-overview',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="zone-overview">
      <div class="overview-header">
        <h3 class="overview-title">Zone Overview</h3>
        <p class="overview-subtitle">Select a node in the hierarchy to configure it.</p>
      </div>

      <!-- Hierarchy Stats -->
      <div class="overview-section">
        <h4 class="section-title">Hierarchy Stats</h4>
        @if (levelStats.length > 0) {
          <div class="stats-grid">
            @for (stat of levelStats; track stat.typeId) {
              <div class="stat-card">
                <span class="stat-icon">{{ stat.icon }}</span>
                <div class="stat-info">
                  <span class="stat-count">{{ stat.count }}</span>
                  <span class="stat-label">{{ stat.label }}</span>
                </div>
              </div>
            }
          </div>
        } @else {
          <p class="empty-hint">No hierarchy nodes defined yet.</p>
        }
      </div>

      <!-- Regions -->
      <div class="overview-section">
        <h4 class="section-title">Regions</h4>
        @if (regions.length > 0) {
          <div class="region-list">
            @for (region of regions; track region.id) {
              <div class="region-row">
                <span class="region-name">{{ region.displayName }}</span>
                <code class="region-identifier">{{ region.regionIdentifier }}</code>
                @if (region.isPrimary) {
                  <span class="region-badge badge-primary">Primary</span>
                }
                @if (region.isDr) {
                  <span class="region-badge badge-dr">DR</span>
                }
              </div>
            }
          </div>
        } @else {
          <p class="empty-hint">No regions configured.</p>
        }
      </div>

      <!-- Tag Policies -->
      <div class="overview-section">
        <h4 class="section-title">Tag Policies</h4>
        @if (tagPolicies.length > 0) {
          <div class="tag-list">
            @for (tag of tagPolicies; track tag.id) {
              <div class="tag-row">
                <span class="tag-key">{{ tag.tagKey }}</span>
                <span class="tag-display">{{ tag.displayName }}</span>
                @if (tag.isRequired) {
                  <span class="tag-required">required</span>
                }
                @if (tag.inherited) {
                  <span class="tag-inherited">inherited</span>
                }
              </div>
            }
          </div>
        } @else {
          <p class="empty-hint">No zone-level tag policies.</p>
        }
      </div>

      <!-- Validation Summary -->
      @if (validation) {
        <div class="overview-section">
          <h4 class="section-title">Validation</h4>
          <div class="validation-summary">
            <div class="validation-status" [class.status-ready]="validation.ready" [class.status-not-ready]="!validation.ready">
              {{ validation.ready ? 'Ready' : 'Not Ready' }}
            </div>
            @if (validation.checks.length > 0) {
              <div class="check-counts">
                @if (checkCounts.pass > 0) {
                  <span class="check-count count-pass">{{ checkCounts.pass }} passed</span>
                }
                @if (checkCounts.warning > 0) {
                  <span class="check-count count-warning">{{ checkCounts.warning }} warnings</span>
                }
                @if (checkCounts.error > 0) {
                  <span class="check-count count-error">{{ checkCounts.error }} errors</span>
                }
              </div>
            }
          </div>
        </div>
      }
    </div>
  `,
  styles: [`
    .zone-overview {
      padding: 0;
      background: #fff;
      height: 100%;
      overflow-y: auto;
    }

    .overview-header {
      padding: 20px 16px 16px 16px;
      border-bottom: 1px solid #e2e8f0;
      background: #f8fafc;
    }

    .overview-title {
      margin: 0 0 4px 0;
      font-size: 16px;
      font-weight: 600;
      color: #1e293b;
    }

    .overview-subtitle {
      margin: 0;
      font-size: 13px;
      color: #94a3b8;
    }

    /* ── Sections ── */
    .overview-section {
      padding: 16px;
      border-bottom: 1px solid #e2e8f0;
    }

    .section-title {
      margin: 0 0 12px 0;
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .empty-hint {
      font-size: 12px;
      color: #94a3b8;
      font-style: italic;
      margin: 0;
    }

    /* ── Hierarchy Stats ── */
    .stats-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
    }

    .stat-card {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 10px 12px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }

    .stat-icon {
      font-size: 20px;
      color: #3b82f6;
    }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-count {
      font-size: 18px;
      font-weight: 700;
      color: #1e293b;
      line-height: 1.2;
    }

    .stat-label {
      font-size: 11px;
      color: #64748b;
    }

    /* ── Regions ── */
    .region-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .region-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
    }

    .region-name {
      font-size: 13px;
      font-weight: 500;
      color: #1e293b;
    }

    .region-identifier {
      font-size: 12px;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      color: #64748b;
      margin-left: auto;
    }

    .region-badge {
      font-size: 10px;
      font-weight: 600;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }

    .badge-primary {
      background: #dbeafe;
      color: #1d4ed8;
    }

    .badge-dr {
      background: #fef3c7;
      color: #92400e;
    }

    /* ── Tag Policies ── */
    .tag-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .tag-row {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 10px;
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
    }

    .tag-key {
      font-size: 13px;
      font-weight: 600;
      color: #1e293b;
    }

    .tag-display {
      font-size: 12px;
      color: #64748b;
      flex: 1;
    }

    .tag-required {
      font-size: 10px;
      font-weight: 500;
      padding: 1px 5px;
      border-radius: 3px;
      background: #fef3c7;
      color: #92400e;
    }

    .tag-inherited {
      font-size: 10px;
      font-weight: 500;
      padding: 1px 5px;
      border-radius: 3px;
      background: #e2e8f0;
      color: #64748b;
      font-style: italic;
    }

    /* ── Validation ── */
    .validation-summary {
      display: flex;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }

    .validation-status {
      font-size: 13px;
      font-weight: 600;
      padding: 4px 12px;
      border-radius: 6px;
    }

    .status-ready {
      background: #dcfce7;
      color: #166534;
    }

    .status-not-ready {
      background: #fee2e2;
      color: #991b1b;
    }

    .check-counts {
      display: flex;
      gap: 8px;
    }

    .check-count {
      font-size: 12px;
      font-weight: 500;
      padding: 2px 8px;
      border-radius: 4px;
    }

    .count-pass {
      background: #dcfce7;
      color: #166534;
    }

    .count-warning {
      background: #fef3c7;
      color: #92400e;
    }

    .count-error {
      background: #fee2e2;
      color: #991b1b;
    }
  `],
})
export class ZoneOverviewComponent {
  @Input() hierarchy: LandingZoneHierarchy | null = null;
  @Input() levelDefs: Map<string, HierarchyLevelDef> = new Map();
  @Input() validation: LandingZoneValidation | null = null;
  @Input() regions: LandingZoneRegion[] = [];
  @Input() tagPolicies: LandingZoneTagPolicy[] = [];

  /** Count of nodes per level type. */
  get levelStats(): LevelStat[] {
    const nodes = this.hierarchy?.nodes || [];
    const stats: LevelStat[] = [];
    this.levelDefs.forEach((def, typeId) => {
      const count = nodes.filter(n => n.typeId === typeId).length;
      stats.push({
        typeId,
        label: def.label,
        icon: def.icon,
        count,
      });
    });
    return stats;
  }

  /** Validation check counts by status. */
  get checkCounts(): { pass: number; warning: number; error: number } {
    const checks = this.validation?.checks || [];
    return {
      pass: checks.filter(c => c.status === 'pass').length,
      warning: checks.filter(c => c.status === 'warning').length,
      error: checks.filter(c => c.status === 'error').length,
    };
  }
}
