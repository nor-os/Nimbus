/**
 * Overview: Landing zone list page — shows all landing zones with status, backend, and actions.
 * Architecture: Feature component for landing zone management (Section 7.2)
 * Dependencies: @angular/core, @angular/router, landing-zone.service, layout
 * Concepts: Landing zone CRUD, status lifecycle, link to visual designer detail page
 */
import { Component, inject, signal, OnInit, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { LandingZoneService } from '@core/services/landing-zone.service';
import { CloudBackendService } from '@core/services/cloud-backend.service';
import { LandingZone, LandingZoneStatus } from '@shared/models/landing-zone.model';
import { CloudBackend } from '@shared/models/cloud-backend.model';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { HasPermissionDirective } from '@shared/directives/has-permission.directive';
import { ConfirmService } from '@shared/services/confirm.service';
import { ToastService } from '@shared/services/toast.service';

@Component({
  selector: 'nimbus-landing-zone-list',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink, LayoutComponent, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="list-page">
        <div class="page-header">
          <div>
            <h1>Landing Zones</h1>
            <p class="subtitle">Infrastructure blueprints for your cloud backends</p>
          </div>
          <div class="header-actions">
            <button
              *nimbusHasPermission="'landingzone:zone:create'"
              class="btn btn-primary"
              (click)="showCreateDialog = true"
            >
              New Landing Zone
            </button>
          </div>
        </div>

        <!-- Status tabs -->
        <div class="status-tabs">
          <button class="tab" [class.active]="statusFilter() === null" (click)="filterByStatus(null)">
            All ({{ zones().length }})
          </button>
          <button class="tab" [class.active]="statusFilter() === 'DRAFT'" (click)="filterByStatus('DRAFT')">
            Drafts
          </button>
          <button class="tab" [class.active]="statusFilter() === 'PUBLISHED'" (click)="filterByStatus('PUBLISHED')">
            Published
          </button>
          <button class="tab" [class.active]="statusFilter() === 'ARCHIVED'" (click)="filterByStatus('ARCHIVED')">
            Archived
          </button>
        </div>

        @if (loading()) {
          <div class="loading">Loading landing zones...</div>
        }

        @if (!loading() && filteredZones().length === 0) {
          <div class="empty-state">
            <div class="empty-icon">&#9878;</div>
            <h3>No landing zones yet</h3>
            <p>Create a landing zone to define your infrastructure blueprint for a cloud backend.</p>
          </div>
        }

        @if (filteredZones().length > 0) {
          <div class="zone-grid">
            @for (zone of filteredZones(); track zone.id) {
              <div class="zone-card" (click)="openZone(zone)">
                <div class="card-header">
                  <div class="card-title">{{ zone.name }}</div>
                  <span class="badge" [class]="'badge-' + zone.status.toLowerCase()">{{ zone.status }}</span>
                </div>
                <div class="card-body">
                  @if (zone.description) {
                    <p class="card-desc">{{ zone.description }}</p>
                  }
                  <div class="card-meta">
                    <div class="meta-item">
                      <span class="meta-label">Backend:</span>
                      <span>{{ getBackendName(zone.backendId) }}</span>
                    </div>
                    <div class="meta-item">
                      <span class="meta-label">Hub Region:</span>
                      <span>{{ zone.region?.displayName || '—' }}</span>
                    </div>
                    <div class="meta-item">
                      <span class="meta-label">Tags:</span>
                      <span>{{ zone.tagPolicies.length }}</span>
                    </div>
                    <div class="meta-item">
                      <span class="meta-label">Version:</span>
                      <span>{{ zone.version }}</span>
                    </div>
                  </div>
                </div>
                <div class="card-footer">
                  <span class="updated">Updated {{ zone.updatedAt | date:'short' }}</span>
                  <div class="card-actions">
                    @if (zone.status === 'DRAFT') {
                      <button class="btn-icon" title="Archive" (click)="archiveZone(zone, $event)">&#9744;</button>
                    }
                    <button class="btn-icon btn-danger" title="Delete" (click)="deleteZone(zone, $event)">&times;</button>
                  </div>
                </div>
              </div>
            }
          </div>
        }

        <!-- Create dialog -->
        @if (showCreateDialog) {
          <div class="dialog-backdrop" (click)="showCreateDialog = false">
            <div class="dialog" (click)="$event.stopPropagation()">
              <h2>New Landing Zone</h2>
              <div class="form-group">
                <label class="form-label">Name *</label>
                <input class="form-input" [(ngModel)]="newName" placeholder="e.g. Production Landing Zone" />
              </div>
              <div class="form-group">
                <label class="form-label">Description</label>
                <textarea class="form-input textarea" [(ngModel)]="newDescription" rows="2" placeholder="Optional description"></textarea>
              </div>
              <div class="form-group">
                <label class="form-label">Backend *</label>
                <select class="form-input" [(ngModel)]="newBackendId">
                  <option value="">Select a backend...</option>
                  @for (b of backends(); track b.id) {
                    <option [value]="b.id">{{ b.name }} ({{ b.providerDisplayName }})</option>
                  }
                </select>
              </div>
              <div class="form-actions">
                <button class="btn btn-secondary" (click)="showCreateDialog = false">Cancel</button>
                <button
                  class="btn btn-primary"
                  (click)="createZone()"
                  [disabled]="!newName.trim() || !newBackendId || creating()"
                >{{ creating() ? 'Creating...' : 'Create' }}</button>
              </div>
            </div>
          </div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .list-page { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .page-header h1 { margin: 0; font-size: 1.5rem; font-weight: 700; color: #1e293b; }
    .subtitle { font-size: 0.8125rem; color: #64748b; margin: 0.25rem 0 0; }
    .header-actions { display: flex; gap: 0.5rem; }

    .status-tabs {
      display: flex; gap: 0; border-bottom: 2px solid #e2e8f0; margin-bottom: 1.5rem;
    }
    .tab {
      padding: 0.5rem 0.875rem; font-size: 0.8125rem; font-weight: 500;
      color: #64748b; background: none; border: none; cursor: pointer;
      border-bottom: 2px solid transparent; margin-bottom: -2px; font-family: inherit;
    }
    .tab:hover { color: #1e293b; }
    .tab.active { color: #3b82f6; border-bottom-color: #3b82f6; }

    .zone-grid {
      display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1rem;
    }
    .zone-card {
      background: #fff; border: 1px solid #e2e8f0; border-radius: 8px;
      cursor: pointer; transition: box-shadow 0.15s, border-color 0.15s;
      display: flex; flex-direction: column;
    }
    .zone-card:hover { border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59, 130, 246, 0.1); }
    .card-header {
      display: flex; justify-content: space-between; align-items: center;
      padding: 1rem 1.25rem 0.5rem;
    }
    .card-title { font-size: 0.9375rem; font-weight: 600; color: #1e293b; }
    .card-body { padding: 0 1.25rem; flex: 1; }
    .card-desc { font-size: 0.8125rem; color: #64748b; margin: 0 0 0.75rem; line-height: 1.4; }
    .card-meta { display: grid; grid-template-columns: 1fr 1fr; gap: 0.375rem; }
    .meta-item { font-size: 0.75rem; color: #374151; }
    .meta-label { color: #94a3b8; margin-right: 0.25rem; }
    .card-footer {
      display: flex; justify-content: space-between; align-items: center;
      padding: 0.75rem 1.25rem; border-top: 1px solid #f1f5f9; margin-top: 0.75rem;
    }
    .updated { font-size: 0.6875rem; color: #94a3b8; }
    .card-actions { display: flex; gap: 0.25rem; }

    .badge {
      padding: 0.125rem 0.5rem; border-radius: 12px; font-size: 0.6875rem;
      font-weight: 600; text-transform: capitalize;
    }
    .badge-draft { background: #fef3c7; color: #92400e; }
    .badge-published { background: #dcfce7; color: #166534; }
    .badge-archived { background: #f1f5f9; color: #64748b; }

    .loading, .empty-state {
      padding: 3rem; text-align: center; color: #64748b; font-size: 0.8125rem;
    }
    .empty-state h3 { font-size: 1.125rem; font-weight: 600; color: #1e293b; margin: 0.5rem 0; }
    .empty-state p { margin: 0; }
    .empty-icon { font-size: 2.5rem; color: #94a3b8; }

    .btn {
      font-family: inherit; font-size: 0.8125rem; font-weight: 500;
      border-radius: 6px; cursor: pointer; border: none;
    }
    .btn-primary { background: #3b82f6; color: #fff; padding: 0.5rem 1rem; }
    .btn-primary:hover { background: #2563eb; }
    .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary { background: #fff; color: #374151; padding: 0.5rem 1rem; border: 1px solid #e2e8f0; }
    .btn-secondary:hover { background: #f8fafc; }
    .btn-icon {
      background: none; border: none; cursor: pointer; padding: 0.25rem 0.375rem;
      font-size: 0.875rem; border-radius: 4px; color: #64748b;
    }
    .btn-icon:hover { background: #f1f5f9; color: #1e293b; }
    .btn-danger { color: #dc2626; }
    .btn-danger:hover { background: #fef2f2; color: #dc2626; }

    .dialog-backdrop {
      position: fixed; inset: 0; background: rgba(0,0,0,0.4);
      display: flex; align-items: center; justify-content: center; z-index: 1000;
    }
    .dialog {
      background: #fff; border-radius: 12px; padding: 1.5rem; width: 480px;
      max-width: 90vw; box-shadow: 0 20px 60px rgba(0,0,0,0.15);
    }
    .dialog h2 { margin: 0 0 1.25rem; font-size: 1.125rem; font-weight: 600; color: #1e293b; }
    .form-group { margin-bottom: 1rem; }
    .form-label {
      display: block; font-size: 0.8125rem; font-weight: 600;
      color: #374151; margin-bottom: 0.375rem;
    }
    .form-input {
      width: 100%; padding: 0.5rem 0.75rem; background: #fff; color: #1e293b;
      border: 1px solid #e2e8f0; border-radius: 6px;
      font-size: 0.8125rem; box-sizing: border-box; font-family: inherit;
    }
    .form-input:focus { border-color: #3b82f6; outline: none; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
    .textarea { resize: vertical; }
    .form-actions { display: flex; gap: 0.5rem; justify-content: flex-end; margin-top: 1.25rem; }
  `],
})
export class LandingZoneListComponent implements OnInit {
  private lzService = inject(LandingZoneService);
  private backendService = inject(CloudBackendService);
  private router = inject(Router);
  private confirmService = inject(ConfirmService);
  private toastService = inject(ToastService);

  zones = signal<LandingZone[]>([]);
  backends = signal<CloudBackend[]>([]);
  loading = signal(false);
  creating = signal(false);
  statusFilter = signal<LandingZoneStatus | null>(null);

  showCreateDialog = false;
  newName = '';
  newDescription = '';
  newBackendId = '';

  private backendMap = new Map<string, string>();

  filteredZones = () => {
    const filter = this.statusFilter();
    const all = this.zones();
    return filter ? all.filter(z => z.status === filter) : all;
  };

  ngOnInit(): void {
    this.loadZones();
    this.loadBackends();
  }

  private loadZones(): void {
    this.loading.set(true);
    this.lzService.listLandingZones().subscribe({
      next: zones => {
        this.zones.set(zones);
        this.loading.set(false);
      },
      error: () => {
        this.toastService.error('Failed to load landing zones');
        this.loading.set(false);
      },
    });
  }

  private loadBackends(): void {
    this.backendService.listBackends().subscribe({
      next: backends => {
        this.backends.set(backends);
        for (const b of backends) {
          this.backendMap.set(b.id, b.name);
        }
      },
    });
  }

  getBackendName(id: string): string {
    return this.backendMap.get(id) || 'Unknown';
  }

  filterByStatus(status: LandingZoneStatus | null): void {
    this.statusFilter.set(status);
  }

  openZone(zone: LandingZone): void {
    this.router.navigate(['/landing-zones', zone.id]);
  }

  createZone(): void {
    if (!this.newName.trim() || !this.newBackendId) return;

    this.creating.set(true);
    // initializeLandingZone creates both the topology and landing zone on the backend
    this.backendService.initializeLandingZone(this.newBackendId).subscribe({
      next: () => {
        this.creating.set(false);
        this.toastService.success('Landing zone created');
        this.showCreateDialog = false;
        this.newName = '';
        this.newDescription = '';
        this.newBackendId = '';
        this.loadZones();
      },
      error: (err) => {
        this.creating.set(false);
        this.toastService.error(err.message || 'Failed to create landing zone');
      },
    });
  }

  async archiveZone(zone: LandingZone, event: Event): Promise<void> {
    event.stopPropagation();
    const ok = await this.confirmService.confirm({
      title: 'Archive Landing Zone',
      message: `Archive "${zone.name}"? It can still be viewed but not edited.`,
      confirmLabel: 'Archive',
    });
    if (!ok) return;

    this.lzService.archiveLandingZone(zone.id).subscribe({
      next: () => {
        this.toastService.success('Landing zone archived');
        this.loadZones();
      },
      error: (err) => this.toastService.error(err.message || 'Failed to archive'),
    });
  }

  async deleteZone(zone: LandingZone, event: Event): Promise<void> {
    event.stopPropagation();
    const ok = await this.confirmService.confirm({
      title: 'Delete Landing Zone',
      message: `Delete "${zone.name}"? This cannot be undone.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;

    this.lzService.deleteLandingZone(zone.id).subscribe({
      next: () => {
        this.toastService.success('Landing zone deleted');
        this.loadZones();
      },
      error: (err) => this.toastService.error(err.message || 'Failed to delete'),
    });
  }
}
