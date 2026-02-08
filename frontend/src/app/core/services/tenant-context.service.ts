/**
 * Overview: Manages the current tenant context with Angular signals.
 * Architecture: Tenant context management (Section 3.2, 4.2)
 * Dependencies: @angular/core, app/core/services/api.service, app/core/auth/auth.service
 * Concepts: Multi-tenancy, tenant switching, signals-based state
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { ApiService } from './api.service';
import { UserTenantInfo } from '../models/tenant.model';

const CURRENT_TENANT_KEY = 'nimbus_current_tenant_id';

@Injectable({ providedIn: 'root' })
export class TenantContextService {
  private api = inject(ApiService);

  private accessibleTenantsSignal = signal<UserTenantInfo[]>([]);
  private currentTenantIdSignal = signal<string | null>(
    localStorage.getItem(CURRENT_TENANT_KEY),
  );

  readonly accessibleTenants = this.accessibleTenantsSignal.asReadonly();
  readonly currentTenantId = this.currentTenantIdSignal.asReadonly();
  readonly hasMultipleTenants = computed(() => this.accessibleTenantsSignal().length > 1);

  readonly currentTenant = computed(() => {
    const id = this.currentTenantIdSignal();
    return this.accessibleTenantsSignal().find((t) => t.tenant_id === id) ?? null;
  });

  readonly isRootTenant = computed(() => {
    const tenant = this.currentTenant();
    return tenant?.is_root ?? false;
  });

  /** True when root tenant is active OR no tenant context exists yet (fresh setup, no tenants loaded). */
  readonly canManageClients = computed(() => {
    const tenants = this.accessibleTenantsSignal();
    if (tenants.length === 0) return true; // no tenants loaded yet — show menu
    return this.isRootTenant();
  });

  loadAccessibleTenants(): void {
    this.api.get<UserTenantInfo[]>('/api/v1/auth/tenants').subscribe({
      next: (tenants) => {
        this.accessibleTenantsSignal.set(tenants);
        if (tenants.length > 0 && !this.currentTenantIdSignal()) {
          const defaultTenant = tenants.find((t) => t.is_default) ?? tenants[0];
          this.setCurrentTenantId(defaultTenant.tenant_id);
        }
      },
      error: () => this.accessibleTenantsSignal.set([]),
    });
  }

  switchTenant(tenantId: string): void {
    interface SwitchTenantResponse {
      access_token: string;
      refresh_token: string;
      token_type: string;
      expires_in: number;
      current_tenant_id: string | null;
    }

    this.api
      .post<SwitchTenantResponse>('/api/v1/auth/switch-tenant', {
        tenant_id: tenantId,
      })
      .subscribe({
        next: (res) => {
          localStorage.setItem('nimbus_access_token', res.access_token);
          localStorage.setItem('nimbus_refresh_token', res.refresh_token);
          this.setCurrentTenantId(tenantId);
          // Reload the page to refresh all data with new tenant context
          window.location.reload();
        },
      });
  }

  clearContext(): void {
    this.currentTenantIdSignal.set(null);
    this.accessibleTenantsSignal.set([]);
    localStorage.removeItem(CURRENT_TENANT_KEY);
  }

  private setCurrentTenantId(id: string): void {
    this.currentTenantIdSignal.set(id);
    localStorage.setItem(CURRENT_TENANT_KEY, id);
  }
}
