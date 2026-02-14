"""Add architecture_topologies table and architecture permissions.

Revision ID: 027
Revises: 026
Create Date: 2026-02-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ARCHITECTURE_PERMISSIONS = [
    ("architecture:topology:create", "Create architecture topologies"),
    ("architecture:topology:read", "View architecture topologies"),
    ("architecture:topology:update", "Update architecture topologies"),
    ("architecture:topology:delete", "Delete architecture topologies"),
    ("architecture:topology:publish", "Publish architecture topologies"),
    ("architecture:template:read", "View architecture templates"),
    ("architecture:template:manage", "Manage architecture templates"),
]

# Provider Admin & Tenant Admin: all permissions
# User: read/create/update topology + template:read
# Read-Only: read topology + template:read
USER_PERMISSIONS = [
    "architecture:topology:create",
    "architecture:topology:read",
    "architecture:topology:update",
    "architecture:template:read",
]
READONLY_PERMISSIONS = [
    "architecture:topology:read",
    "architecture:template:read",
]


def upgrade() -> None:
    # -- Enum --
    op.execute(
        "DO $$ BEGIN "
        "CREATE TYPE topology_status AS ENUM ('DRAFT','PUBLISHED','ARCHIVED'); "
        "EXCEPTION WHEN duplicate_object THEN NULL; END $$"
    )

    topology_status = postgresql.ENUM(
        "DRAFT", "PUBLISHED", "ARCHIVED",
        name="topology_status",
        create_type=False,
    )

    # -- architecture_topologies table --
    op.create_table(
        "architecture_topologies",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("graph", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column(
            "status", topology_status,
            nullable=False, server_default="DRAFT",
        ),
        sa.Column("version", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_template", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("tags", sa.dialects.postgresql.ARRAY(sa.String(100)), nullable=True),
        sa.Column(
            "created_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
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
            name="uq_topology_tenant_name_version",
        ),
    )
    op.create_index(
        "ix_architecture_topologies_tenant", "architecture_topologies", ["tenant_id"]
    )
    op.create_index(
        "ix_architecture_topologies_status", "architecture_topologies",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_architecture_topologies_created_by", "architecture_topologies", ["created_by"]
    )
    op.create_index(
        "ix_architecture_topologies_template", "architecture_topologies", ["is_template"]
    )

    # -- Seed architecture permissions --
    conn = op.get_bind()
    for key, description in ARCHITECTURE_PERMISSIONS:
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

    # Provider Admin & Tenant Admin get all architecture permissions
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'architecture'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )

    # User role: create/read/update topology + template:read
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

    # Read-Only role: read topology + template:read
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

    # Remove architecture role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'architecture'
            )
            """
        )
    )

    # Remove architecture permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'architecture'"))

    # Drop indexes and table
    op.drop_index("ix_architecture_topologies_template", table_name="architecture_topologies")
    op.drop_index("ix_architecture_topologies_created_by", table_name="architecture_topologies")
    op.drop_index("ix_architecture_topologies_status", table_name="architecture_topologies")
    op.drop_index("ix_architecture_topologies_tenant", table_name="architecture_topologies")
    op.drop_table("architecture_topologies")

    # Drop enum
    sa.Enum(name="topology_status").drop(op.get_bind(), checkfirst=True)
