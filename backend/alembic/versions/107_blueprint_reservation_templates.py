"""
Overview: Create blueprint_reservation_templates table for blueprint-level DR defaults.
Architecture: Alembic migration for blueprint reservation templates (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Reservation templates define default DR settings at the blueprint level,
    auto-applied when stack instances are deployed.

Revision ID: 107
Revises: 106
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "107"
down_revision = "106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blueprint_reservation_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("blueprint_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False, unique=True),
        sa.Column("reservation_type", sa.String(30), nullable=False),
        sa.Column("resource_percentage", sa.Integer, nullable=False, server_default="80"),
        sa.Column("target_environment_label", sa.String(255), nullable=True),
        sa.Column("target_provider_id", UUID(as_uuid=True), sa.ForeignKey("semantic_providers.id"), nullable=True),
        sa.Column("rto_seconds", sa.Integer, nullable=True),
        sa.Column("rpo_seconds", sa.Integer, nullable=True),
        sa.Column("auto_create_on_deploy", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("sync_policies_template", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_brt_blueprint_id", "blueprint_reservation_templates", ["blueprint_id"])


def downgrade() -> None:
    op.drop_index("ix_brt_blueprint_id")
    op.drop_table("blueprint_reservation_templates")
