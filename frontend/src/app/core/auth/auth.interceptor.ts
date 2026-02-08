/**
 * Overview: HTTP interceptor that attaches JWT token, refreshes on 401, and handles session expiry.
 * Architecture: Auth middleware for HTTP client (Section 5.1)
 * Dependencies: @angular/common/http, @angular/router
 * Concepts: JWT, HTTP interceptor, token injection, token refresh, session expiry redirect
 */
import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';
import { ApiService } from '../services/api.service';

let isRefreshing = false;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const router = inject(Router);
  const token = localStorage.getItem('nimbus_access_token');

  if (token && !req.url.includes('/setup/')) {
    const authReq = addToken(req, token);
    return next(authReq).pipe(
      catchError((err) => {
        if (
          err.status === 401 &&
          !req.url.includes('/auth/login') &&
          !req.url.includes('/auth/refresh')
        ) {
          return handle401(req, next, router);
        }
        return throwError(() => err);
      }),
    );
  }

  return next(req);
};

function addToken(req: HttpRequest<unknown>, token: string): HttpRequest<unknown> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

function handle401(
  req: HttpRequest<unknown>,
  next: HttpHandlerFn,
  router: Router,
) {
  if (isRefreshing) {
    clearSession(router);
    return throwError(() => new Error('Session expired'));
  }

  isRefreshing = true;
  const refreshToken = localStorage.getItem('nimbus_refresh_token');

  if (!refreshToken) {
    isRefreshing = false;
    clearSession(router);
    return throwError(() => new Error('No refresh token'));
  }

  const api = inject(ApiService);
  return api
    .post<{ access_token: string; refresh_token: string }>(
      '/api/v1/auth/refresh',
      { refresh_token: refreshToken },
    )
    .pipe(
      switchMap((res) => {
        isRefreshing = false;
        localStorage.setItem('nimbus_access_token', res.access_token);
        localStorage.setItem('nimbus_refresh_token', res.refresh_token);
        // Retry the original request with the new token
        return next(addToken(req, res.access_token));
      }),
      catchError((refreshErr) => {
        isRefreshing = false;
        console.error('[auth] Token refresh failed, redirecting to login', refreshErr);
        clearSession(router);
        return throwError(() => refreshErr);
      }),
    );
}

function clearSession(router: Router): void {
  console.warn('[auth] Session cleared — redirecting to /login');
  localStorage.removeItem('nimbus_access_token');
  localStorage.removeItem('nimbus_refresh_token');
  localStorage.removeItem('nimbus_current_tenant_id');
  router.navigate(['/login']);
}
