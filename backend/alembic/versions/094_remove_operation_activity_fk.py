"""
Overview: Drop automated_activity_id FK from component_operations — the link is now implicit
    through the workflow graph's activity nodes.
Architecture: Schema migration for component-activity decoupling (Section 11)
Dependencies: 093_update_deployment_templates
Concepts: Removing shallow bridge pattern, soft-deleting orphaned COMPONENT-scoped activities
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "094"
down_revision: str = "093"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Soft-delete orphaned COMPONENT-scoped deployment activities (UUID-suffixed slugs)
    op.execute(
        sa.text(
            """
            UPDATE automated_activities
            SET deleted_at = NOW()
            WHERE scope = 'COMPONENT'
              AND category = 'deployment'
              AND deleted_at IS NULL
              AND slug ~ '-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            """
        )
    )

    # Drop index, FK, and column
    op.drop_index("ix_component_operations_activity", table_name="component_operations")
    op.drop_constraint(
        "fk_component_operations_automated_activity",
        "component_operations",
        type_="foreignkey",
    )
    op.drop_column("component_operations", "automated_activity_id")


def downgrade() -> None:
    # Re-add the column, FK, and index
    op.add_column(
        "component_operations",
        sa.Column("automated_activity_id", UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_component_operations_automated_activity",
        "component_operations",
        "automated_activities",
        ["automated_activity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_component_operations_activity",
        "component_operations",
        ["automated_activity_id"],
    )
