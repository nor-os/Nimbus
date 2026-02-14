"""Cloud backends: configured provider connections with encrypted credentials and IAM mappings.

Revision ID: 035
Revises: 034
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "035"
down_revision: Union[str, None] = "034"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSIONS = [
    ("cloud:backend:read", "View cloud backend connections"),
    ("cloud:backend:create", "Create cloud backend connections"),
    ("cloud:backend:update", "Update cloud backend connections"),
    ("cloud:backend:delete", "Delete cloud backend connections"),
    ("cloud:backend:manage_iam", "Manage IAM mappings on cloud backends"),
    ("cloud:backend:test", "Test cloud backend connectivity"),
]


def upgrade() -> None:
    # -- cloud_backends table ------------------------------------------------
    op.create_table(
        "cloud_backends",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "provider_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_providers.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("credentials_encrypted", sa.LargeBinary, nullable=True),
        sa.Column(
            "credentials_schema_version", sa.Integer, nullable=False, server_default="1"
        ),
        sa.Column("scope_config", postgresql.JSONB, nullable=True),
        sa.Column("endpoint_url", sa.String(500), nullable=True),
        sa.Column("is_shared", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "last_connectivity_check",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("last_connectivity_status", sa.String(50), nullable=True),
        sa.Column("last_connectivity_error", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
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
    )
    op.create_index("ix_cloud_backends_tenant", "cloud_backends", ["tenant_id"])
    op.create_index("ix_cloud_backends_provider", "cloud_backends", ["provider_id"])
    op.create_index("ix_cloud_backends_status", "cloud_backends", ["status"])

    # Partial unique constraint: (tenant_id, name) WHERE deleted_at IS NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_cloud_backend_tenant_name "
        "ON cloud_backends (tenant_id, name) WHERE deleted_at IS NULL"
    )

    # -- cloud_backend_iam_mappings table ------------------------------------
    op.create_table(
        "cloud_backend_iam_mappings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "backend_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_backends.id"),
            nullable=False,
        ),
        sa.Column(
            "role_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("roles.id"),
            nullable=False,
        ),
        sa.Column("cloud_identity", postgresql.JSONB, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
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
    )
    op.create_index(
        "ix_cloud_iam_backend", "cloud_backend_iam_mappings", ["backend_id"]
    )
    op.create_index(
        "ix_cloud_iam_role", "cloud_backend_iam_mappings", ["role_id"]
    )

    # Partial unique: (backend_id, role_id) WHERE deleted_at IS NULL
    op.execute(
        "CREATE UNIQUE INDEX uq_cloud_iam_backend_role "
        "ON cloud_backend_iam_mappings (backend_id, role_id) WHERE deleted_at IS NULL"
    )

    # -- Add backend_id FK to configuration_items ----------------------------
    op.add_column(
        "configuration_items",
        sa.Column(
            "backend_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("cloud_backends.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_ci_backend_id", "configuration_items", ["backend_id"]
    )

    # -- Seed permissions ----------------------------------------------------
    conn = op.get_bind()
    for key, description in PERMISSIONS:
        parts = key.split(":")
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
                "domain": parts[0],
                "resource": parts[1],
                "action": parts[2],
                "subtype": parts[3] if len(parts) > 3 else None,
                "description": description,
            },
        )

    # Assign read + test to all roles; create/update/delete/manage_iam to admin roles
    # Role names are PascalCase with spaces: 'Provider Admin', 'Tenant Admin'
    # Read-Only gets only read
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'cloud' AND p.resource = 'backend'
              AND (
                -- Provider Admin & Tenant Admin get all cloud:backend permissions
                (r.name IN ('Provider Admin', 'Tenant Admin'))
                -- User gets read + test
                OR (r.name = 'User' AND p.action IN ('read', 'test'))
                -- Read-Only gets read only
                OR (r.name = 'Read-Only' AND p.action = 'read')
              )
              AND NOT EXISTS (
                SELECT 1 FROM role_permissions rp
                WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    op.drop_index("ix_ci_backend_id", table_name="configuration_items")
    op.drop_column("configuration_items", "backend_id")

    op.execute("DROP INDEX IF EXISTS uq_cloud_iam_backend_role")
    op.drop_index("ix_cloud_iam_role", table_name="cloud_backend_iam_mappings")
    op.drop_index("ix_cloud_iam_backend", table_name="cloud_backend_iam_mappings")
    op.drop_table("cloud_backend_iam_mappings")

    op.execute("DROP INDEX IF EXISTS uq_cloud_backend_tenant_name")
    op.drop_index("ix_cloud_backends_status", table_name="cloud_backends")
    op.drop_index("ix_cloud_backends_provider", table_name="cloud_backends")
    op.drop_index("ix_cloud_backends_tenant", table_name="cloud_backends")
    op.drop_table("cloud_backends")

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'cloud' AND resource = 'backend'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE domain = 'cloud' AND resource = 'backend'"
        )
    )
