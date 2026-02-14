"""
Overview: Remove effective_from/effective_to from service_catalogs and price_lists tables.
    Effective dates are managed on the pin tables (tenant_catalog_pins, tenant_price_list_pins)
    instead. Backfill NULL effective_to on pins with 2999-12-31 and make it NOT NULL.
Architecture: Database migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Effective dates belong on tenant pins (the mapping), not on catalog/price list definitions.
"""

revision = "050"
down_revision = "049"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # ── Backfill NULL effective_to on pins with 2999-12-31 ────────────
    op.execute(
        "UPDATE tenant_catalog_pins SET effective_to = '2999-12-31' WHERE effective_to IS NULL"
    )
    op.execute(
        "UPDATE tenant_price_list_pins SET effective_to = '2999-12-31' WHERE effective_to IS NULL"
    )

    # ── Drop old CHECK constraints that allowed NULL effective_to ─────
    op.execute(
        "ALTER TABLE tenant_catalog_pins DROP CONSTRAINT IF EXISTS ck_catalog_pin_date_range"
    )
    op.execute(
        "ALTER TABLE tenant_price_list_pins DROP CONSTRAINT IF EXISTS ck_price_list_pin_date_range"
    )

    # ── Make effective_to NOT NULL on pins ────────────────────────────
    op.alter_column("tenant_catalog_pins", "effective_to", nullable=False)
    op.alter_column("tenant_price_list_pins", "effective_to", nullable=False)

    # ── Re-add CHECK constraints (effective_to >= effective_from) ─────
    op.execute("""
        ALTER TABLE tenant_catalog_pins
        ADD CONSTRAINT ck_catalog_pin_date_range
        CHECK (effective_to >= effective_from)
    """)
    op.execute("""
        ALTER TABLE tenant_price_list_pins
        ADD CONSTRAINT ck_price_list_pin_date_range
        CHECK (effective_to >= effective_from)
    """)

    # ── Drop effective_from/to from service_catalogs ──────────────────
    op.drop_column("service_catalogs", "effective_from")
    op.drop_column("service_catalogs", "effective_to")

    # ── Drop effective_from/to from price_lists ───────────────────────
    op.drop_column("price_lists", "effective_from")
    op.drop_column("price_lists", "effective_to")


def downgrade() -> None:
    # ── Re-add effective_from/to to price_lists ───────────────────────
    op.add_column(
        "price_lists",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "price_lists",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )

    # ── Re-add effective_from/to to service_catalogs ──────────────────
    op.add_column(
        "service_catalogs",
        sa.Column("effective_from", sa.Date(), nullable=True),
    )
    op.add_column(
        "service_catalogs",
        sa.Column("effective_to", sa.Date(), nullable=True),
    )

    # ── Drop CHECK constraints ────────────────────────────────────────
    op.execute(
        "ALTER TABLE tenant_catalog_pins DROP CONSTRAINT IF EXISTS ck_catalog_pin_date_range"
    )
    op.execute(
        "ALTER TABLE tenant_price_list_pins DROP CONSTRAINT IF EXISTS ck_price_list_pin_date_range"
    )

    # ── Make effective_to nullable again on pins ──────────────────────
    op.alter_column("tenant_catalog_pins", "effective_to", nullable=True)
    op.alter_column("tenant_price_list_pins", "effective_to", nullable=True)

    # ── Re-add original CHECK constraints (with NULL allowed) ─────────
    op.execute("""
        ALTER TABLE tenant_catalog_pins
        ADD CONSTRAINT ck_catalog_pin_date_range
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
    """)
    op.execute("""
        ALTER TABLE tenant_price_list_pins
        ADD CONSTRAINT ck_price_list_pin_date_range
        CHECK (effective_to IS NULL OR effective_to >= effective_from)
    """)
