/**
 * Overview: Signal-based breadcrumb service that builds navigation trails from route data.
 * Architecture: Shared service for breadcrumb navigation (Section 3.2)
 * Dependencies: @angular/core, @angular/router
 * Concepts: Breadcrumb navigation, route data, dynamic label overrides, Angular signals
 */
import { Injectable, signal, inject, DestroyRef } from '@angular/core';
import { Router, NavigationEnd, ActivatedRoute } from '@angular/router';
import { filter } from 'rxjs/operators';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';

export interface Breadcrumb {
  label: string;
  url: string;
}

/**
 * Route data breadcrumb format:
 * - string: single breadcrumb label (url built from route segments)
 * - array:  multiple breadcrumbs for multi-segment child paths.
 *           Each entry is either a string (terminal label, uses current url)
 *           or { label, path } where path is the absolute route for the link.
 */
export type BreadcrumbData = string | Array<string | { label: string; path: string }>;

@Injectable({ providedIn: 'root' })
export class BreadcrumbService {
  private readonly router = inject(Router);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  readonly breadcrumbs = signal<Breadcrumb[]>([]);

  private labelOverrides = new Map<string, string>();

  constructor() {
    this.router.events
      .pipe(
        filter((event) => event instanceof NavigationEnd),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe(() => {
        this.labelOverrides.clear();
        this.breadcrumbs.set(this.buildBreadcrumbs());
      });
  }

  /**
   * Override the label for a dynamic route param.
   * Call from feature components after loading entity data.
   * Example: breadcrumbService.setLabel(':id', user.email)
   */
  setLabel(paramKey: string, label: string): void {
    this.labelOverrides.set(paramKey, label);
    this.breadcrumbs.set(this.buildBreadcrumbs());
  }

  private buildBreadcrumbs(): Breadcrumb[] {
    const breadcrumbs: Breadcrumb[] = [];
    let route: ActivatedRoute | null = this.activatedRoute.root;
    let url = '';

    while (route) {
      const segments = route.snapshot.url;
      if (segments.length > 0) {
        url += '/' + segments.map((s) => s.path).join('/');
      }

      const breadcrumbData: BreadcrumbData | undefined = route.snapshot.data['breadcrumb'];
      if (breadcrumbData) {
        if (typeof breadcrumbData === 'string') {
          breadcrumbs.push({ label: this.resolveLabel(breadcrumbData, route), url });
        } else if (Array.isArray(breadcrumbData)) {
          for (const entry of breadcrumbData) {
            if (typeof entry === 'string') {
              breadcrumbs.push({ label: this.resolveLabel(entry, route), url });
            } else {
              breadcrumbs.push({ label: entry.label, url: entry.path });
            }
          }
        }
      }

      route = route.firstChild;
    }

    return breadcrumbs;
  }

  private resolveLabel(label: string, route: ActivatedRoute): string {
    const params = route.snapshot.params;
    for (const [paramKey] of Object.entries(params)) {
      const overrideKey = ':' + paramKey;
      if (this.labelOverrides.has(overrideKey)) {
        return this.labelOverrides.get(overrideKey)!;
      }
    }
    return label;
  }
}
