"""
Overview: Add service_offering_regions junction table for regional delivery.
Architecture: Catalog region linkage (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Service offerings can be linked to specific delivery regions when operating model is 'regional'.
"""

revision: str = "023"
down_revision: str | None = "022"
branch_labels: str | None = None
depends_on: str | None = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    op.create_table(
        "service_offering_regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_offering_id", UUID(as_uuid=True), sa.ForeignKey("service_offerings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("delivery_region_id", UUID(as_uuid=True), sa.ForeignKey("delivery_regions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("service_offering_id", "delivery_region_id", name="uq_offering_region"),
    )
    op.create_index("ix_service_offering_regions_offering_id", "service_offering_regions", ["service_offering_id"])
    op.create_index("ix_service_offering_regions_region_id", "service_offering_regions", ["delivery_region_id"])


def downgrade() -> None:
    op.drop_index("ix_service_offering_regions_region_id")
    op.drop_index("ix_service_offering_regions_offering_id")
    op.drop_table("service_offering_regions")
