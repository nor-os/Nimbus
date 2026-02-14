"""
Overview: Drop service_cluster_members table — CI assignment is a deployment-time concern,
    not part of blueprint templates.
Architecture: Database migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Blueprints are pure templates. The members table linked live CIs to blueprint
    slots, which was conceptually incorrect. CI assignment will be handled by deployment
    instances in a future phase.
"""

revision = "053"
down_revision = "052"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime


def upgrade() -> None:
    op.drop_table("service_cluster_members")


def downgrade() -> None:
    op.create_table(
        "service_cluster_members",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("cluster_id", UUID(as_uuid=True), sa.ForeignKey("service_clusters.id"), nullable=False),
        sa.Column("slot_id", UUID(as_uuid=True), sa.ForeignKey("service_cluster_slots.id"), nullable=False),
        sa.Column("ci_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=False),
        sa.Column("assigned_by", UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("cluster_id", "slot_id", "ci_id", name="uq_member_cluster_slot_ci"),
    )
    op.create_index("ix_service_cluster_members_cluster_id", "service_cluster_members", ["cluster_id"])
    op.create_index("ix_service_cluster_members_slot_id", "service_cluster_members", ["slot_id"])
    op.create_index("ix_service_cluster_members_ci_id", "service_cluster_members", ["ci_id"])
