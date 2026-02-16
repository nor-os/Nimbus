"""Add applicability columns to workflow_definitions.

Overview: Adds applicability FK columns to scope workflows to resource types.
Architecture: Migration for workflow applicability (Section 6/11)
Dependencies: 071_resolver_execution_permissions
Concepts: Workflow applicability, semantic type scoping, provider scoping

Revision ID: 072
Revises: 071
Create Date: 2026-02-15
"""

revision = "072"
down_revision = "071"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade():
    # Add nullable FK columns for workflow applicability
    op.add_column(
        "workflow_definitions",
        sa.Column(
            "applicable_semantic_type_id",
            UUID(as_uuid=True),
            sa.ForeignKey("semantic_resource_types.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column(
            "applicable_provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("semantic_providers.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    # Composite index for filtering by applicability
    op.create_index(
        "ix_workflow_definitions_applicability",
        "workflow_definitions",
        ["applicable_semantic_type_id", "applicable_provider_id"],
    )

    # Backfill: set applicability on the 3 seed operation workflows from migration 068
    conn = op.get_bind()

    pve_comp = conn.execute(
        sa.text(
            "SELECT semantic_type_id, provider_id FROM components "
            "WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1"
        )
    ).fetchone()
    if not pve_comp:
        return

    semantic_type_id = str(pve_comp[0])
    provider_id = str(pve_comp[1])

    for wf_name in [
        "PVE VM: Extend Disk",
        "PVE VM: Create Snapshot",
        "PVE VM: Restart",
    ]:
        conn.execute(
            sa.text(
                "UPDATE workflow_definitions "
                "SET applicable_semantic_type_id = :st_id, applicable_provider_id = :p_id "
                "WHERE name = :name"
            ),
            {"st_id": semantic_type_id, "p_id": provider_id, "name": wf_name},
        )


def downgrade():
    op.drop_index("ix_workflow_definitions_applicability", table_name="workflow_definitions")
    op.drop_column("workflow_definitions", "applicable_provider_id")
    op.drop_column("workflow_definitions", "applicable_semantic_type_id")
