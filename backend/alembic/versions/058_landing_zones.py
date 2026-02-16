"""
Overview: Create landing zone, environment, and IPAM tables with permissions.
Architecture: Database migration (Section 5)
Dependencies: alembic, sqlalchemy
Concepts: Landing zones, environments, IPAM, address management, tag governance
"""

revision = "058"
down_revision = "057"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM


def upgrade() -> None:
    # ── 1. Enum types ────────────────────────────────────────────────────
    for enum_name, values in [
        ("landing_zone_status", ("DRAFT", "PUBLISHED", "ARCHIVED")),
        ("environment_status", ("PLANNED", "PROVISIONING", "ACTIVE", "SUSPENDED", "DECOMMISSIONING", "DECOMMISSIONED")),
        ("address_space_status", ("ACTIVE", "EXHAUSTED", "RESERVED")),
        ("allocation_type", ("REGION", "PROVIDER_RESERVED", "TENANT_POOL", "VCN", "SUBNET")),
        ("allocation_status", ("PLANNED", "ALLOCATED", "IN_USE", "RELEASED")),
        ("reservation_status", ("RESERVED", "IN_USE", "RELEASED")),
    ]:
        vals = ", ".join(f"'{v}'" for v in values)
        op.execute(sa.text(f"""
            DO $$ BEGIN
                CREATE TYPE {enum_name} AS ENUM ({vals});
            EXCEPTION
                WHEN duplicate_object THEN NULL;
            END $$
        """))

    # ── 2. Add is_landing_zone to architecture_topologies ────────────────
    op.add_column(
        "architecture_topologies",
        sa.Column("is_landing_zone", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ── 3. Tables ────────────────────────────────────────────────────────

    # landing_zones
    op.create_table(
        "landing_zones",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("backend_id", UUID(as_uuid=True), sa.ForeignKey("cloud_backends.id"), nullable=False),
        sa.Column("topology_id", UUID(as_uuid=True), sa.ForeignKey("architecture_topologies.id"), nullable=False),
        sa.Column("cloud_tenancy_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", ENUM("DRAFT", "PUBLISHED", "ARCHIVED", name="landing_zone_status", create_type=False), nullable=False, server_default="DRAFT"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_landing_zones_tenant", "landing_zones", ["tenant_id"])
    op.create_index("ix_landing_zones_backend", "landing_zones", ["backend_id"])
    op.create_index("ix_landing_zones_status", "landing_zones", ["tenant_id", "status"])

    # landing_zone_regions
    op.create_table(
        "landing_zone_regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("region_identifier", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_dr", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("landing_zone_id", "region_identifier", name="uq_lz_region"),
    )

    # landing_zone_tag_policies
    op.create_table(
        "landing_zone_tag_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("tag_key", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("allowed_values", JSONB, nullable=True),
        sa.Column("default_value", sa.String(500), nullable=True),
        sa.Column("inherited", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("landing_zone_id", "tag_key", name="uq_lz_tag_key"),
    )

    # environment_templates
    op.create_table(
        "environment_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("default_tags", JSONB, nullable=True),
        sa.Column("default_policies", JSONB, nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # tenant_environments
    op.create_table(
        "tenant_environments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("environment_templates.id"), nullable=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", ENUM("PLANNED", "PROVISIONING", "ACTIVE", "SUSPENDED", "DECOMMISSIONING", "DECOMMISSIONED", name="environment_status", create_type=False), nullable=False, server_default="PLANNED"),
        sa.Column("root_compartment_id", UUID(as_uuid=True), sa.ForeignKey("compartments.id"), nullable=True),
        sa.Column("tags", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("policies", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_tenant_envs_tenant", "tenant_environments", ["tenant_id"])
    op.create_index("ix_tenant_envs_lz", "tenant_environments", ["landing_zone_id"])
    op.create_index("ix_tenant_envs_status", "tenant_environments", ["tenant_id", "status"])

    # address_spaces
    op.create_table(
        "address_spaces",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("landing_zone_id", UUID(as_uuid=True), sa.ForeignKey("landing_zones.id"), nullable=False),
        sa.Column("region_id", UUID(as_uuid=True), sa.ForeignKey("landing_zone_regions.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cidr", sa.String(43), nullable=False),
        sa.Column("ip_version", sa.SmallInteger(), nullable=False, server_default="4"),
        sa.Column("status", ENUM("ACTIVE", "EXHAUSTED", "RESERVED", name="address_space_status", create_type=False), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # address_allocations
    op.create_table(
        "address_allocations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("address_space_id", UUID(as_uuid=True), sa.ForeignKey("address_spaces.id"), nullable=False),
        sa.Column("parent_allocation_id", UUID(as_uuid=True), sa.ForeignKey("address_allocations.id"), nullable=True),
        sa.Column("tenant_environment_id", UUID(as_uuid=True), sa.ForeignKey("tenant_environments.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cidr", sa.String(43), nullable=False),
        sa.Column("allocation_type", ENUM("REGION", "PROVIDER_RESERVED", "TENANT_POOL", "VCN", "SUBNET", name="allocation_type", create_type=False), nullable=False),
        sa.Column("status", ENUM("PLANNED", "ALLOCATED", "IN_USE", "RELEASED", name="allocation_status", create_type=False), nullable=False, server_default="PLANNED"),
        sa.Column("purpose", sa.String(255), nullable=True),
        sa.Column("semantic_type_id", UUID(as_uuid=True), sa.ForeignKey("semantic_resource_types.id"), nullable=True),
        sa.Column("cloud_resource_id", sa.String(500), nullable=True),
        sa.Column("utilization_percent", sa.Float(), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_addr_alloc_space", "address_allocations", ["address_space_id"])
    op.create_index("ix_addr_alloc_parent", "address_allocations", ["parent_allocation_id"])
    op.create_index("ix_addr_alloc_tenant_env", "address_allocations", ["tenant_environment_id"])

    # ip_reservations
    op.create_table(
        "ip_reservations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("allocation_id", UUID(as_uuid=True), sa.ForeignKey("address_allocations.id"), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=False),
        sa.Column("hostname", sa.String(255), nullable=True),
        sa.Column("purpose", sa.String(255), nullable=False),
        sa.Column("ci_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=True),
        sa.Column("status", ENUM("RESERVED", "IN_USE", "RELEASED", name="reservation_status", create_type=False), nullable=False, server_default="RESERVED"),
        sa.Column("reserved_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_ip_res_allocation", "ip_reservations", ["allocation_id"])
    op.create_index("ix_ip_res_ci", "ip_reservations", ["ci_id"])

    # ── 4. Partial unique constraints ────────────────────────────────────
    op.create_index("uq_landing_zone_backend_name", "landing_zones", ["backend_id", "name"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_env_template_provider_name", "environment_templates", ["provider_id", "name"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_tenant_env_name", "tenant_environments", ["tenant_id", "landing_zone_id", "name"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_addr_space_lz_cidr", "address_spaces", ["landing_zone_id", "cidr"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_addr_alloc_space_cidr", "address_allocations", ["address_space_id", "cidr"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))
    op.create_index("uq_ip_res_alloc_ip", "ip_reservations", ["allocation_id", "ip_address"], unique=True, postgresql_where=sa.text("deleted_at IS NULL"))

    # ── 5. Permissions ───────────────────────────────────────────────────
    conn = op.get_bind()

    permissions = [
        ("landingzone", "zone", "read", "View landing zones"),
        ("landingzone", "zone", "create", "Create landing zones"),
        ("landingzone", "zone", "update", "Edit landing zones"),
        ("landingzone", "zone", "delete", "Delete landing zones"),
        ("landingzone", "zone", "publish", "Publish landing zones"),
        ("landingzone", "region", "manage", "Manage landing zone regions"),
        ("landingzone", "tagpolicy", "manage", "Manage tag policies"),
        ("landingzone", "template", "read", "View environment templates"),
        ("landingzone", "template", "manage", "Manage environment templates"),
        ("landingzone", "environment", "read", "View tenant environments"),
        ("landingzone", "environment", "create", "Create tenant environments"),
        ("landingzone", "environment", "update", "Update tenant environments"),
        ("landingzone", "environment", "decommission", "Decommission tenant environments"),
        ("ipam", "space", "read", "View address spaces"),
        ("ipam", "space", "manage", "Create/edit address spaces"),
        ("ipam", "allocation", "read", "View address allocations"),
        ("ipam", "allocation", "manage", "Allocate/release CIDR blocks"),
        ("ipam", "reservation", "read", "View IP reservations"),
        ("ipam", "reservation", "manage", "Reserve/release IP addresses"),
    ]

    for domain, resource, action, description in permissions:
        conn.execute(sa.text("""
            INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), :domain, :resource, :action, :description, true, now(), now())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """), {"domain": domain, "resource": resource, "action": action, "description": description})

    # ── 6. Role-permission assignments ───────────────────────────────────

    # Provider Admin — all 19 permissions
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Provider Admin'
          AND p.domain IN ('landingzone', 'ipam')
        ON CONFLICT DO NOTHING
    """))

    # Tenant Admin — all except publish, tagpolicy:manage, template:manage
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Tenant Admin'
          AND p.domain IN ('landingzone', 'ipam')
          AND NOT (p.resource = 'zone' AND p.action = 'publish')
          AND NOT (p.resource = 'tagpolicy' AND p.action = 'manage')
          AND NOT (p.resource = 'template' AND p.action = 'manage')
        ON CONFLICT DO NOTHING
    """))

    # User — all :read + ipam:reservation:manage
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'User'
          AND p.domain IN ('landingzone', 'ipam')
          AND (p.action = 'read' OR (p.domain = 'ipam' AND p.resource = 'reservation' AND p.action = 'manage'))
        ON CONFLICT DO NOTHING
    """))

    # Read-Only — all :read only
    conn.execute(sa.text("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at)
        SELECT gen_random_uuid(), r.id, p.id, now()
        FROM roles r CROSS JOIN permissions p
        WHERE r.name = 'Read-Only'
          AND p.domain IN ('landingzone', 'ipam')
          AND p.action = 'read'
        ON CONFLICT DO NOTHING
    """))

    # ── 7. Seed environment templates ────────────────────────────────────
    conn.execute(sa.text("""
        INSERT INTO environment_templates (id, provider_id, name, display_name, description, icon, color, default_tags, default_policies, sort_order, is_system, created_at, updated_at)
        SELECT gen_random_uuid(), p.id, t.name, t.display_name, t.description, t.icon, t.color,
               t.default_tags::jsonb, '{}'::jsonb, t.sort_order, true, now(), now()
        FROM providers p
        CROSS JOIN (VALUES
            ('development', 'Development', 'Standard development environment', 'code', '#22c55e', '{"environment": "development"}', 1),
            ('staging', 'Staging', 'Pre-production staging environment', 'flask', '#f59e0b', '{"environment": "staging"}', 2),
            ('production', 'Production', 'Production environment', 'shield-check', '#3b82f6', '{"environment": "production"}', 3),
            ('disaster-recovery', 'Disaster Recovery', 'DR environment for business continuity', 'alert-triangle', '#ef4444', '{"environment": "disaster-recovery"}', 4)
        ) AS t(name, display_name, description, icon, color, default_tags, sort_order)
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Drop tables in reverse order
    op.drop_table("ip_reservations")
    op.drop_table("address_allocations")
    op.drop_table("address_spaces")
    op.drop_table("tenant_environments")
    op.drop_table("environment_templates")
    op.drop_table("landing_zone_tag_policies")
    op.drop_table("landing_zone_regions")
    op.drop_table("landing_zones")

    # Remove is_landing_zone column
    op.drop_column("architecture_topologies", "is_landing_zone")

    # Remove role-permission assignments
    conn.execute(sa.text("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain IN ('landingzone', 'ipam')
        )
    """))

    # Remove permissions
    conn.execute(sa.text("""
        DELETE FROM permissions WHERE domain IN ('landingzone', 'ipam')
    """))

    # Drop enum types
    for enum_name in [
        "reservation_status",
        "allocation_status",
        "allocation_type",
        "address_space_status",
        "environment_status",
        "landing_zone_status",
    ]:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_name}"))
