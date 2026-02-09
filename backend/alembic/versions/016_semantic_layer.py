"""Add semantic_categories, semantic_resource_types, semantic_relationship_kinds,
semantic_provider_mappings tables and seed data from the type registry.

Revision ID: 016
Revises: 015
Create Date: 2026-02-08
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SEMANTIC_PERMISSIONS = [
    ("semantic:type:read", "Browse the semantic type catalog"),
    ("semantic:mapping:read", "View provider-to-semantic mappings"),
    ("semantic:type:manage", "Manage semantic type definitions"),
    ("semantic:mapping:manage", "Manage provider mappings"),
]


def upgrade() -> None:
    # -- 1. semantic_categories table --
    op.create_table(
        "semantic_categories",
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
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
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

    # -- 2. semantic_resource_types table --
    op.create_table(
        "semantic_resource_types",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "category_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_categories.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_abstract", sa.Boolean, nullable=False, server_default="false"),
        sa.Column(
            "parent_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=True,
        ),
        sa.Column("properties_schema", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("allowed_relationship_kinds", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
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
        "ix_semantic_resource_types_category",
        "semantic_resource_types",
        ["category_id"],
    )

    # -- 3. semantic_relationship_kinds table --
    op.create_table(
        "semantic_relationship_kinds",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("inverse_name", sa.String(100), nullable=False),
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

    # -- 4. semantic_provider_mappings table --
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
        sa.Column(
            "semantic_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=False,
        ),
        sa.Column("confidence", sa.String(20), nullable=False, server_default="exact"),
        sa.Column("notes", sa.Text, nullable=True),
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

    # -- 5. Seed data from registry --
    _seed_data()

    # -- 6. Seed permissions --
    _seed_permissions()


def _seed_data() -> None:
    """Seed categories, types, relationship kinds, and provider mappings."""
    from app.services.semantic.registry import (
        CATEGORIES,
        PROVIDER_MAPPINGS,
        RELATIONSHIP_KINDS,
        SEMANTIC_TYPES,
    )

    conn = op.get_bind()

    # Seed categories
    for cat in CATEGORIES:
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_categories (id, name, display_name, description, icon,
                    sort_order, created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :display_name, :description, :icon,
                    :sort_order, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "name": cat.name,
                "display_name": cat.display_name,
                "description": cat.description,
                "icon": cat.icon,
                "sort_order": cat.sort_order,
            },
        )

    # Seed relationship kinds
    for rel in RELATIONSHIP_KINDS:
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_relationship_kinds (id, name, display_name, description,
                    inverse_name, created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :display_name, :description,
                    :inverse_name, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "name": rel.name,
                "display_name": rel.display_name,
                "description": rel.description,
                "inverse_name": rel.inverse_name,
            },
        )

    # Seed semantic types
    import json

    for stype in SEMANTIC_TYPES:
        properties_schema = json.dumps(
            [
                {
                    "name": p.name,
                    "display_name": p.display_name,
                    "data_type": p.data_type,
                    "required": p.required,
                    "default_value": p.default_value,
                    "unit": p.unit,
                    "description": p.description,
                }
                for p in stype.properties
            ]
        )
        allowed_rels = json.dumps(stype.allowed_relationship_kinds)

        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_resource_types (id, category_id, name, display_name,
                    description, icon, is_abstract, parent_type_id, properties_schema,
                    allowed_relationship_kinds, sort_order, created_at, updated_at)
                VALUES (
                    gen_random_uuid(),
                    (SELECT id FROM semantic_categories WHERE name = :category),
                    :name, :display_name, :description, :icon, :is_abstract,
                    NULL,
                    CAST(:properties_schema AS jsonb),
                    CAST(:allowed_rels AS jsonb),
                    :sort_order, now(), now()
                )
                ON CONFLICT (name) DO NOTHING
                """
            ),
            {
                "category": stype.category,
                "name": stype.name,
                "display_name": stype.display_name,
                "description": stype.description,
                "icon": stype.icon,
                "is_abstract": stype.is_abstract,
                "properties_schema": properties_schema,
                "allowed_rels": allowed_rels,
                "sort_order": stype.sort_order,
            },
        )

    # Seed provider mappings
    for mapping in PROVIDER_MAPPINGS:
        conn.execute(
            sa.text(
                """
                INSERT INTO semantic_provider_mappings (id, provider_name,
                    provider_resource_type, semantic_type_id, confidence, notes,
                    created_at, updated_at)
                VALUES (
                    gen_random_uuid(),
                    :provider_name,
                    :provider_resource_type,
                    (SELECT id FROM semantic_resource_types WHERE name = :semantic_type_name),
                    :confidence,
                    :notes,
                    now(), now()
                )
                ON CONFLICT ON CONSTRAINT uq_provider_mapping_provider_resource DO NOTHING
                """
            ),
            {
                "provider_name": mapping.provider_name,
                "provider_resource_type": mapping.provider_resource_type,
                "semantic_type_name": mapping.semantic_type_name,
                "confidence": mapping.confidence,
                "notes": mapping.display_name,
            },
        )


def _seed_permissions() -> None:
    """Seed semantic layer permissions and assign to roles."""
    conn = op.get_bind()

    for key, description in SEMANTIC_PERMISSIONS:
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

    # Assign read permissions to all roles
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE p.domain = 'semantic'
              AND p.action = 'read'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )

    # Assign manage permissions to Tenant Admin and Provider Admin
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
            SELECT gen_random_uuid(), r.id, p.id, now(), now()
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name IN ('Tenant Admin', 'Provider Admin')
              AND p.domain = 'semantic'
              AND p.action = 'manage'
              AND NOT EXISTS (
                  SELECT 1 FROM role_permissions rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Remove semantic role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'semantic'
            )
            """
        )
    )

    # Remove semantic permissions
    conn.execute(sa.text("DELETE FROM permissions WHERE domain = 'semantic'"))

    # Drop tables in reverse dependency order
    op.drop_index("ix_semantic_provider_mappings_provider", table_name="semantic_provider_mappings")
    op.drop_index("ix_semantic_provider_mappings_type", table_name="semantic_provider_mappings")
    op.drop_table("semantic_provider_mappings")

    op.drop_table("semantic_relationship_kinds")

    op.drop_index("ix_semantic_resource_types_category", table_name="semantic_resource_types")
    op.drop_table("semantic_resource_types")

    op.drop_table("semantic_categories")
