"""
Overview: Migration 033 — Service Catalog Redesign: new tables for catalogs, SKUs, groups,
    minimums, consumption; column additions for offerings, price items, overrides.
Architecture: Database schema migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Versioned catalogs, provider SKUs, service groups, tenant minimums, consumption records.

Revision ID: 033
Revises: 032
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "033"
down_revision: Union[str, None] = "032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════
    # 1. New tables
    # ══════════════════════════════════════════════════════════════════

    # ── service_groups ─────────────────────────────────────────────
    op.create_table(
        "service_groups",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── service_catalogs ───────────────────────────────────────────
    op.create_table(
        "service_catalogs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("version_major", sa.Integer(), server_default="1", nullable=False),
        sa.Column("version_minor", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("parent_version_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_catalogs.id"), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=True),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_service_catalogs_group_id", "service_catalogs", ["group_id"])
    op.create_index(
        "ix_service_catalogs_group_version_unique",
        "service_catalogs",
        ["group_id", "version_major", "version_minor"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── service_catalog_items ──────────────────────────────────────
    op.create_table(
        "service_catalog_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_catalogs.id"), nullable=False),
        sa.Column("service_offering_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_offerings.id"), nullable=True),
        sa.Column("service_group_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_groups.id"), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    # CHECK: exactly one of (service_offering_id, service_group_id) non-null
    op.execute("""
        ALTER TABLE service_catalog_items
        ADD CONSTRAINT ck_catalog_item_exactly_one
        CHECK (
            (service_offering_id IS NOT NULL)::int +
            (service_group_id IS NOT NULL)::int = 1
        )
    """)

    # ── tenant_catalog_pins ────────────────────────────────────────
    op.create_table(
        "tenant_catalog_pins",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("catalog_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_catalogs.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_tenant_catalog_pins_unique",
        "tenant_catalog_pins",
        ["tenant_id", "catalog_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── provider_skus ──────────────────────────────────────────────
    op.create_table(
        "provider_skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("provider_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("semantic_providers.id"), nullable=False),
        sa.Column("external_sku_id", sa.String(200), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("ci_class_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("ci_classes.id"), nullable=True),
        sa.Column("measuring_unit", sa.String(20), nullable=False,
                  server_default="month"),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("unit_cost", sa.Numeric(12, 4), nullable=True),
        sa.Column("cost_currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("attributes", postgresql.JSONB, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_provider_skus_provider_id", "provider_skus", ["provider_id"])
    op.create_index("ix_provider_skus_ci_class_id", "provider_skus", ["ci_class_id"])
    op.create_index("ix_provider_skus_category", "provider_skus", ["category"])
    op.create_index(
        "ix_provider_skus_provider_sku_unique",
        "provider_skus",
        ["provider_id", "external_sku_id"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # ── service_offering_skus ──────────────────────────────────────
    op.create_table(
        "service_offering_skus",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_offering_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_offerings.id"), nullable=False),
        sa.Column("provider_sku_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("provider_skus.id"), nullable=False),
        sa.Column("default_quantity", sa.Integer(), server_default="1", nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False,
                  server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("service_offering_id", "provider_sku_id",
                            name="uq_offering_sku"),
    )

    # ── service_group_items ────────────────────────────────────────
    op.create_table(
        "service_group_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("group_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_groups.id"), nullable=False),
        sa.Column("service_offering_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_offerings.id"), nullable=False),
        sa.Column("is_required", sa.Boolean, nullable=False,
                  server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("group_id", "service_offering_id",
                            name="uq_group_offering"),
    )

    # ── tenant_minimum_charges ─────────────────────────────────────
    op.create_table(
        "tenant_minimum_charges",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("minimum_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── consumption_records ────────────────────────────────────────
    op.create_table(
        "consumption_records",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("provider_sku_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("provider_skus.id"), nullable=True),
        sa.Column("activity_definition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("activity_definitions.id"), nullable=True),
        sa.Column("service_offering_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_offerings.id"), nullable=True),
        sa.Column("quantity", sa.Numeric(14, 4), nullable=False),
        sa.Column("period_start", sa.Date, nullable=False),
        sa.Column("period_end", sa.Date, nullable=False),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ══════════════════════════════════════════════════════════════════
    # 2. Column additions on existing tables
    # ══════════════════════════════════════════════════════════════════

    # ── service_offerings: status, cloned_from_id, base_fee, fee_period ──
    op.add_column(
        "service_offerings",
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
    )
    op.add_column(
        "service_offerings",
        sa.Column("cloned_from_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("service_offerings.id"), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("base_fee", sa.Numeric(12, 4), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("fee_period", sa.String(20), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("minimum_amount", sa.Numeric(12, 4), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("minimum_currency", sa.String(3), server_default="EUR", nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("minimum_period", sa.String(20), nullable=True),
    )
    # Backfill: mark existing offerings as published
    op.execute("UPDATE service_offerings SET status = 'published' WHERE status = 'draft'")

    # ── activity_definitions: step_id ──────────────────────────────
    op.add_column(
        "activity_definitions",
        sa.Column("step_id", sa.String(100), nullable=True),
    )

    # ── price_list_items: provider_sku_id, activity_definition_id, markup_percent ──
    op.add_column(
        "price_list_items",
        sa.Column("provider_sku_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("provider_skus.id"), nullable=True),
    )
    op.add_column(
        "price_list_items",
        sa.Column("activity_definition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("activity_definitions.id"), nullable=True),
    )
    op.add_column(
        "price_list_items",
        sa.Column("markup_percent", sa.Numeric(8, 4), nullable=True),
    )
    op.create_index("ix_price_list_items_provider_sku_id",
                    "price_list_items", ["provider_sku_id"])
    op.create_index("ix_price_list_items_activity_def_id",
                    "price_list_items", ["activity_definition_id"])
    # Make service_offering_id nullable
    op.alter_column("price_list_items", "service_offering_id", nullable=True)
    # CHECK: exactly one of (service_offering_id, provider_sku_id, activity_definition_id) non-null
    op.execute("""
        ALTER TABLE price_list_items
        ADD CONSTRAINT ck_price_list_item_exactly_one
        CHECK (
            (service_offering_id IS NOT NULL)::int +
            (provider_sku_id IS NOT NULL)::int +
            (activity_definition_id IS NOT NULL)::int = 1
        )
    """)

    # ── tenant_price_overrides: provider_sku_id, activity_definition_id ──
    op.add_column(
        "tenant_price_overrides",
        sa.Column("provider_sku_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("provider_skus.id"), nullable=True),
    )
    op.add_column(
        "tenant_price_overrides",
        sa.Column("activity_definition_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("activity_definitions.id"), nullable=True),
    )
    # Make service_offering_id nullable
    op.alter_column("tenant_price_overrides", "service_offering_id", nullable=True)
    # CHECK: exactly one of (service_offering_id, provider_sku_id, activity_definition_id) non-null
    op.execute("""
        ALTER TABLE tenant_price_overrides
        ADD CONSTRAINT ck_price_override_exactly_one
        CHECK (
            (service_offering_id IS NOT NULL)::int +
            (provider_sku_id IS NOT NULL)::int +
            (activity_definition_id IS NOT NULL)::int = 1
        )
    """)

    # ══════════════════════════════════════════════════════════════════
    # 3. Permissions seeding
    # ══════════════════════════════════════════════════════════════════
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'catalog', 'catalog',  'read',   NULL, 'View service catalogs',         true, now(), now()),
            (gen_random_uuid(), 'catalog', 'catalog',  'manage', NULL, 'Manage service catalogs',       true, now(), now()),
            (gen_random_uuid(), 'catalog', 'sku',      'read',   NULL, 'View provider SKUs',            true, now(), now()),
            (gen_random_uuid(), 'catalog', 'sku',      'manage', NULL, 'Manage provider SKUs',          true, now(), now()),
            (gen_random_uuid(), 'catalog', 'group',    'read',   NULL, 'View service groups',           true, now(), now()),
            (gen_random_uuid(), 'catalog', 'group',    'manage', NULL, 'Manage service groups',         true, now(), now()),
            (gen_random_uuid(), 'catalog', 'minimum',  'read',   NULL, 'View tenant minimum charges',   true, now(), now()),
            (gen_random_uuid(), 'catalog', 'minimum',  'manage', NULL, 'Manage tenant minimum charges', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING;
    """)

    # Assign read permissions to ALL roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin', 'User', 'Read Only')
          AND p.domain = 'catalog'
          AND p.action = 'read'
        ON CONFLICT DO NOTHING;
    """)

    # Assign manage permissions to Tenant Admin + Provider Admin only
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'catalog'
          AND p.action = 'manage'
        ON CONFLICT DO NOTHING;
    """)

    # ══════════════════════════════════════════════════════════════════
    # 4. Demo data cleanup
    # ══════════════════════════════════════════════════════════════════
    op.execute("DELETE FROM price_list_items;")
    op.execute("DELETE FROM tenant_price_list_pins;")
    op.execute("DELETE FROM tenant_price_overrides;")
    op.execute("DELETE FROM price_lists;")
    op.execute("DELETE FROM service_process_assignments;")
    op.execute("DELETE FROM service_offering_ci_classes;")
    op.execute("DELETE FROM service_offering_regions;")
    op.execute("DELETE FROM service_offerings;")

    # ══════════════════════════════════════════════════════════════════
    # 5. Demo data seeding — realistic MSP catalog
    # ══════════════════════════════════════════════════════════════════

    # ── 5a. Service Offerings (6 items) ──────────────────────────────
    op.execute("""
        WITH root AS (
            SELECT id FROM tenants WHERE slug = 'root' LIMIT 1
        )
        INSERT INTO service_offerings
            (id, tenant_id, name, description, category, measuring_unit,
             service_type, status, base_fee, fee_period,
             minimum_amount, minimum_currency, minimum_period,
             is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), (SELECT id FROM root),
             'Virtual Machine Hosting',
             'Fully managed virtual machine with monitoring, patching, and backup included.',
             'Compute', 'month', 'resource', 'published', 50.0000, 'monthly',
             200.0000, 'EUR', 'monthly',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM root),
             'Managed Database',
             'Managed relational database service with automated backups and HA failover.',
             'Database', 'month', 'resource', 'published', 100.0000, 'monthly',
             300.0000, 'EUR', 'monthly',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM root),
             'Block Storage',
             'High-performance block storage volumes for VMs and databases.',
             'Storage', 'gb', 'resource', 'published', NULL, NULL,
             10.0000, 'EUR', 'monthly',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM root),
             'L2 Support',
             'Level 2 technical support for incident resolution and troubleshooting.',
             'Support', 'hour', 'labor', 'published', NULL, NULL,
             500.0000, 'EUR', 'monthly',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM root),
             'Architecture Consulting',
             'Senior architecture consulting for cloud migration and infrastructure design.',
             'Professional Services', 'day', 'labor', 'draft', NULL, NULL,
             NULL, NULL, NULL,
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM root),
             'Network Monitoring',
             '24/7 network monitoring with alerting and monthly reporting.',
             'Network', 'month', 'resource', 'published', 25.0000, 'monthly',
             25.0000, 'EUR', 'monthly',
             true, NOW(), NOW());
    """)

    # ── 5b. Provider SKUs (8 Proxmox SKUs) ───────────────────────────
    op.execute("""
        WITH prx AS (
            SELECT id FROM semantic_providers WHERE name = 'proxmox' LIMIT 1
        )
        INSERT INTO provider_skus
            (id, provider_id, external_sku_id, name, display_name,
             category, unit_cost, cost_currency, measuring_unit,
             is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-vm-small', 'Small VM (2 vCPU, 4GB RAM)', 'Small VM',
             'Compute', 15.0000, 'EUR', 'month',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-vm-medium', 'Medium VM (4 vCPU, 8GB RAM)', 'Medium VM',
             'Compute', 30.0000, 'EUR', 'month',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-vm-large', 'Large VM (8 vCPU, 16GB RAM)', 'Large VM',
             'Compute', 55.0000, 'EUR', 'month',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-storage-ssd', 'SSD Block Storage', 'SSD Storage',
             'Storage', 0.1000, 'EUR', 'gb',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-storage-hdd', 'HDD Block Storage', 'HDD Storage',
             'Storage', 0.0300, 'EUR', 'gb',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-db-small', 'Small Database Instance', 'Small DB',
             'Database', 25.0000, 'EUR', 'month',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-db-medium', 'Medium Database Instance', 'Medium DB',
             'Database', 50.0000, 'EUR', 'month',
             true, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM prx),
             'proxmox-net-monitor', 'Network Monitoring Agent', 'Net Monitor',
             'Network', 5.0000, 'EUR', 'month',
             true, NOW(), NOW());
    """)

    # ── 5c. Service Offering SKU links (composition) ─────────────────
    op.execute("""
        INSERT INTO service_offering_skus
            (id, service_offering_id, provider_sku_id,
             default_quantity, is_required, sort_order, created_at, updated_at)
        VALUES
            -- VM Hosting → proxmox-vm-medium (qty 1) + proxmox-storage-ssd (qty 50)
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Virtual Machine Hosting' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-vm-medium' LIMIT 1),
             1, true, 0, NOW(), NOW()),
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Virtual Machine Hosting' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-storage-ssd' LIMIT 1),
             50, true, 1, NOW(), NOW()),
            -- Managed Database → proxmox-db-medium (qty 1) + proxmox-storage-ssd (qty 100)
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Managed Database' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-db-medium' LIMIT 1),
             1, true, 0, NOW(), NOW()),
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Managed Database' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-storage-ssd' LIMIT 1),
             100, true, 1, NOW(), NOW()),
            -- Block Storage → proxmox-storage-ssd (qty 1)
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Block Storage' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-storage-ssd' LIMIT 1),
             1, true, 0, NOW(), NOW()),
            -- Network Monitoring → proxmox-net-monitor (qty 1)
            (gen_random_uuid(),
             (SELECT id FROM service_offerings WHERE name = 'Network Monitoring' LIMIT 1),
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-net-monitor' LIMIT 1),
             1, true, 0, NOW(), NOW());
    """)

    # ── 5d. Service Groups (2 bundles) ───────────────────────────────
    op.execute("""
        INSERT INTO service_groups
            (id, tenant_id, name, display_name, description,
             is_active, created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL,
             'Standard Infrastructure Bundle', 'Standard Infra',
             'Core infrastructure bundle: VM hosting, block storage, and network monitoring.',
             true, NOW(), NOW()),
            (gen_random_uuid(), NULL,
             'Database Essentials', 'DB Essentials',
             'Database bundle: managed database with block storage.',
             true, NOW(), NOW());
    """)

    # ── 5e. Service Group Items ──────────────────────────────────────
    op.execute("""
        INSERT INTO service_group_items
            (id, group_id, service_offering_id, is_required, sort_order,
             created_at, updated_at)
        VALUES
            -- Standard Infrastructure Bundle: VM Hosting + Block Storage + Network Monitoring
            (gen_random_uuid(),
             (SELECT id FROM service_groups WHERE name = 'Standard Infrastructure Bundle' LIMIT 1),
             (SELECT id FROM service_offerings WHERE name = 'Virtual Machine Hosting' LIMIT 1),
             true, 0, NOW(), NOW()),
            (gen_random_uuid(),
             (SELECT id FROM service_groups WHERE name = 'Standard Infrastructure Bundle' LIMIT 1),
             (SELECT id FROM service_offerings WHERE name = 'Block Storage' LIMIT 1),
             true, 1, NOW(), NOW()),
            (gen_random_uuid(),
             (SELECT id FROM service_groups WHERE name = 'Standard Infrastructure Bundle' LIMIT 1),
             (SELECT id FROM service_offerings WHERE name = 'Network Monitoring' LIMIT 1),
             true, 2, NOW(), NOW()),
            -- Database Essentials: Managed Database + Block Storage
            (gen_random_uuid(),
             (SELECT id FROM service_groups WHERE name = 'Database Essentials' LIMIT 1),
             (SELECT id FROM service_offerings WHERE name = 'Managed Database' LIMIT 1),
             true, 0, NOW(), NOW()),
            (gen_random_uuid(),
             (SELECT id FROM service_groups WHERE name = 'Database Essentials' LIMIT 1),
             (SELECT id FROM service_offerings WHERE name = 'Block Storage' LIMIT 1),
             true, 1, NOW(), NOW());
    """)

    # ── 5f. Service Catalog (1 versioned catalog) ────────────────────
    op.execute("""
        INSERT INTO service_catalogs
            (id, tenant_id, name, description,
             version_major, version_minor, status,
             effective_from,
             created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL,
             'Provider Standard Catalog',
             'Standard service catalog for managed IT infrastructure and labor services.',
             1, 0, 'published',
             '2026-01-01',
             NOW(), NOW());
    """)

    # ── 5g. Service Catalog Items (6 offerings + 2 groups = 8 items) ─
    op.execute("""
        WITH cat AS (
            SELECT id FROM service_catalogs
            WHERE name = 'Provider Standard Catalog' LIMIT 1
        )
        INSERT INTO service_catalog_items
            (id, catalog_id, service_offering_id, service_group_id,
             sort_order, created_at, updated_at)
        VALUES
            -- Individual offerings
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'Virtual Machine Hosting' LIMIT 1),
             NULL, 0, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'Managed Database' LIMIT 1),
             NULL, 1, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'Block Storage' LIMIT 1),
             NULL, 2, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'L2 Support' LIMIT 1),
             NULL, 3, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'Architecture Consulting' LIMIT 1),
             NULL, 4, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             (SELECT id FROM service_offerings WHERE name = 'Network Monitoring' LIMIT 1),
             NULL, 5, NOW(), NOW()),
            -- Groups
            (gen_random_uuid(), (SELECT id FROM cat),
             NULL,
             (SELECT id FROM service_groups WHERE name = 'Standard Infrastructure Bundle' LIMIT 1),
             6, NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM cat),
             NULL,
             (SELECT id FROM service_groups WHERE name = 'Database Essentials' LIMIT 1),
             7, NOW(), NOW());
    """)

    # ── 5h. Price List (1 list) ──────────────────────────────────────
    op.execute("""
        INSERT INTO price_lists
            (id, tenant_id, name, is_default, effective_from,
             version_major, version_minor, status,
             created_at, updated_at)
        VALUES
            (gen_random_uuid(), NULL,
             'Standard Price List 2026', true, '2026-01-01',
             1, 0, 'published',
             NOW(), NOW());
    """)

    # ── 5i. Price List Items (6 offering-level + 4 SKU-level) ────────
    op.execute("""
        WITH pl AS (
            SELECT id FROM price_lists
            WHERE name = 'Standard Price List 2026' LIMIT 1
        )
        INSERT INTO price_list_items
            (id, price_list_id, service_offering_id, provider_sku_id,
             price_per_unit, currency, markup_percent,
             created_at, updated_at)
        VALUES
            -- Offering-level prices
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'Virtual Machine Hosting' LIMIT 1),
             NULL,
             75.0000, 'EUR', NULL,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'Managed Database' LIMIT 1),
             NULL,
             150.0000, 'EUR', NULL,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'Block Storage' LIMIT 1),
             NULL,
             0.1500, 'EUR', NULL,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'L2 Support' LIMIT 1),
             NULL,
             95.0000, 'EUR', NULL,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'Architecture Consulting' LIMIT 1),
             NULL,
             1200.0000, 'EUR', NULL,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             (SELECT id FROM service_offerings WHERE name = 'Network Monitoring' LIMIT 1),
             NULL,
             30.0000, 'EUR', NULL,
             NOW(), NOW()),
            -- SKU-level prices
            (gen_random_uuid(), (SELECT id FROM pl),
             NULL,
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-vm-small' LIMIT 1),
             20.0000, 'EUR', 33.0000,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             NULL,
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-vm-medium' LIMIT 1),
             40.0000, 'EUR', 33.0000,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             NULL,
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-vm-large' LIMIT 1),
             75.0000, 'EUR', 36.0000,
             NOW(), NOW()),
            (gen_random_uuid(), (SELECT id FROM pl),
             NULL,
             (SELECT id FROM provider_skus WHERE external_sku_id = 'proxmox-storage-ssd' LIMIT 1),
             0.1500, 'EUR', 50.0000,
             NOW(), NOW());
    """)

    # ── 5j. Tenant Minimum Charges (2 items for root tenant) ─────────
    op.execute("""
        WITH root AS (
            SELECT id FROM tenants WHERE slug = 'root' LIMIT 1
        )
        INSERT INTO tenant_minimum_charges
            (id, tenant_id, category, minimum_amount, currency,
             period, effective_from,
             created_at, updated_at)
        VALUES
            -- Global minimum: 500 EUR/month
            (gen_random_uuid(), (SELECT id FROM root),
             NULL, 500.0000, 'EUR',
             'monthly', '2026-01-01',
             NOW(), NOW()),
            -- Compute category minimum: 200 EUR/month
            (gen_random_uuid(), (SELECT id FROM root),
             'Compute', 200.0000, 'EUR',
             'monthly', '2026-01-01',
             NOW(), NOW());
    """)


