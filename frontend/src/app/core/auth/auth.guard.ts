/**
 * Overview: Route guard that redirects unauthenticated users to login.
 * Architecture: Auth guard for protected routes (Section 5.1)
 * Dependencies: @angular/core, @angular/router
 * Concepts: Route protection, authentication
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.accessToken) {
    return true;
  }

  return router.createUrlTree(['/login']);
};
