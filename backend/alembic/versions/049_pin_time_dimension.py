"""
Overview: Add time dimension to tenant catalog pins and tenant price list pins — effective_from,
    effective_to dates with exclusion constraints to prevent overlapping pins per tenant.
Architecture: Database migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Time-dimensional pins with date-range validity and overlap prevention via btree_gist.
"""

revision = "049"
down_revision = "048"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Enable btree_gist extension for exclusion constraints
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # ── tenant_catalog_pins ──────────────────────────────────────────
    op.add_column(
        "tenant_catalog_pins",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "tenant_catalog_pins",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )
    # Backfill existing rows with CURRENT_DATE
    op.execute("UPDATE tenant_catalog_pins SET effective_from = CURRENT_DATE WHERE effective_from IS NULL")
    # Now make it NOT NULL
    op.alter_column("tenant_catalog_pins", "effective_from", nullable=False)

    # CHECK: effective_to >= effective_from (when effective_to is set)
    op.execute("""
        ALTER TABLE tenant_catalog_pins
        ADD CONSTRAINT ck_catalog_pin_date_range
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
    """)

    # Exclusion constraint: no overlapping active pins per tenant
    op.execute("""
        ALTER TABLE tenant_catalog_pins
        ADD CONSTRAINT excl_catalog_pin_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            daterange(effective_from, effective_to, '[]') WITH &&
        ) WHERE (deleted_at IS NULL)
    """)

    # ── tenant_price_list_pins ───────────────────────────────────────
    op.add_column(
        "tenant_price_list_pins",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "tenant_price_list_pins",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )
    # Backfill existing rows with CURRENT_DATE
    op.execute("UPDATE tenant_price_list_pins SET effective_from = CURRENT_DATE WHERE effective_from IS NULL")
    # Now make it NOT NULL
    op.alter_column("tenant_price_list_pins", "effective_from", nullable=False)

    # CHECK: effective_to >= effective_from (when effective_to is set)
    op.execute("""
        ALTER TABLE tenant_price_list_pins
        ADD CONSTRAINT ck_price_list_pin_date_range
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
    """)

    # Exclusion constraint: no overlapping active pins per tenant
    op.execute("""
        ALTER TABLE tenant_price_list_pins
        ADD CONSTRAINT excl_price_list_pin_overlap
        EXCLUDE USING gist (
            tenant_id WITH =,
            daterange(effective_from, effective_to, '[]') WITH &&
        ) WHERE (deleted_at IS NULL)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE tenant_price_list_pins DROP CONSTRAINT IF EXISTS excl_price_list_pin_overlap")
    op.execute("ALTER TABLE tenant_price_list_pins DROP CONSTRAINT IF EXISTS ck_price_list_pin_date_range")
    op.drop_column("tenant_price_list_pins", "effective_to")
    op.drop_column("tenant_price_list_pins", "effective_from")

    op.execute("ALTER TABLE tenant_catalog_pins DROP CONSTRAINT IF EXISTS excl_catalog_pin_overlap")
    op.execute("ALTER TABLE tenant_catalog_pins DROP CONSTRAINT IF EXISTS ck_catalog_pin_date_range")
    op.drop_column("tenant_catalog_pins", "effective_to")
    op.drop_column("tenant_catalog_pins", "effective_from")
