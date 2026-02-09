"""Add workflow_definitions, workflow_executions, workflow_node_executions tables and workflow permissions.

Revision ID: 020
Revises: 019
Create Date: 2026-02-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

WORKFLOW_PERMISSIONS = [
    ("workflow:definition:create", "Create workflow definitions"),
    ("workflow:definition:read", "View workflow definitions"),
    ("workflow:definition:update", "Update workflow definitions"),
    ("workflow:definition:delete", "Delete workflow definitions"),
    ("workflow:definition:publish", "Publish workflow definitions"),
    ("workflow:execution:start", "Start workflow executions"),
    ("workflow:execution:read", "View workflow executions"),
    ("workflow:execution:cancel", "Cancel workflow executions"),
]

# Provider Admin & Tenant Admin: all 8
# User: definition:read + execution:start + execution:read
# Read-Only: definition:read + execution:read
USER_PERMISSIONS = [
    "workflow:definition:read",
    "workflow:execution:start",
    "workflow:execution:read",
]
READONLY_PERMISSIONS = [
    "workflow:definition:read",
    "workflow:execution:read",
]


def upgrade() -> None:
    # -- Enums --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE workflow_definition_status AS ENUM ('DRAFT','ACTIVE','ARCHIVED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE workflow_execution_status AS ENUM "
        "('PENDING','RUNNING','COMPLETED','FAILED','CANCELLED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE workflow_node_execution_status AS ENUM "
        "('PENDING','RUNNING','COMPLETED','FAILED','SKIPPED','CANCELLED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    workflow_definition_status = postgresql.ENUM(
        "DRAFT", "ACTIVE", "ARCHIVED",
        name="workflow_definition_status",
        create_type=False,
    )
    workflow_execution_status = postgresql.ENUM(
        "PENDING", "RUNNING", "COMPLETED", "FAILED", "CANCELLED",
        name="workflow_execution_status",
        create_type=False,
    )
    workflow_node_execution_status = postgresql.ENUM(
        "PENDING", "RUNNING", "COMPLETED", "FAILED", "SKIPPED", "CANCELLED",
        name="workflow_node_execution_status",
        create_type=False,
    )

    # -- 1. workflow_definitions table --
    op.create_table(
        "workflow_definitions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("graph", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column(
            "status", workflow_definition_status,
            nullable=False, server_default="DRAFT",
        ),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column("timeout_seconds", sa.Integer, nullable=False, server_default="3600"),
        sa.Column("max_concurrent", sa.Integer, nullable=False, server_default="10"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "tenant_id", "name", "version",
            name="uq_workflow_def_tenant_name_version",
        ),
    )
    op.create_index("ix_workflow_definitions_tenant", "workflow_definitions", ["tenant_id"])
    op.create_index(
        "ix_workflow_definitions_status", "workflow_definitions", ["tenant_id", "status"]
    )
    op.create_index("ix_workflow_definitions_created_by", "workflow_definitions", ["created_by"])

    # -- 2. workflow_executions table --
    op.create_table(
        "workflow_executions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "definition_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_definitions.id"),
            nullable=False,
        ),
        sa.Column("definition_version", sa.Integer, nullable=False),
        sa.Column(
            "temporal_workflow_id", sa.String(255),
            nullable=True, unique=True,
        ),
        sa.Column(
            "status", workflow_execution_status,
            nullable=False, server_default="PENDING",
        ),
        sa.Column("input", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("output", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "started_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_test", sa.Boolean, nullable=False, server_default="false"),
    )
    op.create_index("ix_workflow_executions_tenant", "workflow_executions", ["tenant_id"])
    op.create_index("ix_workflow_executions_definition", "workflow_executions", ["definition_id"])
    op.create_index(
        "ix_workflow_executions_status", "workflow_executions", ["tenant_id", "status"]
    )
    op.create_index(
        "ix_workflow_executions_temporal", "workflow_executions", ["temporal_workflow_id"]
    )
    op.create_index("ix_workflow_executions_started_by", "workflow_executions", ["started_by"])

    # -- 3. workflow_node_executions table --
    op.create_table(
        "workflow_node_executions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "execution_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id"),
            nullable=False,
        ),
        sa.Column("node_id", sa.String(100), nullable=False),
        sa.Column("node_type", sa.String(100), nullable=False),
        sa.Column(
            "status", workflow_node_execution_status,
            nullable=False, server_default="PENDING",
        ),
        sa.Column("input", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("output", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt", sa.Integer, nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_workflow_node_executions_execution",
        "workflow_node_executions", ["execution_id"],
    )
    op.create_index(
        "ix_workflow_node_executions_node",
        "workflow_node_executions", ["execution_id", "node_id"],
    )

    # -- 4. Seed workflow permissions --
    conn = op.get_bind()
    for key, description in WORKFLOW_PERMISSIONS:
        parts = key.split(":")
        domain = parts[0]
        resource = parts[1]
        action = parts[2]
        subtype = parts[3] if len(parts) > 3 else None

        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, domain, resource, action, subtype, description,
                                         is_system, created_at, updated_at)
                VALUES (gen_random_uuid(), :domain, :resource, :action, :subtype,
                        :description, true, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
                """
            ),
            {
                "domain": domain,
                "resource": resource,
                "action": action,
                "subtype": subtype,
                "description": description,
            },
        )

    # Provider Admin & Tenant Admin get all workflow permissions
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'workflow'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )

    # User role: definition:read + execution:start + execution:read
    for perm_key in USER_PERMISSIONS:
        parts = perm_key.split(":")
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r
                CROSS JOIN permissions p
                WHERE r.name = 'User'
                  AND p.domain = :domain AND p.resource = :resource AND p.action = :action
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissions rp
                      WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  )
                """
            ),
            {"domain": parts[0], "resource": parts[1], "action": parts[2]},
        )

    # Read-Only role: definition:read + execution:read
    for perm_key in READONLY_PERMISSIONS:
        parts = perm_key.split(":")
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r
                CROSS JOIN permissions p
                WHERE r.name = 'Read-Only'
                  AND p.domain = :domain AND p.resource = :resource AND p.action = :action
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissions rp
                      WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  )
                """
            ),
            {"domain": parts[0], "resource": parts[1], "action": parts[2]},
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove workflow role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'workflow'
            )
            """
        )
    )

    # Remove workflow permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'workflow'"))

    # Drop tables in reverse dependency order
    op.drop_index("ix_workflow_node_executions_node", table_name="workflow_node_executions")
    op.drop_index(
        "ix_workflow_node_executions_execution", table_name="workflow_node_executions"
    )
    op.drop_table("workflow_node_executions")

    op.drop_index("ix_workflow_executions_started_by", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_temporal", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_status", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_definition", table_name="workflow_executions")
    op.drop_index("ix_workflow_executions_tenant", table_name="workflow_executions")
    op.drop_table("workflow_executions")

    op.drop_index("ix_workflow_definitions_created_by", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_status", table_name="workflow_definitions")
    op.drop_index("ix_workflow_definitions_tenant", table_name="workflow_definitions")
    op.drop_table("workflow_definitions")

    # Drop enums
    sa.Enum(name="workflow_node_execution_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workflow_execution_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="workflow_definition_status").drop(op.get_bind(), checkfirst=True)
