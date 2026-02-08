"""Permissions, identity providers, SCIM, groups, ABAC.

Revision ID: 003
Revises: 002
Create Date: 2026-02-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSON, UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enums ────────────────────────────────────────────────────────
    idp_type_enum = sa.Enum("local", "oidc", "saml", name="idp_type_enum", create_type=True)
    role_tier_enum = sa.Enum(
        "provider", "tenant_admin", "user", "read_only", name="role_tier_enum", create_type=True
    )
    policy_effect_enum = sa.Enum("allow", "deny", name="policy_effect_enum", create_type=True)

    # ── 1. Identity Providers ────────────────────────────────────────
    op.create_table(
        "identity_providers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("idp_type", idp_type_enum, nullable=False),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.text("false")),
        sa.Column("config", JSON, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_identity_providers_tenant_id", "identity_providers", ["tenant_id"])

    # ── 2. Permissions ───────────────────────────────────────────────
    op.create_table(
        "permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(100), nullable=False),
        sa.Column("resource", sa.String(100), nullable=False),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("subtype", sa.String(100), nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_system", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "domain", "resource", "action", "subtype", name="uq_permission_key"
        ),
    )

    # ── 3. Groups ────────────────────────────────────────────────────
    op.create_table(
        "groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "parent_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_groups_tenant_id", "groups", ["tenant_id"])
    op.create_index("ix_groups_parent_id", "groups", ["parent_id"])

    # ── 4. IdP Claim Mappings ────────────────────────────────────────
    op.create_table(
        "idp_claim_mappings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "identity_provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity_providers.id"),
            nullable=False,
        ),
        sa.Column("claim_name", sa.String(255), nullable=False),
        sa.Column("claim_value", sa.String(255), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_idp_claim_mappings_identity_provider_id",
        "idp_claim_mappings",
        ["identity_provider_id"],
    )

    # ── 5. SCIM Tokens ───────────────────────────────────────────────
    op.create_table(
        "scim_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("token_hash", sa.String(255), nullable=False, unique=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_scim_tokens_tenant_id", "scim_tokens", ["tenant_id"])

    # ── 6. Role Permissions ──────────────────────────────────────────
    op.create_table(
        "role_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column(
            "permission_id", UUID(as_uuid=True), sa.ForeignKey("permissions.id"), nullable=False
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )
    op.create_index("ix_role_permissions_role_id", "role_permissions", ["role_id"])
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])

    # ── 7. User Groups ───────────────────────────────────────────────
    op.create_table(
        "user_groups",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("user_id", "group_id", name="uq_user_group"),
    )
    op.create_index("ix_user_groups_user_id", "user_groups", ["user_id"])
    op.create_index("ix_user_groups_group_id", "user_groups", ["group_id"])

    # ── 8. Group Roles ───────────────────────────────────────────────
    op.create_table(
        "group_roles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("group_id", UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("group_id", "role_id", name="uq_group_role"),
    )
    op.create_index("ix_group_roles_group_id", "group_roles", ["group_id"])
    op.create_index("ix_group_roles_role_id", "group_roles", ["role_id"])

    # ── 9. ABAC Policies ─────────────────────────────────────────────
    op.create_table(
        "abac_policies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("expression", sa.Text, nullable=False),
        sa.Column("effect", policy_effect_enum, nullable=False),
        sa.Column("priority", sa.Integer, nullable=False, server_default=sa.text("0")),
        sa.Column("is_enabled", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "target_permission_id",
            UUID(as_uuid=True),
            sa.ForeignKey("permissions.id"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_abac_policies_tenant_id", "abac_policies", ["tenant_id"])

    # ── ALTER existing tables ────────────────────────────────────────

    # 10. roles: add parent_role_id, tier, is_custom, max_level, deleted_at
    # Explicitly create role_tier_enum since add_column doesn't auto-create enums
    role_tier_enum.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "roles",
        sa.Column(
            "parent_role_id", UUID(as_uuid=True), sa.ForeignKey("roles.id"), nullable=True
        ),
    )
    op.add_column("roles", sa.Column("tier", role_tier_enum, nullable=True))
    op.add_column(
        "roles",
        sa.Column("is_custom", sa.Boolean, nullable=False, server_default=sa.text("false")),
    )
    op.add_column("roles", sa.Column("max_level", sa.Integer, nullable=True))
    op.add_column("roles", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_roles_parent_role_id", "roles", ["parent_role_id"])

    # 11. user_roles: add compartment_id, granted_by, expires_at
    op.add_column(
        "user_roles",
        sa.Column(
            "compartment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("compartments.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_roles",
        sa.Column("granted_by", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "user_roles",
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_user_roles_compartment_id", "user_roles", ["compartment_id"])

    # 12. users: add identity_provider_id, external_id; make password_hash nullable
    op.add_column(
        "users",
        sa.Column(
            "identity_provider_id",
            UUID(as_uuid=True),
            sa.ForeignKey("identity_providers.id"),
            nullable=True,
        ),
    )
    op.add_column("users", sa.Column("external_id", sa.String(255), nullable=True))
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)


def downgrade() -> None:
    # Reverse ALTER on users
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    op.drop_column("users", "external_id")
    op.drop_column("users", "identity_provider_id")

    # Reverse ALTER on user_roles
    op.drop_index("ix_user_roles_compartment_id", "user_roles")
    op.drop_column("user_roles", "expires_at")
    op.drop_column("user_roles", "granted_by")
    op.drop_column("user_roles", "compartment_id")

    # Reverse ALTER on roles
    op.drop_index("ix_roles_parent_role_id", "roles")
    op.drop_column("roles", "deleted_at")
    op.drop_column("roles", "max_level")
    op.drop_column("roles", "is_custom")
    op.drop_column("roles", "tier")
    op.drop_column("roles", "parent_role_id")

    # Drop new tables in reverse order
    op.drop_table("abac_policies")
    op.drop_table("group_roles")
    op.drop_table("user_groups")
    op.drop_table("role_permissions")
    op.drop_table("scim_tokens")
    op.drop_table("idp_claim_mappings")
    op.drop_table("groups")
    op.drop_table("permissions")
    op.drop_table("identity_providers")

    # Drop enums
    sa.Enum(name="policy_effect_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="role_tier_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="idp_type_enum").drop(op.get_bind(), checkfirst=True)
