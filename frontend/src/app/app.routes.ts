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
    path: 'workflows',
    canActivate: [authGuard],
    children: [
      {
        path: 'approvals',
        loadComponent: () =>
          import('./features/approvals/approval-inbox/approval-inbox.component').then(
            (m) => m.ApprovalInboxComponent,
          ),
        canActivate: [permissionGuard('approval:decision:submit')],
        data: { breadcrumb: [{ label: 'Workflows', path: '/workflows/approvals' }, 'Approvals'] },
      },
      {
        path: 'manage',
        loadComponent: () =>
          import('./features/approvals/approval-policy-manage/approval-policy-manage.component').then(
            (m) => m.ApprovalPolicyManageComponent,
          ),
        canActivate: [permissionGuard('approval:policy:manage')],
        data: { breadcrumb: [{ label: 'Workflows', path: '/workflows/approvals' }, 'Manage'] },
      },
      {
        path: 'definitions',
        loadComponent: () =>
          import('./features/workflows/workflow-list/workflow-list.component').then(
            (m) => m.WorkflowListComponent,
          ),
        canActivate: [permissionGuard('workflow:definition:read')],
        data: { breadcrumb: [{ label: 'Workflows', path: '/workflows/definitions' }, 'Definitions'] },
      },
      {
        path: 'definitions/new',
        loadComponent: () =>
          import('./features/workflows/editor/workflow-editor.component').then(
            (m) => m.WorkflowEditorComponent,
          ),
        canActivate: [permissionGuard('workflow:definition:create')],
        data: { breadcrumb: [{ label: 'Definitions', path: '/workflows/definitions' }, 'New'] },
      },
      {
        path: 'definitions/:id',
        loadComponent: () =>
          import('./features/workflows/workflow-detail/workflow-detail.component').then(
            (m) => m.WorkflowDetailComponent,
          ),
        canActivate: [permissionGuard('workflow:definition:read')],
        data: { breadcrumb: [{ label: 'Definitions', path: '/workflows/definitions' }, 'Details'] },
      },
      {
        path: 'definitions/:id/edit',
        loadComponent: () =>
          import('./features/workflows/editor/workflow-editor.component').then(
            (m) => m.WorkflowEditorComponent,
          ),
        canActivate: [permissionGuard('workflow:definition:update')],
        data: { breadcrumb: [{ label: 'Definitions', path: '/workflows/definitions' }, 'Edit'] },
      },
      {
        path: 'executions',
        loadComponent: () =>
          import('./features/workflows/execution-list/execution-list.component').then(
            (m) => m.ExecutionListComponent,
          ),
        canActivate: [permissionGuard('workflow:execution:read')],
        data: { breadcrumb: [{ label: 'Workflows', path: '/workflows/definitions' }, 'Executions'] },
      },
      {
        path: 'executions/:id',
        loadComponent: () =>
          import('./features/workflows/execution-detail/execution-detail.component').then(
            (m) => m.ExecutionDetailComponent,
          ),
        canActivate: [permissionGuard('workflow:execution:read')],
        data: { breadcrumb: [{ label: 'Executions', path: '/workflows/executions' }, 'Details'] },
      },
      {
        path: '',
        redirectTo: 'definitions',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: 'cmdb',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/cmdb/ci-list/ci-list.component').then(
            (m) => m.CIListComponent,
          ),
        canActivate: [permissionGuard('cmdb:ci:read')],
        data: { breadcrumb: 'Configuration Items' },
      },
      {
        path: 'create',
        loadComponent: () =>
          import('./features/cmdb/ci-form/ci-form.component').then(
            (m) => m.CIFormComponent,
          ),
        canActivate: [permissionGuard('cmdb:ci:create')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Create'] },
      },
      {
        path: 'classes',
        loadComponent: () =>
          import('./features/cmdb/classes/class-browser.component').then(
            (m) => m.ClassBrowserComponent,
          ),
        canActivate: [permissionGuard('cmdb:class:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Classes'] },
      },
      {
        path: 'compartments',
        loadComponent: () =>
          import('./features/cmdb/compartment-tree/compartment-tree.component').then(
            (m) => m.CompartmentTreeComponent,
          ),
        canActivate: [permissionGuard('cmdb:compartment:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Compartments'] },
      },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/cmdb/dashboard/cmdb-dashboard.component').then(
            (m) => m.CmdbDashboardComponent,
          ),
        canActivate: [permissionGuard('cmdb:ci:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Dashboard'] },
      },
      {
        path: 'templates',
        loadComponent: () =>
          import('./features/cmdb/templates/template-list.component').then(
            (m) => m.TemplateListComponent,
          ),
        canActivate: [permissionGuard('cmdb:template:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Templates'] },
      },
      {
        path: 'templates/new',
        loadComponent: () =>
          import('./features/cmdb/templates/template-editor.component').then(
            (m) => m.TemplateEditorComponent,
          ),
        canActivate: [permissionGuard('cmdb:template:manage')],
        data: { breadcrumb: [{ label: 'Templates', path: '/cmdb/templates' }, 'New'] },
      },
      {
        path: 'templates/:id/edit',
        loadComponent: () =>
          import('./features/cmdb/templates/template-editor.component').then(
            (m) => m.TemplateEditorComponent,
          ),
        canActivate: [permissionGuard('cmdb:template:manage')],
        data: { breadcrumb: [{ label: 'Templates', path: '/cmdb/templates' }, 'Edit'] },
      },
      {
        path: ':id/graph',
        loadComponent: () =>
          import('./features/cmdb/graph-view/graph-view.component').then(
            (m) => m.GraphViewComponent,
          ),
        canActivate: [permissionGuard('cmdb:relationship:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Graph'] },
      },
      {
        path: ':id/impact',
        loadComponent: () =>
          import('./features/cmdb/impact/impact-analysis.component').then(
            (m) => m.ImpactAnalysisComponent,
          ),
        canActivate: [permissionGuard('cmdb:relationship:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Impact'] },
      },
      {
        path: ':id',
        loadComponent: () =>
          import('./features/cmdb/ci-detail/ci-detail.component').then(
            (m) => m.CIDetailComponent,
          ),
        canActivate: [permissionGuard('cmdb:ci:read')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Details'] },
      },
      {
        path: ':id/edit',
        loadComponent: () =>
          import('./features/cmdb/ci-form/ci-form.component').then(
            (m) => m.CIFormComponent,
          ),
        canActivate: [permissionGuard('cmdb:ci:update')],
        data: { breadcrumb: [{ label: 'CMDB', path: '/cmdb' }, 'Edit'] },
      },
    ],
  },
  {
    path: 'catalog',
    canActivate: [authGuard],
    children: [
      {
        path: 'services',
        loadComponent: () =>
          import('./features/catalog/service-list.component').then(
            (m) => m.ServiceListComponent,
          ),
        canActivate: [permissionGuard('cmdb:catalog:read')],
        data: { breadcrumb: 'Service Catalog' },
      },
      {
        path: 'services/new',
        loadComponent: () =>
          import('./features/catalog/service-form.component').then(
            (m) => m.ServiceFormComponent,
          ),
        canActivate: [permissionGuard('cmdb:catalog:manage')],
        data: { breadcrumb: [{ label: 'Service Catalog', path: '/catalog/services' }, 'New'] },
      },
      {
        path: 'services/:id',
        loadComponent: () =>
          import('./features/catalog/service-form.component').then(
            (m) => m.ServiceFormComponent,
          ),
        canActivate: [permissionGuard('cmdb:catalog:manage')],
        data: { breadcrumb: [{ label: 'Service Catalog', path: '/catalog/services' }, 'Edit'] },
      },
      {
        path: 'pricing',
        loadComponent: () =>
          import('./features/catalog/pricing-config.component').then(
            (m) => m.PricingConfigComponent,
          ),
        canActivate: [permissionGuard('cmdb:catalog:manage')],
        data: { breadcrumb: [{ label: 'Service Catalog', path: '/catalog/services' }, 'Pricing'] },
      },
      {
        path: 'tenant-pricing',
        loadComponent: () =>
          import('./features/catalog/tenant-pricing.component').then(
            (m) => m.TenantPricingComponent,
          ),
        canActivate: [permissionGuard('cmdb:catalog:manage')],
        data: { breadcrumb: [{ label: 'Service Catalog', path: '/catalog/services' }, 'Tenant Pricing'] },
      },
      {
        path: 'regions',
        loadComponent: () =>
          import('./features/catalog/regions/region-list.component').then(
            (m) => m.RegionListComponent,
          ),
        canActivate: [permissionGuard('catalog:region:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Regions'] },
      },
      {
        path: 'regions/create',
        loadComponent: () =>
          import('./features/catalog/regions/region-form.component').then(
            (m) => m.RegionFormComponent,
          ),
        canActivate: [permissionGuard('catalog:region:manage')],
        data: { breadcrumb: [{ label: 'Regions', path: '/catalog/regions' }, 'Create'] },
      },
      {
        path: 'regions/:id',
        loadComponent: () =>
          import('./features/catalog/regions/region-form.component').then(
            (m) => m.RegionFormComponent,
          ),
        canActivate: [permissionGuard('catalog:region:manage')],
        data: { breadcrumb: [{ label: 'Regions', path: '/catalog/regions' }, 'Edit'] },
      },
      {
        path: 'acceptance-templates',
        loadComponent: () =>
          import('./features/catalog/regions/acceptance-template-editor.component').then(
            (m) => m.AcceptanceTemplateEditorComponent,
          ),
        canActivate: [permissionGuard('catalog:compliance:read')],
        data: { breadcrumb: [{ label: 'Regions', path: '/catalog/regions' }, 'Acceptance Templates'] },
      },
      {
        path: 'tenant-regions',
        loadComponent: () =>
          import('./features/catalog/regions/tenant-region-config.component').then(
            (m) => m.TenantRegionConfigComponent,
          ),
        canActivate: [permissionGuard('catalog:compliance:manage')],
        data: { breadcrumb: [{ label: 'Regions', path: '/catalog/regions' }, 'Tenant Config'] },
      },
      {
        path: 'rate-cards',
        loadComponent: () =>
          import('./features/catalog/rate-cards/staff-list.component').then(
            (m) => m.StaffListComponent,
          ),
        canActivate: [permissionGuard('catalog:staff:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Rate Cards'] },
      },
      {
        path: 'rate-cards/matrix',
        loadComponent: () =>
          import('./features/catalog/rate-cards/rate-card-matrix.component').then(
            (m) => m.RateCardMatrixComponent,
          ),
        canActivate: [permissionGuard('catalog:staff:read')],
        data: { breadcrumb: [{ label: 'Rate Cards', path: '/catalog/rate-cards' }, 'Matrix'] },
      },
      {
        path: 'activities',
        loadComponent: () =>
          import('./features/catalog/activities/activity-template-list.component').then(
            (m) => m.ActivityTemplateListComponent,
          ),
        canActivate: [permissionGuard('catalog:activity:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Activities'] },
      },
      {
        path: 'activities/new',
        loadComponent: () =>
          import('./features/catalog/activities/activity-template-editor.component').then(
            (m) => m.ActivityTemplateEditorComponent,
          ),
        canActivate: [permissionGuard('catalog:activity:manage')],
        data: { breadcrumb: [{ label: 'Activities', path: '/catalog/activities' }, 'New'] },
      },
      {
        path: 'activities/:id',
        loadComponent: () =>
          import('./features/catalog/activities/activity-template-editor.component').then(
            (m) => m.ActivityTemplateEditorComponent,
          ),
        canActivate: [permissionGuard('catalog:activity:manage')],
        data: { breadcrumb: [{ label: 'Activities', path: '/catalog/activities' }, 'Edit'] },
      },
      {
        path: 'processes',
        loadComponent: () =>
          import('./features/catalog/processes/process-list.component').then(
            (m) => m.ProcessListComponent,
          ),
        canActivate: [permissionGuard('catalog:process:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Processes'] },
      },
      {
        path: 'processes/:id',
        loadComponent: () =>
          import('./features/catalog/processes/process-editor.component').then(
            (m) => m.ProcessEditorComponent,
          ),
        canActivate: [permissionGuard('catalog:process:manage')],
        data: { breadcrumb: [{ label: 'Processes', path: '/catalog/processes' }, 'Edit'] },
      },
      {
        path: 'estimations',
        loadComponent: () =>
          import('./features/catalog/estimations/estimation-list.component').then(
            (m) => m.EstimationListComponent,
          ),
        canActivate: [permissionGuard('catalog:estimation:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Estimations'] },
      },
      {
        path: 'estimations/new',
        loadComponent: () =>
          import('./features/catalog/estimations/estimation-builder.component').then(
            (m) => m.EstimationBuilderComponent,
          ),
        canActivate: [permissionGuard('catalog:estimation:manage')],
        data: { breadcrumb: [{ label: 'Estimations', path: '/catalog/estimations' }, 'New'] },
      },
      {
        path: 'estimations/:id/edit',
        loadComponent: () =>
          import('./features/catalog/estimations/estimation-builder.component').then(
            (m) => m.EstimationBuilderComponent,
          ),
        canActivate: [permissionGuard('catalog:estimation:manage')],
        data: { breadcrumb: [{ label: 'Estimations', path: '/catalog/estimations' }, 'Edit'] },
      },
      {
        path: 'estimations/:id',
        loadComponent: () =>
          import('./features/catalog/estimations/estimation-detail.component').then(
            (m) => m.EstimationDetailComponent,
          ),
        canActivate: [permissionGuard('catalog:estimation:read')],
        data: { breadcrumb: [{ label: 'Estimations', path: '/catalog/estimations' }, 'Details'] },
      },
      {
        path: 'profitability',
        loadComponent: () =>
          import('./features/catalog/profitability/profitability-dashboard.component').then(
            (m) => m.ProfitabilityDashboardComponent,
          ),
        canActivate: [permissionGuard('catalog:profitability:read')],
        data: { breadcrumb: [{ label: 'Catalog', path: '/catalog/services' }, 'Profitability'] },
      },
      {
        path: '',
        redirectTo: 'services',
        pathMatch: 'full',
      },
    ],
  },
  {
    path: 'semantic',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        loadComponent: () =>
          import('./features/semantic/semantic-explorer/semantic-explorer.component').then(
            (m) => m.SemanticExplorerComponent,
          ),
        canActivate: [permissionGuard('semantic:type:read')],
        data: { breadcrumb: 'Semantic Explorer' },
      },
      {
        path: 'types/:id',
        loadComponent: () =>
          import('./features/semantic/type-detail/type-detail.component').then(
            (m) => m.TypeDetailComponent,
          ),
        canActivate: [permissionGuard('semantic:type:read')],
        data: { breadcrumb: [{ label: 'Semantic Explorer', path: '/semantic' }, 'Details'] },
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
