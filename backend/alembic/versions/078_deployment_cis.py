"""Create deployment_cis junction table linking deployments to configuration items.

Revision ID: 078
Revises: 077
Create Date: 2026-02-15
"""

revision = "078"
down_revision = "077"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    op.create_table(
        "deployment_cis",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("deployment_id", UUID(as_uuid=True), sa.ForeignKey("deployments.id"), nullable=False),
        sa.Column("ci_id", UUID(as_uuid=True), sa.ForeignKey("configuration_items.id"), nullable=False),
        sa.Column("component_id", UUID(as_uuid=True), sa.ForeignKey("components.id"), nullable=False),
        sa.Column("topology_node_id", sa.String(255), nullable=True),
        sa.Column("resolver_outputs", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("deployment_id", "ci_id", name="uq_deployment_ci"),
    )
    op.create_index("ix_deployment_cis_deployment", "deployment_cis", ["deployment_id"])
    op.create_index("ix_deployment_cis_ci", "deployment_cis", ["ci_id"])


def downgrade() -> None:
    op.drop_index("ix_deployment_cis_ci")
    op.drop_index("ix_deployment_cis_deployment")
    op.drop_table("deployment_cis")
