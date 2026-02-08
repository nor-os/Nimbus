/**
 * Overview: Recursive tree visualization for tenant hierarchy.
 * Architecture: Shared tenant dashboard component (Section 3.2)
 * Dependencies: @angular/core, @angular/common, @angular/router
 * Concepts: Tenant hierarchy, recursive component, tree visualization
 */
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink } from '@angular/router';
import { TenantHierarchy } from '@core/models/tenant.model';

@Component({
  selector: 'nimbus-tenant-tree',
  standalone: true,
  imports: [CommonModule, RouterLink, TenantTreeComponent],
  template: `
    <ul class="tree-list">
      @for (node of nodes; track node.id) {
        <li class="tree-item">
          <a [routerLink]="['/tenants', node.id]" class="tree-link">
            @if (node.is_root) { <strong>{{ node.name }}</strong> }
            @else { {{ node.name }} }
          </a>
          @if (node.children.length > 0) {
            <nimbus-tenant-tree [nodes]="node.children" />
          }
        </li>
      }
    </ul>
  `,
  styles: [`
    .tree-list { list-style: none; padding-left: 1.25rem; margin: 0; }
    :host > .tree-list { padding-left: 0; }
    .tree-item { margin: 0.25rem 0; }
    .tree-link {
      text-decoration: none; color: #333; font-size: 0.875rem;
      padding: 0.125rem 0.25rem; border-radius: 4px;
    }
    .tree-link:hover { background: #f5f5f5; color: #1976d2; }
  `],
})
export class TenantTreeComponent {
  @Input({ required: true }) nodes: TenantHierarchy[] = [];
}
