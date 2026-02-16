/**
 * Overview: Resolver definitions list page — table view with navigation to full-page editor.
 * Architecture: Provider-scoped page for managing resolver definitions (Section 11)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/component.service
 * Concepts: Provider Admin manages resolver definitions with provider compatibility.
 */
import { Component, OnInit, inject, signal, computed, ChangeDetectionStrategy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { ComponentService } from '@core/services/component.service';
import { SemanticService } from '@core/services/semantic.service';
import { ToastService } from '@shared/services/toast.service';
import { Resolver } from '@shared/models/component.model';

@Component({
  selector: 'nimbus-resolver-definitions',
  standalone: true,
  imports: [CommonModule, LayoutComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <nimbus-layout>
      <div class="page-container">
        <div class="page-header">
          <div class="header-left">
            <h1>Resolver Definitions</h1>
            <span class="subtitle">Manage resolver types and provider compatibility</span>
          </div>
          <div class="header-right">
            <button class="btn btn-primary" (click)="router.navigate(['/provider/resolvers/new'])">+ New Resolver</button>
          </div>
        </div>

        <!-- Table -->
        @if (!loading()) {
          <div class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Category</th>
                  <th>Can Release</th>
                  <th>Can Update</th>
                  <th>Providers</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                @for (r of resolvers(); track r.id) {
                  <tr>
                    <td class="name-cell">{{ r.displayName }}</td>
                    <td><code class="type-code">{{ r.resolverType }}</code></td>
                    <td>{{ r.category || '—' }}</td>
                    <td>
                      <span class="feature-badge" [class.enabled]="r.supportsRelease">
                        {{ r.supportsRelease ? 'Yes' : 'No' }}
                      </span>
                    </td>
                    <td>
                      <span class="feature-badge" [class.enabled]="r.supportsUpdate">
                        {{ r.supportsUpdate ? 'Yes' : 'No' }}
                      </span>
                    </td>
                    <td>
                      @for (pid of r.compatibleProviderIds; track pid) {
                        <span class="provider-chip">{{ getProviderName(pid) }}</span>
                      }
                      @if (!r.compatibleProviderIds.length) {
                        <span class="muted">None</span>
                      }
                    </td>
                    <td class="actions-cell">
                      <button class="action-btn" (click)="router.navigate(['/provider/resolvers', r.id, 'edit'])">Edit</button>
                      <button class="action-btn danger" (click)="onDelete(r)">Delete</button>
                    </td>
                  </tr>
                } @empty {
                  <tr>
                    <td colspan="7" class="empty-cell">No resolver definitions found</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }

        @if (loading()) {
          <div class="loading-text">Loading resolver definitions...</div>
        }
      </div>
    </nimbus-layout>
  `,
  styles: [`
    .page-container { padding: 0; }
    .page-header {
      display: flex; justify-content: space-between; align-items: flex-start;
      margin-bottom: 1.5rem;
    }
    .header-left h1 { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin: 0; }
    .subtitle { font-size: 0.875rem; color: #64748b; }

    .btn {
      padding: 0.5rem 1rem; border-radius: 6px; font-size: 0.875rem;
      font-weight: 500; cursor: pointer; border: none; font-family: inherit;
    }
    .btn-primary { background: #3b82f6; color: #fff; }
    .btn-primary:hover { background: #2563eb; }

    .table-container { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; }
    .table { width: 100%; border-collapse: collapse; }
    .table th {
      padding: 0.625rem 1rem; text-align: left; font-size: 0.6875rem; font-weight: 600;
      text-transform: uppercase; letter-spacing: 0.04em; color: #64748b;
      border-bottom: 1px solid #e2e8f0; background: #fafbfc;
    }
    .table td {
      padding: 0.75rem 1rem; font-size: 0.875rem; color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    .table tr:last-child td { border-bottom: none; }
    .table tr:hover td { background: #fafbfc; }
    .name-cell { font-weight: 500; color: #1e293b; }

    .type-code {
      padding: 2px 6px; background: #f1f5f9; border-radius: 4px;
      font-size: 0.75rem; font-family: monospace; color: #475569;
    }

    .feature-badge {
      padding: 2px 8px; border-radius: 12px; font-size: 0.6875rem; font-weight: 600;
      background: #f1f5f9; color: #94a3b8;
    }
    .feature-badge.enabled { background: #d1fae5; color: #065f46; }

    .provider-chip {
      display: inline-block; padding: 2px 8px; border-radius: 12px;
      font-size: 0.6875rem; font-weight: 500; background: #dbeafe; color: #1e40af;
      margin-right: 4px;
    }

    .actions-cell { white-space: nowrap; }
    .action-btn {
      padding: 0.25rem 0.5rem; border: none; background: none; color: #3b82f6;
      font-size: 0.8125rem; font-weight: 500; cursor: pointer; font-family: inherit;
    }
    .action-btn:hover { text-decoration: underline; }
    .action-btn.danger { color: #ef4444; }

    .empty-cell { text-align: center; padding: 2rem 1rem !important; color: #94a3b8; }
    .muted { color: #94a3b8; font-size: 0.75rem; }
    .loading-text { color: #94a3b8; font-size: 0.875rem; padding: 2rem 0; text-align: center; }
  `],
})
export class ResolverDefinitionsComponent implements OnInit {
  router = inject(Router);
  private componentService = inject(ComponentService);
  private semanticService = inject(SemanticService);
  private toast = inject(ToastService);
  private cdr = inject(ChangeDetectorRef);

  resolvers = signal<Resolver[]>([]);
  providers = signal<Array<{ id: string; name: string; displayName: string }>>([]);
  loading = signal(true);

  private providerMap = computed(() => {
    const map = new Map<string, string>();
    for (const p of this.providers()) {
      map.set(p.id, p.displayName || p.name);
    }
    return map;
  });

  ngOnInit(): void {
    this.loadData();
  }

  private loadData(): void {
    this.loading.set(true);
    this.componentService.listResolverDefinitions().subscribe({
      next: (r) => {
        this.resolvers.set(r);
        this.loading.set(false);
        this.cdr.markForCheck();
      },
      error: () => {
        this.toast.error('Failed to load resolver definitions');
        this.loading.set(false);
        this.cdr.markForCheck();
      },
    });

    this.semanticService.listProviders().subscribe({
      next: (p: Array<{ id: string; name: string; displayName: string }>) => {
        this.providers.set(p);
        this.cdr.markForCheck();
      },
    });
  }

  getProviderName(id: string): string {
    return this.providerMap().get(id) || id.slice(0, 8) + '...';
  }

  onDelete(r: Resolver): void {
    if (!confirm(`Delete resolver definition "${r.displayName}"?`)) return;
    this.componentService.deleteResolverDefinition(r.id).subscribe({
      next: () => {
        this.toast.success('Resolver definition deleted');
        this.loadData();
      },
      error: (e: Error) => this.toast.error(e.message || 'Failed to delete'),
    });
  }
}
