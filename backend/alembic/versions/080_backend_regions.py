"""Backend regions table, drop 1:1 tenant-backend constraint, add LZ region_id.

Revision ID: 080
Revises: 079
Create Date: 2026-02-17
"""

revision = "080"
down_revision = "079"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


def upgrade() -> None:
    # 1. Create backend_regions table
    op.create_table(
        "backend_regions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("backend_id", UUID(as_uuid=True), sa.ForeignKey("cloud_backends.id"), nullable=False),
        sa.Column("region_identifier", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("provider_region_code", sa.String(100), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("availability_zones", JSONB, nullable=True),
        sa.Column("settings", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Indexes
    op.create_index("ix_backend_regions_tenant", "backend_regions", ["tenant_id"])
    op.create_index("ix_backend_regions_backend", "backend_regions", ["backend_id"])
    op.execute("""
        CREATE UNIQUE INDEX uq_backend_region_identifier
        ON backend_regions (backend_id, region_identifier)
        WHERE deleted_at IS NULL
    """)

    # 2. Drop partial unique index on tenant_id (enables N backends per tenant)
    op.execute("DROP INDEX IF EXISTS uq_cloud_backends_tenant_id")

    # 3. Add region_id FK to landing_zones
    op.add_column("landing_zones", sa.Column("region_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_landing_zones_region_id",
        "landing_zones",
        "backend_regions",
        ["region_id"],
        ["id"],
    )
    op.create_index("ix_landing_zones_region", "landing_zones", ["region_id"])

    # 4. Add backend_region_id FK to address_spaces
    op.add_column("address_spaces", sa.Column("backend_region_id", UUID(as_uuid=True), nullable=True))
    op.create_foreign_key(
        "fk_address_spaces_backend_region_id",
        "address_spaces",
        "backend_regions",
        ["backend_region_id"],
        ["id"],
    )

    # 5. Migrate data: landing_zone_regions -> backend_regions, populate LZ.region_id
    op.execute("""
        INSERT INTO backend_regions (id, tenant_id, backend_id, region_identifier, display_name, settings, created_at, updated_at)
        SELECT DISTINCT ON (lz.backend_id, lzr.region_identifier)
            gen_random_uuid(),
            lz.tenant_id,
            lz.backend_id,
            lzr.region_identifier,
            lzr.display_name,
            lzr.settings,
            lzr.created_at,
            lzr.updated_at
        FROM landing_zone_regions lzr
        JOIN landing_zones lz ON lz.id = lzr.landing_zone_id
        WHERE lz.deleted_at IS NULL
        ORDER BY lz.backend_id, lzr.region_identifier, lzr.is_primary DESC
    """)

    # Populate landing_zones.region_id from primary region
    op.execute("""
        UPDATE landing_zones lz
        SET region_id = br.id
        FROM landing_zone_regions lzr, backend_regions br
        WHERE lzr.landing_zone_id = lz.id
            AND lzr.is_primary = true
            AND br.backend_id = lz.backend_id
            AND br.region_identifier = lzr.region_identifier
            AND br.deleted_at IS NULL
            AND lz.deleted_at IS NULL
    """)

    # For LZs that had regions but none marked primary, pick first
    op.execute("""
        UPDATE landing_zones lz
        SET region_id = br.id
        FROM (
            SELECT DISTINCT ON (lzr.landing_zone_id)
                lzr.landing_zone_id,
                br2.id
            FROM landing_zone_regions lzr
            JOIN landing_zones lz2 ON lz2.id = lzr.landing_zone_id
            JOIN backend_regions br2 ON br2.backend_id = lz2.backend_id
                AND br2.region_identifier = lzr.region_identifier
                AND br2.deleted_at IS NULL
            ORDER BY lzr.landing_zone_id, lzr.created_at
        ) br
        WHERE br.landing_zone_id = lz.id
            AND lz.region_id IS NULL
            AND lz.deleted_at IS NULL
    """)

    # 6. Seed permissions for backend regions
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cloud', 'region', 'create', 'Create regions on cloud backends', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'region', 'read', 'View regions on cloud backends', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'region', 'update', 'Modify regions on cloud backends', true, now(), now()),
            (gen_random_uuid(), 'cloud', 'region', 'delete', 'Remove regions from cloud backends', true, now(), now())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    # Assign to Provider Admin and Tenant Admin roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, now(), now()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Provider Admin', 'Tenant Admin')
            AND p.domain = 'cloud' AND p.resource = 'region'
            AND p.action IN ('create', 'read', 'update', 'delete')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    op.drop_constraint("fk_address_spaces_backend_region_id", "address_spaces", type_="foreignkey")
    op.drop_column("address_spaces", "backend_region_id")
    op.drop_index("ix_landing_zones_region", "landing_zones")
    op.drop_constraint("fk_landing_zones_region_id", "landing_zones", type_="foreignkey")
    op.drop_column("landing_zones", "region_id")
    op.execute("""
        CREATE UNIQUE INDEX uq_cloud_backends_tenant_id
        ON cloud_backends (tenant_id)
        WHERE deleted_at IS NULL
    """)
    op.drop_index("uq_backend_region_identifier", "backend_regions")
    op.drop_index("ix_backend_regions_backend", "backend_regions")
    op.drop_index("ix_backend_regions_tenant", "backend_regions")
    op.drop_table("backend_regions")
