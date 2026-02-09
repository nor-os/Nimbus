/**
 * Overview: CI detail component — tabbed view of a configuration item.
 * Architecture: CMDB feature component (Section 8)
 * Dependencies: @angular/core, @angular/router, app/core/services/cmdb.service
 * Concepts: CI attributes, relationships, version history, lifecycle management
 */
import { Component, inject, signal, computed, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CmdbService } from '@core/services/cmdb.service';
import {
  ConfigurationItem,
  CIRelationship,
  CISnapshot,
  CompartmentNode,
  LifecycleState,
} from '@shared/models/cmdb.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { SearchableSelectComponent, SelectOption } from '@shared/components/searchable-select/searchable-select.component';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

type TabName = 'attributes' | 'relationships' | 'history' | 'actions';

const LIFECYCLE_STATES: LifecycleState[] = ['planned', 'active', 'maintenance', 'retired'];

const LIFECYCLE_COLORS: Record<string, { bg: string; fg: string }> = {
  planned: { bg: '#f1f5f9', fg: '#64748b' },
  active: { bg: '#dcfce7', fg: '#16a34a' },
  maintenance: { bg: '#fef9c3', fg: '#a16207' },
  retired: { bg: '#fef2f2', fg: '#dc2626' },
  deleted: { bg: '#fce7f3', fg: '#be185d' },
};

