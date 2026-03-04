"""
Overview: Remove redundant activity classification fields, add is_component_activity, add resolver_bindings
    to versions, remove schema fields from components/component_versions/component_operations.
Architecture: Schema migration for activity model cleanup (Section 11.5)
Dependencies: 097_activity_centric_columns
Concepts: Simplify activity model — replace activity_type/scope/category/is_system with is_component_activity.
    Move schema/resolver concerns from component to activity versions.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "098"
down_revision: str = "097"


def upgrade() -> None:
    # ── 1. Add is_component_activity to automated_activities ──
    op.add_column(
        "automated_activities",
        sa.Column("is_component_activity", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Populate: activities with component_id are component activities
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET is_component_activity = true
        WHERE component_id IS NOT NULL
    """))

    # ── 2. Add resolver_bindings to automated_activity_versions ──
    op.add_column(
        "automated_activity_versions",
        sa.Column("resolver_bindings", JSONB, nullable=True),
    )

    # ── 3. Drop columns from automated_activities ──
    op.drop_column("automated_activities", "activity_type")
    op.drop_column("automated_activities", "scope")
    op.drop_column("automated_activities", "category")
    op.drop_column("automated_activities", "is_system")

    # ── 4. Drop schema/resolver columns from components ──
    op.drop_column("components", "input_schema")
    op.drop_column("components", "output_schema")
    op.drop_column("components", "resolver_bindings")

    # ── 5. Drop schema/resolver columns from component_versions ──
    op.drop_column("component_versions", "input_schema")
    op.drop_column("component_versions", "output_schema")
    op.drop_column("component_versions", "resolver_bindings")

    # ── 6. Drop schema columns from component_operations ──
    op.drop_column("component_operations", "input_schema")
    op.drop_column("component_operations", "output_schema")


def downgrade() -> None:
    # ── Re-add component_operations schema columns ──
    op.add_column("component_operations", sa.Column("output_schema", JSONB, nullable=True))
    op.add_column("component_operations", sa.Column("input_schema", JSONB, nullable=True))

    # ── Re-add component_versions schema/resolver columns ──
    op.add_column("component_versions", sa.Column("resolver_bindings", JSONB, nullable=True))
    op.add_column("component_versions", sa.Column("output_schema", JSONB, nullable=True))
    op.add_column("component_versions", sa.Column("input_schema", JSONB, nullable=True))

    # ── Re-add components schema/resolver columns ──
    op.add_column("components", sa.Column("resolver_bindings", JSONB, nullable=True))
    op.add_column("components", sa.Column("output_schema", JSONB, nullable=True))
    op.add_column("components", sa.Column("input_schema", JSONB, nullable=True))

    # ── Re-add automated_activities classification columns ──
    op.add_column("automated_activities", sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("automated_activities", sa.Column("category", sa.String(100), nullable=True))
    op.add_column("automated_activities", sa.Column("scope", sa.String(50), nullable=False, server_default="WORKFLOW"))
    op.add_column("automated_activities", sa.Column("activity_type", sa.String(50), nullable=False, server_default="DEPLOYMENT"))

    # ── Drop new columns ──
    op.drop_column("automated_activity_versions", "resolver_bindings")
    op.drop_column("automated_activities", "is_component_activity")
