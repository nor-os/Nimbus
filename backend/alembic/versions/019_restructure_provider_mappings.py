"""Restructure semantic provider mappings into normalized provider/resource-type/mapping tables.

Creates semantic_providers, semantic_provider_resource_types, semantic_type_mappings.
Migrates data from semantic_provider_mappings. Drops old table.
Adds semantic:provider:read and semantic:provider:manage permissions.

Revision ID: 019
Revises: 017
Create Date: 2026-02-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PROVIDER_PERMISSIONS = [
    ("semantic:provider:read", "Browse semantic providers"),
    ("semantic:provider:manage", "Manage semantic providers"),
]

PROVIDERS = [
    {
        "name": "proxmox",
        "display_name": "Proxmox VE",
        "description": "Open-source server virtualization platform with KVM and LXC",
        "icon": "server",
        "provider_type": "on_prem",
        "website_url": "https://www.proxmox.com/",
        "documentation_url": "https://pve.proxmox.com/pve-docs/",
    },
    {
        "name": "aws",
        "display_name": "Amazon Web Services",
        "description": "Public cloud platform by Amazon",
        "icon": "cloud",
        "provider_type": "cloud",
        "website_url": "https://aws.amazon.com/",
        "documentation_url": "https://docs.aws.amazon.com/",
    },
    {
        "name": "azure",
        "display_name": "Microsoft Azure",
        "description": "Public cloud platform by Microsoft",
        "icon": "cloud",
        "provider_type": "cloud",
        "website_url": "https://azure.microsoft.com/",
        "documentation_url": "https://learn.microsoft.com/en-us/azure/",
    },
    {
        "name": "gcp",
        "display_name": "Google Cloud Platform",
        "description": "Public cloud platform by Google",
        "icon": "cloud",
        "provider_type": "cloud",
        "website_url": "https://cloud.google.com/",
        "documentation_url": "https://cloud.google.com/docs",
    },
    {
        "name": "oci",
        "display_name": "Oracle Cloud Infrastructure",
        "description": "Public cloud platform by Oracle",
        "icon": "cloud",
        "provider_type": "cloud",
        "website_url": "https://www.oracle.com/cloud/",
        "documentation_url": "https://docs.oracle.com/en-us/iaas/Content/",
    },
]


def upgrade() -> None:
    # -- 1. Create semantic_providers table --
    op.create_table(
        "semantic_providers",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("provider_type", sa.String(20), nullable=False, server_default="custom"),
        sa.Column("website_url", sa.String(500), nullable=True),
        sa.Column("documentation_url", sa.String(500), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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

    # -- 2. Create semantic_provider_resource_types table --
    op.create_table(
        "semantic_provider_resource_types",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "provider_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_providers.id"),
            nullable=False,
        ),
        sa.Column("api_type", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("documentation_url", sa.String(500), nullable=True),
        sa.Column("parameter_schema", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="available"),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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
            "provider_id", "api_type",
            name="uq_provider_resource_type_provider_api",
        ),
    )
    op.create_index(
        "ix_semantic_prt_provider",
        "semantic_provider_resource_types",
        ["provider_id"],
    )
    op.create_index(
        "ix_semantic_prt_status",
        "semantic_provider_resource_types",
        ["status"],
    )

    # -- 3. Create semantic_type_mappings table --
    op.create_table(
        "semantic_type_mappings",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "provider_resource_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_provider_resource_types.id"),
            nullable=False,
        ),
        sa.Column(
            "semantic_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=False,
        ),
        sa.Column("parameter_mapping", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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
            "provider_resource_type_id", "semantic_type_id",
            name="uq_type_mapping_prt_semantic",
        ),
    )
    op.create_index(
        "ix_semantic_type_mappings_prt",
        "semantic_type_mappings",
        ["provider_resource_type_id"],
    )
    op.create_index(
        "ix_semantic_type_mappings_semantic",
        "semantic_type_mappings",
        ["semantic_type_id"],
    )

    # -- 4. Seed providers --
    _seed_providers()

    # -- 5. Migrate data from old table --
    _migrate_data()

    # -- 6. Drop old table --
    op.drop_index("ix_semantic_provider_mappings_provider", table_name="semantic_provider_mappings")
    op.drop_index("ix_semantic_provider_mappings_type", table_name="semantic_provider_mappings")
    op.drop_table("semantic_provider_mappings")

    # -- 7. Seed permissions --
    _seed_permissions()


def _seed_providers() -> None:
    """Seed the 5 default providers."""
    conn = op.get_bind()
    for p in PROVIDERS:
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_providers (id, name, display_name, description, icon,
                    provider_type, website_url, documentation_url, is_system,
                    created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :display_name, :description, :icon,
                    :provider_type, :website_url, :documentation_url, true,
                    now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            p,
        )


def _migrate_data() -> None:
    """Migrate data from semantic_provider_mappings to new normalized tables."""
    conn = op.get_bind()

    # Get all existing mappings
    rows = conn.execute(
        sa.text(
            """
            SELECT provider_name, provider_resource_type, display_name,
                   semantic_type_id, notes, is_system
            FROM semantic_provider_mappings
            WHERE deleted_at IS NULL
            """
        )
    ).fetchall()

    for row in rows:
        provider_name = row[0]
        api_type = row[1]
        display_name = row[2] or api_type
        semantic_type_id = row[3]
        notes = row[4]
        is_system = row[5]

        # Ensure provider exists (handles custom providers not in seed list)
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_providers (id, name, display_name, provider_type,
                    is_system, created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :name, 'custom', false, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {"name": provider_name},
        )

        # Insert provider resource type
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_provider_resource_types
                    (id, provider_id, api_type, display_name, is_system, created_at, updated_at)
                VALUES (
                    gen_random_uuid(),
                    (SELECT id FROM semantic_providers WHERE name = :provider_name),
                    :api_type, :display_name, :is_system, now(), now()
                )
                ON CONFLICT ON CONSTRAINT uq_provider_resource_type_provider_api DO NOTHING
                """
            ),
            {
                "provider_name": provider_name,
                "api_type": api_type,
                "display_name": display_name,
                "is_system": is_system,
            },
        )

        # Insert type mapping
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_type_mappings
                    (id, provider_resource_type_id, semantic_type_id, notes, is_system,
                     created_at, updated_at)
                VALUES (
                    gen_random_uuid(),
                    (SELECT prt.id FROM semantic_provider_resource_types prt
                     JOIN semantic_providers sp ON sp.id = prt.provider_id
                     WHERE sp.name = :provider_name AND prt.api_type = :api_type),
                    :semantic_type_id,
                    :notes,
                    :is_system,
                    now(), now()
                )
                ON CONFLICT ON CONSTRAINT uq_type_mapping_prt_semantic DO NOTHING
                """
            ),
            {
                "provider_name": provider_name,
                "api_type": api_type,
                "semantic_type_id": semantic_type_id,
                "notes": notes,
                "is_system": is_system,
            },
        )


def _seed_permissions() -> None:
    """Seed provider permissions and assign to roles."""
    conn = op.get_bind()

    for key, description in PROVIDER_PERMISSIONS:
        parts = key.split(":")
        domain = parts[0]
        resource = parts[1]
        action = parts[2]

        conn.execute(
            sa.text(
                """
                INSERT INTO permissions (id, domain, resource, action, subtype, description,
                                         is_system, created_at, updated_at)
                VALUES (gen_random_uuid(), :domain, :resource, :action, NULL,
                        :description, true, now(), now())
                ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
                """
            ),
            {
                "domain": domain,
                "resource": resource,
                "action": action,
                "description": description,
            },
        )

    # Assign read to all roles
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'semantic' AND p.resource = 'provider' AND p.action = 'read'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )

    # Assign manage to Tenant Admin and Provider Admin
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'semantic' AND p.resource = 'provider' AND p.action = 'manage'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Re-create the old semantic_provider_mappings table
    op.create_table(
        "semantic_provider_mappings",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("provider_resource_type", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=True),
        sa.Column(
            "semantic_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=False,
        ),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="exact"),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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
            "provider_name",
            "provider_resource_type",
            name="uq_provider_mapping_provider_resource",
        ),
    )
    op.create_index(
        "ix_semantic_provider_mappings_type",
        "semantic_provider_mappings",
        ["semantic_type_id"],
    )
    op.create_index(
        "ix_semantic_provider_mappings_provider",
        "semantic_provider_mappings",
        ["provider_name"],
    )

    # Migrate data back
    conn.execute(
        sa.text(
            """
            INSERT INTO semantic_provider_mappings
                (id, provider_name, provider_resource_type, display_name,
                 semantic_type_id, confidence, notes, is_system, created_at, updated_at)
            SELECT gen_random_uuid(), sp.name, prt.api_type, prt.display_name,
                   tm.semantic_type_id, 'exact', tm.notes, tm.is_system, tm.created_at, tm.updated_at
            FROM semantic_type_mappings tm
            JOIN semantic_provider_resource_types prt ON prt.id = tm.provider_resource_type_id
            JOIN semantic_providers sp ON sp.id = prt.provider_id
            WHERE tm.deleted_at IS NULL
            ON CONFLICT ON CONSTRAINT uq_provider_mapping_provider_resource DO NOTHING
            """
        )
    )

    # Remove provider permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE domain = 'semantic' AND resource = 'provider'
            )
            """
        )
    )
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE domain = 'semantic' AND resource = 'provider'"
        )
    )

    # Drop new tables in reverse order
    op.drop_index("ix_semantic_type_mappings_semantic", table_name="semantic_type_mappings")
    op.drop_index("ix_semantic_type_mappings_prt", table_name="semantic_type_mappings")
    op.drop_table("semantic_type_mappings")

    op.drop_index("ix_semantic_prt_status", table_name="semantic_provider_resource_types")
    op.drop_index("ix_semantic_prt_provider", table_name="semantic_provider_resource_types")
    op.drop_table("semantic_provider_resource_types")

    op.drop_table("semantic_providers")
