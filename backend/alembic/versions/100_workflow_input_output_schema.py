"""
Overview: Add input_schema and output_schema JSONB columns to workflow_definitions.
Architecture: Schema migration for workflow editor (Section 6)
Dependencies: 099_event_log_nullable_tenant
Concepts: Workflow definitions declare expected I/O shape, matching the activity pattern.
"""

revision = "100"
down_revision = "099"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


def upgrade() -> None:
    op.add_column("workflow_definitions", sa.Column("input_schema", JSONB, nullable=True))
    op.add_column("workflow_definitions", sa.Column("output_schema", JSONB, nullable=True))


def downgrade() -> None:
    op.drop_column("workflow_definitions", "output_schema")
    op.drop_column("workflow_definitions", "input_schema")
