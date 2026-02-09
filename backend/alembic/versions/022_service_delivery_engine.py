"""Service delivery engine: delivery regions, staff profiles, internal rate cards,
activity templates, service estimations, price list templates, region acceptance
compliance. Extends service_offerings, price_list_items, tenant_price_overrides
with delivery region and coverage model support. Seeds system regions, staff
profiles, acceptance templates, and delivery permissions.

Revision ID: 022
Revises: 021
Create Date: 2026-02-09
"""

import uuid

import sqlalchemy as sa

from alembic import op

revision: str = "022"
down_revision: str | None = "021"
branch_labels: str | list[str] | None = None
depends_on: str | list[str] | None = None

# ── Permission definitions ────────────────────────────────────────────

DELIVERY_PERMISSIONS = [
    ("catalog:region:read", "View delivery regions"),
    ("catalog:region:manage", "Manage delivery regions"),
    ("catalog:staff:read", "View staff profiles"),
    ("catalog:staff:manage", "Manage staff profiles"),
    ("catalog:activity:read", "View activity templates"),
    ("catalog:activity:manage", "Manage activity templates"),
    ("catalog:estimation:read", "View service estimations"),
    ("catalog:estimation:manage", "Manage service estimations"),
    ("catalog:estimation:approve", "Approve service estimations"),
    ("catalog:profitability:read", "View profitability data"),
    ("catalog:compliance:read", "View compliance data"),
    ("catalog:compliance:manage", "Manage compliance settings"),
    ("catalog:orgunit:read", "View organizational units"),
    ("catalog:orgunit:manage", "Manage organizational units"),
    ("catalog:process:read", "View processes"),
    ("catalog:process:manage", "Manage processes"),
]

# Read permissions assigned to all roles
READ_PERMISSIONS = [
    "catalog:region:read",
    "catalog:staff:read",
    "catalog:activity:read",
    "catalog:estimation:read",
    "catalog:profitability:read",
    "catalog:compliance:read",
    "catalog:orgunit:read",
    "catalog:process:read",
]

# Manage/approve permissions assigned to Tenant Admin and Provider Admin
MANAGE_PERMISSIONS = [
    "catalog:region:manage",
    "catalog:staff:manage",
    "catalog:activity:manage",
    "catalog:estimation:manage",
    "catalog:estimation:approve",
    "catalog:compliance:manage",
    "catalog:orgunit:manage",
    "catalog:process:manage",
]

# ── Seed data: delivery regions ───────────────────────────────────────

# Top-level region UUIDs (pre-generated for parent FK references)
APAC_ID = str(uuid.uuid4())
EMEA_ID = str(uuid.uuid4())
AMER_ID = str(uuid.uuid4())

SYSTEM_REGIONS = [
    # Top-level regions
    {
        "id": APAC_ID,
        "parent_region_id": None,
        "name": "APAC",
        "display_name": "Asia-Pacific",
        "code": "APAC",
        "timezone": None,
        "country_code": None,
        "sort_order": 1,
    },
    {
        "id": EMEA_ID,
        "parent_region_id": None,
        "name": "EMEA",
        "display_name": "Europe, Middle East & Africa",
        "code": "EMEA",
        "timezone": None,
        "country_code": None,
        "sort_order": 2,
    },
    {
        "id": AMER_ID,
        "parent_region_id": None,
        "name": "AMER",
        "display_name": "Americas",
        "code": "AMER",
        "timezone": None,
        "country_code": None,
        "sort_order": 3,
    },
    # APAC children
    {
        "id": str(uuid.uuid4()),
        "parent_region_id": APAC_ID,
        "name": "Manila",
        "display_name": "Manila",
        "code": "APAC-MNL",
        "timezone": "Asia/Manila",
        "country_code": "PH",
        "sort_order": 1,
    },
    {
        "id": str(uuid.uuid4()),
        "parent_region_id": APAC_ID,
        "name": "Bangalore",
        "display_name": "Bangalore",
        "code": "APAC-BLR",
        "timezone": "Asia/Kolkata",
        "country_code": "IN",
        "sort_order": 2,
    },
    # EMEA children
    {
        "id": str(uuid.uuid4()),
        "parent_region_id": EMEA_ID,
        "name": "Frankfurt",
        "display_name": "Frankfurt",
        "code": "EMEA-FRA",
        "timezone": "Europe/Berlin",
        "country_code": "DE",
        "sort_order": 1,
    },
    # AMER children
    {
        "id": str(uuid.uuid4()),
        "parent_region_id": AMER_ID,
        "name": "São Paulo",
        "display_name": "São Paulo",
        "code": "AMER-GRU",
        "timezone": "America/Sao_Paulo",
        "country_code": "BR",
        "sort_order": 1,
    },
    {
        "id": str(uuid.uuid4()),
        "parent_region_id": AMER_ID,
        "name": "New York",
        "display_name": "New York",
        "code": "AMER-NYC",
        "timezone": "America/New_York",
        "country_code": "US",
        "sort_order": 2,
    },
]

