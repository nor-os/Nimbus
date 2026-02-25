/**
 * Overview: Automated activity service — GraphQL queries and mutations for activity catalog,
 *     versioning, execution, and config change management.
 * Architecture: Core service layer for activity catalog (Section 11.5)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: Activity CRUD, version publish, execution lifecycle, config mutations.
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  AutomatedActivity,
  AutomatedActivityCreateInput,
  AutomatedActivityUpdateInput,
  AutomatedActivityVersion,
  ActivityVersionCreateInput,
  ActivityExecution,
  ConfigurationChange,
} from '@shared/models/automated-activity.model';

const ACTIVITY_FIELDS = `
  id tenantId name slug description category
  semanticActivityTypeId semanticTypeId providerId
  operationKind implementationType scope idempotent timeoutSeconds
  isSystem createdBy createdAt updatedAt
`;

const VERSION_FIELDS = `
  id activityId version sourceCode inputSchema outputSchema
  configMutations rollbackMutations changelog
  publishedAt publishedBy runtimeConfig createdAt updatedAt
`;

const EXECUTION_FIELDS = `
  id tenantId activityVersionId workflowExecutionId ciId deploymentId
  inputSnapshot outputSnapshot status error
  startedAt completedAt createdAt updatedAt
  configChanges {
    id tenantId deploymentId activityExecutionId version
    parameterPath mutationType oldValue newValue
    appliedAt appliedBy rollbackOf
  }
`;

const CONFIG_CHANGE_FIELDS = `
  id tenantId deploymentId activityExecutionId version
  parameterPath mutationType oldValue newValue
  appliedAt appliedBy rollbackOf
`;

@Injectable({ providedIn: 'root' })
export class AutomatedActivityService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // -- Activity queries -----------------------------------------------------

  listActivities(options?: {
    category?: string;
    operationKind?: string;
    providerId?: string;
    scope?: string;
    search?: string;
    offset?: number;
    limit?: number;
  }): Observable<AutomatedActivity[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ automatedActivities: AutomatedActivity[] }>(`
      query AutomatedActivities(
        $tenantId: UUID!
        $category: String
        $operationKind: String
        $providerId: UUID
        $scope: String
        $search: String
        $offset: Int
        $limit: Int
      ) {
        automatedActivities(
          tenantId: $tenantId
          category: $category
          operationKind: $operationKind
          providerId: $providerId
          scope: $scope
          search: $search
          offset: $offset
          limit: $limit
        ) {
          ${ACTIVITY_FIELDS}
        }
      }
    `, { tenantId, ...options }).pipe(
      map((data) => data.automatedActivities),
    );
  }

  getActivity(id: string): Observable<AutomatedActivity | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ automatedActivity: AutomatedActivity | null }>(`
      query AutomatedActivity($tenantId: UUID!, $activityId: UUID!) {
        automatedActivity(tenantId: $tenantId, activityId: $activityId) {
          ${ACTIVITY_FIELDS}
          versions { ${VERSION_FIELDS} }
        }
      }
    `, { tenantId, activityId: id }).pipe(
      map((data) => data.automatedActivity),
    );
  }

  createActivity(input: AutomatedActivityCreateInput): Observable<AutomatedActivity> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createAutomatedActivity: AutomatedActivity }>(`
      mutation CreateAutomatedActivity($tenantId: UUID!, $input: AutomatedActivityCreateInput!) {
        createAutomatedActivity(tenantId: $tenantId, input: $input) {
          ${ACTIVITY_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map((data) => data.createAutomatedActivity),
    );
  }

  updateActivity(id: string, input: AutomatedActivityUpdateInput): Observable<AutomatedActivity> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateAutomatedActivity: AutomatedActivity }>(`
      mutation UpdateAutomatedActivity($tenantId: UUID!, $activityId: UUID!, $input: AutomatedActivityUpdateInput!) {
        updateAutomatedActivity(tenantId: $tenantId, activityId: $activityId, input: $input) {
          ${ACTIVITY_FIELDS}
        }
      }
    `, { tenantId, activityId: id, input }).pipe(
      map((data) => data.updateAutomatedActivity),
    );
  }

  deleteActivity(id: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteAutomatedActivity: boolean }>(`
      mutation DeleteAutomatedActivity($tenantId: UUID!, $activityId: UUID!) {
        deleteAutomatedActivity(tenantId: $tenantId, activityId: $activityId)
      }
    `, { tenantId, activityId: id }).pipe(
      map((data) => data.deleteAutomatedActivity),
    );
  }

  // -- Version queries/mutations --------------------------------------------

  listVersions(activityId: string): Observable<AutomatedActivityVersion[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ automatedActivityVersions: AutomatedActivityVersion[] }>(`
      query AutomatedActivityVersions($tenantId: UUID!, $activityId: UUID!) {
        automatedActivityVersions(tenantId: $tenantId, activityId: $activityId) {
          ${VERSION_FIELDS}
        }
      }
    `, { tenantId, activityId }).pipe(
      map((data) => data.automatedActivityVersions),
    );
  }

  createVersion(activityId: string, input: ActivityVersionCreateInput): Observable<AutomatedActivityVersion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createActivityVersion: AutomatedActivityVersion }>(`
      mutation CreateActivityVersion($tenantId: UUID!, $activityId: UUID!, $input: ActivityVersionCreateInput!) {
        createActivityVersion(tenantId: $tenantId, activityId: $activityId, input: $input) {
          ${VERSION_FIELDS}
        }
      }
    `, { tenantId, activityId, input }).pipe(
      map((data) => data.createActivityVersion),
    );
  }

  publishVersion(activityId: string, versionId: string): Observable<AutomatedActivityVersion> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishActivityVersion: AutomatedActivityVersion }>(`
      mutation PublishActivityVersion($tenantId: UUID!, $activityId: UUID!, $versionId: UUID!) {
        publishActivityVersion(tenantId: $tenantId, activityId: $activityId, versionId: $versionId) {
          ${VERSION_FIELDS}
        }
      }
    `, { tenantId, activityId, versionId }).pipe(
      map((data) => data.publishActivityVersion),
    );
  }

  // -- Execution queries/mutations ------------------------------------------

  listExecutions(options?: {
    activityId?: string;
    status?: string;
    deploymentId?: string;
    offset?: number;
    limit?: number;
  }): Observable<ActivityExecution[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ activityExecutions: ActivityExecution[] }>(`
      query ActivityExecutions(
        $tenantId: UUID!
        $activityId: UUID
        $status: String
        $deploymentId: UUID
        $offset: Int
        $limit: Int
      ) {
        activityExecutions(
          tenantId: $tenantId
          activityId: $activityId
          status: $status
          deploymentId: $deploymentId
          offset: $offset
          limit: $limit
        ) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, ...options }).pipe(
      map((data) => data.activityExecutions),
    );
  }

  getExecution(id: string): Observable<ActivityExecution | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ activityExecution: ActivityExecution | null }>(`
      query ActivityExecution($tenantId: UUID!, $executionId: UUID!) {
        activityExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId: id }).pipe(
      map((data) => data.activityExecution),
    );
  }

  startExecution(
    activityId: string,
    versionId?: string | null,
    ciId?: string | null,
    deploymentId?: string | null,
    inputData?: Record<string, unknown> | null,
  ): Observable<ActivityExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ startActivityExecution: ActivityExecution }>(`
      mutation StartActivityExecution(
        $tenantId: UUID!
        $activityId: UUID!
        $versionId: UUID
        $ciId: UUID
        $deploymentId: UUID
        $inputData: JSON
      ) {
        startActivityExecution(
          tenantId: $tenantId
          activityId: $activityId
          versionId: $versionId
          ciId: $ciId
          deploymentId: $deploymentId
          inputData: $inputData
        ) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, activityId, versionId, ciId, deploymentId, inputData }).pipe(
      map((data) => data.startActivityExecution),
    );
  }

  cancelExecution(id: string): Observable<ActivityExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cancelActivityExecution: ActivityExecution }>(`
      mutation CancelActivityExecution($tenantId: UUID!, $executionId: UUID!) {
        cancelActivityExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId: id }).pipe(
      map((data) => data.cancelActivityExecution),
    );
  }

  rollbackExecution(id: string): Observable<ActivityExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ rollbackActivityExecution: ActivityExecution }>(`
      mutation RollbackActivityExecution($tenantId: UUID!, $executionId: UUID!) {
        rollbackActivityExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId: id }).pipe(
      map((data) => data.rollbackActivityExecution),
    );
  }

  // -- CMDB bridge ----------------------------------------------------------

  linkActivityTemplate(templateId: string, activityId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ linkActivityTemplate: boolean }>(`
      mutation LinkActivityTemplate($tenantId: UUID!, $templateId: UUID!, $activityId: UUID!) {
        linkActivityTemplate(tenantId: $tenantId, templateId: $templateId, activityId: $activityId)
      }
    `, { tenantId, templateId, activityId }).pipe(
      map((data) => data.linkActivityTemplate),
    );
  }

  unlinkActivityTemplate(templateId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ unlinkActivityTemplate: boolean }>(`
      mutation UnlinkActivityTemplate($tenantId: UUID!, $templateId: UUID!) {
        unlinkActivityTemplate(tenantId: $tenantId, templateId: $templateId)
      }
    `, { tenantId, templateId }).pipe(
      map((data) => data.unlinkActivityTemplate),
    );
  }

  // -- Config changes -------------------------------------------------------

  listConfigChanges(deploymentId: string, offset = 0, limit = 50): Observable<ConfigurationChange[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ configurationChanges: ConfigurationChange[] }>(`
      query ConfigurationChanges($tenantId: UUID!, $deploymentId: UUID!, $offset: Int, $limit: Int) {
        configurationChanges(tenantId: $tenantId, deploymentId: $deploymentId, offset: $offset, limit: $limit) {
          ${CONFIG_CHANGE_FIELDS}
        }
      }
    `, { tenantId, deploymentId, offset, limit }).pipe(
      map((data) => data.configurationChanges),
    );
  }

  // -- GraphQL helper -------------------------------------------------------

  private gql<T>(
    query: string,
    variables: Record<string, unknown> = {},
  ): Observable<T> {
    return this.api
      .post<{ data: T; errors?: Array<{ message: string }> }>(this.gqlUrl, {
        query,
        variables,
      })
      .pipe(
        map((response) => {
          if (response.errors?.length) {
            throw new Error(response.errors[0].message);
          }
          return response.data;
        }),
      );
  }
}
