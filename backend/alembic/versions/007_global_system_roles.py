"""Consolidate per-tenant system roles to global (tenant_id=NULL).

Revision ID: 007
Revises: 006
Create Date: 2026-02-07
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Consolidate per-tenant system role copies into single global rows.

    Strategy:
    1. For each system role name, pick the canonical one (lowest created_at).
    2. Remap user_roles.role_id and group_roles.role_id from per-tenant copies to canonical.
    3. Delete orphaned role_permissions for non-canonical copies.
    4. Delete the non-canonical system role rows.
    5. Set tenant_id = NULL on canonical system roles.
    """
    conn = op.get_bind()

    # Step 1: Identify canonical system roles (one per name, earliest created_at)
    canonical_rows = conn.execute(
        sa.text("""
            SELECT DISTINCT ON (name) id, name
            FROM roles
            WHERE is_system = true AND deleted_at IS NULL
            ORDER BY name, created_at ASC
        """)
    ).fetchall()

    if not canonical_rows:
        return

    canonical_map = {row[1]: row[0] for row in canonical_rows}  # name -> canonical id
    canonical_ids = set(canonical_map.values())

    # Step 2: Find all non-canonical system role copies
    all_system_rows = conn.execute(
        sa.text("""
            SELECT id, name
            FROM roles
            WHERE is_system = true AND deleted_at IS NULL
        """)
    ).fetchall()

    non_canonical = [(row[0], row[1]) for row in all_system_rows if row[0] not in canonical_ids]

    # Step 3: Remap user_roles and group_roles from non-canonical to canonical
    for old_id, role_name in non_canonical:
        new_id = canonical_map[role_name]

        # Remap user_roles — skip if the canonical assignment already exists
        conn.execute(
            sa.text("""
                UPDATE user_roles
                SET role_id = :new_id
                WHERE role_id = :old_id
                  AND NOT EXISTS (
                      SELECT 1 FROM user_roles ur2
                      WHERE ur2.user_id = user_roles.user_id
                        AND ur2.tenant_id = user_roles.tenant_id
                        AND ur2.role_id = :new_id
                  )
            """),
            {"old_id": old_id, "new_id": new_id},
        )

        # Delete any remaining user_roles that point to old_id (duplicates)
        conn.execute(
            sa.text("DELETE FROM user_roles WHERE role_id = :old_id"),
            {"old_id": old_id},
        )

        # Remap group_roles — skip if canonical assignment already exists
        conn.execute(
            sa.text("""
                UPDATE group_roles
                SET role_id = :new_id
                WHERE role_id = :old_id
                  AND NOT EXISTS (
                      SELECT 1 FROM group_roles gr2
                      WHERE gr2.group_id = group_roles.group_id
                        AND gr2.role_id = :new_id
                  )
            """),
            {"old_id": old_id, "new_id": new_id},
        )

        # Delete remaining group_roles pointing to old_id
        conn.execute(
            sa.text("DELETE FROM group_roles WHERE role_id = :old_id"),
            {"old_id": old_id},
        )

    # Step 4: Delete role_permissions for non-canonical system roles
    for old_id, _ in non_canonical:
        conn.execute(
            sa.text("DELETE FROM role_permissions WHERE role_id = :old_id"),
            {"old_id": old_id},
        )

    # Step 5: Delete the non-canonical system role rows
    for old_id, _ in non_canonical:
        conn.execute(
            sa.text("DELETE FROM roles WHERE id = :old_id"),
            {"old_id": old_id},
        )

    # Step 6: Set tenant_id = NULL on canonical system roles
    for canonical_id in canonical_ids:
        conn.execute(
            sa.text("UPDATE roles SET tenant_id = NULL WHERE id = :id"),
            {"id": canonical_id},
        )


def downgrade() -> None:
    """Reverse: re-create per-tenant system role copies.

    For each tenant that has user_roles or group_roles referencing a global system role,
    create a tenant-scoped copy and remap references back.
    """
    conn = op.get_bind()

    # Get all global system roles
    global_roles = conn.execute(
        sa.text("""
            SELECT id, name, description, scope
            FROM roles
            WHERE is_system = true AND tenant_id IS NULL AND deleted_at IS NULL
        """)
    ).fetchall()

    if not global_roles:
        return

    # Get all tenants
    tenants = conn.execute(
        sa.text("SELECT id FROM tenants WHERE deleted_at IS NULL")
    ).fetchall()

    for tenant_row in tenants:
        tenant_id = tenant_row[0]

        for global_id, role_name, description, scope in global_roles:
            # Check if this tenant has any references to this global role
            has_user_roles = conn.execute(
                sa.text("""
                    SELECT 1 FROM user_roles
                    WHERE role_id = :role_id AND tenant_id = :tenant_id
                    LIMIT 1
                """),
                {"role_id": global_id, "tenant_id": tenant_id},
            ).fetchone()

            has_group_roles = conn.execute(
                sa.text("""
                    SELECT 1 FROM group_roles gr
                    JOIN groups g ON g.id = gr.group_id
                    WHERE gr.role_id = :role_id AND g.tenant_id = :tenant_id
                    LIMIT 1
                """),
                {"role_id": global_id, "tenant_id": tenant_id},
            ).fetchone()

            if not has_user_roles and not has_group_roles:
                continue

            # Create tenant-scoped copy
            new_role = conn.execute(
                sa.text("""
                    INSERT INTO roles (tenant_id, name, description, scope, is_system, is_custom)
                    VALUES (:tenant_id, :name, :desc, :scope, true, false)
                    RETURNING id
                """),
                {
                    "tenant_id": tenant_id,
                    "name": role_name,
                    "desc": description,
                    "scope": scope,
                },
            ).fetchone()
            new_id = new_role[0]

            # Copy role_permissions from global role
            conn.execute(
                sa.text("""
                    INSERT INTO role_permissions (role_id, permission_id)
                    SELECT :new_id, permission_id
                    FROM role_permissions
                    WHERE role_id = :global_id
                """),
                {"new_id": new_id, "global_id": global_id},
            )

            # Remap user_roles for this tenant
            conn.execute(
                sa.text("""
                    UPDATE user_roles
                    SET role_id = :new_id
                    WHERE role_id = :global_id AND tenant_id = :tenant_id
                """),
                {"new_id": new_id, "global_id": global_id, "tenant_id": tenant_id},
            )

            # Remap group_roles for groups in this tenant
            conn.execute(
                sa.text("""
                    UPDATE group_roles
                    SET role_id = :new_id
                    WHERE role_id = :global_id
                      AND group_id IN (
                          SELECT id FROM groups WHERE tenant_id = :tenant_id
                      )
                """),
                {"new_id": new_id, "global_id": global_id, "tenant_id": tenant_id},
            )

    # Assign the global system roles back to the first tenant (root)
    # so they don't become orphaned; then set tenant_id on remaining globals
    root_tenant = conn.execute(
        sa.text("""
            SELECT id FROM tenants
            WHERE parent_id IS NULL AND deleted_at IS NULL
            ORDER BY created_at ASC LIMIT 1
        """)
    ).fetchone()

    if root_tenant:
        for global_id, _, _, _ in global_roles:
            conn.execute(
                sa.text("UPDATE roles SET tenant_id = :tid WHERE id = :id"),
                {"tid": root_tenant[0], "id": global_id},
            )
