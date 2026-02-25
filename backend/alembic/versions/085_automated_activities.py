"""Create automated activities catalog, versions, executions, and configuration changes tables.

Seeds automation permissions and assigns to Tenant Admin and Provider Admin roles.
Also adds automated_activity_id FK to activity_templates for CMDB bridge.

Revision ID: 085
Revises: 084
Create Date: 2026-02-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "085"
down_revision: Union[str, None] = "084"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. automated_activities (catalog) ────────────────────────────────
    op.create_table(
        "automated_activities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("semantic_activity_type_id", UUID(as_uuid=True), sa.ForeignKey("semantic_activity_types.id"), nullable=True),
        sa.Column("semantic_type_id", UUID(as_uuid=True), sa.ForeignKey("semantic_resource_types.id"), nullable=True),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=True),
        sa.Column("operation_kind", sa.String(20), nullable=False, server_default="update"),
        sa.Column("implementation_type", sa.String(20), nullable=False, server_default="python_script"),
        sa.Column("idempotent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_automated_activities_tenant", "automated_activities", ["tenant_id"])
    op.execute("""
        CREATE UNIQUE INDEX uq_automated_activity_slug
        ON automated_activities (tenant_id, slug)
        WHERE deleted_at IS NULL
    """)

    # ── 2. automated_activity_versions (immutable snapshots) ─────────────
    op.create_table(
        "automated_activity_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("activity_id", UUID(as_uuid=True), sa.ForeignKey("automated_activities.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=True),
        sa.Column("input_schema", JSONB, nullable=True),
        sa.Column("output_schema", JSONB, nullable=True),
        sa.Column("config_mutations", JSONB, nullable=True),
        sa.Column("rollback_mutations", JSONB, nullable=True),
        sa.Column("changelog", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("runtime_config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("activity_id", "version", name="uq_activity_version"),
    )
    op.create_index("ix_activity_versions_activity", "automated_activity_versions", ["activity_id"])

    # ── 3. activity_executions (runtime log) ─────────────────────────────
    op.create_table(
        "activity_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("activity_version_id", UUID(as_uuid=True), sa.ForeignKey("automated_activity_versions.id"), nullable=False),
        sa.Column("workflow_execution_id", UUID(as_uuid=True), sa.ForeignKey("workflow_executions.id"), nullable=True),
        sa.Column("ci_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=True),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=True),
        sa.Column("input_snapshot", JSONB, nullable=True),
        sa.Column("output_snapshot", JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_activity_executions_tenant", "activity_executions", ["tenant_id"])
    op.create_index("ix_activity_executions_status", "activity_executions", ["status"])

    # ── 4. configuration_changes (migration ledger) ──────────────────────
    op.create_table(
        "configuration_changes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=False),
        sa.Column("activity_execution_id", UUID(as_uuid=True), sa.ForeignKey("activity_executions.id"), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("parameter_path", sa.Text(), nullable=False),
        sa.Column("mutation_type", sa.String(20), nullable=False),
        sa.Column("old_value", JSONB, nullable=True),
        sa.Column("new_value", JSONB, nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("applied_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("rollback_of", UUID(as_uuid=True), sa.ForeignKey("configuration_changes.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("deployment_id", "version", name="uq_config_change_version"),
    )
    op.create_index("ix_configuration_changes_tenant", "configuration_changes", ["tenant_id"])

    # ── 5. Add CMDB bridge FK to activity_templates ──────────────────────
    op.add_column(
        "activity_templates",
        sa.Column("automated_activity_id", UUID(as_uuid=True), sa.ForeignKey("automated_activities.id"), nullable=True),
    )
    op.create_index("ix_activity_templates_automated_activity", "activity_templates", ["automated_activity_id"])

    # ── 6. Seed automation permissions ───────────────────────────────────
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'automation', 'activity', 'read', 'View automated activities', true, now(), now()),
            (gen_random_uuid(), 'automation', 'activity', 'create', 'Create automated activities', true, now(), now()),
            (gen_random_uuid(), 'automation', 'activity', 'update', 'Update automated activities', true, now(), now()),
            (gen_random_uuid(), 'automation', 'activity', 'delete', 'Delete automated activities', true, now(), now()),
            (gen_random_uuid(), 'automation', 'activity', 'publish', 'Publish activity versions', true, now(), now()),
            (gen_random_uuid(), 'automation', 'activity', 'execute', 'Execute automated activities', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    # ── 7. Assign permissions to roles ───────────────────────────────────

    # Tenant Admin + Provider Admin get all automation permissions
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Provider Admin', 'Tenant Admin')
            AND p.domain = 'automation' AND p.resource = 'activity'
        ON CONFLICT DO NOTHING
    """)

    # Read-Only gets automation:activity:read
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Read-Only'
            AND p.domain = 'automation' AND p.resource = 'activity' AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """)

    # User gets read + execute
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'User'
            AND p.domain = 'automation' AND p.resource = 'activity' AND p.action IN ('read', 'execute')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # 1. Remove role_permissions for automation perms
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'automation' AND resource = 'activity'
        )
    """)

    # 2. Remove permissions
    op.execute("""
        DELETE FROM permissions
        WHERE domain = 'automation' AND resource = 'activity'
    """)

    # 3. Drop column automated_activity_id from activity_templates
    op.drop_index("ix_activity_templates_automated_activity", table_name="activity_templates")
    op.drop_column("activity_templates", "automated_activity_id")

    # 4. Drop tables in reverse order
    op.drop_table("configuration_changes")
    op.drop_table("activity_executions")
    op.drop_table("automated_activity_versions")
    op.drop_index("uq_automated_activity_slug", table_name="automated_activities")
    op.drop_table("automated_activities")
