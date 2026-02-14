"""
Overview: Pricing overlay redesign — replaces standalone overrides with pin-scoped overlays,
    adds geographic region constraints, moves minimum charges to pins.
Architecture: Overlay pricing model (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Price list overlays, catalog overlays, pin minimum charges, region constraints,
    tenant primary region.
"""

from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "048"
down_revision: Union[str, None] = "047"
branch_labels: Union[str, None] = None
depends_on: Union[str, None] = None


def upgrade() -> None:
    # ── A. price_list_overlay_items ────────────────────────────────────
    op.create_table(
        "price_list_overlay_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("pin_id", UUID(as_uuid=True), sa.ForeignKey("tenant_price_list_pins.id"), nullable=False, index=True),
        sa.Column("overlay_action", sa.String(10), nullable=False),
        sa.Column("base_item_id", UUID(as_uuid=True), sa.ForeignKey("price_list_items.id"), nullable=True),
        sa.Column("service_offering_id", UUID(as_uuid=True), sa.ForeignKey("service_offerings.id"), nullable=True),
        sa.Column("provider_sku_id", UUID(as_uuid=True), sa.ForeignKey("provider_skus.id"), nullable=True),
        sa.Column("activity_definition_id", UUID(as_uuid=True), sa.ForeignKey("activity_definitions.id"), nullable=True),
        sa.Column("delivery_region_id", UUID(as_uuid=True), sa.ForeignKey("delivery_regions.id"), nullable=True),
        sa.Column("coverage_model", sa.String(20), nullable=True),
        sa.Column("price_per_unit", sa.Numeric(12, 4), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("markup_percent", sa.Numeric(8, 4), nullable=True),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("min_quantity", sa.Numeric, nullable=True),
        sa.Column("max_quantity", sa.Numeric, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("overlay_action IN ('modify', 'add', 'exclude')", name="ck_price_list_overlay_action"),
    )

    # ── B. catalog_overlay_items ──────────────────────────────────────
    op.create_table(
        "catalog_overlay_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("pin_id", UUID(as_uuid=True), sa.ForeignKey("tenant_catalog_pins.id"), nullable=False, index=True),
        sa.Column("overlay_action", sa.String(10), nullable=False),
        sa.Column("base_item_id", UUID(as_uuid=True), sa.ForeignKey("service_catalog_items.id"), nullable=True),
        sa.Column("service_offering_id", UUID(as_uuid=True), sa.ForeignKey("service_offerings.id"), nullable=True),
        sa.Column("service_group_id", UUID(as_uuid=True), sa.ForeignKey("service_groups.id"), nullable=True),
        sa.Column("sort_order", sa.Integer, server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("overlay_action IN ('include', 'exclude')", name="ck_catalog_overlay_action"),
    )

    # ── C. pin_minimum_charges ────────────────────────────────────────
    op.create_table(
        "pin_minimum_charges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("pin_id", UUID(as_uuid=True), sa.ForeignKey("tenant_price_list_pins.id"), nullable=False, index=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("minimum_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── D. price_list_region_constraints ──────────────────────────────
    op.create_table(
        "price_list_region_constraints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("price_list_id", UUID(as_uuid=True), sa.ForeignKey("price_lists.id"), nullable=False, index=True),
        sa.Column("delivery_region_id", UUID(as_uuid=True), sa.ForeignKey("delivery_regions.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("price_list_id", "delivery_region_id", name="uq_price_list_region_constraint"),
    )

    # ── E. catalog_region_constraints ─────────────────────────────────
    op.create_table(
        "catalog_region_constraints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("catalog_id", UUID(as_uuid=True), sa.ForeignKey("service_catalogs.id"), nullable=False, index=True),
        sa.Column("delivery_region_id", UUID(as_uuid=True), sa.ForeignKey("delivery_regions.id"), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("catalog_id", "delivery_region_id", name="uq_catalog_region_constraint"),
    )

    # ── Alter tenants: add primary_region_id ──────────────────────────
    op.add_column(
        "tenants",
        sa.Column(
            "primary_region_id",
            UUID(as_uuid=True),
            sa.ForeignKey("delivery_regions.id"),
            nullable=True,
        ),
    )

    # ── Drop old tables ───────────────────────────────────────────────
    op.drop_table("tenant_price_overrides")
    op.drop_table("tenant_minimum_charges")


def downgrade() -> None:
    # Re-create old tables
    op.create_table(
        "tenant_price_overrides",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("service_offering_id", UUID(as_uuid=True), sa.ForeignKey("service_offerings.id"), nullable=True, index=True),
        sa.Column("provider_sku_id", UUID(as_uuid=True), sa.ForeignKey("provider_skus.id"), nullable=True),
        sa.Column("activity_definition_id", UUID(as_uuid=True), sa.ForeignKey("activity_definitions.id"), nullable=True),
        sa.Column("delivery_region_id", UUID(as_uuid=True), sa.ForeignKey("delivery_regions.id"), nullable=True),
        sa.Column("coverage_model", sa.String(20), nullable=True),
        sa.Column("price_per_unit", sa.Numeric(12, 4), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "tenant_minimum_charges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, index=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("minimum_amount", sa.Numeric(12, 4), nullable=False),
        sa.Column("currency", sa.String(3), server_default="EUR", nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Remove primary_region_id from tenants
    op.drop_column("tenants", "primary_region_id")

    # Drop new tables
    op.drop_table("catalog_region_constraints")
    op.drop_table("price_list_region_constraints")
    op.drop_table("pin_minimum_charges")
    op.drop_table("catalog_overlay_items")
    op.drop_table("price_list_overlay_items")