def downgrade() -> None:
    # ══════════════════════════════════════════════════════════════════
    # 1. Remove permissions
    # ══════════════════════════════════════════════════════════════════
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain = 'catalog'
        );
    """)
    op.execute("DELETE FROM permissions WHERE domain = 'catalog';")

    # ══════════════════════════════════════════════════════════════════
    # 2. Drop check constraints on existing tables
    # ══════════════════════════════════════════════════════════════════
    op.execute("ALTER TABLE tenant_price_overrides DROP CONSTRAINT IF EXISTS ck_price_override_exactly_one;")
    op.execute("ALTER TABLE price_list_items DROP CONSTRAINT IF EXISTS ck_price_list_item_exactly_one;")
    op.execute("ALTER TABLE service_catalog_items DROP CONSTRAINT IF EXISTS ck_catalog_item_exactly_one;")

    # ══════════════════════════════════════════════════════════════════
    # 3. Revert column additions on existing tables
    # ══════════════════════════════════════════════════════════════════

    # ── tenant_price_overrides ─────────────────────────────────────
    op.alter_column("tenant_price_overrides", "service_offering_id", nullable=False)
    op.drop_column("tenant_price_overrides", "activity_definition_id")
    op.drop_column("tenant_price_overrides", "provider_sku_id")

    # ── price_list_items ───────────────────────────────────────────
    op.drop_index("ix_price_list_items_activity_def_id", table_name="price_list_items")
    op.drop_index("ix_price_list_items_provider_sku_id", table_name="price_list_items")
    op.alter_column("price_list_items", "service_offering_id", nullable=False)
    op.drop_column("price_list_items", "markup_percent")
    op.drop_column("price_list_items", "activity_definition_id")
    op.drop_column("price_list_items", "provider_sku_id")

    # ── activity_definitions ───────────────────────────────────────
    op.drop_column("activity_definitions", "step_id")

    # ── service_offerings ──────────────────────────────────────────
    op.drop_column("service_offerings", "minimum_period")
    op.drop_column("service_offerings", "minimum_currency")
    op.drop_column("service_offerings", "minimum_amount")
    op.drop_column("service_offerings", "fee_period")
    op.drop_column("service_offerings", "base_fee")
    op.drop_column("service_offerings", "cloned_from_id")
    op.drop_column("service_offerings", "status")

    # ══════════════════════════════════════════════════════════════════
    # 4. Drop new tables in reverse dependency order
    # ══════════════════════════════════════════════════════════════════
    op.drop_table("consumption_records")
    op.drop_table("tenant_minimum_charges")
    op.drop_table("service_group_items")
    op.drop_table("service_offering_skus")
    op.drop_table("provider_skus")
    op.drop_table("tenant_catalog_pins")
    op.drop_table("service_catalog_items")
    op.drop_table("service_catalogs")
    op.drop_table("service_groups")
