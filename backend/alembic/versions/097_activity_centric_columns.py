"""
Overview: Add activity-centric columns — is_mandatory, forked_at_version, BUILTIN enum, workflow component_id.
Architecture: Schema + data migration for activity-centric operations model (Section 11.5)
Dependencies: 096_activity_type_and_component_activities
Concepts: Mandatory activity protection, fork version tracking, builtin activity category, workflow-component link
"""

from alembic import op
import sqlalchemy as sa

revision: str = "097"
down_revision: str = "096"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. Add is_mandatory column to automated_activities ──
    op.add_column(
        "automated_activities",
        sa.Column("is_mandatory", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ── 2. Add forked_at_version column to automated_activities ──
    op.add_column(
        "automated_activities",
        sa.Column("forked_at_version", sa.Integer(), nullable=True),
    )

    # ── 3. Add component_id column to workflow_definitions ──
    op.add_column(
        "workflow_definitions",
        sa.Column("component_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_workflow_definitions_component_id",
        "workflow_definitions",
        "components",
        ["component_id"],
        ["id"],
    )
    op.create_index(
        "ix_workflow_definitions_component_id",
        "workflow_definitions",
        ["component_id"],
    )

    # ── 4. Add BUILTIN to activity_type enum values ──
    # The activity_type column uses a non-native VARCHAR(20)-based enum,
    # so no ALTER TYPE needed — just update the data directly.

    # ── 5. Data migration: mark mandatory activities ──
    conn = op.get_bind()
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET is_mandatory = true
        WHERE is_system = true
          AND slug IN (
            'deploy-resource', 'decommission-resource', 'upgrade-resource',
            'rollback-resource', 'dry-run-resource', 'validate-resource'
          )
          AND deleted_at IS NULL
    """))

    # ── 6. Data migration: reclassify builtins ──
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET activity_type = 'BUILTIN'
        WHERE is_system = true
          AND slug IN (
            'send-email', 'send-notification', 'http-request', 'log-audit-entry'
          )
          AND deleted_at IS NULL
    """))


def downgrade() -> None:
    conn = op.get_bind()

    # Revert builtins back to CUSTOM
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET activity_type = 'CUSTOM'
        WHERE activity_type = 'BUILTIN'
    """))

    # Revert mandatory flags
    conn.execute(sa.text("""
        UPDATE automated_activities
        SET is_mandatory = false
        WHERE is_mandatory = true
    """))

    # Drop workflow_definitions.component_id
    op.drop_index("ix_workflow_definitions_component_id", table_name="workflow_definitions")
    op.drop_constraint("fk_workflow_definitions_component_id", "workflow_definitions", type_="foreignkey")
    op.drop_column("workflow_definitions", "component_id")

    # Drop forked_at_version and is_mandatory
    op.drop_column("automated_activities", "forked_at_version")
    op.drop_column("automated_activities", "is_mandatory")
