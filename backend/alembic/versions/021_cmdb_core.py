"""CMDB core tables: CI classes, configuration items, relationships, snapshots, templates,
service catalog, price lists, saved searches. Extends compartments with cloud_id/provider_type.
Seeds CMDB permissions, system CI classes from semantic types, and relationship types.

Revision ID: 021
Revises: 020
Create Date: 2026-02-09
"""

import sqlalchemy as sa

from alembic import op

revision: str = "021"
down_revision: str | None = "020"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

# ── Permission definitions ────────────────────────────────────────────

CMDB_PERMISSIONS = [
    ("cmdb:ci:read", "View configuration items"),
    ("cmdb:ci:create", "Create configuration items"),
    ("cmdb:ci:update", "Update configuration items"),
    ("cmdb:ci:delete", "Delete configuration items"),
    ("cmdb:class:read", "View CI classes"),
    ("cmdb:class:manage", "Manage CI classes"),
    ("cmdb:compartment:read", "View compartments"),
    ("cmdb:compartment:manage", "Manage compartments"),
    ("cmdb:relationship:read", "View CI relationships"),
    ("cmdb:relationship:manage", "Manage CI relationships"),
    ("cmdb:template:read", "View CI templates"),
    ("cmdb:template:manage", "Manage CI templates"),
    ("cmdb:catalog:read", "View service catalog"),
    ("cmdb:catalog:manage", "Manage service catalog"),
]

# Read permissions assigned to all roles
READ_PERMISSIONS = [
    "cmdb:ci:read",
    "cmdb:class:read",
    "cmdb:compartment:read",
    "cmdb:relationship:read",
    "cmdb:template:read",
    "cmdb:catalog:read",
]

# Manage permissions assigned to Tenant Admin and Provider Admin
MANAGE_PERMISSIONS = [
    "cmdb:ci:create",
    "cmdb:ci:update",
    "cmdb:ci:delete",
    "cmdb:class:manage",
    "cmdb:compartment:manage",
    "cmdb:relationship:manage",
    "cmdb:template:manage",
    "cmdb:catalog:manage",
]

# ── System relationship types ─────────────────────────────────────────

RELATIONSHIP_TYPES = [
    {
        "name": "contains",
        "display_name": "Contains",
        "inverse_name": "contained_by",
        "description": "Parent contains child resource (e.g. host contains VMs)",
    },
    {
        "name": "belongs_to",
        "display_name": "Belongs To",
        "inverse_name": "owns",
        "description": "Resource belongs to a logical grouping",
    },
    {
        "name": "connects_to",
        "display_name": "Connects To",
        "inverse_name": "connected_from",
        "description": "Network or logical connectivity between resources",
    },
    {
        "name": "depends_on",
        "display_name": "Depends On",
        "inverse_name": "depended_on_by",
        "description": "Functional dependency — target failure impacts source",
    },
    {
        "name": "uses",
        "display_name": "Uses",
        "inverse_name": "used_by",
        "description": "Resource consumes or leverages another resource",
    },
    {
        "name": "secures",
        "display_name": "Secures",
        "inverse_name": "secured_by",
        "description": "Security relationship (firewall protects network, etc.)",
    },
    {
        "name": "monitors",
        "display_name": "Monitors",
        "inverse_name": "monitored_by",
        "description": "Monitoring or observability relationship",
    },
    {
        "name": "backs_up",
        "display_name": "Backs Up",
        "inverse_name": "backed_up_by",
        "description": "Backup or replication relationship",
    },
]


