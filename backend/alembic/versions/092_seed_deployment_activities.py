"""
Overview: Seed 6 system deployment activities for use as workflow node building blocks.
Architecture: Data migration for deployment activity catalog (Section 11.5)
Dependencies: 091_operation_activity_link
Concepts: Deployment activities (deploy, decommission, rollback, upgrade, validate, dry-run),
    PULUMI_OPERATION implementation type, system-level seeds, versioned source code
"""

from alembic import op

revision: str = "092"
down_revision: str = "091"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
    DO $$
    DECLARE
      aid UUID;
      vid UUID;
    BEGIN
      -- 1. deploy-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Deploy Resource', 'deploy-resource',
        'Provision a new infrastructure resource via Pulumi.',
        'deployment', 'CREATE', 'PULUMI_OPERATION', false, 3600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "provider_id": {"type": "string"}, "semantic_type_id": {"type": "string"}, "parameters": {"type": "object"}, "stack_name": {"type": "string"}}, "required": ["component_id", "provider_id", "stack_name"]}'::jsonb,
        '{"type": "object", "properties": {"resource_id": {"type": "string"}, "stack_name": {"type": "string"}, "status": {"type": "string"}, "outputs": {"type": "object"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

      -- 2. decommission-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Decommission Resource', 'decommission-resource',
        'Tear down and decommission an infrastructure resource via Pulumi.',
        'deployment', 'DELETE', 'PULUMI_OPERATION', false, 3600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "stack_name": {"type": "string"}, "confirm_name": {"type": "string"}}, "required": ["component_id", "stack_name", "confirm_name"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "destroyed_resources": {"type": "integer"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

      -- 3. rollback-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Rollback Resource', 'rollback-resource',
        'Rollback a resource to a previous version via Pulumi.',
        'deployment', 'RESTORE', 'PULUMI_OPERATION', false, 3600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "target_version": {"type": "string"}, "stack_name": {"type": "string"}}, "required": ["component_id", "target_version", "stack_name"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "rolled_back_to": {"type": "string"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

      -- 4. upgrade-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Upgrade Resource', 'upgrade-resource',
        'Update an existing resource in place via Pulumi.',
        'deployment', 'UPDATE', 'PULUMI_OPERATION', false, 3600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "parameters": {"type": "object"}, "stack_name": {"type": "string"}, "target_version": {"type": "string"}}, "required": ["component_id", "stack_name"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "updated_resources": {"type": "integer"}, "outputs": {"type": "object"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

      -- 5. validate-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Validate Resource', 'validate-resource',
        'Validate health and configuration of a deployed resource.',
        'deployment', 'VALIDATE', 'PULUMI_OPERATION', true, 600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "stack_name": {"type": "string"}}, "required": ["component_id", "stack_name"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "healthy": {"type": "boolean"}, "diagnostics": {"type": "array"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

      -- 6. dry-run-resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, scope,
        created_at, updated_at)
      VALUES (aid, NULL, 'Dry Run Resource', 'dry-run-resource',
        'Preview deployment changes without applying them.',
        'deployment', 'READ', 'PULUMI_OPERATION', true, 600, true, 'WORKFLOW',
        NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        '# Pulumi operation — implemented in Phase 12',
        '{"type": "object", "properties": {"component_id": {"type": "string"}, "parameters": {"type": "object"}, "stack_name": {"type": "string"}}, "required": ["component_id", "stack_name"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "plan": {"type": "object"}, "changes_count": {"type": "integer"}}}'::jsonb,
        'Initial deployment activity version', NOW(), NULL, NOW(), NOW());

    END $$;
    """)


def downgrade() -> None:
    conn = op.get_bind()
    conn.exec_driver_sql("""
    DELETE FROM automated_activity_versions
    WHERE activity_id IN (
      SELECT id FROM automated_activities
      WHERE is_system = true AND tenant_id IS NULL
        AND slug IN ('deploy-resource', 'decommission-resource', 'rollback-resource',
                     'upgrade-resource', 'validate-resource', 'dry-run-resource')
    );
    """)
    conn.exec_driver_sql("""
    DELETE FROM automated_activities
    WHERE is_system = true AND tenant_id IS NULL
      AND slug IN ('deploy-resource', 'decommission-resource', 'rollback-resource',
                   'upgrade-resource', 'validate-resource', 'dry-run-resource');
    """)
