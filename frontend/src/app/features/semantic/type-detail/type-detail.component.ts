/**
 * Overview: Semantic type detail — display a single type's properties, relationships,
 *     provider mappings, and hierarchy.
 * Architecture: Feature component for the semantic layer (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/semantic.service
 * Concepts: Type detail, property schema, provider mappings, parent/child hierarchy
 */
import { Component, inject, signal, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute, Router } from '@angular/router';
import { SemanticService } from '@core/services/semantic.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import { SemanticResourceType } from '@shared/models/semantic.model';

@Component({
  selector: 'nimbus-type-detail',
  standalone: true,
  imports: [CommonModule, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="detail-page">
      @if (loading()) {
        <div class="loading">Loading type details...</div>
      }

      @if (!loading() && !type()) {
        <div class="empty-state">Type not found.</div>
      }

      @if (type(); as t) {
        <div class="page-header">
          <button class="back-btn" (click)="goBack()">&#8592; Back to catalog</button>
          <div class="title-row">
            <h1>{{ t.displayName }}</h1>
            <span class="badge category">{{ t.category.displayName }}</span>
            @if (t.isAbstract) {
              <span class="badge abstract">Abstract</span>
            }
          </div>
          @if (t.description) {
            <p class="description">{{ t.description }}</p>
          }
        </div>

        <!-- Property Schema -->
        @if (t.propertiesSchema?.length) {
          <section class="section">
            <h2>Properties ({{ t.propertiesSchema!.length }})</h2>
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Display Name</th>
                    <th>Type</th>
                    <th>Required</th>
                    <th>Unit</th>
                    <th>Default</th>
                    <th>Description</th>
                  </tr>
                </thead>
                <tbody>
                  @for (prop of t.propertiesSchema; track prop.name) {
                    <tr>
                      <td class="mono">{{ prop.name }}</td>
                      <td>{{ prop.display_name }}</td>
                      <td><span class="badge type-badge">{{ prop.data_type }}</span></td>
                      <td>
                        @if (prop.required) {
                          <span class="required-dot">&#9679;</span>
                        }
                      </td>
                      <td class="muted">{{ prop.unit || '—' }}</td>
                      <td class="muted">{{ prop.default_value || '—' }}</td>
                      <td class="muted">{{ prop.description || '—' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }

        <!-- Provider Mappings -->
        @if (t.mappings.length) {
          <section class="section">
            <h2>Provider Mappings ({{ t.mappings.length }})</h2>
            <div class="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Provider</th>
                    <th>Resource Type</th>
                    <th>Notes</th>
                  </tr>
                </thead>
                <tbody>
                  @for (m of t.mappings; track m.id) {
                    <tr>
                      <td class="provider-name">{{ m.providerName }}</td>
                      <td class="mono">{{ m.providerDisplayName || m.providerApiType }}</td>
                      <td class="muted">{{ m.notes || '—' }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </section>
        }

        <!-- Allowed Relationships -->
        @if (t.allowedRelationshipKinds?.length) {
          <section class="section">
            <h2>Allowed Relationships</h2>
            <div class="relationship-chips">
              @for (kind of t.allowedRelationshipKinds; track kind) {
                <span class="chip">{{ kind }}</span>
              }
            </div>
          </section>
        }

        <!-- Hierarchy -->
        @if (t.parentTypeName || t.children.length) {
          <section class="section">
            <h2>Type Hierarchy</h2>
            @if (t.parentTypeName) {
              <div class="hierarchy-item">
                <span class="muted">Parent:</span>
                <span class="mono">{{ t.parentTypeName }}</span>
              </div>
            }
            @if (t.children.length) {
              <div class="hierarchy-item">
                <span class="muted">Children:</span>
                @for (child of t.children; track child.id) {
                  <span class="chip clickable" (click)="navigateToType(child.id)">
                    {{ child.displayName }}
                  </span>
                }
              </div>
            }
          </section>
        }
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .detail-page {
      padding: 1.5rem;
      max-width: 1000px;
    }
    .loading, .empty-state {
      padding: 3rem;
      text-align: center;
      color: #64748b;
    }

    .back-btn {
      background: none;
      border: none;
      color: #3b82f6;
      cursor: pointer;
      font-size: 0.8125rem;
      padding: 0;
      margin-bottom: 0.75rem;
      font-family: inherit;
    }
    .back-btn:hover { text-decoration: underline; }

    .title-row {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.375rem;
    }
    .title-row h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #1e293b;
      margin: 0;
    }
    .description {
      color: #64748b;
      font-size: 0.875rem;
      margin: 0 0 1.5rem;
    }

    .badge {
      font-size: 0.6875rem;
      padding: 0.125rem 0.5rem;
      border-radius: 3px;
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .badge.category {
      background: #dbeafe;
      color: #1d4ed8;
    }
    .badge.abstract {
      background: #f3e8ff;
      color: #7c3aed;
    }
    .badge.type-badge {
      background: #dcfce7;
      color: #16a34a;
      font-size: 0.625rem;
      text-transform: lowercase;
    }
    .section {
      margin-bottom: 2rem;
    }
    .section h2 {
      font-size: 1.0625rem;
      font-weight: 600;
      color: #1e293b;
      margin: 0 0 0.75rem;
      padding-bottom: 0.375rem;
      border-bottom: 1px solid #e2e8f0;
    }

    .table-wrapper {
      overflow-x: auto;
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 0.8125rem;
    }
    th {
      text-align: left;
      padding: 0.5rem 0.75rem;
      color: #64748b;
      font-weight: 600;
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid #e2e8f0;
    }
    td {
      padding: 0.5rem 0.75rem;
      color: #374151;
      border-bottom: 1px solid #f1f5f9;
    }
    tr:last-child td {
      border-bottom: none;
    }
    tr:hover td {
      background: #f8fafc;
    }
    .mono {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      font-size: 0.8125rem;
    }
    .muted { color: #94a3b8; }
    .required-dot { color: #dc2626; }

    .provider-name {
      text-transform: capitalize;
      font-weight: 500;
    }

    .relationship-chips, .hierarchy-item {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 0.5rem;
    }
    .hierarchy-item {
      margin-bottom: 0.5rem;
    }
    .chip {
      font-size: 0.75rem;
      padding: 0.25rem 0.625rem;
      background: #f1f5f9;
      border: 1px solid #e2e8f0;
      border-radius: 999px;
      color: #475569;
    }
    .chip.clickable {
      cursor: pointer;
    }
    .chip.clickable:hover {
      border-color: #3b82f6;
      color: #3b82f6;
    }
  `],
})
export class TypeDetailComponent implements OnInit {
  private semanticService = inject(SemanticService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);

  type = signal<SemanticResourceType | null>(null);
  loading = signal(true);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id');
    if (id) {
      this.loadType(id);
    } else {
      this.loading.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(['/semantic/types']);
  }

  navigateToType(id: string): void {
    this.router.navigate(['/semantic/types', id]);
  }

  private loadType(id: string): void {
    this.loading.set(true);
    this.semanticService.getType(id).subscribe({
      next: (t) => {
        this.type.set(t);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
