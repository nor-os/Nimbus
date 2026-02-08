"""Permission rework: drop tier, add scope, create permission_overrides.

Revision ID: 006
Revises: 005
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add scope column (before dropping tier, so we can migrate data)
    op.add_column(
        "roles",
        sa.Column("scope", sa.String(20), nullable=False, server_default="tenant"),
    )

    # 2. Set scope based on existing tier values
    op.execute(
        """
        UPDATE roles SET scope = 'provider'
        WHERE tier IN ('provider') AND is_system = TRUE
        """
    )

    # 3. Drop tier column
    op.drop_column("roles", "tier")

    # 4. Drop the enum type
    op.execute("DROP TYPE IF EXISTS role_tier_enum")

    # 5. Create permission_overrides table
    op.create_table(
        "permission_overrides",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            UUID(as_uuid=True),
            sa.ForeignKey("permissions.id"),
            nullable=False,
        ),
        sa.Column(
            "principal_type",
            sa.String(10),
            nullable=False,
        ),
        sa.Column(
            "principal_id",
            UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "effect",
            sa.String(5),
            nullable=False,
            server_default="deny",
        ),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column(
            "created_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
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
        sa.UniqueConstraint(
            "tenant_id", "permission_id", "principal_type", "principal_id"
        ),
        sa.CheckConstraint(
            "principal_type IN ('user', 'group', 'role')",
            name="ck_perm_overrides_principal_type",
        ),
        sa.CheckConstraint(
            "effect IN ('deny')",
            name="ck_perm_overrides_effect",
        ),
    )

    op.create_index(
        "ix_perm_overrides_tenant",
        "permission_overrides",
        ["tenant_id"],
    )
    op.create_index(
        "ix_perm_overrides_principal",
        "permission_overrides",
        ["principal_type", "principal_id"],
    )


def downgrade() -> None:
    # Drop permission_overrides
    op.drop_index("ix_perm_overrides_principal", table_name="permission_overrides")
    op.drop_index("ix_perm_overrides_tenant", table_name="permission_overrides")
    op.drop_table("permission_overrides")

    # Re-create tier enum and column
    role_tier_enum = sa.Enum(
        "provider", "tenant_admin", "user", "read_only",
        name="role_tier_enum",
    )
    role_tier_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "roles",
        sa.Column("tier", role_tier_enum, nullable=True),
    )

    # Migrate scope back to tier
    op.execute(
        """
        UPDATE roles SET tier = 'provider'
        WHERE scope = 'provider' AND is_system = TRUE
        """
    )

    # Drop scope column
    op.drop_column("roles", "scope")
