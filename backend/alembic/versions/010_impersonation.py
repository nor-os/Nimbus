"""Add impersonation_sessions table, IMPERSONATE/OVERRIDE audit actions, and impersonation permissions.

Revision ID: 010
Revises: 009
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Permissions: key, description, assign_to_tenant_admin
IMPERSONATION_PERMISSIONS = [
    ("impersonation:session:create", "Request standard impersonation", False),
    ("impersonation:session:read", "View impersonation sessions", True),
    ("impersonation:override:create", "Request override mode impersonation", False),
    ("impersonation:approval:decide", "Approve or reject impersonation requests", True),
    ("impersonation:config:manage", "Configure impersonation settings", True),
]


def upgrade() -> None:
    # 1. Add IMPERSONATE and OVERRIDE to audit_action enum
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'IMPERSONATE'")
    op.execute("ALTER TYPE audit_action ADD VALUE IF NOT EXISTS 'OVERRIDE'")

    # 2. Create impersonation_sessions table
    op.create_table(
        "impersonation_sessions",
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
            "requester_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "target_user_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "mode",
            sa.Enum("STANDARD", "OVERRIDE", name="impersonation_mode"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "PENDING_APPROVAL", "APPROVED", "ACTIVE", "ENDED",
                "REJECTED", "EXPIRED", "CANCELLED",
                name="impersonation_status",
            ),
            nullable=False,
            server_default="PENDING_APPROVAL",
        ),
        sa.Column("workflow_id", sa.String(255), nullable=True),
        sa.Column(
            "approver_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("approval_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_reason", sa.String(255), nullable=True),
        sa.Column("original_password_hash", sa.Text, nullable=True),
        sa.Column("original_is_active", sa.Boolean, nullable=True),
        sa.Column("token_jti", sa.String(255), nullable=True),
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
    op.create_index("ix_impersonation_sessions_tenant", "impersonation_sessions", ["tenant_id"])
    op.create_index("ix_impersonation_sessions_requester", "impersonation_sessions", ["requester_id"])
    op.create_index("ix_impersonation_sessions_target", "impersonation_sessions", ["target_user_id"])
    op.create_index("ix_impersonation_sessions_status", "impersonation_sessions", ["status"])
    op.create_index("ix_impersonation_sessions_workflow", "impersonation_sessions", ["workflow_id"])

    # 3. Seed impersonation permissions
    conn = op.get_bind()
    for key, description, assign in IMPERSONATION_PERMISSIONS:
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

    # 4. Assign session:read, approval:decide, config:manage to tenant_admin
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'impersonation'
              AND (
                  (p.resource = 'session' AND p.action = 'read')
                  OR (p.resource = 'approval' AND p.action = 'decide')
                  OR (p.resource = 'config' AND p.action = 'manage')
              )
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove impersonation role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'impersonation'
            )
            """
        )
    )

    # Remove impersonation permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'impersonation'"))

    # Drop table and indexes
    op.drop_index("ix_impersonation_sessions_workflow", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_status", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_target", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_requester", table_name="impersonation_sessions")
    op.drop_index("ix_impersonation_sessions_tenant", table_name="impersonation_sessions")
    op.drop_table("impersonation_sessions")

    sa.Enum(name="impersonation_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="impersonation_mode").drop(op.get_bind(), checkfirst=True)

    # Note: Cannot remove individual values from PostgreSQL enums.
    # IMPERSONATE and OVERRIDE values will remain in audit_action enum.
