"""
Overview: Add deployment activity support to component operations with workflow templates.
Architecture: Migration for deployment lifecycle operations (Section 11)
Dependencies: alembic, sqlalchemy
Concepts: Deployment operations (deploy, decommission, rollback, upgrade, validate, dry-run),
    workflow templates, operation categories
"""

revision = "090"
down_revision = "089"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # ── 1. component_operations: add operation_category + operation_kind ──
    op.add_column(
        "component_operations",
        sa.Column(
            "operation_category",
            sa.String(20),
            nullable=False,
            server_default="DAY2",
        ),
    )
    op.add_column(
        "component_operations",
        sa.Column("operation_kind", sa.String(20), nullable=True),
    )
    op.create_index(
        "ix_component_operations_category",
        "component_operations",
        ["component_id", "operation_category"],
    )

    # ── 2. workflow_definitions: add is_template + template_source_id ──
    op.add_column(
        "workflow_definitions",
        sa.Column("is_template", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column("template_source_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_definitions_template_source",
        "workflow_definitions",
        "workflow_definitions",
        ["template_source_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # ── 3. Seed 6 deployment workflow templates ──
    # Use a system tenant_id placeholder (UUID zero) — templates are system-level
    system_tenant = "00000000-0000-0000-0000-000000000000"
    templates = [
        {
            "name": "deployment:deploy",
            "description": "Default deployment workflow template — provisions a new resource.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "deploy", "type": "script", "label": "Deploy Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Deploy logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "deploy", "targetInput": "in"}, {"id": "c2", "source": "deploy", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
        {
            "name": "deployment:decommission",
            "description": "Default decommission workflow template — tears down a resource.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "decommission", "type": "script", "label": "Decommission Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Decommission logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "decommission", "targetInput": "in"}, {"id": "c2", "source": "decommission", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
        {
            "name": "deployment:rollback",
            "description": "Default rollback workflow template — reverts to a previous version.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "rollback", "type": "script", "label": "Rollback Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Rollback logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "rollback", "targetInput": "in"}, {"id": "c2", "source": "rollback", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
        {
            "name": "deployment:upgrade",
            "description": "Default upgrade workflow template — updates a resource in place.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "upgrade", "type": "script", "label": "Upgrade Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Upgrade logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "upgrade", "targetInput": "in"}, {"id": "c2", "source": "upgrade", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
        {
            "name": "deployment:validate",
            "description": "Default validation workflow template — checks resource health.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "validate", "type": "script", "label": "Validate Resource", "position": {"x": 350, "y": 200}, "data": {"script": "# Validation logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "validate", "targetInput": "in"}, {"id": "c2", "source": "validate", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
        {
            "name": "deployment:dry-run",
            "description": "Default dry-run workflow template — simulates deployment without changes.",
            "graph": '{"nodes": [{"id": "start", "type": "start", "label": "Start", "position": {"x": 100, "y": 200}, "data": {}}, {"id": "dryrun", "type": "script", "label": "Dry Run", "position": {"x": 350, "y": 200}, "data": {"script": "# Dry-run logic here\\npass"}}, {"id": "end", "type": "end", "label": "End", "position": {"x": 600, "y": 200}, "data": {}}], "connections": [{"id": "c1", "source": "start", "sourceOutput": "out", "target": "dryrun", "targetInput": "in"}, {"id": "c2", "source": "dryrun", "sourceOutput": "out", "target": "end", "targetInput": "in"}]}',
        },
    ]

    for tmpl in templates:
        op.execute(
            sa.text(
                """
                INSERT INTO workflow_definitions (
                    id, tenant_id, name, description, version, graph, status,
                    created_by, timeout_seconds, max_concurrent, workflow_type,
                    is_system, is_template, created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), CAST(:tenant_id AS uuid), :name, :description, 0,
                    CAST(:graph AS jsonb), 'ACTIVE', CAST(:tenant_id AS uuid), 3600, 10, 'DEPLOYMENT',
                    true, true, now(), now()
                )
                """
            ).bindparams(
                tenant_id=system_tenant,
                name=tmpl["name"],
                description=tmpl["description"],
                graph=tmpl["graph"],
            )
        )

    # ── 4. Seed permission: component:deployment:manage ──
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), 'component', 'deployment', 'manage',
                    'Manage deployment lifecycle operations on components', true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
            """
        )
    )

    # Assign to Tenant Admin + Provider Admin
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r, permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'component' AND p.resource = 'deployment' AND p.action = 'manage'
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    # Remove role_permissions
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE domain = 'component' AND resource = 'deployment' AND action = 'manage'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE domain = 'component' AND resource = 'deployment' AND action = 'manage'
            """
        )
    )

    # Remove seeded templates
    op.execute(
        sa.text(
            """
            DELETE FROM workflow_definitions
            WHERE is_template = true AND is_system = true AND workflow_type = 'DEPLOYMENT'
              AND name LIKE 'deployment:%'
            """
        )
    )

    # Drop workflow_definitions columns
    op.drop_constraint(
        "fk_workflow_definitions_template_source", "workflow_definitions", type_="foreignkey"
    )
    op.drop_column("workflow_definitions", "template_source_id")
    op.drop_column("workflow_definitions", "is_template")

    # Drop component_operations columns
    op.drop_index("ix_component_operations_category", table_name="component_operations")
    op.drop_column("component_operations", "operation_kind")
    op.drop_column("component_operations", "operation_category")
