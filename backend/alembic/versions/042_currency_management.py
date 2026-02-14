"""Add currency management — provider default currency, tenant invoice currency,
and exchange rates table with permissions.

Revision ID: 042
Revises: 041
Create Date: 2026-02-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "042"
down_revision: Union[str, None] = "041"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Provider default currency ────────────────────────────────────
    op.add_column(
        "providers",
        sa.Column("default_currency", sa.String(3), nullable=False, server_default="EUR"),
    )

    # ── Tenant invoice currency (nullable = inherit from provider) ───
    op.add_column(
        "tenants",
        sa.Column("invoice_currency", sa.String(3), nullable=True),
    )

    # ── Exchange rates table ─────────────────────────────────────────
    op.create_table(
        "currency_exchange_rates",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "provider_id",
            sa.dialects.postgresql.UUID(as_uuid=True),
            sa.ForeignKey("providers.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("source_currency", sa.String(3), nullable=False),
        sa.Column("target_currency", sa.String(3), nullable=False),
        sa.Column("rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("effective_from", sa.Date, nullable=False),
        sa.Column("effective_to", sa.Date, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Partial unique index: one active rate per provider/source/target/date
    op.execute(
        """
        CREATE UNIQUE INDEX uq_exchange_rate_active
        ON currency_exchange_rates (provider_id, source_currency, target_currency, effective_from)
        WHERE deleted_at IS NULL
        """
    )

    # ── Seed permissions ─────────────────────────────────────────────
    op.execute(
        """
        INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'settings', 'currency', 'read', NULL, 'View provider and tenant currency settings', true, now(), now()),
            (gen_random_uuid(), 'settings', 'currency', 'manage', NULL, 'Manage provider and tenant currency settings', true, now(), now()),
            (gen_random_uuid(), 'settings', 'exchange_rate', 'read', NULL, 'View exchange rates', true, now(), now()),
            (gen_random_uuid(), 'settings', 'exchange_rate', 'manage', NULL, 'Manage exchange rates', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """
    )

    # Assign read + manage to Provider Admin; read only to Tenant Admin
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Provider Admin'
          AND p.domain || ':' || p.resource || ':' || p.action IN (
              'settings:currency:read', 'settings:currency:manage',
              'settings:exchange_rate:read', 'settings:exchange_rate:manage'
          )
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Tenant Admin'
          AND p.domain || ':' || p.resource || ':' || p.action IN (
              'settings:currency:read', 'settings:exchange_rate:read'
          )
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_exchange_rate_active")
    op.drop_table("currency_exchange_rates")
    op.drop_column("tenants", "invoice_currency")
    op.drop_column("providers", "default_currency")
    op.execute(
        """
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain || ':' || resource || ':' || action IN (
                'settings:currency:read', 'settings:currency:manage',
                'settings:exchange_rate:read', 'settings:exchange_rate:manage'
            )
        )
        """
    )
    op.execute(
        """
        DELETE FROM permissions
        WHERE domain || ':' || resource || ':' || action IN (
            'settings:currency:read', 'settings:currency:manage',
            'settings:exchange_rate:read', 'settings:exchange_rate:manage'
        )
        """
    )
