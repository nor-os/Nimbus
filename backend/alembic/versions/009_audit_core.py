"""Add audit_logs, retention_policies, redaction_rules, saved_queries tables and audit permissions.

Revision ID: 009
Revises: 008
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

AUDIT_PERMISSIONS = [
    ("audit:log:read", "View audit logs"),
    ("audit:archive:read", "View audit archives"),
    ("audit:export:create", "Create audit exports"),
    ("audit:export:read", "View audit exports"),
    ("audit:retention:read", "View retention policies"),
    ("audit:retention:update", "Update retention policies"),
    ("audit:redaction:read", "View redaction rules"),
    ("audit:redaction:create", "Create redaction rules"),
    ("audit:redaction:update", "Update redaction rules"),
    ("audit:redaction:delete", "Delete redaction rules"),
    ("audit:query:read", "View saved queries"),
    ("audit:query:create", "Create saved queries"),
    ("audit:query:delete", "Delete saved queries"),
    ("audit:chain:verify", "Verify hash chain integrity"),
]


def upgrade() -> None:
    # 1. audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("actor_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_email", sa.String(320), nullable=True),
        sa.Column("actor_ip", sa.String(45), nullable=True),
        sa.Column(
            "action",
            sa.Enum(
                "CREATE", "READ", "UPDATE", "DELETE", "LOGIN", "LOGOUT",
                "PERMISSION_CHANGE", "BREAK_GLASS", "EXPORT", "ARCHIVE", "SYSTEM",
                name="audit_action",
            ),
            nullable=False,
        ),
        sa.Column("resource_type", sa.String(255), nullable=True),
        sa.Column("resource_id", sa.String(255), nullable=True),
        sa.Column("resource_name", sa.String(500), nullable=True),
        sa.Column("old_values", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("new_values", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("trace_id", sa.String(64), nullable=True),
        sa.Column(
            "priority",
            sa.Enum("INFO", "WARN", "ERR", name="audit_priority"),
            nullable=False,
            server_default="INFO",
        ),
        sa.Column("hash", sa.String(64), nullable=True),
        sa.Column("previous_hash", sa.String(64), nullable=True),
        sa.Column("metadata", sa.dialects.postgresql.JSONB, nullable=True),
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
    )
    op.create_index("ix_audit_logs_tenant_created", "audit_logs", ["tenant_id", "created_at"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource", "audit_logs", ["resource_type", "resource_id"])
    op.create_index("ix_audit_logs_trace_id", "audit_logs", ["trace_id"])
    op.create_index("ix_audit_logs_actor", "audit_logs", ["actor_id"])

    # 2. retention_policies table
    op.create_table(
        "retention_policies",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("hot_days", sa.Integer, nullable=False, server_default="30"),
        sa.Column("cold_days", sa.Integer, nullable=False, server_default="365"),
        sa.Column("archive_enabled", sa.Boolean, nullable=False, server_default="true"),
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
    )

    # 3. redaction_rules table
    op.create_table(
        "redaction_rules",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("field_pattern", sa.String(500), nullable=False),
        sa.Column("replacement", sa.String(255), nullable=False, server_default="[REDACTED]"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("priority", sa.Integer, nullable=False, server_default="0"),
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
    )
    op.create_index("ix_redaction_rules_tenant_id", "redaction_rules", ["tenant_id"])

    # 4. saved_queries table
    op.create_table(
        "saved_queries",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("query_params", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("is_shared", sa.Boolean, nullable=False, server_default="false"),
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
    )
    op.create_index("ix_saved_queries_tenant_id", "saved_queries", ["tenant_id"])
    op.create_index("ix_saved_queries_user_id", "saved_queries", ["user_id"])

    # 5. Seed audit permissions and assign to tenant_admin role
    # Permission keys use domain:resource:action[:subtype] format
    # The permissions table has separate columns: domain, resource, action, subtype
    conn = op.get_bind()
    for key, description in AUDIT_PERMISSIONS:
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

    # Assign all audit permissions to the tenant_admin role
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'tenant_admin'
              AND p.domain = 'audit'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove audit role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'audit'
            )
            """
        )
    )

    # Remove audit permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'audit'"))

    op.drop_index("ix_saved_queries_user_id", table_name="saved_queries")
    op.drop_index("ix_saved_queries_tenant_id", table_name="saved_queries")
    op.drop_table("saved_queries")

    op.drop_index("ix_redaction_rules_tenant_id", table_name="redaction_rules")
    op.drop_table("redaction_rules")

    op.drop_table("retention_policies")

    op.drop_index("ix_audit_logs_actor", table_name="audit_logs")
    op.drop_index("ix_audit_logs_trace_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_tenant_created", table_name="audit_logs")
    op.drop_table("audit_logs")

    sa.Enum(name="audit_action").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audit_priority").drop(op.get_bind(), checkfirst=True)
