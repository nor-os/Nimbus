"""
Overview: Fix existing cloned workflows stuck at v0 DRAFT, add component_version to deployment_cis.
Architecture: Schema migration (Section 6, 7.2)
Dependencies: 100_workflow_input_output_schema
Concepts: Cloned deployment workflows should be ACTIVE v1. DeploymentCI tracks which component version was deployed.
"""

revision = "101"
down_revision = "100"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa


def upgrade() -> None:
    # Fix existing cloned workflows that are stuck at DRAFT v0
    # These were created by clone_from_template() but never published
    op.execute("""
        UPDATE workflow_definitions
        SET version = 1, status = 'ACTIVE'
        WHERE template_source_id IS NOT NULL
          AND status = 'DRAFT'
          AND version = 0
          AND deleted_at IS NULL
    """)

    # Add component_version column to deployment_cis
    op.add_column(
        "deployment_cis",
        sa.Column("component_version", sa.Integer(), nullable=True),
    )

    # Backfill existing rows with the component's current version
    op.execute("""
        UPDATE deployment_cis dc
        SET component_version = c.version
        FROM components c
        WHERE dc.component_id = c.id
          AND dc.component_version IS NULL
    """)

    # Make topology_id nullable on deployments (for component-only deployments)
    op.alter_column(
        "deployments", "topology_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Make ci_id nullable on deployment_cis (for component-only deployments without CI)
    op.alter_column(
        "deployment_cis", "ci_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    # Revert ci_id to NOT NULL
    op.alter_column(
        "deployment_cis", "ci_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    # Revert topology_id to NOT NULL
    op.alter_column(
        "deployments", "topology_id",
        existing_type=sa.dialects.postgresql.UUID(as_uuid=True),
        nullable=False,
    )

    op.drop_column("deployment_cis", "component_version")

    # Revert fixed workflows back to DRAFT v0 (best effort)
    op.execute("""
        UPDATE workflow_definitions
        SET version = 0, status = 'DRAFT'
        WHERE template_source_id IS NOT NULL
          AND status = 'ACTIVE'
          AND version = 1
          AND deleted_at IS NULL
    """)
