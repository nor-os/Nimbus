/**
 * Overview: Functional route guard factory that checks a single permission before allowing navigation.
 * Architecture: Client-side route protection (Section 3.2, 5.2)
 * Dependencies: @angular/router, @core/services/permission-check.service
 * Concepts: CanActivateFn, permission-based routing, guard factory pattern
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { PermissionCheckService } from '@core/services/permission-check.service';

/**
 * Creates a route guard that checks whether the current user holds the
 * specified permission key.  Returns `true` to allow navigation, or
 * redirects to `/dashboard` when the permission is missing.
 *
 * Usage in route config:
 * ```ts
 * {
 *   path: 'users',
 *   component: UsersComponent,
 *   canActivate: [permissionGuard('users:user:read')],
 * }
 * ```
 */
export function permissionGuard(requiredPermission: string): CanActivateFn {
  return () => {
    const permissionCheck = inject(PermissionCheckService);
    const router = inject(Router);

    // While permissions are still loading, allow navigation to avoid a flash redirect.
    // Once loaded, the backend is authoritative — deny if the user lacks the permission.
    if (permissionCheck.isLoading()) {
      return true;
    }

    if (permissionCheck.hasPermission(requiredPermission)) {
      return true;
    }

    return router.createUrlTree(['/dashboard']);
  };
}
