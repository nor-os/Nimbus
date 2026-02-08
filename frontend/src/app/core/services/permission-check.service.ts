/**
 * Overview: Signal-based runtime permission checking service loaded on login.
 * Architecture: Client-side permission resolution (Section 3.2, 5.2)
 * Dependencies: @angular/core, app/core/services/permission.service
 * Concepts: Permission checking, signals, runtime access control
 */
import { Injectable, inject, signal, computed } from '@angular/core';
import { PermissionService } from './permission.service';
import { EffectivePermission } from '../models/permission.model';

@Injectable({ providedIn: 'root' })
export class PermissionCheckService {
  private permissionService = inject(PermissionService);

  private permissionsSignal = signal<EffectivePermission[]>([]);
  private loadingSignal = signal(false);

  readonly permissions = this.permissionsSignal.asReadonly();
  readonly isLoading = this.loadingSignal.asReadonly();

  readonly permissionKeys = computed(() =>
    new Set(this.permissionsSignal().map((p) => p.permission_key)),
  );

  loadMyPermissions(): void {
    this.loadingSignal.set(true);
    this.permissionService.getMyPermissions().subscribe({
      next: (perms) => {
        this.permissionsSignal.set(perms);
        this.loadingSignal.set(false);
      },
      error: () => {
        this.permissionsSignal.set([]);
        this.loadingSignal.set(false);
      },
    });
  }

  hasPermission(key: string): boolean {
    const keys = this.permissionKeys();
    if (keys.has(key)) return true;
    if (keys.has('*:*:*')) return true;

    // Check partial wildcard
    const parts = key.split(':');
    for (let i = parts.length - 1; i > 0; i--) {
      const wildcard = parts.slice(0, i).join(':') + ':' + Array(parts.length - i).fill('*').join(':');
      if (keys.has(wildcard)) return true;
    }
    return false;
  }

  clearPermissions(): void {
    this.permissionsSignal.set([]);
  }
}
