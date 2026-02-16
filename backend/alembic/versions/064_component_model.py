"""
Overview: Create component model, resolver, and governance tables with permissions.
Architecture: Migration for component & resolver framework (Section 11)
Dependencies: alembic, sqlalchemy
Concepts: Components are typed Pulumi scripts bound to semantic types. Resolvers handle
    deploy-time parameter pre-resolution (IPAM, naming, image catalog). Governance controls
    per-tenant allow/deny and parameter constraints.
"""

"""component model

Revision ID: 064
Revises: 063
Create Date: 2026-02-15
"""

from alembic import op

revision = "064"
down_revision = "063"
branch_labels = None
depends_on = None

NIL_UUID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # ── 1. components ──────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE components (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id),
            provider_id UUID NOT NULL REFERENCES semantic_providers(id),
            semantic_type_id UUID NOT NULL REFERENCES semantic_resource_types(id),
            name VARCHAR(255) NOT NULL,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            language VARCHAR(20) NOT NULL DEFAULT 'typescript',
            code TEXT NOT NULL DEFAULT '',
            input_schema JSONB,
            output_schema JSONB,
            resolver_bindings JSONB,
            version INTEGER NOT NULL DEFAULT 1,
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            upgrade_workflow_id UUID REFERENCES workflow_definitions(id),
            created_by UUID NOT NULL REFERENCES users(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_components_provider_tenant_name_version
        ON components (provider_id, COALESCE(tenant_id, '00000000-0000-0000-0000-000000000000'::uuid), name, version)
        WHERE deleted_at IS NULL
    """)
    op.execute("CREATE INDEX ix_components_tenant ON components (tenant_id)")
    op.execute("CREATE INDEX ix_components_provider ON components (provider_id)")
    op.execute("CREATE INDEX ix_components_semantic_type ON components (semantic_type_id)")

    # ── 2. component_versions ──────────────────────────────────────────
    op.execute("""
        CREATE TABLE component_versions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            component_id UUID NOT NULL REFERENCES components(id) ON DELETE CASCADE,
            version INTEGER NOT NULL,
            code TEXT NOT NULL,
            input_schema JSONB,
            output_schema JSONB,
            resolver_bindings JSONB,
            changelog TEXT,
            published_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            published_by UUID NOT NULL REFERENCES users(id)
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_component_versions_component_version
        ON component_versions (component_id, version)
    """)

    # ── 3. resolvers ───────────────────────────────────────────────────
    op.execute("""
        CREATE TABLE resolvers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resolver_type VARCHAR(100) NOT NULL UNIQUE,
            display_name VARCHAR(255) NOT NULL,
            description TEXT,
            input_schema JSONB,
            output_schema JSONB,
            handler_class VARCHAR(500) NOT NULL,
            is_system BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            deleted_at TIMESTAMPTZ
        )
    """)

    # ── 4. resolver_configurations ─────────────────────────────────────
    op.execute("""
        CREATE TABLE resolver_configurations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            resolver_id UUID NOT NULL REFERENCES resolvers(id),
            landing_zone_id UUID REFERENCES landing_zones(id),
            environment_id UUID REFERENCES tenant_environments(id),
            config JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_resolver_config_scope
        ON resolver_configurations (
            resolver_id,
            COALESCE(landing_zone_id, '00000000-0000-0000-0000-000000000000'::uuid),
            COALESCE(environment_id, '00000000-0000-0000-0000-000000000000'::uuid)
        )
    """)

    # ── 5. component_governance ────────────────────────────────────────
    op.execute("""
        CREATE TABLE component_governance (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            component_id UUID NOT NULL REFERENCES components(id),
            tenant_id UUID NOT NULL REFERENCES tenants(id),
            is_allowed BOOLEAN NOT NULL DEFAULT TRUE,
            parameter_constraints JSONB,
            max_instances INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)

    op.execute("""
        CREATE UNIQUE INDEX uq_component_governance_component_tenant
        ON component_governance (component_id, tenant_id)
    """)

    # ── 6. Seed built-in resolvers ─────────────────────────────────────
    op.execute("""
        INSERT INTO resolvers (resolver_type, display_name, description, handler_class, input_schema, output_schema) VALUES
        (
            'ipam',
            'IPAM Resolver',
            'Automatically allocates IP addresses and subnets from the IPAM system.',
            'app.services.resolver.ipam_resolver.IPAMResolver',
            '{"type": "object", "properties": {"allocation_type": {"type": "string", "enum": ["subnet", "ip"]}, "prefix_length": {"type": "integer"}, "parent_scope": {"type": "string"}, "ip_version": {"type": "integer", "default": 4}}}',
            '{"type": "object", "properties": {"cidr": {"type": "string"}, "gateway": {"type": "string"}, "ip_address": {"type": "string"}, "subnet_id": {"type": "string"}}}'
        ),
        (
            'naming',
            'Naming Convention Resolver',
            'Generates resource names following configurable naming patterns.',
            'app.services.resolver.naming_resolver.NamingResolver',
            '{"type": "object", "properties": {"resource_type": {"type": "string"}, "environment_name": {"type": "string"}, "sequence": {"type": "integer"}}}',
            '{"type": "object", "properties": {"name": {"type": "string"}, "fqdn": {"type": "string"}}}'
        ),
        (
            'image_catalog',
            'Image Catalog Resolver',
            'Resolves abstract OS image choices to provider-specific image references.',
            'app.services.resolver.image_resolver.ImageCatalogResolver',
            '{"type": "object", "properties": {"os_family": {"type": "string"}, "os_version": {"type": "string"}, "architecture": {"type": "string", "default": "x86_64"}}}',
            '{"type": "object", "properties": {"image_id": {"type": "string"}, "image_reference": {"type": "string"}, "image_name": {"type": "string"}}}'
        )
    """)

    # ── 7. Permissions ─────────────────────────────────────────────────
    # Columns: domain, resource, action, subtype
    permissions = [
        ("component", "definition", "read", None, "Read component definitions"),
        ("component", "definition", "create", None, "Create component definitions"),
        ("component", "definition", "update", None, "Update component definitions"),
        ("component", "definition", "delete", None, "Delete component definitions"),
        ("component", "definition", "publish", None, "Publish component definitions"),
        ("component", "governance", "manage", None, "Manage component governance rules"),
        ("resolver", "config", "read", None, "Read resolver configurations"),
        ("resolver", "config", "manage", None, "Manage resolver configurations"),
    ]

    for domain, resource, action, subtype, desc in permissions:
        sub_val = f"'{subtype}'" if subtype else "NULL"
        op.execute(f"""
            INSERT INTO permissions (id, domain, resource, action, subtype, description, is_system, created_at, updated_at)
            VALUES (gen_random_uuid(), '{domain}', '{resource}', '{action}', {sub_val}, '{desc}', TRUE, NOW(), NOW())
            ON CONFLICT ON CONSTRAINT uq_permission_key DO NOTHING
        """)

    # Role assignments — PascalCase role names!
    # Read-Only+ gets read permissions
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Read Only', 'User', 'Tenant Admin', 'Provider Admin')
          AND (
            (p.domain = 'component' AND p.resource = 'definition' AND p.action = 'read')
            OR (p.domain = 'resolver' AND p.resource = 'config' AND p.action = 'read')
          )
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # Tenant Admin+ gets create/update/delete
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name IN ('Tenant Admin', 'Provider Admin')
          AND p.domain = 'component' AND p.resource = 'definition'
          AND p.action IN ('create', 'update', 'delete')
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)

    # Provider Admin only gets publish, governance manage, resolver manage
    op.execute("""
        INSERT INTO role_permissions (id, role_id, permission_id, created_at, updated_at)
        SELECT gen_random_uuid(), r.id, p.id, NOW(), NOW()
        FROM roles r
        CROSS JOIN permissions p
        WHERE r.name = 'Provider Admin'
          AND (
            (p.domain = 'component' AND p.resource = 'definition' AND p.action = 'publish')
            OR (p.domain = 'component' AND p.resource = 'governance' AND p.action = 'manage')
            OR (p.domain = 'resolver' AND p.resource = 'config' AND p.action = 'manage')
          )
          AND NOT EXISTS (
            SELECT 1 FROM role_permissions rp WHERE rp.role_id = r.id AND rp.permission_id = p.id
          )
    """)


def downgrade() -> None:
    # Remove role_permissions
    op.execute("""
        DELETE FROM role_permissions WHERE permission_id IN (
            SELECT id FROM permissions WHERE domain IN ('component', 'resolver')
        )
    """)
    op.execute("DELETE FROM permissions WHERE domain IN ('component', 'resolver')")

    op.execute("DROP TABLE IF EXISTS component_governance")
    op.execute("DROP TABLE IF EXISTS resolver_configurations")
    op.execute("DROP TABLE IF EXISTS resolvers")
    op.execute("DROP TABLE IF EXISTS component_versions")
    op.execute("DROP TABLE IF EXISTS components")
