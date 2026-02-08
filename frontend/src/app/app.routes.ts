/**
 * Overview: Application route definitions with lazy loading and permission guards.
 * Architecture: Hash-based routing (Section 3.2)
 * Dependencies: @angular/router, app/core/auth/auth.guard, app/core/guards/permission.guard
 * Concepts: Routing, lazy loading, auth guards, permission guards, breadcrumb navigation
 */
import { Routes } from '@angular/router';
import { authGuard } from './core/auth/auth.guard';
import { permissionGuard } from './core/guards/permission.guard';

export const routes: Routes = [
  {
    path: 'setup',
    loadComponent: () =>
      import('./features/setup/setup.component').then((m) => m.SetupComponent),
  },
  {
    path: 'login/:slug',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'dashboard',
    loadComponent: () =>
      import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
    canActivate: [authGuard],
    data: { breadcrumb: 'Dashboard' },
  },
  {
    path: 'tenants',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/tenants/tenant-list/tenant-list.component').then(
            (m) => m.TenantListComponent,
          ),
        canActivate: [permissionGuard('settings:tenant:read')],
        data: { breadcrumb: 'Tenants' },
      },
      {
        path: 'create',
        loadComponent: () =>
          import('./features/tenants/tenant-form/tenant-form.component').then(
            (m) => m.TenantFormComponent,
          ),
        canActivate: [permissionGuard('settings:tenant:create')],
        data: { breadcrumb: [{ label: 'Tenants', path: '/tenants' }, 'Create'] },
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./features/tenants/tenant-dashboard/tenant-dashboard.component').then(
            (m) => m.TenantDashboardComponent,
          ),
        canActivate: [permissionGuard('settings:tenant:read')],
        data: { breadcrumb: [{ label: 'Tenants', path: '/tenants' }, 'Details'] },
      },
      {
        path: ':id/settings',
        loadComponent: () =>
          import('./features/tenants/tenant-settings/tenant-settings.component').then(
            (m) => m.TenantSettingsComponent,
          ),
        canActivate: [permissionGuard('settings:tenant:update')],
        data: { breadcrumb: [{ label: 'Tenants', path: '/tenants' }, 'Settings'] },
      },
    ],
  },
  {
    path: 'users',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/users/user-list/user-list.component').then(
            (m) => m.UserListComponent,
          ),
        canActivate: [permissionGuard('users:user:list')],
        data: { breadcrumb: 'Users' },
      },
      {
        path: 'create',
        loadComponent: () =>
          import('./features/users/user-form/user-form.component').then(
            (m) => m.UserFormComponent,
          ),
        canActivate: [permissionGuard('users:user:create')],
        data: { breadcrumb: [{ label: 'Users', path: '/users' }, 'Create'] },
      },
      {
        path: 'roles',
        loadComponent: () =>
          import('./features/permissions/roles/role-list/role-list.component').then(
            (m) => m.RoleListComponent,
          ),
        canActivate: [permissionGuard('users:role:list')],
        data: { breadcrumb: 'Roles' },
      },
      {
        path: 'roles/create',
        loadComponent: () =>
          import('./features/permissions/roles/role-form/role-form.component').then(
            (m) => m.RoleFormComponent,
          ),
        canActivate: [permissionGuard('users:role:create')],
        data: { breadcrumb: [{ label: 'Roles', path: '/users/roles' }, 'Create'] },
      },
      {
        path: 'roles/:id',
        loadComponent: () =>
          import('./features/permissions/roles/role-form/role-form.component').then(
            (m) => m.RoleFormComponent,
          ),
        canActivate: [permissionGuard('users:role:update')],
        data: { breadcrumb: [{ label: 'Roles', path: '/users/roles' }, 'Edit'] },
      },
      {
        path: 'groups',
        loadComponent: () =>
          import('./features/permissions/groups/group-list/group-list.component').then(
            (m) => m.GroupListComponent,
          ),
        canActivate: [permissionGuard('users:group:list')],
        data: { breadcrumb: 'Groups' },
      },
      {
        path: 'groups/create',
        loadComponent: () =>
          import('./features/permissions/groups/group-form/group-form.component').then(
            (m) => m.GroupFormComponent,
          ),
        canActivate: [permissionGuard('users:group:create')],
        data: { breadcrumb: [{ label: 'Groups', path: '/users/groups' }, 'Create'] },
      },
      {
        path: 'groups/:id',
        loadComponent: () =>
          import('./features/permissions/groups/group-form/group-form.component').then(
            (m) => m.GroupFormComponent,
          ),
        canActivate: [permissionGuard('users:group:update')],
        data: { breadcrumb: [{ label: 'Groups', path: '/users/groups' }, 'Edit'] },
      },
      {
        path: 'impersonate',
        loadComponent: () =>
          import('./features/impersonation/impersonation-sessions/impersonation-sessions.component').then(
            (m) => m.ImpersonationSessionsComponent,
          ),
        canActivate: [permissionGuard('impersonation:session:read')],
        data: { breadcrumb: [{ label: 'Users', path: '/users' }, 'Impersonate'] },
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./features/users/user-detail/user-detail.component').then(
            (m) => m.UserDetailComponent,
          ),
        canActivate: [permissionGuard('users:user:read')],
        data: { breadcrumb: [{ label: 'Users', path: '/users' }, 'Details'] },
      },
    ],
  },
  {
    path: 'permissions',
    canActivate: [authGuard],
    children: [
      {
        path: 'abac',
        loadComponent: () =>
          import('./features/permissions/abac/abac-list/abac-list.component').then(
            (m) => m.ABACListComponent,
          ),
        canActivate: [permissionGuard('permissions:abac:list')],
        data: { breadcrumb: 'ABAC Policies' },
      },
      {
        path: 'abac/create',
        loadComponent: () =>
          import('./features/permissions/abac/abac-editor/abac-editor.component').then(
            (m) => m.ABACEditorComponent,
          ),
        canActivate: [permissionGuard('permissions:abac:create')],
        data: { breadcrumb: [{ label: 'ABAC Policies', path: '/permissions/abac' }, 'Create'] },
      },
      {
        path: 'abac/:id',
        loadComponent: () =>
          import('./features/permissions/abac/abac-editor/abac-editor.component').then(
            (m) => m.ABACEditorComponent,
          ),
        canActivate: [permissionGuard('permissions:abac:update')],
        data: { breadcrumb: [{ label: 'ABAC Policies', path: '/permissions/abac' }, 'Edit'] },
      },
      {
        path: 'overrides',
        loadComponent: () =>
          import('./features/permissions/overrides/override-list/override-list.component').then(
            (m) => m.OverrideListComponent,
          ),
        canActivate: [permissionGuard('permissions:abac:list')],
        data: { breadcrumb: 'Permission Overrides' },
      },
      {
        path: 'simulator',
        loadComponent: () =>
          import('./features/permissions/simulator/permission-simulator.component').then(
            (m) => m.PermissionSimulatorComponent,
          ),
        canActivate: [permissionGuard('permissions:permission:simulate')],
        data: { breadcrumb: 'Permission Simulator' },
      },
      {
        path: 'assignment/:userId',
        loadComponent: () =>
          import('./features/permissions/assignment/permission-assignment.component').then(
            (m) => m.PermissionAssignmentComponent,
          ),
        canActivate: [permissionGuard('users:role:assign')],
        data: { breadcrumb: 'Permission Assignment' },
      },
    ],
  },
  {
    path: 'audit',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/audit/audit-explorer/audit-explorer.component').then(
            (m) => m.AuditExplorerComponent,
          ),
        canActivate: [permissionGuard('audit:log:read')],
        data: { breadcrumb: 'Audit Log' },
      },
      {
        path: 'config',
        loadComponent: () =>
          import('./features/audit/audit-config/audit-config.component').then(
            (m) => m.AuditConfigComponent,
          ),
        canActivate: [permissionGuard('audit:retention:read')],
        data: { breadcrumb: [{ label: 'Audit Log', path: '/audit' }, 'Configuration'] },
      },
    ],
  },
  {
    path: 'notifications',
    loadComponent: () =>
      import('./features/notifications/notification-center/notification-center.component').then(
        (m) => m.NotificationCenterComponent,
      ),
    canActivate: [authGuard],
    data: { breadcrumb: 'Notifications' },
  },
  {
    path: 'settings',
    canActivate: [authGuard],
    children: [
      {
        path: 'auth',
        loadComponent: () =>
          import('./features/settings/authentication/idp-list/idp-list.component').then(
            (m) => m.IdpListComponent,
          ),
        canActivate: [permissionGuard('settings:idp:list')],
        data: { breadcrumb: 'Authentication' },
      },
      {
        path: 'auth/create',
        loadComponent: () =>
          import('./features/settings/authentication/idp-form/idp-form.component').then(
            (m) => m.IdpFormComponent,
          ),
        canActivate: [permissionGuard('settings:idp:create')],
        data: { breadcrumb: [{ label: 'Authentication', path: '/settings/auth' }, 'Create'] },
      },
      {
        path: 'auth/:id',
        loadComponent: () =>
          import('./features/settings/authentication/idp-form/idp-form.component').then(
            (m) => m.IdpFormComponent,
          ),
        canActivate: [permissionGuard('settings:idp:update')],
        data: { breadcrumb: [{ label: 'Authentication', path: '/settings/auth' }, 'Edit'] },
      },
      {
        path: 'auth/:id/claim-mappings',
        loadComponent: () =>
          import('./features/settings/authentication/claim-mapping/claim-mapping.component').then(
            (m) => m.ClaimMappingComponent,
          ),
        canActivate: [permissionGuard('settings:idp:update')],
        data: {
          breadcrumb: [{ label: 'Authentication', path: '/settings/auth' }, 'Claim Mappings'],
        },
      },
      {
        path: 'impersonation',
        loadComponent: () =>
          import('./features/impersonation/impersonation-config/impersonation-config.component').then(
            (m) => m.ImpersonationConfigComponent,
          ),
        canActivate: [permissionGuard('impersonation:config:manage')],
        data: {
          breadcrumb: [{ label: 'Settings', path: '/settings/auth' }, 'Impersonation'],
        },
      },
      {
        path: 'notifications',
        loadComponent: () =>
          import(
            './features/notifications/notification-preferences/notification-preferences.component'
          ).then((m) => m.NotificationPreferencesComponent),
        canActivate: [permissionGuard('notification:preference:manage')],
        data: {
          breadcrumb: [{ label: 'Settings', path: '/settings/auth' }, 'Notifications'],
        },
      },
      {
        path: 'webhooks',
        loadComponent: () =>
          import(
            './features/notifications/webhook-management/webhook-management.component'
          ).then((m) => m.WebhookManagementComponent),
        canActivate: [permissionGuard('notification:webhook:manage')],
        data: {
          breadcrumb: [{ label: 'Settings', path: '/settings/auth' }, 'Webhooks'],
        },
      },
      {
        path: 'webhooks/:id',
        loadComponent: () =>
          import(
            './features/notifications/webhook-detail/webhook-detail.component'
          ).then((m) => m.WebhookDetailComponent),
        canActivate: [permissionGuard('notification:webhook:read')],
        data: {
          breadcrumb: [{ label: 'Webhooks', path: '/settings/webhooks' }, 'Deliveries'],
        },
      },
    ],
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'dashboard' },
];
