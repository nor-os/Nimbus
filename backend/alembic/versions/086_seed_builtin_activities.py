"""
Overview: Seed 10 built-in automated activities with version 1 published.
Architecture: Data migration for activity catalog (Section 11.5)
Dependencies: 085_automated_activities
Concepts: Built-in activities, system seeds, versioned source code
"""

from alembic import op

revision: str = "086"
down_revision: str = "085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # For each activity, insert into automated_activities then automated_activity_versions
    # Use DO $$ ... END $$ block for cleaner SQL with variable reuse
    # NOTE: exec_driver_sql bypasses SQLAlchemy bind-parameter parsing
    # (source code strings contain :8 slices and ::jsonb casts that confuse SA)

    conn = op.get_bind()
    conn.exec_driver_sql("""
    DO $$
    DECLARE
      aid UUID;
      vid UUID;
    BEGIN
      -- 1. disk_resize
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Disk Resize', 'disk-resize',
        'Resize a disk volume attached to a virtual machine or container.',
        'storage', 'UPDATE', 'PYTHON_SCRIPT', true, 300, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, config_mutations, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    target_size_gb = input_data[\"target_size_gb\"]\\n    disk_id = input_data[\"disk_id\"]\\n    # Provider-specific resize logic would go here\\n    print(json.dumps({\"status\": \"resized\", \"disk_id\": disk_id, \"new_size_gb\": target_size_gb}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"disk_id": {"type": "string"}, "target_size_gb": {"type": "integer", "minimum": 1}}, "required": ["disk_id", "target_size_gb"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "disk_id": {"type": "string"}, "new_size_gb": {"type": "integer"}}}'::jsonb,
        '[{"mutation_type": "SET_FROM_INPUT", "parameter_path": "storage.disk_size_gb", "source_field": "new_size_gb"}]'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 2. create_snapshot
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Create Snapshot', 'create-snapshot',
        'Create a point-in-time snapshot of a virtual machine.',
        'compute', 'BACKUP', 'PYTHON_SCRIPT', false, 600, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    vm_id = input_data[\"vm_id\"]\\n    label = input_data.get(\"label\", \"snapshot\")\\n    # Provider-specific snapshot logic\\n    print(json.dumps({\"snapshot_id\": \"snap-\" + vm_id[:8], \"vm_id\": vm_id, \"label\": label}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"vm_id": {"type": "string"}, "label": {"type": "string"}}, "required": ["vm_id"]}'::jsonb,
        '{"type": "object", "properties": {"snapshot_id": {"type": "string"}, "vm_id": {"type": "string"}, "label": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 3. restore_snapshot
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Restore Snapshot', 'restore-snapshot',
        'Restore a virtual machine from a previously created snapshot.',
        'compute', 'RESTORE', 'PYTHON_SCRIPT', false, 900, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    snapshot_id = input_data[\"snapshot_id\"]\\n    vm_id = input_data[\"vm_id\"]\\n    # Provider-specific restore logic\\n    print(json.dumps({\"status\": \"restored\", \"vm_id\": vm_id, \"from_snapshot\": snapshot_id}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"snapshot_id": {"type": "string"}, "vm_id": {"type": "string"}}, "required": ["snapshot_id", "vm_id"]}'::jsonb,
        '{"type": "object", "properties": {"status": {"type": "string"}, "vm_id": {"type": "string"}, "from_snapshot": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 4. run_backup
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Run Backup', 'run-backup',
        'Execute a backup job for a resource or dataset.',
        'backup', 'BACKUP', 'PYTHON_SCRIPT', true, 1800, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    resource_id = input_data[\"resource_id\"]\\n    backup_type = input_data.get(\"backup_type\", \"full\")\\n    print(json.dumps({\"backup_id\": \"bkp-\" + resource_id[:8], \"type\": backup_type, \"status\": \"completed\"}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"resource_id": {"type": "string"}, "backup_type": {"type": "string", "enum": ["full", "incremental", "differential"]}}, "required": ["resource_id"]}'::jsonb,
        '{"type": "object", "properties": {"backup_id": {"type": "string"}, "type": {"type": "string"}, "status": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 5. apply_patch
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Apply Patch', 'apply-patch',
        'Apply OS or software patches to a target system.',
        'security', 'UPDATE', 'PYTHON_SCRIPT', true, 1200, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    target_id = input_data[\"target_id\"]\\n    patches = input_data.get(\"patches\", [])\\n    print(json.dumps({\"target_id\": target_id, \"applied_count\": len(patches), \"status\": \"patched\"}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"target_id": {"type": "string"}, "patches": {"type": "array", "items": {"type": "string"}}}, "required": ["target_id"]}'::jsonb,
        '{"type": "object", "properties": {"target_id": {"type": "string"}, "applied_count": {"type": "integer"}, "status": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 6. validate_connectivity
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Validate Connectivity', 'validate-connectivity',
        'Validate network connectivity between endpoints.',
        'network', 'VALIDATE', 'PYTHON_SCRIPT', true, 120, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    source = input_data[\"source\"]\\n    target = input_data[\"target\"]\\n    port = input_data.get(\"port\", 443)\\n    print(json.dumps({\"source\": source, \"target\": target, \"port\": port, \"reachable\": True, \"latency_ms\": 12}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"source": {"type": "string"}, "target": {"type": "string"}, "port": {"type": "integer"}}, "required": ["source", "target"]}'::jsonb,
        '{"type": "object", "properties": {"source": {"type": "string"}, "target": {"type": "string"}, "port": {"type": "integer"}, "reachable": {"type": "boolean"}, "latency_ms": {"type": "number"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 7. scale_resource
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Scale Resource', 'scale-resource',
        'Scale compute resources (CPU cores, RAM) for a virtual machine.',
        'compute', 'UPDATE', 'PYTHON_SCRIPT', true, 600, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, config_mutations, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    vm_id = input_data[\"vm_id\"]\\n    cpu = input_data.get(\"cpu_cores\")\\n    ram = input_data.get(\"ram_gb\")\\n    result = {\"vm_id\": vm_id, \"status\": \"scaled\"}\\n    if cpu: result[\"cpu_cores\"] = cpu\\n    if ram: result[\"ram_gb\"] = ram\\n    print(json.dumps(result))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"vm_id": {"type": "string"}, "cpu_cores": {"type": "integer", "minimum": 1}, "ram_gb": {"type": "integer", "minimum": 1}}, "required": ["vm_id"]}'::jsonb,
        '{"type": "object", "properties": {"vm_id": {"type": "string"}, "status": {"type": "string"}, "cpu_cores": {"type": "integer"}, "ram_gb": {"type": "integer"}}}'::jsonb,
        '[{"mutation_type": "SET_FROM_INPUT", "parameter_path": "compute.cpu_cores", "source_field": "cpu_cores"}, {"mutation_type": "SET_FROM_INPUT", "parameter_path": "compute.ram_gb", "source_field": "ram_gb"}]'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 8. rotate_credentials
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Rotate Credentials', 'rotate-credentials',
        'Rotate access credentials for a service or resource.',
        'security', 'UPDATE', 'PYTHON_SCRIPT', false, 300, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\nimport secrets\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    service_id = input_data[\"service_id\"]\\n    credential_type = input_data.get(\"credential_type\", \"api_key\")\\n    print(json.dumps({\"service_id\": service_id, \"credential_type\": credential_type, \"rotated\": True, \"new_key_prefix\": secrets.token_hex(4)}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"service_id": {"type": "string"}, "credential_type": {"type": "string", "enum": ["api_key", "password", "certificate", "token"]}}, "required": ["service_id"]}'::jsonb,
        '{"type": "object", "properties": {"service_id": {"type": "string"}, "credential_type": {"type": "string"}, "rotated": {"type": "boolean"}, "new_key_prefix": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 9. restart_service (Shell script)
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Restart Service', 'restart-service',
        'Restart a service or virtual machine.',
        'compute', 'REMEDIATE', 'SHELL_SCRIPT', true, 300, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'#!/bin/bash\\nset -e\\nINPUT=$(cat /dev/stdin)\\nSERVICE_ID=$(echo "$INPUT" | python3 -c \"import sys,json; print(json.load(sys.stdin)[''service_id''])\")\\necho \"{\\\"service_id\\\": \\\"$SERVICE_ID\\\", \\\"status\\\": \\\"restarted\\\"}\"\\n',
        '{"type": "object", "properties": {"service_id": {"type": "string"}}, "required": ["service_id"]}'::jsonb,
        '{"type": "object", "properties": {"service_id": {"type": "string"}, "status": {"type": "string"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

      -- 10. export_config
      aid := gen_random_uuid();
      INSERT INTO automated_activities (id, tenant_id, name, slug, description, category,
        operation_kind, implementation_type, idempotent, timeout_seconds, is_system, created_at, updated_at)
      VALUES (aid, NULL, 'Export Config', 'export-config',
        'Export the current configuration of a resource for backup or audit.',
        'backup', 'READ', 'PYTHON_SCRIPT', true, 120, true, NOW(), NOW());
      vid := gen_random_uuid();
      INSERT INTO automated_activity_versions (id, activity_id, version, source_code,
        input_schema, output_schema, changelog, published_at, published_by, created_at, updated_at)
      VALUES (vid, aid, 1,
        E'import json\\nimport sys\\n\\ndef main():\\n    input_data = json.load(sys.stdin)\\n    resource_id = input_data[\"resource_id\"]\\n    format = input_data.get(\"format\", \"json\")\\n    print(json.dumps({\"resource_id\": resource_id, \"format\": format, \"config\": {\"exported\": True}, \"export_size_bytes\": 1024}))\\n\\nif __name__ == \"__main__\":\\n    main()\\n',
        '{"type": "object", "properties": {"resource_id": {"type": "string"}, "format": {"type": "string", "enum": ["json", "yaml", "toml"]}}, "required": ["resource_id"]}'::jsonb,
        '{"type": "object", "properties": {"resource_id": {"type": "string"}, "format": {"type": "string"}, "config": {"type": "object"}, "export_size_bytes": {"type": "integer"}}}'::jsonb,
        'Initial built-in version', NOW(), NULL, NOW(), NOW());

    END $$;
    """)


def downgrade() -> None:
    # Remove seeded activities and their versions
    conn = op.get_bind()
    conn.exec_driver_sql("""
    DELETE FROM automated_activity_versions
    WHERE activity_id IN (
      SELECT id FROM automated_activities WHERE is_system = true AND tenant_id IS NULL
    );
    """)
    conn.exec_driver_sql("""
    DELETE FROM automated_activities WHERE is_system = true AND tenant_id IS NULL;
    """)
