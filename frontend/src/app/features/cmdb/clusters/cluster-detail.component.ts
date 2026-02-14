/**
 * Overview: Stack blueprint detail — displays blueprint info, slot definitions,
 *     parameters, and deployed stacks (via tag key).
 * Architecture: Architecture blueprint detail view (Section 8)
 * Dependencies: @angular/core, @angular/router, cluster.service
 * Concepts: Standalone component, signals-based, light theme. Blueprints are pure
 *     templates — CI assignment is a deployment-time concern, not shown here.
 */
import { Component, ChangeDetectionStrategy, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ClusterService } from '@core/services/cluster.service';
import {
  ServiceCluster,
  StackList,
} from '@shared/models/cluster.model';

@Component({
  selector: 'nimbus-cluster-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        @if (loading()) {
          <div class="loading-state">Loading blueprint...</div>
        } @else if (!cluster()) {
          <div class="empty-state">Blueprint not found.</div>
        } @else {
          <div class="page-header">
            <div>
              <div class="breadcrumb">
                <a routerLink="/architecture/blueprints" class="breadcrumb-link">Stack Blueprints</a>
                <span class="breadcrumb-sep">/</span>
                <span>{{ cluster()!.name }}</span>
              </div>
              <h1 class="page-title">{{ cluster()!.name }}</h1>
              @if (cluster()!.description) {
                <p class="page-subtitle">{{ cluster()!.description }}</p>
              }
            </div>
            <div class="header-actions">
              <a
                *nimbusHasPermission="'cmdb:cluster:manage'"
                [routerLink]="'/architecture/blueprints/' + cluster()!.id + '/edit'"
                class="btn btn-outline"
              >Edit</a>
              <button
                *nimbusHasPermission="'cmdb:cluster:delete'"
                class="btn btn-danger"
                (click)="onDelete()"
              >Delete</button>
            </div>
          </div>

          <!-- Blueprint Info -->
          <div class="info-row">
            <div class="info-card">
              <div class="info-label">Type</div>
              <div class="info-value">{{ cluster()!.clusterType }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Slots</div>
              <div class="info-value">{{ cluster()!.slots.length }}</div>
            </div>
            <div class="info-card">
              <div class="info-label">Parameters</div>
              <div class="info-value">{{ cluster()!.parameters.length }}</div>
            </div>
            @if (cluster()!.stackTagKey) {
              <div class="info-card">
                <div class="info-label">Stack Tag Key</div>
                <div class="info-value tag-value">{{ cluster()!.stackTagKey }}</div>
              </div>
            }
          </div>

          <!-- Deployed Stacks -->
          @if (cluster()!.stackTagKey) {
            <div class="stacks-section">
              <div class="section-header">
                <h2 class="section-title">
                  Deployed Stacks
                  <span class="tag-key-badge">tag: {{ cluster()!.stackTagKey }}</span>
                </h2>
                <button class="btn btn-sm btn-outline" (click)="refreshStacks()">Refresh</button>
              </div>
              @if (stacksLoading()) {
                <div class="stacks-loading">Loading stacks...</div>
              } @else if (stackData()?.stacks?.length) {
                <div class="stacks-grid">
                  @for (stack of stackData()!.stacks; track stack.tagValue) {
                    <div class="stack-card">
                      <div class="stack-name">{{ stack.tagValue }}</div>
                      <div class="stack-stats">
                        <div class="stack-stat">
                          <span class="stat-value">{{ stack.ciCount }}</span>
                          <span class="stat-label">CIs</span>
                        </div>
                        <div class="stack-stat">
                          <span class="stat-value stat-active">{{ stack.activeCount }}</span>
                          <span class="stat-label">Active</span>
                        </div>
                        @if (stack.plannedCount) {
                          <div class="stack-stat">
                            <span class="stat-value stat-planned">{{ stack.plannedCount }}</span>
                            <span class="stat-label">Planned</span>
                          </div>
                        }
                        @if (stack.maintenanceCount) {
                          <div class="stack-stat">
                            <span class="stat-value stat-maintenance">{{ stack.maintenanceCount }}</span>
                            <span class="stat-label">Maint.</span>
                          </div>
                        }
                      </div>
                    </div>
                  }
                </div>
              } @else {
                <div class="empty-state-sm">No deployed stacks found. CIs with tag "{{ cluster()!.stackTagKey }}" will appear here.</div>
              }
            </div>
          }

          <!-- Slots -->
          <div class="slots-section">
            <div class="section-header">
              <h2 class="section-title">Slots ({{ cluster()!.slots.length || 0 }})</h2>
              <button
                *nimbusHasPermission="'cmdb:cluster:manage'"
                class="btn btn-sm btn-primary"
                (click)="showAddSlot.set(!showAddSlot())"
              >+ Add Slot</button>
            </div>

            @if (showAddSlot()) {
              <div class="inline-form">
                <input type="text" class="form-input" placeholder="Slot name" [(ngModel)]="newSlotName" />
                <input type="text" class="form-input" placeholder="Display name" [(ngModel)]="newSlotDisplay" />
                <input type="number" class="form-input form-input-sm" placeholder="Min" [(ngModel)]="newSlotMin" />
                <button class="btn btn-sm btn-primary" (click)="addSlot()" [disabled]="!newSlotName">Save</button>
                <button class="btn btn-sm btn-outline" (click)="showAddSlot.set(false)">Cancel</button>
              </div>
            }

            @for (slot of cluster()!.slots; track slot.id) {
              <div class="slot-card">
                <div class="slot-header" (click)="toggleSlot(slot.id)">
                  <div class="slot-info">
                    <span class="slot-name">{{ slot.displayName }}</span>
                    @if (slot.semanticCategoryName || slot.semanticTypeName) {
                      <span class="slot-type-tag">
                        {{ slot.semanticCategoryName }}@if (slot.semanticTypeName) { / {{ slot.semanticTypeName }} }
                      </span>
                    }
                    <span class="slot-meta">
                      min: {{ slot.minCount }}@if (slot.maxCount) { / max: {{ slot.maxCount }} }
                      @if (slot.isRequired) { <span class="required-tag">Required</span> }
                    </span>
                  </div>
                  <span class="chevron" [class.expanded]="expandedSlots().has(slot.id)">&#9206;</span>
                </div>

                @if (expandedSlots().has(slot.id)) {
                  <div class="slot-body">
                    @if (slot.description) {
                      <p class="slot-desc">{{ slot.description }}</p>
                    }
                    <div class="slot-details">
                      <div class="detail-row">
                        <span class="detail-label">Name (key):</span>
                        <code class="detail-value">{{ slot.name }}</code>
                      </div>
                      <div class="detail-row">
                        <span class="detail-label">Min count:</span>
                        <span class="detail-value">{{ slot.minCount }}</span>
                      </div>
                      @if (slot.maxCount) {
                        <div class="detail-row">
                          <span class="detail-label">Max count:</span>
                          <span class="detail-value">{{ slot.maxCount }}</span>
                        </div>
                      }
                      @if (slot.allowedCiClassIds?.length) {
                        <div class="detail-row">
                          <span class="detail-label">Allowed CI classes:</span>
                          <span class="detail-value">{{ slot.allowedCiClassIds!.length }} class(es)</span>
                        </div>
                      }
                    </div>
                  </div>
                }
              </div>
            } @empty {
              <div class="empty-state">No slots defined. Add slots to define the blueprint's structure.</div>
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; max-width: 1200px; }
    .page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
    .page-title { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .page-subtitle { font-size: 0.875rem; color: #64748b; margin: 4px 0 0; }
    .breadcrumb { font-size: 0.8rem; color: #64748b; margin-bottom: 2px; }
    .breadcrumb-link { color: #3b82f6; text-decoration: none; }
    .breadcrumb-link:hover { text-decoration: underline; }
    .breadcrumb-sep { margin: 0 4px; }
    .header-actions { display: flex; gap: 8px; }

    .info-row { display: flex; gap: 16px; margin-bottom: 20px; flex-wrap: wrap; }
    .info-card {
      flex: 1; min-width: 140px; padding: 16px; background: #fff; border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    .info-label { font-size: 0.75rem; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; }
    .info-value { font-size: 1.1rem; font-weight: 600; color: #1e293b; }
    .tag-value { font-size: 0.9rem; font-family: monospace; color: #0284c7; }

    .stacks-section { margin-bottom: 24px; }
    .tag-key-badge {
      display: inline-block; padding: 2px 8px; border-radius: 4px;
      font-size: 0.7rem; font-weight: 500; background: #f0f9ff; color: #0284c7;
      margin-left: 8px; vertical-align: middle;
    }
    .stacks-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; }
    .stack-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px;
    }
    .stack-card:hover { border-color: #cbd5e1; }
    .stack-name { font-weight: 600; color: #1e293b; font-size: 0.9rem; margin-bottom: 10px; }
    .stack-stats { display: flex; gap: 16px; }
    .stack-stat { text-align: center; }
    .stat-value { display: block; font-size: 1.1rem; font-weight: 600; color: #1e293b; }
    .stat-active { color: #16a34a; }
    .stat-planned { color: #0284c7; }
    .stat-maintenance { color: #d97706; }
    .stat-label { font-size: 0.65rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }
    .stacks-loading { padding: 24px; text-align: center; color: #64748b; font-size: 0.85rem; }
    .empty-state-sm { padding: 24px; text-align: center; color: #94a3b8; font-size: 0.85rem; }

    .slots-section { margin-top: 8px; }
    .section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
    .section-title { font-size: 1.1rem; font-weight: 600; color: #1e293b; margin: 0; }

    .inline-form {
      display: flex; gap: 8px; align-items: center; padding: 12px; margin-bottom: 12px;
      background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px;
    }

    .slot-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 8px; overflow: hidden;
    }
    .slot-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 12px 16px; cursor: pointer; user-select: none;
    }
    .slot-header:hover { background: #f8fafc; }
    .slot-info { display: flex; align-items: center; gap: 12px; }
    .slot-name { font-weight: 500; color: #1e293b; }
    .slot-meta { font-size: 0.8rem; color: #64748b; }
    .required-tag {
      display: inline-block; padding: 1px 6px; border-radius: 3px;
      font-size: 0.7rem; background: #fef3c7; color: #92400e;
    }
    .slot-type-tag {
      display: inline-block; padding: 1px 6px; border-radius: 3px;
      font-size: 0.7rem; background: #eff6ff; color: #2563eb;
    }
    .chevron { transition: transform 0.2s; font-size: 0.8rem; color: #94a3b8; }
    .chevron.expanded { transform: rotate(180deg); }

    .slot-body { padding: 0 16px 16px; border-top: 1px solid #f1f5f9; }
    .slot-desc { font-size: 0.8rem; color: #64748b; margin: 8px 0; }
    .slot-details { display: grid; grid-template-columns: 1fr 1fr; gap: 4px 16px; margin-top: 8px; }
    .detail-row { display: flex; gap: 8px; align-items: center; }
    .detail-label { font-size: 0.8rem; color: #64748b; }
    .detail-value { font-size: 0.8rem; color: #1e293b; font-weight: 500; }

    .form-input {
      padding: 6px 10px; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.85rem; background: #fff; color: #1e293b;
    }
    .form-input:focus { outline: none; border-color: #3b82f6; }
    .form-input-sm { width: 80px; }

    .btn { padding: 8px 16px; border-radius: 6px; font-size: 0.875rem; font-weight: 500; cursor: pointer; text-decoration: none; border: none; display: inline-block; }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }
    .btn-outline { background: #fff; color: #1e293b; border: 1px solid #e2e8f0; }
    .btn-outline:hover { background: #f8fafc; }
    .btn-danger { background: #ef4444; color: #fff; }
    .btn-danger:hover { background: #dc2626; }
    .btn-sm { padding: 4px 10px; font-size: 0.8rem; }
    .btn:disabled { opacity: 0.5; cursor: not-allowed; }
    .loading-state, .empty-state { padding: 48px; text-align: center; color: #64748b; }
  `],
})
export class ClusterDetailComponent implements OnInit {
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private clusterService = inject(ClusterService);

  cluster = signal<ServiceCluster | null>(null);
  loading = signal(false);
  expandedSlots = signal<Set<string>>(new Set());
  showAddSlot = signal(false);
  stackData = signal<StackList | null>(null);
  stacksLoading = signal(false);

  newSlotName = '';
  newSlotDisplay = '';
  newSlotMin = 1;

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadCluster(id);
    }
  }

  loadCluster(id: string): void {
    this.loading.set(true);
    this.clusterService.getCluster(id).subscribe({
      next: (cluster) => {
        this.cluster.set(cluster);
        this.loading.set(false);
        if (cluster?.stackTagKey) {
          this.loadStacks(cluster.id);
        }
      },
      error: () => this.loading.set(false),
    });
  }

  toggleSlot(slotId: string): void {
    const current = new Set(this.expandedSlots());
    if (current.has(slotId)) {
      current.delete(slotId);
    } else {
      current.add(slotId);
    }
    this.expandedSlots.set(current);
  }

  addSlot(): void {
    if (!this.newSlotName || !this.cluster()) return;
    this.clusterService.addSlot(this.cluster()!.id, {
      name: this.newSlotName,
      displayName: this.newSlotDisplay || this.newSlotName,
      minCount: this.newSlotMin,
    }).subscribe({
      next: (updated) => {
        this.cluster.set(updated);
        this.showAddSlot.set(false);
        this.newSlotName = '';
        this.newSlotDisplay = '';
        this.newSlotMin = 1;
      },
    });
  }

  loadStacks(blueprintId: string): void {
    this.stacksLoading.set(true);
    this.clusterService.getBlueprintStacks(blueprintId).subscribe({
      next: (data) => {
        this.stackData.set(data);
        this.stacksLoading.set(false);
      },
      error: () => this.stacksLoading.set(false),
    });
  }

  refreshStacks(): void {
    if (this.cluster()) {
      this.loadStacks(this.cluster()!.id);
    }
  }

  onDelete(): void {
    if (!this.cluster()) return;
    if (!confirm(`Delete blueprint "${this.cluster()!.name}"?`)) return;
    this.clusterService.deleteCluster(this.cluster()!.id).subscribe({
      next: () => this.router.navigate(['/architecture/blueprints']),
    });
  }
}
