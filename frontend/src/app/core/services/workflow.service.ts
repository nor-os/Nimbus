/**
 * Overview: Workflow service with GraphQL methods for definitions, executions, node types.
 * Architecture: Core service layer for workflow editor (Section 3.2)
 * Dependencies: @angular/core, rxjs, app/core/services/api.service
 * Concepts: GraphQL queries/mutations, workflow CRUD, execution lifecycle
 */
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { ApiService } from './api.service';
import { TenantContextService } from './tenant-context.service';
import { environment } from '@env/environment';
import {
  WorkflowDefinition,
  WorkflowExecution,
  NodeTypeInfo,
  ValidationResult,
  WorkflowDefinitionCreateInput,
  WorkflowDefinitionUpdateInput,
  WorkflowExecutionStartInput,
  GenerateDeploymentWorkflowInput,
  WorkflowType,
} from '@shared/models/workflow.model';

const DEFINITION_FIELDS = `
  id tenantId name description version graph status createdBy
  timeoutSeconds maxConcurrent workflowType sourceTopologyId isSystem
  applicableSemanticTypeId applicableProviderId
  createdAt updatedAt
`;

const NODE_EXECUTION_FIELDS = `
  id executionId nodeId nodeType status input output error
  startedAt completedAt attempt
`;

const EXECUTION_FIELDS = `
  id tenantId definitionId definitionVersion temporalWorkflowId
  status input output error startedBy startedAt completedAt isTest
  nodeExecutions { ${NODE_EXECUTION_FIELDS} }
`;

@Injectable({ providedIn: 'root' })
export class WorkflowService {
  private api = inject(ApiService);
  private tenantContext = inject(TenantContextService);
  private gqlUrl = environment.graphqlUrl;

  // ── Definition queries ──────────────────────────────

  listDefinitions(params: {
    status?: string;
    workflowType?: WorkflowType;
    offset?: number;
    limit?: number;
    applicableSemanticTypeId?: string;
    applicableProviderId?: string;
  } = {}): Observable<WorkflowDefinition[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ workflowDefinitions: WorkflowDefinition[] }>(`
      query WorkflowDefinitions(
        $tenantId: UUID!, $status: String, $workflowType: String,
        $offset: Int, $limit: Int,
        $applicableSemanticTypeId: UUID, $applicableProviderId: UUID
      ) {
        workflowDefinitions(
          tenantId: $tenantId, status: $status, workflowType: $workflowType,
          offset: $offset, limit: $limit,
          applicableSemanticTypeId: $applicableSemanticTypeId, applicableProviderId: $applicableProviderId
        ) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, ...params }).pipe(
      map(data => data.workflowDefinitions),
    );
  }

  /**
   * List workflows applicable to a specific semantic type + provider combination.
   * Returns ACTIVE workflows where applicability matches or is NULL (applies to all).
   */
  listOperationWorkflows(semanticTypeId: string, providerId: string): Observable<WorkflowDefinition[]> {
    return this.listDefinitions({
      status: 'ACTIVE',
      applicableSemanticTypeId: semanticTypeId,
      applicableProviderId: providerId,
      limit: 500,
    });
  }

  getDefinition(definitionId: string): Observable<WorkflowDefinition | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ workflowDefinition: WorkflowDefinition | null }>(`
      query WorkflowDefinition($tenantId: UUID!, $definitionId: UUID!) {
        workflowDefinition(tenantId: $tenantId, definitionId: $definitionId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, definitionId }).pipe(
      map(data => data.workflowDefinition),
    );
  }

  getDefinitionVersions(name: string): Observable<WorkflowDefinition[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ workflowDefinitionVersions: WorkflowDefinition[] }>(`
      query WorkflowDefinitionVersions($tenantId: UUID!, $name: String!) {
        workflowDefinitionVersions(tenantId: $tenantId, name: $name) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, name }).pipe(
      map(data => data.workflowDefinitionVersions),
    );
  }

  // ── Definition mutations ────────────────────────────

  createDefinition(input: WorkflowDefinitionCreateInput): Observable<WorkflowDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ createWorkflowDefinition: WorkflowDefinition }>(`
      mutation CreateWorkflowDefinition($tenantId: UUID!, $input: WorkflowDefinitionCreateInput!) {
        createWorkflowDefinition(tenantId: $tenantId, input: $input) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map(data => data.createWorkflowDefinition),
    );
  }

