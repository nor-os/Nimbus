"""
Overview: Add component_operations table for day-2 operation declarations on components.
Architecture: Migration for component operations (Section 11)
Dependencies: 066_update_and_add_example_components
Concepts: Operations are workflow-backed day-2 actions declared on components (extend disk, snapshot, restart).
    Each operation references a workflow_definition that defines the multi-step execution logic.
"""

revision = "067"
down_revision = "066"

from alembic import op


def upgrade() -> None:
    # ── 1. component_operations table ───────────────────────────────────
    op.execute("""
        CREATE TABLE component_operations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            component_id UUID NOT NULL REFERENCES components(id) ON DELETE CASCADE,
            name VARCHAR(100) NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            input_schema JSONB,
            output_schema JSONB,
            workflow_definition_id UUID NOT NULL REFERENCES workflow_definitions(id),
            is_destructive BOOLEAN NOT NULL DEFAULT FALSE,
            requires_approval BOOLEAN NOT NULL DEFAULT FALSE,
            estimated_downtime VARCHAR(20) NOT NULL DEFAULT 'NONE',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_component_operations_component_name
        ON component_operations (component_id, name)
        WHERE deleted_at IS NULL
    """)

    op.execute("CREATE INDEX ix_component_operations_component ON component_operations (component_id)")
    op.execute("CREATE INDEX ix_component_operations_workflow ON component_operations (workflow_definition_id)")

    # ── 2. Permissions ──────────────────────────────────────────────────
    permissions = [
        ("component", "operation", "read", None, "Read component operations"),
        ("component", "operation", "create", None, "Create component operations"),
        ("component", "operation", "update", None, "Update component operations"),
        ("component", "operation", "delete", None, "Delete component operations"),
    ]

    for domain, resource, action, subtype, desc in permissions:
        sub_val = f"'{subtype}'" if subtype else "NULL"
        op.execute(f"""
            INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), '{domain}', '{resource}', '{action}', {sub_val}, '{desc}', TRUE, NOW(), NOW())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """)

    # Read-Only+ gets read
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
          AND p.domain = 'component' AND p.resource = 'operation' AND p.action = 'read'
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # Tenant Admin+ gets create/update/delete
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'component' AND p.resource = 'operation'
          AND p.action IN ('create', 'update', 'delete')
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'component' AND resource = 'operation'
        )
    """)
    op.execute("DELETE FROM permissions WHERE domain = 'component' AND resource = 'operation'")
    op.execute("DROP TABLE IF EXISTS component_operations")
