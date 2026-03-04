"""
Overview: Create component_reservation_templates table for per-component DR reservation config.
Architecture: Migration for per-component reservation templates (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Per-component reservation templates allow different DR strategies per blueprint component.
"""

revision = "110"
down_revision = "109"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade() -> None:
    op.create_table(
        "component_reservation_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("blueprint_component_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reservation_type", sa.String(30), nullable=False),
        sa.Column("resource_percentage", sa.Integer(), server_default="80", nullable=False),
        sa.Column("target_environment_label", sa.String(255), nullable=True),
        sa.Column("target_provider_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("rto_seconds", sa.Integer(), nullable=True),
        sa.Column("rpo_seconds", sa.Integer(), nullable=True),
        sa.Column("auto_create_on_deploy", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("sync_policies_template", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["blueprint_component_id"], ["stack_blueprint_components.id"]),
        sa.ForeignKeyConstraint(["target_provider_id"], ["semantic_providers.id"]),
        sa.UniqueConstraint("blueprint_component_id", name="uq_component_reservation_template"),
    )
    op.create_index("ix_component_reservation_templates_blueprint_component_id", "component_reservation_templates", ["blueprint_component_id"])


def downgrade() -> None:
    op.drop_index("ix_component_reservation_templates_blueprint_component_id")
    op.drop_table("component_reservation_templates")