  updateDefinition(definitionId: string, input: WorkflowDefinitionUpdateInput): Observable<WorkflowDefinition | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ updateWorkflowDefinition: WorkflowDefinition | null }>(`
      mutation UpdateWorkflowDefinition($tenantId: UUID!, $definitionId: UUID!, $input: WorkflowDefinitionUpdateInput!) {
        updateWorkflowDefinition(tenantId: $tenantId, definitionId: $definitionId, input: $input) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, definitionId, input }).pipe(
      map(data => data.updateWorkflowDefinition),
    );
  }

  publishDefinition(definitionId: string): Observable<WorkflowDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ publishWorkflowDefinition: WorkflowDefinition }>(`
      mutation PublishWorkflowDefinition($tenantId: UUID!, $definitionId: UUID!) {
        publishWorkflowDefinition(tenantId: $tenantId, definitionId: $definitionId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, definitionId }).pipe(
      map(data => data.publishWorkflowDefinition),
    );
  }

  archiveDefinition(definitionId: string): Observable<WorkflowDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ archiveWorkflowDefinition: WorkflowDefinition }>(`
      mutation ArchiveWorkflowDefinition($tenantId: UUID!, $definitionId: UUID!) {
        archiveWorkflowDefinition(tenantId: $tenantId, definitionId: $definitionId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, definitionId }).pipe(
      map(data => data.archiveWorkflowDefinition),
    );
  }

  cloneDefinition(definitionId: string): Observable<WorkflowDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cloneWorkflowDefinition: WorkflowDefinition }>(`
      mutation CloneWorkflowDefinition($tenantId: UUID!, $definitionId: UUID!) {
        cloneWorkflowDefinition(tenantId: $tenantId, definitionId: $definitionId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, definitionId }).pipe(
      map(data => data.cloneWorkflowDefinition),
    );
  }

  deleteDefinition(definitionId: string): Observable<boolean> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deleteWorkflowDefinition: boolean }>(`
      mutation DeleteWorkflowDefinition($tenantId: UUID!, $definitionId: UUID!) {
        deleteWorkflowDefinition(tenantId: $tenantId, definitionId: $definitionId)
      }
    `, { tenantId, definitionId }).pipe(
      map(data => data.deleteWorkflowDefinition),
    );
  }

  // ── Deployment & System ─────────────────────────────

  generateDeploymentWorkflow(input: GenerateDeploymentWorkflowInput): Observable<WorkflowDefinition> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ generateDeploymentWorkflow: WorkflowDefinition }>(`
      mutation GenerateDeploymentWorkflow($tenantId: UUID!, $input: GenerateDeploymentWorkflowInput!) {
        generateDeploymentWorkflow(tenantId: $tenantId, input: $input) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map(data => data.generateDeploymentWorkflow),
    );
  }

  seedSystemWorkflows(): Observable<WorkflowDefinition[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ seedSystemWorkflows: WorkflowDefinition[] }>(`
      mutation SeedSystemWorkflows($tenantId: UUID!) {
        seedSystemWorkflows(tenantId: $tenantId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId }).pipe(
      map(data => data.seedSystemWorkflows),
    );
  }

  getDeploymentWorkflowsForTopology(topologyId: string): Observable<WorkflowDefinition[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ deploymentWorkflowsForTopology: WorkflowDefinition[] }>(`
      query DeploymentWorkflowsForTopology($tenantId: UUID!, $topologyId: UUID!) {
        deploymentWorkflowsForTopology(tenantId: $tenantId, topologyId: $topologyId) {
          ${DEFINITION_FIELDS}
        }
      }
    `, { tenantId, topologyId }).pipe(
      map(data => data.deploymentWorkflowsForTopology),
    );
  }

  // ── Execution queries ───────────────────────────────

  listExecutions(params: {
    definitionId?: string;
    status?: string;
    offset?: number;
    limit?: number;
  } = {}): Observable<WorkflowExecution[]> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ workflowExecutions: WorkflowExecution[] }>(`
      query WorkflowExecutions(
        $tenantId: UUID!, $definitionId: UUID, $status: String, $offset: Int, $limit: Int
      ) {
        workflowExecutions(
          tenantId: $tenantId, definitionId: $definitionId, status: $status, offset: $offset, limit: $limit
        ) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, ...params }).pipe(
      map(data => data.workflowExecutions),
    );
  }

  getExecution(executionId: string): Observable<WorkflowExecution | null> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ workflowExecution: WorkflowExecution | null }>(`
      query WorkflowExecution($tenantId: UUID!, $executionId: UUID!) {
        workflowExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId }).pipe(
      map(data => data.workflowExecution),
    );
  }

  // ── Execution mutations ─────────────────────────────

  startExecution(input: WorkflowExecutionStartInput): Observable<WorkflowExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ startWorkflowExecution: WorkflowExecution }>(`
      mutation StartWorkflowExecution($tenantId: UUID!, $input: WorkflowExecutionStartInput!) {
        startWorkflowExecution(tenantId: $tenantId, input: $input) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, input }).pipe(
      map(data => data.startWorkflowExecution),
    );
  }

  cancelExecution(executionId: string): Observable<WorkflowExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ cancelWorkflowExecution: WorkflowExecution }>(`
      mutation CancelWorkflowExecution($tenantId: UUID!, $executionId: UUID!) {
        cancelWorkflowExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId }).pipe(
      map(data => data.cancelWorkflowExecution),
    );
  }

  retryExecution(executionId: string): Observable<WorkflowExecution> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ retryWorkflowExecution: WorkflowExecution }>(`
      mutation RetryWorkflowExecution($tenantId: UUID!, $executionId: UUID!) {
        retryWorkflowExecution(tenantId: $tenantId, executionId: $executionId) {
          ${EXECUTION_FIELDS}
        }
      }
    `, { tenantId, executionId }).pipe(
      map(data => data.retryWorkflowExecution),
    );
  }

  // ── Node types ──────────────────────────────────────

  getNodeTypes(): Observable<NodeTypeInfo[]> {
    return this.gql<{ nodeTypes: NodeTypeInfo[] }>(`
      query NodeTypes {
        nodeTypes {
          typeId label category description icon isMarker
          ports { name direction portType label required multiple }
          configSchema
        }
      }
    `).pipe(
      map(data => data.nodeTypes),
    );
  }

  // ── Validation ──────────────────────────────────────

  validateGraph(graph: Record<string, unknown>): Observable<ValidationResult> {
    const tenantId = this.tenantContext.currentTenantId();
    return this.gql<{ validateWorkflowGraph: ValidationResult }>(`
      query ValidateWorkflowGraph($tenantId: UUID!, $graph: JSON!) {
        validateWorkflowGraph(tenantId: $tenantId, graph: $graph) {
          valid
          errors { nodeId message severity }
          warnings { nodeId message severity }
        }
      }
    `, { tenantId, graph }).pipe(
      map(data => data.validateWorkflowGraph),
    );
  }

  // ── Private GraphQL helper ──────────────────────────

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
        map(response => {
          if (response.errors?.length) {
            throw new Error(response.errors[0].message);
          }
          return response.data;
        }),
      );
  }
}