# ── Seed data: staff profiles ─────────────────────────────────────────

SYSTEM_STAFF_PROFILES = [
    {"name": "junior_engineer", "display_name": "Junior Engineer", "sort_order": 1},
    {"name": "engineer", "display_name": "Engineer", "sort_order": 2},
    {"name": "senior_engineer", "display_name": "Senior Engineer", "sort_order": 3},
    {"name": "consultant", "display_name": "Consultant", "sort_order": 4},
    {"name": "senior_consultant", "display_name": "Senior Consultant", "sort_order": 5},
    {"name": "architect", "display_name": "Architect", "sort_order": 6},
]

# ── Seed data: acceptance templates ───────────────────────────────────

SYSTEM_ACCEPTANCE_TEMPLATES = [
    {
        "name": "APAC Client Default",
        "description": "Default region acceptance template for APAC-based clients",
    },
    {
        "name": "EU Sovereign",
        "description": "Region acceptance template enforcing EU data sovereignty requirements",
    },
    {
        "name": "Global Delivery",
        "description": "Region acceptance template allowing delivery from all regions",
    },
]


def upgrade() -> None:
    # ── 1. Delivery regions ────────────────────────────────────────────
    op.create_table(
        "delivery_regions",
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
        sa.Column(
            "parent_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("timezone", sa.String(50), nullable=True),
        sa.Column("country_code", sa.String(2), nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
    op.create_index("ix_delivery_regions_tenant_id", "delivery_regions", ["tenant_id"])
    op.create_index(
        "ix_delivery_regions_parent_id", "delivery_regions", ["parent_region_id"]
    )

    # ── 2. Region acceptance templates ─────────────────────────────────
    op.create_table(
        "region_acceptance_templates",
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
        sa.Column("description", sa.Text, nullable=True),
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
    op.create_index(
        "ix_region_acceptance_templates_tenant_id",
        "region_acceptance_templates",
        ["tenant_id"],
    )

    # ── 3. Region acceptance template rules ────────────────────────────
    op.create_table(
        "region_acceptance_template_rules",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("region_acceptance_templates.id"),
            nullable=False,
        ),
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=False,
        ),
        sa.Column("acceptance_type", sa.String(20), nullable=False),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_ra_template_rules_template_id",
        "region_acceptance_template_rules",
        ["template_id"],
    )
    op.create_index(
        "ix_ra_template_rules_region_id",
        "region_acceptance_template_rules",
        ["delivery_region_id"],
    )

    # ── 4. Tenant region acceptances ───────────────────────────────────
    op.create_table(
        "tenant_region_acceptances",
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
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=False,
        ),
        sa.Column("acceptance_type", sa.String(20), nullable=False),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "is_compliance_enforced",
            sa.Boolean,
            nullable=False,
            server_default="false",
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
    op.create_index(
        "ix_tenant_region_acceptances_tenant_id",
        "tenant_region_acceptances",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_region_acceptances_region_id",
        "tenant_region_acceptances",
        ["delivery_region_id"],
    )

    # ── 5. Tenant region template assignments ──────────────────────────
    op.create_table(
        "tenant_region_template_assignments",
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
            "template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("region_acceptance_templates.id"),
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
    )
    op.create_index(
        "ix_tenant_region_tmpl_assign_tenant_id",
        "tenant_region_template_assignments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_tenant_region_tmpl_assign_tmpl_id",
        "tenant_region_template_assignments",
        ["template_id"],
    )

    # ── 6a. Organizational units ──────────────────────────────────────
    op.create_table(
        "organizational_units",
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
        sa.Column(
            "parent_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizational_units.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("cost_center", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
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
        "ix_organizational_units_tenant_id", "organizational_units", ["tenant_id"]
    )
    op.create_index(
        "ix_organizational_units_parent_id", "organizational_units", ["parent_id"]
    )

    # ── 6b. Staff profiles ─────────────────────────────────────────────
    op.create_table(
        "staff_profiles",
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
        sa.Column(
            "org_unit_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizational_units.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default="false"),
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
    op.create_index("ix_staff_profiles_tenant_id", "staff_profiles", ["tenant_id"])
    op.create_index("ix_staff_profiles_org_unit_id", "staff_profiles", ["org_unit_id"])

    # ── 7. Internal rate cards ─────────────────────────────────────────
    op.create_table(
        "internal_rate_cards",
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
            "staff_profile_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("staff_profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=False,
        ),
        sa.Column("hourly_cost", sa.Numeric(12, 4), nullable=False),
        sa.Column("hourly_sell_rate", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="EUR"),
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
        "ix_internal_rate_cards_tenant_id", "internal_rate_cards", ["tenant_id"]
    )
    op.create_index(
        "ix_internal_rate_cards_staff_id", "internal_rate_cards", ["staff_profile_id"]
    )
    op.create_index(
        "ix_internal_rate_cards_region_id", "internal_rate_cards", ["delivery_region_id"]
    )

    # ── 8. Activity templates ──────────────────────────────────────────
    op.create_table(
        "activity_templates",
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
    op.create_index(
        "ix_activity_templates_tenant_id", "activity_templates", ["tenant_id"]
    )

    # ── 9. Activity definitions ────────────────────────────────────────
    op.create_table(
        "activity_definitions",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_templates.id"),
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "staff_profile_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("staff_profiles.id"),
            nullable=False,
        ),
        sa.Column("estimated_hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_optional", sa.Boolean, nullable=False, server_default="false"),
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
        "ix_activity_definitions_template_id",
        "activity_definitions",
        ["template_id"],
    )
    op.create_index(
        "ix_activity_definitions_staff_id",
        "activity_definitions",
        ["staff_profile_id"],
    )

    # ── 10a. Service processes ────────────────────────────────────────
    op.create_table(
        "service_processes",
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
        sa.Column("version", sa.Integer, nullable=False, server_default="1"),
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
        "ix_service_processes_tenant_id",
        "service_processes",
        ["tenant_id"],
    )

    # ── 10b. Process activity links ───────────────────────────────────
    op.create_table(
        "process_activity_links",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "process_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_processes.id"),
            nullable=False,
        ),
        sa.Column(
            "activity_template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_templates.id"),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean, nullable=False, server_default="true"),
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
        "ix_process_activity_links_process_id",
        "process_activity_links",
        ["process_id"],
    )
    op.create_index(
        "ix_process_activity_links_template_id",
        "process_activity_links",
        ["activity_template_id"],
    )

    # ── 10c. Service process assignments ──────────────────────────────
    op.create_table(
        "service_process_assignments",
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
        sa.Column(
            "process_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_processes.id"),
            nullable=False,
        ),
        sa.Column("coverage_model", sa.String(20), nullable=True),
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
    op.create_index(
        "ix_svc_process_assign_tenant_id",
        "service_process_assignments",
        ["tenant_id"],
    )
    op.create_index(
        "ix_svc_process_assign_offering_id",
        "service_process_assignments",
        ["service_offering_id"],
    )
    op.create_index(
        "ix_svc_process_assign_process_id",
        "service_process_assignments",
        ["process_id"],
    )

    # ── 11. Service estimations ────────────────────────────────────────
    op.create_table(
        "service_estimations",
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
            "client_tenant_id",
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
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
        sa.Column("coverage_model", sa.String(20), nullable=True),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="draft"
        ),
        sa.Column(
            "quantity",
            sa.Numeric(12, 4),
            nullable=False,
            server_default="1",
        ),
        sa.Column(
            "sell_price_per_unit",
            sa.Numeric(12, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "sell_currency", sa.String(3), nullable=False, server_default="EUR"
        ),
        sa.Column("total_estimated_cost", sa.Numeric(14, 4), nullable=True),
        sa.Column("total_sell_price", sa.Numeric(14, 4), nullable=True),
        sa.Column("margin_amount", sa.Numeric(14, 4), nullable=True),
        sa.Column("margin_percent", sa.Numeric(8, 4), nullable=True),
        sa.Column(
            "approved_by",
            sa.dialects.postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "approved_at", sa.DateTime(timezone=True), nullable=True
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
    op.create_index(
        "ix_service_estimations_tenant_id", "service_estimations", ["tenant_id"]
    )
    op.create_index(
        "ix_service_estimations_client_id",
        "service_estimations",
        ["client_tenant_id"],
    )
    op.create_index(
        "ix_service_estimations_offering_id",
        "service_estimations",
        ["service_offering_id"],
    )
    op.create_index(
        "ix_service_estimations_region_id",
        "service_estimations",
        ["delivery_region_id"],
    )
    op.create_index(
        "ix_service_estimations_status", "service_estimations", ["status"]
    )

    # ── 12. Estimation line items ──────────────────────────────────────
    op.create_table(
        "estimation_line_items",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "estimation_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_estimations.id"),
            nullable=False,
        ),
        sa.Column(
            "activity_definition_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_definitions.id"),
            nullable=True,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "staff_profile_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("staff_profiles.id"),
            nullable=False,
        ),
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=False,
        ),
        sa.Column("estimated_hours", sa.Numeric(8, 2), nullable=False),
        sa.Column("hourly_rate", sa.Numeric(12, 4), nullable=False),
        sa.Column(
            "rate_currency", sa.String(3), nullable=False, server_default="EUR"
        ),
        sa.Column("line_cost", sa.Numeric(14, 4), nullable=False),
        sa.Column("actual_hours", sa.Numeric(8, 2), nullable=True),
        sa.Column("actual_cost", sa.Numeric(14, 4), nullable=True),
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
        "ix_estimation_line_items_estimation_id",
        "estimation_line_items",
        ["estimation_id"],
    )
    op.create_index(
        "ix_estimation_line_items_staff_id",
        "estimation_line_items",
        ["staff_profile_id"],
    )
    op.create_index(
        "ix_estimation_line_items_region_id",
        "estimation_line_items",
        ["delivery_region_id"],
    )
    op.add_column(
        "estimation_line_items",
        sa.Column(
            "rate_card_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internal_rate_cards.id"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_estimation_line_items_rate_card_id",
        "estimation_line_items",
        ["rate_card_id"],
    )

    # ── 13. Price list templates ───────────────────────────────────────
    op.create_table(
        "price_list_templates",
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
            "region_acceptance_template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("region_acceptance_templates.id"),
            nullable=True,
        ),
        sa.Column(
            "status", sa.String(20), nullable=False, server_default="draft"
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
    op.create_index(
        "ix_price_list_templates_tenant_id",
        "price_list_templates",
        ["tenant_id"],
    )

    # ── 14. Price list template items ──────────────────────────────────
    op.create_table(
        "price_list_template_items",
        sa.Column(
            "id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "template_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("price_list_templates.id"),
            nullable=False,
        ),
        sa.Column(
            "service_offering_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("service_offerings.id"),
            nullable=False,
        ),
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
        sa.Column("coverage_model", sa.String(20), nullable=True),
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
        "ix_pl_template_items_template_id",
        "price_list_template_items",
        ["template_id"],
    )
    op.create_index(
        "ix_pl_template_items_offering_id",
        "price_list_template_items",
        ["service_offering_id"],
    )

    # ── 15. Extend existing tables ─────────────────────────────────────

    # service_offerings: add service_type, operating_model, default_coverage_model
    op.add_column(
        "service_offerings",
        sa.Column(
            "service_type",
            sa.String(20),
            nullable=False,
            server_default="resource",
        ),
    )
    op.add_column(
        "service_offerings",
        sa.Column("operating_model", sa.String(20), nullable=True),
    )
    op.add_column(
        "service_offerings",
        sa.Column("default_coverage_model", sa.String(20), nullable=True),
    )

    # price_list_items: add delivery_region_id, coverage_model
    op.add_column(
        "price_list_items",
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "price_list_items",
        sa.Column("coverage_model", sa.String(20), nullable=True),
    )

    # tenant_price_overrides: add delivery_region_id, coverage_model
    op.add_column(
        "tenant_price_overrides",
        sa.Column(
            "delivery_region_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "tenant_price_overrides",
        sa.Column("coverage_model", sa.String(20), nullable=True),
    )

    # ── 16. Seed data ─────────────────────────────────────────────────
    _seed_delivery_regions()
    _seed_organizational_units()
    _seed_staff_profiles()
    _seed_acceptance_templates()
    _seed_permissions()


def _seed_delivery_regions() -> None:
    """Seed the 8 system delivery regions (3 top-level + 5 children)."""
    conn = op.get_bind()
    for region in SYSTEM_REGIONS:
        conn.execute(
            sa.text(
                """
                INSERT INTO delivery_regions
                    (id, tenant_id, parent_region_id, name, display_name, code,
                     timezone, country_code, is_system, is_active, sort_order,
                     created_at, updated_at)
                VALUES (:id, NULL, :parent_region_id, :name, :display_name, :code,
                        :timezone, :country_code, true, true, :sort_order,
                        now(), now())
                ON CONFLICT (code) DO NOTHING
                """
            ),
            region,
        )


def _seed_organizational_units() -> None:
    """Seed the 3 system organizational units."""
    conn = op.get_bind()
    for ou in [
        {"name": "engineering", "display_name": "Engineering", "cost_center": "CC-ENG", "sort_order": 1},
        {"name": "operations", "display_name": "Operations", "cost_center": "CC-OPS", "sort_order": 2},
        {"name": "management", "display_name": "Management", "cost_center": "CC-MGT", "sort_order": 3},
    ]:
        conn.execute(
            sa.text(
                """
                INSERT INTO organizational_units
                    (id, tenant_id, parent_id, name, display_name, cost_center,
                     is_active, sort_order, created_at, updated_at)
                VALUES (gen_random_uuid(), NULL, NULL, :name, :display_name,
                        :cost_center, true, :sort_order, now(), now())
                """
            ),
            ou,
        )


def _seed_staff_profiles() -> None:
    """Seed the 6 system staff profiles."""
    conn = op.get_bind()
    for profile in SYSTEM_STAFF_PROFILES:
        conn.execute(
            sa.text(
                """
                INSERT INTO staff_profiles
                    (id, tenant_id, name, display_name, is_system, sort_order,
                     created_at, updated_at)
                VALUES (gen_random_uuid(), NULL, :name, :display_name, true,
                        :sort_order, now(), now())
                """
            ),
            profile,
        )


def _seed_acceptance_templates() -> None:
    """Seed the 3 system region acceptance templates."""
    conn = op.get_bind()
    for template in SYSTEM_ACCEPTANCE_TEMPLATES:
        conn.execute(
            sa.text(
                """
                INSERT INTO region_acceptance_templates
                    (id, tenant_id, name, description, is_system,
                     created_at, updated_at)
                VALUES (gen_random_uuid(), NULL, :name, :description, true,
                        now(), now())
                """
            ),
            template,
        )


def _seed_permissions() -> None:
    """Seed delivery engine permissions and assign to roles."""
    conn = op.get_bind()

    # Insert all permissions
    for key, description in DELIVERY_PERMISSIONS:
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

    # Assign manage/approve permissions to Tenant Admin and Provider Admin
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

    # ── Remove delivery permissions from role_permissions ──────────────
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE domain = 'catalog'
                  AND resource IN ('region', 'staff', 'activity', 'estimation',
                                   'profitability', 'compliance', 'orgunit', 'process')
            )
            """
        )
    )
    conn.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE domain = 'catalog'
              AND resource IN ('region', 'staff', 'activity', 'estimation',
                               'profitability', 'compliance', 'orgunit', 'process')
            """
        )
    )

    # ── Remove system acceptance templates ─────────────────────────────
    conn.execute(
        sa.text(
            "DELETE FROM region_acceptance_templates WHERE is_system = true"
        )
    )

    # ── Remove system organizational units ────────────────────────────
    conn.execute(
        sa.text("DELETE FROM organizational_units WHERE tenant_id IS NULL")
    )

    # ── Remove system staff profiles ───────────────────────────────────
    conn.execute(
        sa.text("DELETE FROM staff_profiles WHERE is_system = true")
    )

    # ── Remove system delivery regions ─────────────────────────────────
    conn.execute(
        sa.text("DELETE FROM delivery_regions WHERE is_system = true")
    )

    # ── Remove added columns from existing tables ──────────────────────
    op.drop_column("tenant_price_overrides", "coverage_model")
    op.drop_column("tenant_price_overrides", "delivery_region_id")
    op.drop_column("price_list_items", "coverage_model")
    op.drop_column("price_list_items", "delivery_region_id")
    op.drop_column("service_offerings", "default_coverage_model")
    op.drop_column("service_offerings", "operating_model")
    op.drop_column("service_offerings", "service_type")

    # ── Drop tables in reverse dependency order ────────────────────────

    # 14. price_list_template_items
    op.drop_index(
        "ix_pl_template_items_offering_id",
        table_name="price_list_template_items",
    )
    op.drop_index(
        "ix_pl_template_items_template_id",
        table_name="price_list_template_items",
    )
    op.drop_table("price_list_template_items")

    # 13. price_list_templates
    op.drop_index(
        "ix_price_list_templates_tenant_id",
        table_name="price_list_templates",
    )
    op.drop_table("price_list_templates")

    # 12. estimation_line_items
    op.drop_index(
        "ix_estimation_line_items_rate_card_id",
        table_name="estimation_line_items",
    )
    op.drop_column("estimation_line_items", "rate_card_id")
    op.drop_index(
        "ix_estimation_line_items_region_id",
        table_name="estimation_line_items",
    )
    op.drop_index(
        "ix_estimation_line_items_staff_id",
        table_name="estimation_line_items",
    )
    op.drop_index(
        "ix_estimation_line_items_estimation_id",
        table_name="estimation_line_items",
    )
    op.drop_table("estimation_line_items")

    # 11. service_estimations
    op.drop_index(
        "ix_service_estimations_status", table_name="service_estimations"
    )
    op.drop_index(
        "ix_service_estimations_region_id", table_name="service_estimations"
    )
    op.drop_index(
        "ix_service_estimations_offering_id",
        table_name="service_estimations",
    )
    op.drop_index(
        "ix_service_estimations_client_id", table_name="service_estimations"
    )
    op.drop_index(
        "ix_service_estimations_tenant_id", table_name="service_estimations"
    )
    op.drop_table("service_estimations")

    # 10c. service_process_assignments
    op.drop_index(
        "ix_svc_process_assign_process_id",
        table_name="service_process_assignments",
    )
    op.drop_index(
        "ix_svc_process_assign_offering_id",
        table_name="service_process_assignments",
    )
    op.drop_index(
        "ix_svc_process_assign_tenant_id",
        table_name="service_process_assignments",
    )
    op.drop_table("service_process_assignments")

    # 10b. process_activity_links
    op.drop_index(
        "ix_process_activity_links_template_id",
        table_name="process_activity_links",
    )
    op.drop_index(
        "ix_process_activity_links_process_id",
        table_name="process_activity_links",
    )
    op.drop_table("process_activity_links")

    # 10a. service_processes
    op.drop_index(
        "ix_service_processes_tenant_id",
        table_name="service_processes",
    )
    op.drop_table("service_processes")

    # 9. activity_definitions
    op.drop_index(
        "ix_activity_definitions_staff_id",
        table_name="activity_definitions",
    )
    op.drop_index(
        "ix_activity_definitions_template_id",
        table_name="activity_definitions",
    )
    op.drop_table("activity_definitions")

    # 8. activity_templates
    op.drop_index(
        "ix_activity_templates_tenant_id", table_name="activity_templates"
    )
    op.drop_table("activity_templates")

    # 7. internal_rate_cards
    op.drop_index(
        "ix_internal_rate_cards_region_id", table_name="internal_rate_cards"
    )
    op.drop_index(
        "ix_internal_rate_cards_staff_id", table_name="internal_rate_cards"
    )
    op.drop_index(
        "ix_internal_rate_cards_tenant_id", table_name="internal_rate_cards"
    )
    op.drop_table("internal_rate_cards")

    # 6b. staff_profiles
    op.drop_index("ix_staff_profiles_org_unit_id", table_name="staff_profiles")
    op.drop_index("ix_staff_profiles_tenant_id", table_name="staff_profiles")
    op.drop_table("staff_profiles")

    # 6a. organizational_units
    op.drop_index("ix_organizational_units_parent_id", table_name="organizational_units")
    op.drop_index("ix_organizational_units_tenant_id", table_name="organizational_units")
    op.drop_table("organizational_units")

    # 5. tenant_region_template_assignments
    op.drop_index(
        "ix_tenant_region_tmpl_assign_tmpl_id",
        table_name="tenant_region_template_assignments",
    )
    op.drop_index(
        "ix_tenant_region_tmpl_assign_tenant_id",
        table_name="tenant_region_template_assignments",
    )
    op.drop_table("tenant_region_template_assignments")

    # 4. tenant_region_acceptances
    op.drop_index(
        "ix_tenant_region_acceptances_region_id",
        table_name="tenant_region_acceptances",
    )
    op.drop_index(
        "ix_tenant_region_acceptances_tenant_id",
        table_name="tenant_region_acceptances",
    )
    op.drop_table("tenant_region_acceptances")

    # 3. region_acceptance_template_rules
    op.drop_index(
        "ix_ra_template_rules_region_id",
        table_name="region_acceptance_template_rules",
    )
    op.drop_index(
        "ix_ra_template_rules_template_id",
        table_name="region_acceptance_template_rules",
    )
    op.drop_table("region_acceptance_template_rules")

    # 2. region_acceptance_templates
    op.drop_index(
        "ix_region_acceptance_templates_tenant_id",
        table_name="region_acceptance_templates",
    )
    op.drop_table("region_acceptance_templates")

    # 1. delivery_regions
    op.drop_index(
        "ix_delivery_regions_parent_id", table_name="delivery_regions"
    )
    op.drop_index(
        "ix_delivery_regions_tenant_id", table_name="delivery_regions"
    )
    op.drop_table("delivery_regions")
