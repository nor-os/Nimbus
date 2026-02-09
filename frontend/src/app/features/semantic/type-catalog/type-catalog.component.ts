/**
 * Overview: Semantic type catalog — browse all semantic types grouped by category with search.
 * Architecture: Feature component for the semantic layer (Section 5)
 * Dependencies: @angular/core, @angular/common, @angular/router, app/core/services/semantic.service
 * Concepts: Semantic types grouped by categories, search filtering, navigation to type detail
 */
import { Component, inject, signal, computed, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { SemanticService } from '@core/services/semantic.service';
import { LayoutComponent } from '@shared/components/layout/layout.component';
import {
  SemanticCategoryWithTypes,
  SemanticResourceType,
} from '@shared/models/semantic.model';

@Component({
  selector: 'nimbus-type-catalog',
  standalone: true,
  imports: [CommonModule, FormsModule, LayoutComponent],
  template: `
    <nimbus-layout>
    <div class="catalog-page">
      <div class="page-header">
        <h1>Semantic Type Catalog</h1>
        <p class="subtitle">Abstract resource types that normalize provider-specific concepts into a unified model.</p>
      </div>

      <div class="toolbar">
        <div class="search-box">
          <input
            type="text"
            placeholder="Search types..."
            [ngModel]="searchTerm()"
            (ngModelChange)="searchTerm.set($event)"
          />
        </div>
        <div class="stats">
          {{ totalTypes() }} types across {{ categories().length }} categories
        </div>
      </div>

      @if (loading()) {
        <div class="loading">Loading semantic types...</div>
      }

      @if (!loading() && filteredCategories().length === 0) {
        <div class="empty-state">
          @if (searchTerm()) {
            No types matching "{{ searchTerm() }}"
          } @else {
            No semantic types found.
          }
        </div>
      }

      @for (cat of filteredCategories(); track cat.id) {
        <div class="category-section">
          <div class="category-header">
            <span class="category-name">{{ cat.displayName }}</span>
            <span class="category-count">{{ cat.types.length }} types</span>
          </div>
          @if (cat.description) {
            <p class="category-desc">{{ cat.description }}</p>
          }
          <div class="type-grid">
            @for (t of cat.types; track t.id) {
              <div class="type-card" (click)="navigateToType(t.id)">
                <div class="type-card-header">
                  <span class="type-name">{{ t.displayName }}</span>
                  @if (t.isAbstract) {
                    <span class="badge abstract">Abstract</span>
                  }
                </div>
                <p class="type-desc">{{ t.description }}</p>
                <div class="type-meta">
                  @if (t.propertiesSchema) {
                    <span class="meta-item">{{ t.propertiesSchema.length }} properties</span>
                  }
                  @if (t.mappings.length) {
                    <span class="meta-item">{{ t.mappings.length }} providers</span>
                  }
                </div>
              </div>
            }
          </div>
        </div>
      }
    </div>
    </nimbus-layout>
  `,
  styles: [`
    .catalog-page {
      padding: 1.5rem;
      max-width: 1200px;
    }

    .page-header h1 {
      font-size: 1.5rem;
      font-weight: 700;
      color: #1e293b;
      margin: 0 0 0.25rem;
    }
    .subtitle {
      color: #64748b;
      font-size: 0.875rem;
      margin: 0 0 1.5rem;
    }

    .toolbar {
      display: flex;
      align-items: center;
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    .search-box input {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 0.5rem 0.75rem;
      color: #374151;
      font-size: 0.875rem;
      width: 300px;
      outline: none;
    }
    .search-box input:focus {
      border-color: #3b82f6;
    }
    .stats {
      color: #64748b;
      font-size: 0.8125rem;
    }

    .loading, .empty-state {
      padding: 3rem;
      text-align: center;
      color: #64748b;
      font-size: 0.875rem;
    }

    .category-section {
      margin-bottom: 2rem;
    }
    .category-header {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      margin-bottom: 0.375rem;
    }
    .category-name {
      font-size: 1.125rem;
      font-weight: 600;
      color: #1e293b;
    }
    .category-count {
      font-size: 0.75rem;
      color: #64748b;
      background: #f1f5f9;
      padding: 0.125rem 0.5rem;
      border-radius: 999px;
    }
    .category-desc {
      color: #64748b;
      font-size: 0.8125rem;
      margin: 0 0 0.75rem;
    }

    .type-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 0.75rem;
    }

    .type-card {
      background: #fff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 1rem;
      cursor: pointer;
      transition: border-color 0.15s, background 0.15s;
    }
    .type-card:hover {
      border-color: #3b82f6;
      background: #f8fafc;
    }
    .type-card-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.375rem;
    }
    .type-name {
      font-size: 0.9375rem;
      font-weight: 600;
      color: #1e293b;
    }
    .badge {
      font-size: 0.625rem;
      padding: 0.125rem 0.375rem;
      border-radius: 3px;
      text-transform: uppercase;
      font-weight: 600;
      letter-spacing: 0.03em;
    }
    .badge.abstract {
      background: #f3e8ff;
      color: #7c3aed;
    }
    .type-desc {
      color: #64748b;
      font-size: 0.8125rem;
      margin: 0 0 0.5rem;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .type-meta {
      display: flex;
      gap: 0.75rem;
    }
    .meta-item {
      font-size: 0.75rem;
      color: #3b82f6;
    }
  `],
})
export class TypeCatalogComponent implements OnInit {
  private semanticService = inject(SemanticService);
  private router = inject(Router);

  categories = signal<SemanticCategoryWithTypes[]>([]);
  loading = signal(true);
  searchTerm = signal('');

  totalTypes = computed(() =>
    this.categories().reduce((sum, cat) => sum + cat.types.length, 0)
  );

  filteredCategories = computed(() => {
    const term = this.searchTerm().toLowerCase().trim();
    if (!term) return this.categories();

    return this.categories()
      .map((cat) => ({
        ...cat,
        types: cat.types.filter(
          (t) =>
            t.name.toLowerCase().includes(term) ||
            t.displayName.toLowerCase().includes(term) ||
            (t.description || '').toLowerCase().includes(term)
        ),
      }))
      .filter((cat) => cat.types.length > 0);
  });

  ngOnInit(): void {
    this.loadCategories();
  }

  navigateToType(id: string): void {
    this.router.navigate(['/semantic/types', id]);
  }

  private loadCategories(): void {
    this.loading.set(true);
    this.semanticService.listCategories().subscribe({
      next: (categories) => {
        this.categories.set(categories);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }
}