def upgrade() -> None:
    # ── 1. Extend compartments table ──────────────────────────────────
    op.add_column(
        "compartments",
        sa.Column("cloud_id", sa.String(255), nullable=True),
    )
    op.add_column(
        "compartments",
        sa.Column("provider_type", sa.String(50), nullable=True),
    )

    # ── 2. CI classes ─────────────────────────────────────────────────
    op.create_table(
        "ci_classes",
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
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column(
            "parent_class_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ci_classes.id"),
            nullable=True,
        ),
        sa.Column(
            "semantic_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id"),
            nullable=True,
        ),
        sa.Column("schema", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("icon", sa.String(100), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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
        sa.UniqueConstraint("tenant_id", "name", name="uq_ci_class_tenant_name"),
    )
    op.create_index("ix_ci_classes_tenant_id", "ci_classes", ["tenant_id"])
    op.create_index("ix_ci_classes_parent_class_id", "ci_classes", ["parent_class_id"])

    # ── 3. CI attribute definitions ───────────────────────────────────
    op.create_table(
        "ci_attribute_definitions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ci_class_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ci_classes.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("data_type", sa.String(50), nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("default_value", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("validation_rules", sa.dialects.postgresql.JSONB, nullable=True),
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
        sa.UniqueConstraint(
            "ci_class_id", "name", name="uq_ci_attr_def_class_name"
        ),
    )
    op.create_index(
        "ix_ci_attribute_definitions_class_id",
        "ci_attribute_definitions",
        ["ci_class_id"],
    )

    # ── 4. Configuration items ────────────────────────────────────────
    op.create_table(
        "configuration_items",
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
            "ci_class_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ci_classes.id"),
            nullable=False,
        ),
        sa.Column(
            "compartment_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("compartments.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "lifecycle_state", sa.String(20), nullable=False, server_default="planned"
        ),
        sa.Column(
            "attributes",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "tags",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column("cloud_resource_id", sa.String(500), nullable=True),
        sa.Column("pulumi_urn", sa.String(500), nullable=True),
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
    op.create_index("ix_ci_tenant_id", "configuration_items", ["tenant_id"])
    op.create_index("ix_ci_ci_class_id", "configuration_items", ["ci_class_id"])
    op.create_index("ix_ci_compartment_id", "configuration_items", ["compartment_id"])
    op.create_index("ix_ci_tenant_class", "configuration_items", ["tenant_id", "ci_class_id"])
    op.create_index(
        "ix_ci_tenant_compartment",
        "configuration_items",
        ["tenant_id", "compartment_id"],
    )
    op.create_index("ix_ci_cloud_resource_id", "configuration_items", ["cloud_resource_id"])
    op.create_index("ix_ci_pulumi_urn", "configuration_items", ["pulumi_urn"])
    op.create_index("ix_ci_lifecycle_state", "configuration_items", ["lifecycle_state"])

    # ── 5. Relationship types ─────────────────────────────────────────
    op.create_table(
        "relationship_types",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("inverse_name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("source_class_ids", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("target_class_ids", sa.dialects.postgresql.JSONB, nullable=True),
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

    # ── 6. CI relationships ───────────────────────────────────────────
    op.create_table(
        "ci_relationships",
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
            "source_ci_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("configuration_items.id"),
            nullable=False,
        ),
        sa.Column(
            "target_ci_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("configuration_items.id"),
            nullable=False,
        ),
        sa.Column(
            "relationship_type_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("relationship_types.id"),
            nullable=False,
        ),
        sa.Column("attributes", sa.dialects.postgresql.JSONB, nullable=True),
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
            "source_ci_id",
            "target_ci_id",
            "relationship_type_id",
            name="uq_ci_relationship_src_tgt_type",
        ),
        sa.CheckConstraint(
            "source_ci_id != target_ci_id",
            name="ck_ci_relationship_no_self_ref",
        ),
    )
    op.create_index("ix_ci_rel_tenant_id", "ci_relationships", ["tenant_id"])
    op.create_index("ix_ci_rel_source_ci_id", "ci_relationships", ["source_ci_id"])
    op.create_index("ix_ci_rel_target_ci_id", "ci_relationships", ["target_ci_id"])
    op.create_index("ix_ci_rel_type_id", "ci_relationships", ["relationship_type_id"])

    # ── 7. CI snapshots ───────────────────────────────────────────────
    op.create_table(
        "ci_snapshots",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "ci_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("configuration_items.id"),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column(
            "snapshot_data", sa.dialects.postgresql.JSONB, nullable=False
        ),
        sa.Column(
            "changed_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column(
            "changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column(
            "change_type", sa.String(50), nullable=False, server_default="update"
        ),
        sa.UniqueConstraint(
            "ci_id", "version_number", name="uq_ci_snapshot_ci_version"
        ),
    )
    op.create_index("ix_ci_snapshots_ci_id", "ci_snapshots", ["ci_id"])
    op.create_index("ix_ci_snapshots_tenant_id", "ci_snapshots", ["tenant_id"])

    # ── 8. CI templates ───────────────────────────────────────────────
    op.create_table(
        "ci_templates",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "ci_class_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ci_classes.id"),
            nullable=False,
        ),
        sa.Column(
            "attributes",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "tags",
            sa.dialects.postgresql.JSONB,
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "relationship_templates", sa.dialects.postgresql.JSONB, nullable=True
        ),
        sa.Column("constraints", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
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
    op.create_index("ix_ci_templates_tenant_id", "ci_templates", ["tenant_id"])

    # ── 9. Service offerings ──────────────────────────────────────────
    op.create_table(
        "service_offerings",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "measuring_unit", sa.String(20), nullable=False, server_default="month"
        ),
        sa.Column(
            "ci_class_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("ci_classes.id"),
            nullable=True,
        ),
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
    op.create_index("ix_service_offerings_tenant_id", "service_offerings", ["tenant_id"])

    # ── 10. Price lists ───────────────────────────────────────────────
    op.create_table(
        "price_lists",
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
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
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
    op.create_index("ix_price_lists_tenant_id", "price_lists", ["tenant_id"])

    # ── 11. Price list items ──────────────────────────────────────────
    op.create_table(
        "price_list_items",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "price_list_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("price_lists.id"),
            nullable=False,
        ),
        sa.Column(
            "service_offering_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_offerings.id"),
            nullable=False,
        ),
        sa.Column("price_per_unit", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
        sa.Column("min_quantity", sa.Numeric, nullable=True),
        sa.Column("max_quantity", sa.Numeric, nullable=True),
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
        "ix_price_list_items_price_list_id",
        "price_list_items",
        ["price_list_id"],
    )
    op.create_index(
        "ix_price_list_items_service_offering_id",
        "price_list_items",
        ["service_offering_id"],
    )

    # ── 12. Tenant price overrides ────────────────────────────────────
    op.create_table(
        "tenant_price_overrides",
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
            "service_offering_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_offerings.id"),
            nullable=False,
        ),
        sa.Column("price_per_unit", sa.Numeric(12, 4), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
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
        "ix_tenant_price_overrides_tenant_id",
        "tenant_price_overrides",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_price_overrides_service_id",
        "tenant_price_overrides",
        ["service_offering_id"],
    )

    # ── 13. Saved searches ────────────────────────────────────────────
    op.create_table(
        "saved_searches",
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
        sa.Column("query_text", sa.String(1000), nullable=True),
        sa.Column("filters", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("sort_config", sa.dialects.postgresql.JSONB, nullable=True),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
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
    op.create_index("ix_saved_searches_tenant_id", "saved_searches", ["tenant_id"])
    op.create_index("ix_saved_searches_user_id", "saved_searches", ["user_id"])

    # ── 14. Seed data ─────────────────────────────────────────────────
    _seed_relationship_types()
    _seed_ci_classes_from_semantic_types()
    _seed_permissions()


def _seed_relationship_types() -> None:
    """Seed the 8 system relationship types."""
    conn = op.get_bind()
    for rt in RELATIONSHIP_TYPES:
        conn.execute(
            sa.text(
                """
                INSERT INTO relationship_types
                    (id, name, display_name, inverse_name, description, is_system,
                     created_at, updated_at)
                VALUES (gen_random_uuid(), :name, :display_name, :inverse_name,
                        :description, true, now(), now())
                ON CONFLICT (name) DO NOTHING
                """
            ),
            rt,
        )


def _seed_ci_classes_from_semantic_types() -> None:
    """Create system CI classes from existing concrete semantic resource types."""
    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            INSERT INTO ci_classes
                (id, tenant_id, name, display_name, semantic_type_id,
                 schema, icon, is_system, is_active, created_at, updated_at)
            SELECT
                gen_random_uuid(), NULL, srt.name, srt.display_name, srt.id,
                srt.properties_schema, srt.icon, true, true, now(), now()
            FROM semantic_resource_types srt
            WHERE srt.is_abstract = false
              AND srt.deleted_at IS NULL
            ON CONFLICT ON CONSTRAINT uq_ci_class_tenant_name DO NOTHING
            """
        )
    )


def _seed_permissions() -> None:
    """Seed CMDB permissions and assign to roles."""
    conn = op.get_bind()

    # Insert all permissions
    for key, description in CMDB_PERMISSIONS:
        parts = key.split(":")
        domain = parts[0]
        resource = parts[1]
        action = parts[2]

        conn.execute(
            sa.text(
                """
                INSERT INTO permissions
                    (id, domain, resource, action, subtype, description,
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

    # Assign read permissions to all roles
    for perm_key in READ_PERMISSIONS:
        parts = perm_key.split(":")
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r
                CROSS JOIN permissions p
                WHERE p.domain = :domain AND p.resource = :resource AND p.action = :action
                  AND NOT EXISTS (
                      SELECT 1 FROM role_permissions rp
                      WHERE rp.role_id = r.id AND rp.permission_id = p.id
                  )
                """
            ),
            {"domain": parts[0], "resource": parts[1], "action": parts[2]},
        )

    # Assign manage permissions to Tenant Admin and Provider Admin
    for perm_key in MANAGE_PERMISSIONS:
        parts = perm_key.split(":")
        conn.execute(
            sa.text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
                SELECT gen_random_uuid(), r.id, p.id, now(), now()
                FROM roles r
                CROSS JOIN permissions p
                WHERE r.name IN ('Tenant Admin', 'Provider Admin')
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

    # Remove CMDB permissions from role_permissions
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE domain = 'cmdb'
            )
            """
        )
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE domain = 'cmdb'")
    )

    # Delete system CI classes
    conn.execute(
        sa.text("DELETE FROM ci_classes WHERE is_system = true")
    )

    # Delete system relationship types
    conn.execute(
        sa.text("DELETE FROM relationship_types WHERE is_system = true")
    )

    # Drop tables in reverse dependency order
    op.drop_index("ix_saved_searches_user_id", table_name="saved_searches")
    op.drop_index("ix_saved_searches_tenant_id", table_name="saved_searches")
    op.drop_table("saved_searches")

    op.drop_index("ix_tenant_price_overrides_service_id", table_name="tenant_price_overrides")
    op.drop_index("ix_tenant_price_overrides_tenant_id", table_name="tenant_price_overrides")
    op.drop_table("tenant_price_overrides")

    op.drop_index("ix_price_list_items_service_offering_id", table_name="price_list_items")
    op.drop_index("ix_price_list_items_price_list_id", table_name="price_list_items")
    op.drop_table("price_list_items")

    op.drop_index("ix_price_lists_tenant_id", table_name="price_lists")
    op.drop_table("price_lists")

    op.drop_index("ix_service_offerings_tenant_id", table_name="service_offerings")
    op.drop_table("service_offerings")

    op.drop_index("ix_ci_templates_tenant_id", table_name="ci_templates")
    op.drop_table("ci_templates")

    op.drop_index("ix_ci_snapshots_tenant_id", table_name="ci_snapshots")
    op.drop_index("ix_ci_snapshots_ci_id", table_name="ci_snapshots")
    op.drop_table("ci_snapshots")

    op.drop_index("ix_ci_rel_type_id", table_name="ci_relationships")
    op.drop_index("ix_ci_rel_target_ci_id", table_name="ci_relationships")
    op.drop_index("ix_ci_rel_source_ci_id", table_name="ci_relationships")
    op.drop_index("ix_ci_rel_tenant_id", table_name="ci_relationships")
    op.drop_table("ci_relationships")

    op.drop_table("relationship_types")

    op.drop_index("ix_ci_lifecycle_state", table_name="configuration_items")
    op.drop_index("ix_ci_pulumi_urn", table_name="configuration_items")
    op.drop_index("ix_ci_cloud_resource_id", table_name="configuration_items")
    op.drop_index("ix_ci_tenant_compartment", table_name="configuration_items")
    op.drop_index("ix_ci_tenant_class", table_name="configuration_items")
    op.drop_index("ix_ci_compartment_id", table_name="configuration_items")
    op.drop_index("ix_ci_ci_class_id", table_name="configuration_items")
    op.drop_index("ix_ci_tenant_id", table_name="configuration_items")
    op.drop_table("configuration_items")

    op.drop_index(
        "ix_ci_attribute_definitions_class_id",
        table_name="ci_attribute_definitions",
    )
    op.drop_table("ci_attribute_definitions")

    op.drop_index("ix_ci_classes_parent_class_id", table_name="ci_classes")
    op.drop_index("ix_ci_classes_tenant_id", table_name="ci_classes")
    op.drop_table("ci_classes")

    # Remove compartment extension columns
    op.drop_column("compartments", "provider_type")
    op.drop_column("compartments", "cloud_id")
