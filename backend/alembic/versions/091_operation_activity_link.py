"""
Overview: Link component operations to automated activities via FK.
Architecture: Migration for component-activity bridge (Section 11)
Dependencies: alembic, sqlalchemy
Concepts: Each deployment operation gets a corresponding AutomatedActivity entry so it appears
    in the Activities UI. The FK allows navigation from operation → activity.
"""

revision = "091"
down_revision = "090"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # Add automated_activity_id FK to component_operations
    op.add_column(
        "component_operations",
        sa.Column(
            "automated_activity_id",
            UUID(as_uuid=True),
            nullable=True,
        ),
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


def downgrade() -> None:
    op.drop_index("ix_component_operations_activity", table_name="component_operations")
    op.drop_constraint(
        "fk_component_operations_automated_activity",
        "component_operations",
        type_="foreignkey",
    )
    op.drop_column("component_operations", "automated_activity_id")
