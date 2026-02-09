/**
 * Overview: Impact analysis component — displays upstream/downstream dependency graph for a CI.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/cmdb.service
 * Concepts: CI impact analysis, dependency traversal, upstream/downstream graph, depth-layered tree
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
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CmdbService } from '@core/services/cmdb.service';
import { GraphNode } from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';

type Direction = 'upstream' | 'downstream';

@Component({
  selector: 'nimbus-impact-analysis',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="impact-page">
        <div class="page-header">
          <button class="back-btn" (click)="goBack()">&#8592; Back to CI</button>
          <h1>Impact Analysis</h1>
          <p class="subtitle" *ngIf="ciId">
            Showing {{ direction() }} dependencies for CI
            <span class="mono">{{ ciId }}</span>
          </p>
        </div>

        <div class="controls">
          <div class="control-group">
            <label class="control-label">Direction</label>
            <div class="toggle-group">
              <button
                class="toggle-btn"
                [class.active]="direction() === 'upstream'"
                (click)="setDirection('upstream')"
              >Upstream</button>
              <button
                class="toggle-btn"
                [class.active]="direction() === 'downstream'"
                (click)="setDirection('downstream')"
              >Downstream</button>
            </div>
          </div>

          <div class="control-group">
            <label class="control-label">Max Depth: {{ maxDepth() }}</label>
            <div class="depth-control">
              <input
                type="range"
                [min]="1"
                [max]="10"
                [ngModel]="maxDepth()"
                (ngModelChange)="setMaxDepth($event)"
                class="depth-slider"
              />
              <span class="depth-value">{{ maxDepth() }}</span>
            </div>
          </div>

          <button class="btn btn-primary" (click)="loadImpact()">
            Analyze
          </button>
        </div>

        @if (loading()) {
          <div class="loading">Analyzing dependencies...</div>
        }

        @if (!loading() && error()) {
          <div class="error-state">
            <p>{{ error() }}</p>
            <button class="btn btn-primary btn-sm" (click)="loadImpact()">Retry</button>
          </div>
        }

        @if (!loading() && !error() && hasLoaded() && nodes().length === 0) {
          <div class="empty-state">
            <p>No {{ direction() }} dependencies found for this configuration item.</p>
          </div>
        }

        @if (!loading() && !error() && groupedByDepth().length > 0) {
          <div class="results-summary">
            <span class="summary-badge">{{ nodes().length }} node(s)</span>
            <span class="summary-badge">{{ groupedByDepth().length }} depth level(s)</span>
          </div>

          <div class="depth-layers">
            @for (group of groupedByDepth(); track group.depth) {
              <div class="depth-layer">
                <div class="layer-header">
                  <span class="layer-depth">Depth {{ group.depth }}</span>
                  <span class="layer-count">{{ group.nodes.length }} item(s)</span>
                </div>
                <div class="layer-nodes">
                  @for (node of group.nodes; track node.ciId) {
                    <div class="node-card">
                      <div class="node-main">
                        <a
                          class="node-name"
                          [routerLink]="['/cmdb', node.ciId]"
                        >{{ node.name }}</a>
                        <span class="node-class">{{ node.ciClass }}</span>
                      </div>
                      <div class="node-path">
                        @for (segment of node.path; track $index; let last = $last) {
                          <span class="path-segment">{{ segment }}</span>
                          @if (!last) {
                            <span class="path-sep">&#8594;</span>
                          }
                        }
                      </div>
                    </div>
                  }
                </div>
              </div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .impact-page { padding: 0; }

    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; padding: 0; margin-bottom: 0.75rem; font-family: inherit;
    }
    .back-btn:hover { text-decoration: underline; }

    .page-header { margin-bottom: 1.5rem; }
    .page-header h1 {
      font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0 0 0.25rem;
    }
    .subtitle { color: #64748b; font-size: 0.8125rem; margin: 0; }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 0.75rem;
    }

    .controls {
      display: flex; align-items: flex-end; gap: 1.5rem; flex-wrap: wrap;
      padding: 1rem 1.25rem; margin-bottom: 1.5rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .control-group {
      display: flex; flex-direction: column; gap: 0.375rem;
    }
    .control-label {
      font-size: 0.75rem; font-weight: 600; color: #64748b;
      text-transform: uppercase; letter-spacing: 0.05em;
    }

    .toggle-group {
      display: flex; border: 1px solid #e2e8f0; border-radius: 6px; overflow: hidden;
    }
    .toggle-btn {
      padding: 0.5rem 1rem; border: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; font-family: inherit;
      background: #fff; color: #64748b; transition: background 0.15s, color 0.15s;
    }
    .toggle-btn:not(:last-child) { border-right: 1px solid #e2e8f0; }
    .toggle-btn.active { background: #3b82f6; color: #fff; }
    .toggle-btn:hover:not(.active) { background: #f8fafc; color: #1e293b; }

    .depth-control { display: flex; align-items: center; gap: 0.75rem; }
    .depth-slider {
      width: 160px; cursor: pointer;
      accent-color: #3b82f6;
    }
    .depth-value {
      font-size: 0.875rem; font-weight: 600; color: #1e293b;
      min-width: 1.5rem; text-align: center;
    }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; text-decoration: none; display: inline-block;
    }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }

    .loading {
      padding: 3rem; text-align: center; color: #94a3b8; font-size: 0.875rem;
    }
    .error-state {
      padding: 2rem; text-align: center; background: #fff;
      border: 1px solid #fecaca; border-radius: 8px;
    }
    .error-state p { color: #dc2626; font-size: 0.8125rem; margin: 0 0 1rem; }
    .empty-state {
      padding: 3rem; text-align: center; background: #fff;
      border: 1px solid #e2e8f0; border-radius: 8px;
    }
    .empty-state p { color: #94a3b8; font-size: 0.8125rem; margin: 0; }

    .results-summary {
      display: flex; gap: 0.75rem; margin-bottom: 1rem;
    }
    .summary-badge {
      padding: 0.25rem 0.75rem; font-size: 0.75rem; font-weight: 600;
      background: #dbeafe; color: #2563eb; border-radius: 999px;
    }

    .depth-layers {
      display: flex; flex-direction: column; gap: 1rem;
    }
    .depth-layer {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      overflow: hidden;
    }
    .layer-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 1rem; background: #f8fafc;
      border-bottom: 1px solid #f1f5f9;
    }
    .layer-depth {
      font-size: 0.8125rem; font-weight: 700; color: #3b82f6;
    }
    .layer-count {
      font-size: 0.75rem; color: #64748b;
    }

    .layer-nodes {
      display: flex; flex-direction: column;
    }
    .node-card {
      padding: 0.75rem 1rem;
      border-bottom: 1px solid #f1f5f9;
      transition: background 0.1s;
    }
    .node-card:last-child { border-bottom: none; }
    .node-card:hover { background: #f8fafc; }

    .node-main {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.25rem;
    }
    .node-name {
      color: #3b82f6; text-decoration: none; font-weight: 600;
      font-size: 0.875rem;
    }
    .node-name:hover { text-decoration: underline; color: #2563eb; }
    .node-class {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; background: #dbeafe; color: #2563eb;
    }

    .node-path {
      display: flex; align-items: center; gap: 0.25rem; flex-wrap: wrap;
    }
    .path-segment {
      font-size: 0.6875rem; color: #64748b;
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
    }
    .path-sep {
      font-size: 0.625rem; color: #94a3b8;
    }
  `],
})
export class ImpactAnalysisComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  ciId = '';

  direction = signal<Direction>('downstream');
  maxDepth = signal(5);
  nodes = signal<GraphNode[]>([]);
  loading = signal(false);
  error = signal<string | null>(null);
  hasLoaded = signal(false);

  groupedByDepth = computed(() => {
    const items = this.nodes();
    if (!items.length) return [];

    const depthMap = new Map<number, GraphNode[]>();
    for (const node of items) {
      const existing = depthMap.get(node.depth);
      if (existing) {
        existing.push(node);
      } else {
        depthMap.set(node.depth, [node]);
      }
    }

    return Array.from(depthMap.entries())
      .sort(([a], [b]) => a - b)
      .map(([depth, depthNodes]) => ({ depth, nodes: depthNodes }));
  });

  ngOnInit(): void {
    this.ciId = this.route.snapshot.paramMap.get('id') ?? '';
    if (!this.ciId) {
      this.error.set('No CI ID provided.');
      return;
    }

    this.loadImpact();
  }

  setDirection(dir: Direction): void {
    this.direction.set(dir);
  }

  setMaxDepth(value: number): void {
    this.maxDepth.set(value);
  }

  loadImpact(): void {
    if (!this.ciId) return;

    this.loading.set(true);
    this.error.set(null);

    this.cmdbService
      .getCIImpact(this.ciId, this.direction(), this.maxDepth())
      .subscribe({
        next: (result) => {
          this.nodes.set(result);
          this.loading.set(false);
          this.hasLoaded.set(true);
        },
        error: (err) => {
          this.error.set(err.message || 'Failed to load impact analysis data.');
          this.loading.set(false);
          this.hasLoaded.set(true);
        },
      });
  }

  goBack(): void {
    this.router.navigate(['/cmdb', this.ciId]);
  }
}
