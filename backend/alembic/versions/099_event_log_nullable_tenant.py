"""
Overview: Make event_log.tenant_id and event_type_id nullable for tenant-less events (e.g. failed logins).
Architecture: Schema migration for event system (Section 11.6)
Dependencies: 098_activity_model_cleanup
Concepts: Pre-authentication events have no tenant context; event_type may not be resolved at emit time.
"""

revision = "099"
down_revision = "098"

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    op.alter_column("event_log", "tenant_id", existing_type=postgresql.UUID(), nullable=True)
    op.alter_column("event_log", "event_type_id", existing_type=postgresql.UUID(), nullable=True)


def downgrade():
    # Backfill NULLs before restoring NOT NULL (use system zero UUID as placeholder)
    op.execute("UPDATE event_log SET tenant_id = '00000000-0000-0000-0000-000000000000' WHERE tenant_id IS NULL")
    op.execute("UPDATE event_log SET event_type_id = (SELECT id FROM event_types LIMIT 1) WHERE event_type_id IS NULL")
    op.alter_column("event_log", "event_type_id", existing_type=postgresql.UUID(), nullable=False)
    op.alter_column("event_log", "tenant_id", existing_type=postgresql.UUID(), nullable=False)
