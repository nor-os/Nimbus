/**
 * Overview: Structural directive that conditionally renders template content based on a permission key.
 * Architecture: Client-side permission gating for UI elements (Section 3.2, 5.2)
 * Dependencies: @angular/core, @core/services/permission-check.service
 * Concepts: Structural directive, permission-based rendering, reactive effect
 */
import {
  Directive,
  effect,
  inject,
  Input,
  TemplateRef,
  ViewContainerRef,
} from '@angular/core';
import { PermissionCheckService } from '@core/services/permission-check.service';

/**
 * Conditionally stamps the host template into the DOM when the current
 * user holds the specified permission.  Reacts to permission signal
 * changes so the view updates automatically if permissions are reloaded.
 *
 * Usage:
 * ```html
 * <button *hasPermission="'users:user:create'">Create User</button>
 * ```
 */
@Directive({
  selector: '[hasPermission]',
  standalone: true,
})
export class HasPermissionDirective {
  private readonly permissionCheck = inject(PermissionCheckService);
  private readonly templateRef = inject(TemplateRef<unknown>);
  private readonly viewContainer = inject(ViewContainerRef);

  @Input({ required: true }) hasPermission = '';

  private hasView = false;

  constructor() {
    effect(() => {
      // Reading the permissions signal registers a reactive dependency.
      // The effect re-runs whenever the permission set changes.
      this.permissionCheck.permissions();
      this.updateView();
    });
  }

  private updateView(): void {
    const permitted = this.permissionCheck.hasPermission(this.hasPermission);

    if (permitted && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!permitted && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }
}
