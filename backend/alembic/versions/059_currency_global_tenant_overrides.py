"""
Overview: Restructure exchange rates — drop provider_id, add nullable tenant_id for global defaults
    + per-tenant overrides. Seed 6 EUR/USD/CHF cross-rates. Grant Tenant Admin manage permission.
Architecture: Currency management migration (Section 4)
Dependencies: alembic, sqlalchemy
Concepts: Global exchange rates, tenant overrides, pre-populated rates
"""

revision = "059"
down_revision = "058"
branch_labels = None
depends_on = None

import uuid
from datetime import datetime, UTC

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # ── Drop old provider-scoped index and column ─────────────────────
    op.execute("DROP INDEX IF EXISTS uq_exchange_rate_active")
    op.drop_column("currency_exchange_rates", "provider_id")

    # ── Add nullable tenant_id (NULL = global default) ────────────────
    op.add_column(
        "currency_exchange_rates",
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True),
    )
    op.create_index("ix_currency_exchange_rates_tenant_id", "currency_exchange_rates", ["tenant_id"])

    # ── New partial unique index (NULL-safe via COALESCE) ─────────────
    op.execute("""
        CREATE UNIQUE INDEX uq_exchange_rate_tenant_active
        ON currency_exchange_rates (
            COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'),
            source_currency, target_currency, effective_from
        )
        WHERE deleted_at IS NULL
    """)

    # ── Seed 6 global cross-rates ─────────────────────────────────────
    now = datetime.now(UTC).isoformat()
    rates = [
        ("EUR", "USD", "1.08000000"),
        ("USD", "EUR", "0.92590000"),
        ("EUR", "CHF", "0.94000000"),
        ("CHF", "EUR", "1.06380000"),
        ("USD", "CHF", "0.87040000"),
        ("CHF", "USD", "1.14890000"),
    ]
    for src, tgt, rate in rates:
        rid = str(uuid.uuid4())
        op.execute(
            f"""
            INSERT INTO currency_exchange_rates
                (id, tenant_id, source_currency, target_currency, rate, effective_from, created_at, updated_at)
            VALUES
                ('{rid}', NULL, '{src}', '{tgt}', {rate}, '2026-01-01', '{now}', '{now}')
            """
        )

    # ── Grant Tenant Admin the manage permission ──────────────────────
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r, permissions p
        WHERE r.name = 'Tenant Admin'
          AND p.domain = 'settings' AND p.resource = 'exchange_rate' AND p.action = 'manage'
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_exchange_rate_tenant_active")
    op.drop_index("ix_currency_exchange_rates_tenant_id", "currency_exchange_rates")
    op.drop_column("currency_exchange_rates", "tenant_id")
    op.add_column(
        "currency_exchange_rates",
        sa.Column("provider_id", UUID(as_uuid=True), sa.ForeignKey("providers.id"), nullable=False),
    )
    op.execute("""
        CREATE UNIQUE INDEX uq_exchange_rate_active
        ON currency_exchange_rates (provider_id, source_currency, target_currency, effective_from)
        WHERE deleted_at IS NULL
    """)
