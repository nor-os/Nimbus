"""
Overview: Add workflow_type discriminator (AUTOMATION/SYSTEM/DEPLOYMENT) to workflow_definitions,
    source_topology_id FK, and is_system flag. Seeds new permissions.
Architecture: Database migration (Section 6)
Dependencies: alembic, sqlalchemy
Concepts: Workflow classification, deployment workflows, system workflow templates
"""

revision = "051"
down_revision = "050"
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


def upgrade() -> None:
    # Create the workflow_type enum
    workflow_type_enum = sa.Enum(
        "AUTOMATION", "SYSTEM", "DEPLOYMENT",
        name="workflow_type",
        create_type=True,
    )
    workflow_type_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to workflow_definitions
    op.add_column(
        "workflow_definitions",
        sa.Column(
            "workflow_type",
            workflow_type_enum,
            nullable=False,
            server_default="AUTOMATION",
        ),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column(
            "source_topology_id",
            UUID(as_uuid=True),
            sa.ForeignKey("architecture_topologies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "workflow_definitions",
        sa.Column(
            "is_system",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )

    # Add indexes
    op.create_index(
        "ix_workflow_definitions_type",
        "workflow_definitions",
        ["tenant_id", "workflow_type"],
    )
    op.create_index(
        "ix_workflow_definitions_source_topology",
        "workflow_definitions",
        ["source_topology_id"],
    )

    # Seed permissions (columns: domain, resource, action, description, is_system)
    op.execute("""
        INSERT INTO permissions (id, domain, resource, action, description, is_system)
        VALUES
            (gen_random_uuid(), 'workflow', 'deployment', 'generate',
             'Generate a deployment workflow from a topology', true),
            (gen_random_uuid(), 'workflow', 'system', 'manage',
             'Seed and manage system workflow templates', true)
        ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING;
    """)

    # Assign to Tenant Admin and Provider Admin roles
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id)
        SELECT gen_random_uuid(), r.id, p.id
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'workflow'
          AND p.resource IN ('deployment', 'system')
          AND p.action IN ('generate', 'manage')
          AND NOT EXISTS (
              SELECT 1 FROM role_permissions rp
              WHERE rp.role_id = r.id AND rp.permission_id = p.id
          );
    """)


def downgrade() -> None:
    op.drop_index("ix_workflow_definitions_source_topology")
    op.drop_index("ix_workflow_definitions_type")
    op.drop_column("workflow_definitions", "is_system")
    op.drop_column("workflow_definitions", "source_topology_id")
    op.drop_column("workflow_definitions", "workflow_type")

    # Remove seeded permissions
    op.execute("""
        DELETE FROM role_permissions
        WHERE permission_id IN (
            SELECT id FROM permissions
            WHERE domain = 'workflow'
              AND resource IN ('deployment', 'system')
              AND action IN ('generate', 'manage')
        );
    """)
    op.execute("""
        DELETE FROM permissions
        WHERE domain = 'workflow'
          AND resource IN ('deployment', 'system')
          AND action IN ('generate', 'manage');
    """)

    sa.Enum(name="workflow_type").drop(op.get_bind(), checkfirst=True)