@Component({
  selector: 'nimbus-ci-detail',
  standalone: true,
  imports: [CommonModule, RouterLink, FormsModule, LayoutComponent, HasPermissionDirective, SearchableSelectComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="ci-detail-page">
        @if (loading()) {
          <div class="loading">Loading configuration item...</div>
        }

        @if (!loading() && !ci()) {
          <div class="empty-state">Configuration item not found.</div>
        }

        @if (ci(); as item) {
          <div class="page-header">
            <button class="back-btn" (click)="goBack()">&#8592; Back to list</button>
            <div class="title-row">
              <h1>{{ item.name }}</h1>
              <span
                class="badge lifecycle-badge"
                [style.background]="lifecycleColor(item.lifecycleState).bg"
                [style.color]="lifecycleColor(item.lifecycleState).fg"
              >
                {{ item.lifecycleState | titlecase }}
              </span>
              <span class="badge class-badge">{{ item.ciClassName }}</span>
            </div>
            @if (item.description) {
              <p class="description">{{ item.description }}</p>
            }
            <div class="header-actions">
              <a
                *nimbusHasPermission="'cmdb:ci:update'"
                [routerLink]="['/cmdb', item.id, 'edit']"
                class="btn btn-primary btn-sm"
              >Edit</a>
            </div>
          </div>

          <div class="tabs">
            <button
              class="tab"
              [class.active]="activeTab() === 'attributes'"
              (click)="setTab('attributes')"
            >Attributes</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'relationships'"
              (click)="setTab('relationships')"
            >Relationships ({{ relationships().length }})</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'history'"
              (click)="setTab('history')"
            >History ({{ versions().length }})</button>
            <button
              class="tab"
              [class.active]="activeTab() === 'actions'"
              (click)="setTab('actions')"
            >Actions</button>
          </div>

          <div class="tab-content">
            @switch (activeTab()) {
              @case ('attributes') {
                <section class="section">
                  <h2>CI Properties</h2>
                  <div class="table-container">
                    <table class="table kv-table">
                      <tbody>
                        <tr>
                          <td class="kv-key">ID</td>
                          <td class="kv-val mono">{{ item.id }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Class</td>
                          <td class="kv-val">{{ item.ciClassName }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Compartment</td>
                          <td class="kv-val">{{ item.compartmentId || '\u2014' }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Lifecycle State</td>
                          <td class="kv-val">
                            <span
                              class="badge lifecycle-badge"
                              [style.background]="lifecycleColor(item.lifecycleState).bg"
                              [style.color]="lifecycleColor(item.lifecycleState).fg"
                            >
                              {{ item.lifecycleState | titlecase }}
                            </span>
                          </td>
                        </tr>
                        <tr>
                          <td class="kv-key">Cloud Resource ID</td>
                          <td class="kv-val mono">{{ item.cloudResourceId || '\u2014' }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Pulumi URN</td>
                          <td class="kv-val mono">{{ item.pulumiUrn || '\u2014' }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Created</td>
                          <td class="kv-val">{{ item.createdAt | date: 'medium' }}</td>
                        </tr>
                        <tr>
                          <td class="kv-key">Updated</td>
                          <td class="kv-val">{{ item.updatedAt | date: 'medium' }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>

                  @if (attributeKeys().length) {
                    <h2>Custom Attributes</h2>
                    <div class="table-container">
                      <table class="table kv-table">
                        <tbody>
                          @for (key of attributeKeys(); track key) {
                            <tr>
                              <td class="kv-key">{{ key }}</td>
                              <td class="kv-val mono">{{ formatAttrValue(item.attributes[key]) }}</td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  }

                  @if (tagKeys().length) {
                    <h2>Tags</h2>
                    <div class="tags-grid">
                      @for (key of tagKeys(); track key) {
                        <span class="tag-chip">{{ key }}: {{ item.tags[key] }}</span>
                      }
                    </div>
                  }
                </section>
              }

              @case ('relationships') {
                <section class="section">
                  <div class="section-header">
                    <h2>Relationships</h2>
                  </div>
                  @if (relationships().length) {
                    <div class="table-container">
                      <table class="table">
                        <thead>
                          <tr>
                            <th>Type</th>
                            <th>Source</th>
                            <th>Target</th>
                            <th>Created</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (rel of relationships(); track rel.id) {
                            <tr>
                              <td class="rel-type">{{ rel.relationshipTypeName }}</td>
                              <td>
                                @if (rel.sourceCiId === item.id) {
                                  <span class="this-ci">{{ rel.sourceCiName }}</span>
                                } @else {
                                  <a class="ci-link" [routerLink]="['/cmdb', rel.sourceCiId]">
                                    {{ rel.sourceCiName }}
                                  </a>
                                }
                              </td>
                              <td>
                                @if (rel.targetCiId === item.id) {
                                  <span class="this-ci">{{ rel.targetCiName }}</span>
                                } @else {
                                  <a class="ci-link" [routerLink]="['/cmdb', rel.targetCiId]">
                                    {{ rel.targetCiName }}
                                  </a>
                                }
                              </td>
                              <td>{{ rel.createdAt | date: 'medium' }}</td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else {
                    <div class="empty-state-box">
                      <p>No relationships found for this configuration item.</p>
                    </div>
                  }
                </section>
              }

              @case ('history') {
                <section class="section">
                  <div class="section-header">
                    <h2>Version History</h2>
                  </div>
                  @if (versions().length) {
                    <div class="table-container">
                      <table class="table">
                        <thead>
                          <tr>
                            <th>Version</th>
                            <th>Change Type</th>
                            <th>Changed At</th>
                            <th>Changed By</th>
                            <th>Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          @for (v of versions(); track v.id) {
                            <tr>
                              <td class="version-num">v{{ v.versionNumber }}</td>
                              <td>
                                <span
                                  class="badge"
                                  [class.badge-create]="v.changeType === 'create'"
                                  [class.badge-update]="v.changeType === 'update'"
                                  [class.badge-delete]="v.changeType === 'delete'"
                                >
                                  {{ v.changeType | titlecase }}
                                </span>
                              </td>
                              <td>{{ v.changedAt | date: 'medium' }}</td>
                              <td class="mono">{{ v.changedBy || '\u2014' }}</td>
                              <td>{{ v.changeReason || '\u2014' }}</td>
                            </tr>
                          }
                        </tbody>
                      </table>
                    </div>
                  } @else {
                    <div class="empty-state-box">
                      <p>No version history available.</p>
                    </div>
                  }
                </section>
              }

              @case ('actions') {
                <section class="section">
                  <h2>Lifecycle State</h2>
                  <div class="action-card">
                    <div class="action-row">
                      <label class="action-label">Change State</label>
                      <select
                        class="action-select"
                        [(ngModel)]="selectedState"
                      >
                        @for (state of lifecycleStates; track state) {
                          <option [value]="state">{{ state | titlecase }}</option>
                        }
                      </select>
                      <button
                        *nimbusHasPermission="'cmdb:ci:update'"
                        class="btn btn-primary btn-sm"
                        [disabled]="selectedState === item.lifecycleState"
                        (click)="changeState()"
                      >Apply</button>
                    </div>
                  </div>

                  <h2>Compartment</h2>
                  <div class="action-card">
                    <div class="action-row">
                      <label class="action-label">Move to Compartment</label>
                      <nimbus-searchable-select
                        class="action-select"
                        [(ngModel)]="selectedCompartmentId"
                        [options]="compartmentOptions()"
                        placeholder="None (root)"
                        [allowClear]="true"
                      />
                      <button
                        *nimbusHasPermission="'cmdb:ci:update'"
                        class="btn btn-primary btn-sm"
                        [disabled]="selectedCompartmentId === (item.compartmentId || '')"
                        (click)="moveToCompartment()"
                      >Move</button>
                    </div>
                  </div>

                  <h2>Danger Zone</h2>
                  <div class="action-card danger-card">
                    <div class="action-row">
                      <div class="danger-info">
                        <span class="danger-title">Delete Configuration Item</span>
                        <span class="danger-desc">Soft-deletes this CI. It can be recovered later.</span>
                      </div>
                      <button
                        *nimbusHasPermission="'cmdb:ci:delete'"
                        class="btn btn-danger btn-sm"
                        (click)="deleteCI()"
                      >Delete</button>
                    </div>
                  </div>
                </section>
              }
            }
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .ci-detail-page { padding: 0; }
    .loading, .empty-state {
      padding: 3rem; text-align: center; color: #64748b;
    }

    .back-btn {
      background: none; border: none; color: #3b82f6; cursor: pointer;
      font-size: 0.8125rem; padding: 0; margin-bottom: 0.75rem; font-family: inherit;
    }
    .back-btn:hover { text-decoration: underline; }

    .page-header { margin-bottom: 1.5rem; }
    .title-row {
      display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.375rem;
    }
    .title-row h1 {
      font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0;
    }
    .description { color: #64748b; font-size: 0.875rem; margin: 0 0 0.75rem; }
    .header-actions { display: flex; gap: 0.5rem; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; display: inline-block;
    }
    .lifecycle-badge { text-transform: capitalize; }
    .class-badge { background: #dbeafe; color: #1d4ed8; }
    .badge-create { background: #dcfce7; color: #16a34a; }
    .badge-update { background: #fef3c7; color: #d97706; }
    .badge-delete { background: #fef2f2; color: #dc2626; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; padding: 0.5rem 1rem;
      transition: background 0.15s; text-decoration: none; display: inline-block;
    }
    .btn-sm { padding: 0.375rem 0.75rem; font-size: 0.75rem; }
    .btn-primary { background: #3b82f6; color: #fff; border: none; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-danger { background: #dc2626; color: #fff; border: none; }
    .btn-danger:hover { background: #b91c1c; }

    .tabs {
      display: flex; border-bottom: 1px solid #e2e8f0; margin-bottom: 1.5rem; gap: 0.25rem;
    }
    .tab {
      padding: 0.625rem 1rem; border: none; background: none; cursor: pointer;
      font-size: 0.8125rem; font-weight: 500; color: #64748b;
      border-bottom: 2px solid transparent; font-family: inherit;
      transition: color 0.15s;
    }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }
    .tab:hover { color: #3b82f6; }

    .tab-content { min-height: 200px; }

    .section { margin-bottom: 2rem; }
    .section h2 {
      font-size: 1.0625rem; font-weight: 600; color: #1e293b; margin: 0 0 0.75rem;
      padding-bottom: 0.375rem; border-bottom: 1px solid #e2e8f0;
    }
    .section h2 + .table-container { margin-bottom: 1.5rem; }
    .section-header {
      display: flex; justify-content: space-between; align-items: center;
      margin-bottom: 1rem;
    }
    .section-header h2 { margin-bottom: 0; }

    .table-container {
      overflow-x: auto; background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      margin-bottom: 1.5rem;
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
    .table tbody tr:hover { background: #f8fafc; }
    .table tbody tr:last-child td { border-bottom: none; }

    .kv-table .kv-key {
      font-weight: 600; color: #64748b; width: 180px; white-space: nowrap;
    }
    .kv-table .kv-val { color: #1e293b; word-break: break-all; }
    .mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 0.75rem; }

    .tags-grid {
      display: flex; flex-wrap: wrap; gap: 0.5rem;
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem; margin-bottom: 1.5rem;
    }
    .tag-chip {
      font-size: 0.75rem; padding: 0.25rem 0.625rem;
      background: #f1f5f9; border: 1px solid #e2e8f0;
      border-radius: 999px; color: #475569;
    }

    .rel-type { font-weight: 500; color: #1e293b; }
    .this-ci { font-weight: 500; color: #1e293b; }
    .ci-link {
      color: #3b82f6; text-decoration: none; font-weight: 500;
    }
    .ci-link:hover { text-decoration: underline; }

    .version-num { font-weight: 600; color: #1e293b; }

    .empty-state-box {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 2rem; text-align: center;
    }
    .empty-state-box p { color: #94a3b8; font-size: 0.8125rem; margin: 0; }

    .action-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      padding: 1rem 1.25rem; margin-bottom: 1.5rem;
    }
    .action-row {
      display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;
    }
    .action-label {
      font-size: 0.8125rem; font-weight: 600; color: #374151;
      min-width: 140px; flex-shrink: 0;
    }
    .action-select {
      padding: 0.5rem 0.75rem; border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; background: #fff; font-family: inherit;
      cursor: pointer; min-width: 180px;
    }
    .action-select:focus { border-color: #3b82f6; outline: none; }

    .danger-card { border-color: #fecaca; }
    .danger-info { display: flex; flex-direction: column; gap: 0.125rem; flex: 1; }
    .danger-title { font-size: 0.8125rem; font-weight: 600; color: #dc2626; }
    .danger-desc { font-size: 0.75rem; color: #64748b; }
  `],
})
export class CIDetailComponent implements OnInit {
  private cmdbService = inject(CmdbService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  ci = signal<ConfigurationItem | null>(null);
  relationships = signal<CIRelationship[]>([]);
  versions = signal<CISnapshot[]>([]);
  compartments = signal<CompartmentNode[]>([]);
  activeTab = signal<TabName>('attributes');
  loading = signal(true);

  readonly lifecycleStates = LIFECYCLE_STATES;
  selectedState = '';
  selectedCompartmentId = '';

  compartmentOptions = computed(() => this.compartments().map(c => ({ value: c.id, label: c.name })));

  private ciId = '';

  ngOnInit(): void {
    this.ciId = this.route.snapshot.paramMap.get('id') ?? '';
    if (!this.ciId) {
      this.loading.set(false);
      return;
    }

    const tabParam = this.route.snapshot.queryParamMap.get('tab');
    if (tabParam === 'attributes' || tabParam === 'relationships' || tabParam === 'history' || tabParam === 'actions') {
      this.activeTab.set(tabParam);
    }

    this.loadCI();
    this.loadRelationships();
    this.loadVersions();
    this.loadCompartments();
  }

  setTab(tab: TabName): void {
    this.activeTab.set(tab);
  }

  goBack(): void {
    this.router.navigate(['/cmdb']);
  }

  lifecycleColor(state: string): { bg: string; fg: string } {
    return LIFECYCLE_COLORS[state] ?? { bg: '#f1f5f9', fg: '#64748b' };
  }

  attributeKeys(): string[] {
    const item = this.ci();
    if (!item?.attributes) return [];
    return Object.keys(item.attributes).sort();
  }

  tagKeys(): string[] {
    const item = this.ci();
    if (!item?.tags) return [];
    return Object.keys(item.tags).sort();
  }

  formatAttrValue(value: unknown): string {
    if (value === null || value === undefined) return '\u2014';
    if (typeof value === 'object') return JSON.stringify(value);
    return String(value);
  }

  changeState(): void {
    if (!this.selectedState || this.selectedState === this.ci()?.lifecycleState) return;
    this.cmdbService.changeCIState(this.ciId, this.selectedState).subscribe({
      next: (updated) => {
        this.ci.set(updated);
        this.selectedState = updated.lifecycleState;
        this.toastService.success(`State changed to "${updated.lifecycleState}"`);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to change lifecycle state');
      },
    });
  }

  moveToCompartment(): void {
    const compartmentId = this.selectedCompartmentId || null;
    this.cmdbService.moveCI(this.ciId, compartmentId).subscribe({
      next: (updated) => {
        this.ci.set(updated);
        this.selectedCompartmentId = updated.compartmentId || '';
        this.toastService.success('Configuration item moved');
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to move configuration item');
      },
    });
  }

  async deleteCI(): Promise<void> {
    const item = this.ci();
    if (!item) return;
    const ok = await this.confirmService.confirm({
      title: 'Delete Configuration Item',
      message: `Delete "${item.name}"? This uses soft delete and can be recovered later.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    this.cmdbService.deleteCI(this.ciId).subscribe({
      next: () => {
        this.toastService.success(`"${item.name}" deleted`);
        this.router.navigate(['/cmdb']);
      },
      error: (err) => {
        this.toastService.error(err.message || 'Failed to delete configuration item');
      },
    });
  }

  private loadCI(): void {
    this.loading.set(true);
    this.cmdbService.getCI(this.ciId).subscribe({
      next: (item) => {
        this.ci.set(item);
        this.selectedState = item?.lifecycleState ?? '';
        this.selectedCompartmentId = item?.compartmentId ?? '';
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  private loadRelationships(): void {
    this.cmdbService.getCIRelationships(this.ciId).subscribe({
      next: (rels) => this.relationships.set(rels),
    });
  }

  private loadVersions(): void {
    this.cmdbService.getCIVersions(this.ciId).subscribe({
      next: (result) => this.versions.set(result.items),
    });
  }

  private loadCompartments(): void {
    this.cmdbService.getCompartmentTree().subscribe({
      next: (tree) => this.compartments.set(this.flattenCompartments(tree)),
    });
  }

  private flattenCompartments(nodes: CompartmentNode[], result: CompartmentNode[] = []): CompartmentNode[] {
    for (const node of nodes) {
      result.push(node);
      if (node.children?.length) {
        this.flattenCompartments(node.children, result);
      }
    }
    return result;
  }
}
