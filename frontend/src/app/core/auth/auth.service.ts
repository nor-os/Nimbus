/**
 * Overview: Authentication service managing login state with Angular signals.
 * Architecture: Core auth service (Section 3.2, 5.1)
 * Dependencies: @angular/core, @angular/router, app/core/services/api.service
 * Concepts: Authentication, JWT, signals-based state management, tenant context
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap, catchError, of } from 'rxjs';
import { ApiService } from '../services/api.service';
import { ImpersonationService } from '../services/impersonation.service';
import { TenantContextService } from '../services/tenant-context.service';
import { PermissionCheckService } from '../services/permission-check.service';
import {
  DiscoverResponse,
  LoginRequest,
  TenantLoginInfo,
  TokenResponse,
  UserInfo,
  SetupStatus,
  SetupRequest,
} from './auth.models';

const TOKEN_KEY = 'nimbus_access_token';
const REFRESH_KEY = 'nimbus_refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(ApiService);
  private router = inject(Router);
  private impersonation = inject(ImpersonationService);
  private tenantContext = inject(TenantContextService);
  private permissionCheck = inject(PermissionCheckService);

  private currentUserSignal = signal<UserInfo | null>(null);
  private loadingSignal = signal(false);

  readonly currentUser = this.currentUserSignal.asReadonly();
  readonly isAuthenticated = computed(() => this.currentUserSignal() !== null);
  readonly isLoading = this.loadingSignal.asReadonly();

  get accessToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  login(credentials: LoginRequest): Observable<TokenResponse> {
    this.loadingSignal.set(true);
    return this.api.post<TokenResponse>('/api/v1/auth/login', credentials).pipe(
      tap((res) => {
        this.storeTokens(res);
        this.loadCurrentUser();
        this.tenantContext.loadAccessibleTenants();
        this.permissionCheck.loadMyPermissions();
      }),
      tap({ finalize: () => this.loadingSignal.set(false) }),
    );
  }

  logout(): void {
    this.api.post('/api/v1/auth/logout', {}).subscribe({
      complete: () => this.clearSession(),
      error: () => this.clearSession(),
    });
  }

  refreshToken(): Observable<TokenResponse | null> {
    const refreshToken = localStorage.getItem(REFRESH_KEY);
    if (!refreshToken) {
      this.clearSession();
      return of(null);
    }

    return this.api
      .post<TokenResponse>('/api/v1/auth/refresh', { refresh_token: refreshToken })
      .pipe(
        tap((res) => this.storeTokens(res)),
        catchError(() => {
          this.clearSession();
          return of(null);
        }),
      );
  }

  loadCurrentUser(): void {
    this.api.get<UserInfo>('/api/v1/auth/me').subscribe({
      next: (user) => this.currentUserSignal.set(user),
      error: () => this.currentUserSignal.set(null),
    });
  }

  checkSetupStatus(): Observable<SetupStatus> {
    return this.api.get<SetupStatus>('/api/v1/setup/status');
  }

  initializeSetup(data: SetupRequest): Observable<TokenResponse> {
    return this.api.post<TokenResponse>('/api/v1/setup/initialize', data).pipe(
      tap((res) => {
        this.storeTokens(res);
        this.loadCurrentUser();
        this.tenantContext.loadAccessibleTenants();
        this.permissionCheck.loadMyPermissions();
      }),
    );
  }

  discover(email: string): Observable<DiscoverResponse> {
    return this.api.post<DiscoverResponse>('/api/v1/auth/discover', { email });
  }

  getLoginInfo(slug: string): Observable<TenantLoginInfo> {
    return this.api.get<TenantLoginInfo>(`/api/v1/auth/login-info/${slug}`);
  }

  loginWithProvider(tenantId: string, providerId: string, idpType: string): void {
    if (idpType === 'oidc') {
      this.api
        .get<{ authorization_url: string }>(
          `/api/v1/auth/sso/${tenantId}/oidc/authorize?provider_id=${providerId}`,
        )
        .subscribe({
          next: (res) => (window.location.href = res.authorization_url),
        });
    } else if (idpType === 'saml') {
      this.api
        .get<{ redirect_url: string }>(
          `/api/v1/auth/sso/${tenantId}/saml/login?provider_id=${providerId}`,
        )
        .subscribe({
          next: (res) => (window.location.href = res.redirect_url),
        });
    }
  }

  tryRestoreSession(): void {
    if (this.accessToken) {
      this.loadCurrentUser();
      this.tenantContext.loadAccessibleTenants();
      this.permissionCheck.loadMyPermissions();
      this.impersonation.checkStatus().subscribe();
    }
  }

  private storeTokens(res: TokenResponse): void {
    localStorage.setItem(TOKEN_KEY, res.access_token);
    localStorage.setItem(REFRESH_KEY, res.refresh_token);
  }

  private clearSession(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
    this.currentUserSignal.set(null);
    this.tenantContext.clearContext();
    this.permissionCheck.clearPermissions();
    this.impersonation.clearState();
    this.router.navigate(['/login']);
  }
}
