/**
 * Overview: TypeScript interfaces for audit log data structures.
 * Architecture: Shared audit type definitions (Section 8)
 * Dependencies: none
 * Concepts: Audit logging, retention, redaction, saved queries, event taxonomy
 */

export type AuditAction =
  | 'CREATE'
  | 'READ'
  | 'UPDATE'
  | 'DELETE'
  | 'LOGIN'
  | 'LOGOUT'
  | 'PERMISSION_CHANGE'
  | 'BREAK_GLASS'
  | 'EXPORT'
  | 'ARCHIVE'
  | 'SYSTEM'
  | 'IMPERSONATE'
  | 'OVERRIDE';

export type AuditPriority = 'DEBUG' | 'INFO' | 'WARN' | 'ERR' | 'CRITICAL';

export type EventCategory =
  | 'API'
  | 'AUTH'
  | 'DATA'
  | 'PERMISSION'
  | 'SYSTEM'
  | 'SECURITY'
  | 'TENANT'
  | 'USER';

export type ActorType = 'USER' | 'SYSTEM' | 'SERVICE' | 'ANONYMOUS';

export interface AuditLog {
  id: string;
  tenant_id: string;
  actor_id: string | null;
  actor_email: string | null;
  actor_ip: string | null;
  action: AuditAction;
  event_category: EventCategory | null;
  event_type: string | null;
  actor_type: ActorType | null;
  impersonator_id: string | null;
  resource_type: string | null;
  resource_id: string | null;
  resource_name: string | null;
  old_values: Record<string, unknown> | null;
  new_values: Record<string, unknown> | null;
  trace_id: string | null;
  priority: AuditPriority;
  hash: string | null;
  previous_hash: string | null;
  metadata: Record<string, unknown> | null;
  user_agent: string | null;
  request_method: string | null;
  request_path: string | null;
  request_body: Record<string, unknown> | null;
  response_status: number | null;
  response_body: Record<string, unknown> | null;
  archived_at: string | null;
  created_at: string;
}

export interface AuditLogListResponse {
  items: AuditLog[];
  total: number;
  offset: number;
  limit: number;
}

export interface AuditSearchParams {
  date_from?: string;
  date_to?: string;
  actor_id?: string;
  action?: AuditAction;
  event_categories?: string[];
  event_types?: string[];
  resource_type?: string;
  resource_id?: string;
  priority?: AuditPriority;
  trace_id?: string;
  full_text?: string;
  offset?: number;
  limit?: number;
}

export interface CategoryRetentionOverride {
  id: string;
  tenant_id: string;
  event_category: EventCategory;
  hot_days: number;
  cold_days: number;
  created_at: string;
  updated_at: string;
}

export interface CategoryRetentionOverrideUpsert {
  event_category: EventCategory;
  hot_days: number;
  cold_days: number;
}

export interface RetentionPolicy {
  id: string;
  tenant_id: string;
  hot_days: number;
  cold_days: number;
  archive_enabled: boolean;
  category_overrides: CategoryRetentionOverride[];
  created_at: string;
  updated_at: string;
}

export interface RetentionPolicyUpdate {
  hot_days?: number;
  cold_days?: number;
  archive_enabled?: boolean;
}

export interface RedactionRule {
  id: string;
  tenant_id: string;
  field_pattern: string;
  replacement: string;
  is_active: boolean;
  priority: number;
  created_at: string;
  updated_at: string;
}

export interface RedactionRuleCreate {
  field_pattern: string;
  replacement?: string;
  is_active?: boolean;
  priority?: number;
}

export interface RedactionRuleUpdate {
  field_pattern?: string;
  replacement?: string;
  is_active?: boolean;
  priority?: number;
}

export interface SavedQuery {
  id: string;
  tenant_id: string;
  user_id: string;
  name: string;
  query_params: Record<string, unknown>;
  is_shared: boolean;
  created_at: string;
  updated_at: string;
}

export interface SavedQueryCreate {
  name: string;
  query_params: Record<string, unknown>;
  is_shared?: boolean;
}

export interface ArchiveEntry {
  key: string;
  size: number;
  last_modified: string;
}

export interface ExportRequest {
  format: 'json' | 'csv';
  date_from?: string;
  date_to?: string;
  action?: AuditAction;
  resource_type?: string;
  priority?: AuditPriority;
}

export interface ExportResponse {
  export_id: string;
  status: string;
}

export interface ExportStatus {
  export_id: string;
  status: string;
  download_url?: string;
}

export interface VerifyChainResult {
  valid: boolean;
  total_checked: number;
  broken_links: Record<string, unknown>[];
}

// ── Logging Config ────────────────────────────────────────

export interface AuditLoggingConfig {
  log_api_reads: boolean;
  log_api_writes: boolean;
  log_auth_events: boolean;
  log_graphql: boolean;
  log_errors: boolean;
}

export type AuditLoggingConfigUpdate = Partial<AuditLoggingConfig>;

// ── Taxonomy Types ────────────────────────────────────────

export interface TaxonomyEventType {
  key: string;
  label: string;
  description: string;
  default_priority: AuditPriority;
}

export interface TaxonomyCategory {
  category: EventCategory;
  label: string;
  event_types: TaxonomyEventType[];
}

export interface TaxonomyResponse {
  categories: TaxonomyCategory[];
}
