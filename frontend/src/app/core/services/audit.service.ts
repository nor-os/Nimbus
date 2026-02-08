/**
 * Overview: Service for audit log operations via REST API.
 * Architecture: Core service layer for audit logging (Section 3.2)
 * Dependencies: @angular/core, app/core/services/api.service
 * Concepts: Audit logging, search, export, retention, redaction, taxonomy
 */
import { Injectable, inject } from '@angular/core';
import { Observable, shareReplay } from 'rxjs';
import { ApiService } from './api.service';
import {
  AuditLog,
  AuditLogListResponse,
  AuditLoggingConfig,
  AuditLoggingConfigUpdate,
  AuditSearchParams,
  ArchiveEntry,
  ExportRequest,
  ExportResponse,
  ExportStatus,
  RedactionRule,
  RedactionRuleCreate,
  RedactionRuleUpdate,
  RetentionPolicy,
  RetentionPolicyUpdate,
  SavedQuery,
  SavedQueryCreate,
  TaxonomyResponse,
  VerifyChainResult,
} from '@shared/models/audit.model';

@Injectable({ providedIn: 'root' })
export class AuditService {
  private api = inject(ApiService);
  private basePath = '/api/v1/audit';

  private taxonomyCache$: Observable<TaxonomyResponse> | null = null;

  // ── Taxonomy ──────────────────────────────────────

  getTaxonomy(): Observable<TaxonomyResponse> {
    if (!this.taxonomyCache$) {
      this.taxonomyCache$ = this.api
        .get<TaxonomyResponse>(`${this.basePath}/taxonomy`)
        .pipe(shareReplay(1));
    }
    return this.taxonomyCache$;
  }

  // ── Logs ──────────────────────────────────────────

  searchLogs(params: AuditSearchParams = {}): Observable<AuditLogListResponse> {
    const query = new URLSearchParams();
    if (params.date_from) query.set('date_from', params.date_from);
    if (params.date_to) query.set('date_to', params.date_to);
    if (params.actor_id) query.set('actor_id', params.actor_id);
    if (params.action) query.set('action', params.action);
    if (params.event_categories?.length) {
      params.event_categories.forEach(c => query.append('event_categories', c));
    }
    if (params.event_types?.length) {
      params.event_types.forEach(t => query.append('event_types', t));
    }
    if (params.resource_type) query.set('resource_type', params.resource_type);
    if (params.resource_id) query.set('resource_id', params.resource_id);
    if (params.priority) query.set('priority', params.priority);
    if (params.trace_id) query.set('trace_id', params.trace_id);
    if (params.full_text) query.set('full_text', params.full_text);
    query.set('offset', String(params.offset ?? 0));
    query.set('limit', String(params.limit ?? 50));

    const qs = query.toString();
    return this.api.get<AuditLogListResponse>(`${this.basePath}/logs?${qs}`);
  }

  getLog(logId: string): Observable<AuditLog> {
    return this.api.get<AuditLog>(`${this.basePath}/logs/${logId}`);
  }

  getLogsByTrace(traceId: string): Observable<AuditLog[]> {
    return this.api.get<AuditLog[]>(`${this.basePath}/logs/trace/${traceId}`);
  }

  // ── Archives ──────────────────────────────────────

  listArchives(): Observable<ArchiveEntry[]> {
    return this.api.get<ArchiveEntry[]>(`${this.basePath}/archives`);
  }

  getArchiveDownloadUrl(key: string): Observable<{ download_url: string }> {
    return this.api.get<{ download_url: string }>(`${this.basePath}/archives/${key}`);
  }

  // ── Export ────────────────────────────────────────

  startExport(request: ExportRequest): Observable<ExportResponse> {
    return this.api.post<ExportResponse>(`${this.basePath}/export`, request);
  }

  getExportStatus(exportId: string): Observable<ExportStatus> {
    return this.api.get<ExportStatus>(`${this.basePath}/export/${exportId}`);
  }

  getExportDownloadUrl(exportId: string): Observable<{ download_url: string }> {
    return this.api.get<{ download_url: string }>(
      `${this.basePath}/export/${exportId}/download`,
    );
  }

  // ── Retention ─────────────────────────────────────

  getRetentionPolicy(): Observable<RetentionPolicy> {
    return this.api.get<RetentionPolicy>(`${this.basePath}/retention`);
  }

  updateRetentionPolicy(update: RetentionPolicyUpdate): Observable<RetentionPolicy> {
    return this.api.put<RetentionPolicy>(`${this.basePath}/retention`, update);
  }

  // ── Redaction Rules ───────────────────────────────

  listRedactionRules(): Observable<RedactionRule[]> {
    return this.api.get<RedactionRule[]>(`${this.basePath}/redaction-rules`);
  }

  createRedactionRule(rule: RedactionRuleCreate): Observable<RedactionRule> {
    return this.api.post<RedactionRule>(`${this.basePath}/redaction-rules`, rule);
  }

  updateRedactionRule(
    ruleId: string,
    update: RedactionRuleUpdate,
  ): Observable<RedactionRule> {
    return this.api.patch<RedactionRule>(
      `${this.basePath}/redaction-rules/${ruleId}`,
      update,
    );
  }

  deleteRedactionRule(ruleId: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/redaction-rules/${ruleId}`);
  }

  // ── Saved Queries ─────────────────────────────────

  listSavedQueries(): Observable<SavedQuery[]> {
    return this.api.get<SavedQuery[]>(`${this.basePath}/saved-queries`);
  }

  createSavedQuery(query: SavedQueryCreate): Observable<SavedQuery> {
    return this.api.post<SavedQuery>(`${this.basePath}/saved-queries`, query);
  }

  deleteSavedQuery(queryId: string): Observable<void> {
    return this.api.delete<void>(`${this.basePath}/saved-queries/${queryId}`);
  }

  // ── Logging Config ──────────────────────────────────

  getLoggingConfig(): Observable<AuditLoggingConfig> {
    return this.api.get<AuditLoggingConfig>(`${this.basePath}/logging-config`);
  }

  updateLoggingConfig(update: AuditLoggingConfigUpdate): Observable<AuditLoggingConfig> {
    return this.api.put<AuditLoggingConfig>(`${this.basePath}/logging-config`, update);
  }

  // ── Chain Verification ────────────────────────────

  verifyChain(start = 0, limit = 1000): Observable<VerifyChainResult> {
    return this.api.post<VerifyChainResult>(`${this.basePath}/verify-chain`, {
      start,
      limit,
    });
  }
}
