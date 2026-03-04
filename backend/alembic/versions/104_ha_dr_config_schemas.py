"""
Overview: Add HA/DR configuration schemas and defaults to blueprints.
Architecture: Alembic migration for blueprint HA/DR configuration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Blueprints define what HA/DR settings are available for their stack type
    via JSON Schema, with sensible defaults.

Revision ID: 104
Revises: 103
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "104"
down_revision = "103"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("service_clusters", sa.Column(
        "ha_config_schema", JSONB, nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "ha_config_defaults", JSONB, nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "dr_config_schema", JSONB, nullable=True,
    ))
    op.add_column("service_clusters", sa.Column(
        "dr_config_defaults", JSONB, nullable=True,
    ))


def downgrade() -> None:
    op.drop_column("service_clusters", "dr_config_defaults")
    op.drop_column("service_clusters", "dr_config_schema")
    op.drop_column("service_clusters", "ha_config_defaults")
    op.drop_column("service_clusters", "ha_config_schema")
