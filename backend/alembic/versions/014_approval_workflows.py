"""Add approval_policies, approval_requests, approval_steps tables and approval permissions.

Revision ID: 014
Revises: 013
Create Date: 2026-02-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APPROVAL_PERMISSIONS = [
    ("approval:policy:read", "View approval policies"),
    ("approval:policy:manage", "Manage approval policies"),
    ("approval:request:read", "View approval requests"),
    ("approval:request:create", "Create approval requests"),
    ("approval:decision:submit", "Submit approval decisions"),
    ("approval:decision:delegate", "Delegate approval decisions"),
]


def upgrade() -> None:
    # -- Enums (created via raw SQL to avoid SQLAlchemy auto-create conflicts) --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE approval_chain_mode AS ENUM ('SEQUENTIAL','PARALLEL','QUORUM'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE approval_request_status AS ENUM "
        "('PENDING','APPROVED','REJECTED','EXPIRED','CANCELLED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE approval_step_status AS ENUM "
        "('PENDING','APPROVED','REJECTED','DELEGATED','SKIPPED','EXPIRED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    approval_chain_mode = postgresql.ENUM(
        "SEQUENTIAL", "PARALLEL", "QUORUM",
        name="approval_chain_mode",
        create_type=False,
    )
    approval_request_status = postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", "EXPIRED", "CANCELLED",
        name="approval_request_status",
        create_type=False,
    )
    approval_step_status = postgresql.ENUM(
        "PENDING", "APPROVED", "REJECTED", "DELEGATED", "SKIPPED", "EXPIRED",
        name="approval_step_status",
        create_type=False,
    )

    # -- 1. approval_policies table --
    op.create_table(
        "approval_policies",
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
        sa.Column("operation_type", sa.String(100), nullable=False),
        sa.Column("chain_mode", approval_chain_mode, nullable=False),
        sa.Column("quorum_required", sa.Integer, nullable=False, server_default="1"),
        sa.Column("timeout_minutes", sa.Integer, nullable=False, server_default="1440"),
        sa.Column("escalation_user_ids", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("approver_role_names", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("approver_user_ids", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
            "tenant_id", "operation_type",
            name="uq_approval_policy_tenant_op",
        ),
    )
    op.create_index("ix_approval_policies_tenant", "approval_policies", ["tenant_id"])
    op.create_index(
        "ix_approval_policies_operation", "approval_policies", ["tenant_id", "operation_type"]
    )

    # -- 2. approval_requests table --
    op.create_table(
        "approval_requests",
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
        sa.Column("operation_type", sa.String(100), nullable=False),
        sa.Column(
            "requester_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("workflow_id", sa.String(200), nullable=True),
        sa.Column("parent_workflow_id", sa.String(200), nullable=True),
        sa.Column("chain_mode", sa.String(20), nullable=False),
        sa.Column("quorum_required", sa.Integer, nullable=False, server_default="1"),
        sa.Column(
            "status", approval_request_status, nullable=False, server_default="PENDING"
        ),
        sa.Column("title", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("context", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
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
    op.create_index("ix_approval_requests_tenant", "approval_requests", ["tenant_id"])
    op.create_index("ix_approval_requests_requester", "approval_requests", ["requester_id"])
    op.create_index(
        "ix_approval_requests_status", "approval_requests", ["tenant_id", "status"]
    )
    op.create_index("ix_approval_requests_workflow", "approval_requests", ["workflow_id"])
    op.create_index(
        "ix_approval_requests_parent_workflow", "approval_requests", ["parent_workflow_id"]
    )
    op.create_index(
        "ix_approval_requests_operation", "approval_requests", ["tenant_id", "operation_type"]
    )

    # -- 3. approval_steps table --
    op.create_table(
        "approval_steps",
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
            "approval_request_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_requests.id"),
            nullable=False,
        ),
        sa.Column("step_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "approver_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "delegate_to_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "status", approval_step_status, nullable=False, server_default="PENDING"
        ),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
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
    op.create_index("ix_approval_steps_request", "approval_steps", ["approval_request_id"])
    op.create_index("ix_approval_steps_approver", "approval_steps", ["approver_id"])
    op.create_index(
        "ix_approval_steps_tenant_approver",
        "approval_steps",
        ["tenant_id", "approver_id", "status"],
    )
    op.create_index("ix_approval_steps_delegate", "approval_steps", ["delegate_to_id"])

    # -- 4. Seed approval permissions and assign to tenant_admin --
    conn = op.get_bind()
    for key, description in APPROVAL_PERMISSIONS:
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

    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'approval'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove approval role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'approval'
            )
            """
        )
    )

    # Remove approval permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'approval'"))

    # Drop tables in reverse dependency order
    op.drop_index("ix_approval_steps_delegate", table_name="approval_steps")
    op.drop_index("ix_approval_steps_tenant_approver", table_name="approval_steps")
    op.drop_index("ix_approval_steps_approver", table_name="approval_steps")
    op.drop_index("ix_approval_steps_request", table_name="approval_steps")
    op.drop_table("approval_steps")

    op.drop_index("ix_approval_requests_operation", table_name="approval_requests")
    op.drop_index("ix_approval_requests_parent_workflow", table_name="approval_requests")
    op.drop_index("ix_approval_requests_workflow", table_name="approval_requests")
    op.drop_index("ix_approval_requests_status", table_name="approval_requests")
    op.drop_index("ix_approval_requests_requester", table_name="approval_requests")
    op.drop_index("ix_approval_requests_tenant", table_name="approval_requests")
    op.drop_table("approval_requests")

    op.drop_index("ix_approval_policies_operation", table_name="approval_policies")
    op.drop_index("ix_approval_policies_tenant", table_name="approval_policies")
    op.drop_table("approval_policies")

    # Drop enums
    sa.Enum(name="approval_step_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="approval_request_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="approval_chain_mode").drop(op.get_bind(), checkfirst=True)
