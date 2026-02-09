"""
Overview: Service form redesign — multi-CI-class junction, CI class ↔ activity associations.
Architecture: Catalog form enhancement migration (Section 8)
Dependencies: alembic, sqlalchemy
Concepts: Replaces single ci_class_id FK on service_offerings with a many-to-many junction table.
    Adds ci_class_activity_associations for tenant-scoped relationship management.
"""

revision: str = "024"
down_revision: str | None = "023"
branch_labels: str | None = None
depends_on: str | None = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # 1. Create service_offering_ci_classes junction table
    op.create_table(
        "service_offering_ci_classes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("service_offering_id", UUID(as_uuid=True), sa.ForeignKey("service_offerings.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ci_class_id", UUID(as_uuid=True), sa.ForeignKey("ci_classes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("service_offering_id", "ci_class_id", name="uq_offering_ci_class"),
    )
    op.create_index("ix_service_offering_ci_classes_offering_id", "service_offering_ci_classes", ["service_offering_id"])
    op.create_index("ix_service_offering_ci_classes_ci_class_id", "service_offering_ci_classes", ["ci_class_id"])

    # 2. Create ci_class_activity_associations table
    op.create_table(
        "ci_class_activity_associations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("ci_class_id", UUID(as_uuid=True), sa.ForeignKey("ci_classes.id"), nullable=False),
        sa.Column("activity_template_id", UUID(as_uuid=True), sa.ForeignKey("activity_templates.id"), nullable=False),
        sa.Column("relationship_type", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "ci_class_id", "activity_template_id", "relationship_type", name="uq_ci_class_activity_assoc"),
    )
    op.create_index("ix_ci_class_activity_associations_tenant_id", "ci_class_activity_associations", ["tenant_id"])
    op.create_index("ix_ci_class_activity_associations_ci_class_id", "ci_class_activity_associations", ["ci_class_id"])
    op.create_index("ix_ci_class_activity_associations_template_id", "ci_class_activity_associations", ["activity_template_id"])

    # 3. Migrate existing ci_class_id data into junction table
    op.execute("""
        INSERT INTO service_offering_ci_classes (id, service_offering_id, ci_class_id, created_at, updated_at)
        SELECT gen_random_uuid(), id, ci_class_id, NOW(), NOW()
        FROM service_offerings
        WHERE ci_class_id IS NOT NULL AND deleted_at IS NULL
    """)

    # 4. Drop the old ci_class_id FK constraint and column
    # Find and drop the FK constraint first
    op.drop_constraint("service_offerings_ci_class_id_fkey", "service_offerings", type_="foreignkey")
    op.drop_column("service_offerings", "ci_class_id")

    # 5. Seed permissions
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
        VALUES
            (gen_random_uuid(), 'cmdb', 'activity-association', 'read', NULL, 'View CI class to activity template associations', true, NOW(), NOW()),
            (gen_random_uuid(), 'cmdb', 'activity-association', 'manage', NULL, 'Create and delete CI class to activity template associations', true, NOW(), NOW())
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
    """)

    # Assign permissions to Tenant Admin and Provider Admin roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'cmdb' AND p.resource = 'activity-association'
          AND p.action IN ('read', 'manage')
        ON CONFLICT DO NOTHING
    """)


def downgrade() -> None:
    # Remove permission assignments
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'cmdb' AND resource = 'activity-association'
              AND action IN ('read', 'manage')
        )
    """)
    op.execute("""
        DELETE FROM permissions
        WHERE domain = 'cmdb' AND resource = 'activity-association'
          AND action IN ('read', 'manage')
    """)

    # Re-add ci_class_id column
    op.add_column(
        "service_offerings",
        sa.Column("ci_class_id", UUID(as_uuid=True), sa.ForeignKey("ci_classes.id"), nullable=True),
    )

    # Migrate data back from junction table
    op.execute("""
        UPDATE service_offerings so
        SET ci_class_id = socc.ci_class_id
        FROM (
            SELECT DISTINCT ON (service_offering_id) service_offering_id, ci_class_id
            FROM service_offering_ci_classes
            ORDER BY service_offering_id, created_at
        ) socc
        WHERE so.id = socc.service_offering_id
    """)

    # Drop tables
    op.drop_index("ix_ci_class_activity_associations_template_id")
    op.drop_index("ix_ci_class_activity_associations_ci_class_id")
    op.drop_index("ix_ci_class_activity_associations_tenant_id")
    op.drop_table("ci_class_activity_associations")

    op.drop_index("ix_service_offering_ci_classes_ci_class_id")
    op.drop_index("ix_service_offering_ci_classes_offering_id")
    op.drop_table("service_offering_ci_classes")
