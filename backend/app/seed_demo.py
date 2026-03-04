"""
Overview: Standalone demo data seeder — runs setup wizard + runtime seeders + migration seeds.
Architecture: Called as a one-shot container after migrations and backend are up.
Dependencies: httpx, sqlalchemy, app.services, alembic.versions (migration seed helpers)
Concepts: Idempotent seeding, setup wizard automation, demo data population
"""

import asyncio
import importlib.util
import logging
import os
import sys
from pathlib import Path
from types import ModuleType

import httpx
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.tenant import Tenant
from app.models.user import User
from app.services.cmdb.class_seed import sync_semantic_types_to_ci_classes
from app.services.component.operation_service import ComponentOperationService
from app.services.notification.template_service import TemplateService
from app.services.workflow.system_workflow_seeder import SystemWorkflowSeeder

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("seed_demo")

# ── Configuration ───────────────────────────────────────────────
DATABASE_URL = os.environ.get(
    "NIMBUS_DATABASE_URL",
    "postgresql+asyncpg://nimbus:nimbus_dev@localhost:5432/nimbus",
)
BACKEND_URL = os.environ.get("NIMBUS_BACKEND_URL", "http://localhost:8000")
ADMIN_EMAIL = os.environ.get("NIMBUS_ADMIN_EMAIL", "admin@nimbus.dev")
ADMIN_PASSWORD = os.environ.get("NIMBUS_ADMIN_PASSWORD", "admin")
ORG_NAME = os.environ.get("NIMBUS_ORG_NAME", "Nimbus Demo")


async def call_setup_wizard() -> bool:
    """POST /api/v1/setup/initialize to run the first-run wizard.

    Returns True if setup was performed, False if already complete.
    """
    url = f"{BACKEND_URL}/api/v1/setup/initialize"
    payload = {
        "admin_email": ADMIN_EMAIL,
        "admin_password": ADMIN_PASSWORD,
        "organization_name": ORG_NAME,
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(url, json=payload)

    if resp.status_code == 200:
        logger.info("Setup wizard completed — provider, admin, root tenant created")
        return True

    if resp.status_code == 409:
        detail = resp.json().get("detail", {})
        code = detail.get("error", {}).get("code", "")
        if code == "ALREADY_SETUP":
            logger.info("Setup already complete — skipping")
            return False
        logger.warning("Setup returned 409: %s", detail)
        return False

    logger.error("Setup wizard failed: %s %s", resp.status_code, resp.text)
    sys.exit(1)


# ── Migration seed replay ──────────────────────────────────────
# Migrations 025, 038, 039, 084 silently skip when root tenant
# doesn't exist at migration time. After the setup wizard creates
# the tenant we replay their seed logic via run_sync (same pattern
# Alembic uses — asyncpg connection in sync mode, no psycopg2).

# Resolve alembic/versions/ directory (relative to backend root)
_BACKEND_DIR = Path(__file__).resolve().parent.parent  # backend/
_VERSIONS_DIR = _BACKEND_DIR / "alembic" / "versions"


def _load_migration(filename: str) -> ModuleType:
    """Load an Alembic migration file by filename (not a package import)."""
    path = _VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(filename.removesuffix(".py"), path)
    if not spec or not spec.loader:
        raise ImportError(f"Cannot load migration: {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _get_root_tenant_id(conn) -> str | None:
    row = conn.execute(
        sa.text("SELECT id FROM tenants WHERE parent_id IS NULL AND deleted_at IS NULL LIMIT 1")
    ).fetchone()
    return str(row[0]) if row else None


def _replay_025(conn, tid: str) -> None:
    """Activity templates, service processes, offerings, process assignments."""
    count = conn.execute(
        sa.text("SELECT count(*) FROM activity_templates WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar()
    if count and count > 0:
        logger.info("Migration 025: %d activity templates exist — skipping", count)
        return

    profiles = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM staff_profiles WHERE is_system = true AND deleted_at IS NULL")
    ):
        profiles[r[0]] = str(r[1])

    jr = profiles.get("junior_engineer")
    eng = profiles.get("engineer")
    sr = profiles.get("senior_engineer")
    con = profiles.get("consultant")
    sc = profiles.get("senior_consultant")
    arch = profiles.get("architect")

    if not all([jr, eng, sr, con, sc, arch]):
        logger.warning("Migration 025: staff profiles missing — skipping")
        return

    m = _load_migration("025_seed_catalog.py")
    m._seed_activity_templates(conn, tid, jr, eng, sr, con, sc, arch)
    m._seed_service_processes(conn, tid)
    m._seed_service_offerings(conn, tid)
    m._seed_process_assignments(conn, tid)
    logger.info("Migration 025: activities, processes, offerings seeded")


def _replay_038(conn, tid: str) -> None:
    """Service groups, catalogs, rate cards, price lists."""
    count = conn.execute(
        sa.text("SELECT count(*) FROM service_groups WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar()
    if count and count > 0:
        logger.info("Migration 038: %d service groups exist — skipping", count)
        return

    m = _load_migration("038_seed_catalog_demo_data.py")

    # Backfill offerings if 025 didn't create them
    existing = conn.execute(
        sa.text("SELECT count(*) FROM service_offerings WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar()
    if not existing:
        m._seed_service_offerings(conn, tid)
        m._seed_process_assignments(conn, tid)

    # Resolve IDs by name
    offerings = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM service_offerings WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ):
        offerings[r[0]] = str(r[1])
    if not offerings:
        logger.warning("Migration 038: no offerings — skipping")
        return

    regions = {}
    for r in conn.execute(
        sa.text("SELECT code, id FROM delivery_regions WHERE is_system = true AND deleted_at IS NULL")
    ):
        regions[r[0]] = str(r[1])

    profiles = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM staff_profiles WHERE is_system = true AND deleted_at IS NULL")
    ):
        profiles[r[0]] = str(r[1])

    activity_defs = {}
    for r in conn.execute(
        sa.text("""
            SELECT ad.name, ad.id
            FROM activity_definitions ad
            JOIN activity_templates at ON ad.template_id = at.id
            WHERE at.tenant_id = :tid AND ad.deleted_at IS NULL AND at.deleted_at IS NULL
        """),
        {"tid": tid},
    ):
        activity_defs[r[0]] = str(r[1])

    m._seed_service_groups(conn, tid, offerings)
    m._seed_service_catalogs(conn, tid, offerings)
    m._seed_rate_cards(conn, tid, profiles, regions)
    m._seed_price_lists(conn, tid, offerings, activity_defs, regions)
    logger.info("Migration 038: groups, catalogs, rate cards, price lists seeded")


def _replay_039(conn, tid: str) -> None:
    """Cloud backends and provider SKUs."""
    count = conn.execute(
        sa.text("SELECT count(*) FROM cloud_backends WHERE tenant_id = :tid AND deleted_at IS NULL"),
        {"tid": tid},
    ).scalar()
    if count and count > 0:
        logger.info("Migration 039: %d cloud backends exist — skipping", count)
        return

    providers = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM semantic_providers WHERE deleted_at IS NULL")
    ):
        providers[r[0]] = str(r[1])
    if len(providers) < 5:
        logger.warning("Migration 039: fewer than 5 providers — skipping")
        return

    ci = {}
    for r in conn.execute(
        sa.text("SELECT name, id FROM ci_classes WHERE is_system = true AND deleted_at IS NULL")
    ):
        ci[r[0]] = str(r[1])

    m = _load_migration("039_seed_cloud_backends_and_skus.py")
    m._seed_cloud_backends(conn, tid, providers)
    m._seed_provider_skus(conn, providers, ci)
    logger.info("Migration 039: cloud backends and SKUs seeded")


def _replay_084(conn, tid: str) -> None:
    """Enterprise demo data (regions, landing zones, environments, address spaces).

    Migration 084 has all logic inline (no helper functions) and uses ON CONFLICT
    DO NOTHING throughout. We call upgrade() via an Alembic Operations context.
    """
    count = conn.execute(
        sa.text("""
            SELECT count(*) FROM backend_regions br
            JOIN cloud_backends cb ON br.backend_id = cb.id
            WHERE cb.tenant_id = :tid AND br.deleted_at IS NULL
        """),
        {"tid": tid},
    ).scalar()
    if count and count > 0:
        logger.info("Migration 084: %d backend regions exist — skipping", count)
        return

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mc = MigrationContext.configure(conn)
    with Operations.context(mc):
        m = _load_migration("084_seed_enterprise_demo_data.py")
        m.upgrade()

    logger.info("Migration 084: enterprise demo data seeded")


def _replay_components(conn) -> None:
    """Seed system components (Proxmox VM + OCI Flex VM).

    Migrations 065/066/068/073 cannot be replayed because later migrations (098)
    dropped columns they reference (input_schema, output_schema, resolver_bindings
    from components/component_versions/component_operations). Instead we insert
    directly using the current schema. Day-2 operations and deployment operations
    are provisioned at runtime via provision_deployment_operations.
    """
    count = conn.execute(
        sa.text("SELECT count(*) FROM components WHERE is_system = true")
    ).scalar()
    if count and count > 0:
        logger.info("Components: %d system components exist — skipping", count)
        return

    # Look up prerequisites
    user = conn.execute(
        sa.text("SELECT id FROM users ORDER BY created_at ASC LIMIT 1")
    ).fetchone()
    if not user:
        logger.warning("Components: no users found — skipping")
        return

    providers = {}
    for r in conn.execute(sa.text("SELECT name, id FROM semantic_providers WHERE deleted_at IS NULL")):
        providers[r[0]] = str(r[1])

    vm_type = conn.execute(
        sa.text("SELECT id FROM semantic_resource_types WHERE name = 'VirtualMachine' LIMIT 1")
    ).fetchone()
    if not vm_type:
        logger.warning("Components: VirtualMachine semantic type not found — skipping")
        return

    user_id = str(user[0])
    vm_type_id = str(vm_type[0])

    # Load code from migration modules (they have the full source text)
    m066 = _load_migration("066_update_and_add_example_components.py")

    # ── Proxmox VM ──
    pve_provider = providers.get("proxmox")
    if pve_provider:
        conn.execute(sa.text("""
            INSERT INTO components (
                id, tenant_id, provider_id, semantic_type_id,
                name, display_name, description, language,
                code, version, is_published, is_system,
                created_by, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), NULL, :provider_id, :semantic_type_id,
                'pve-vm-basic', 'Proxmox Basic VM',
                'Deploy a KVM virtual machine on Proxmox VE with IPAM, naming, and image resolution',
                'PYTHON', :code, 2, true, true,
                :user_id, NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
        """), {
            "provider_id": pve_provider,
            "semantic_type_id": vm_type_id,
            "user_id": user_id,
            "code": m066.PVE_CODE,
        })

        pve_comp = conn.execute(
            sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND tenant_id IS NULL LIMIT 1")
        ).fetchone()
        if pve_comp:
            conn.execute(sa.text("""
                INSERT INTO component_versions (
                    id, component_id, version, code,
                    changelog, published_at, published_by
                ) VALUES (
                    gen_random_uuid(), :comp_id, 1, :code,
                    'Initial release — basic Proxmox KVM VM with resolver bindings',
                    NOW(), :user_id
                )
                ON CONFLICT DO NOTHING
            """), {
                "comp_id": str(pve_comp[0]),
                "user_id": user_id,
                "code": m066.PVE_CODE,
            })
        logger.info("Component seed: pve-vm-basic created")

    # ── OCI Flex VM ──
    oci_provider = providers.get("oci")
    if oci_provider:
        conn.execute(sa.text("""
            INSERT INTO components (
                id, tenant_id, provider_id, semantic_type_id,
                name, display_name, description, language,
                code, version, is_published, is_system,
                created_by, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), NULL, :provider_id, :semantic_type_id,
                'oci-vm-flex', 'OCI Flex Compute Instance',
                'Deploy a flexible compute instance on Oracle Cloud Infrastructure with shape config, VNIC, and cloud-init',
                'PYTHON', :code, 2, true, true,
                :user_id, NOW(), NOW()
            )
            ON CONFLICT DO NOTHING
        """), {
            "provider_id": oci_provider,
            "semantic_type_id": vm_type_id,
            "user_id": user_id,
            "code": m066.OCI_CODE,
        })

        oci_comp = conn.execute(
            sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND tenant_id IS NULL LIMIT 1")
        ).fetchone()
        if oci_comp:
            conn.execute(sa.text("""
                INSERT INTO component_versions (
                    id, component_id, version, code,
                    changelog, published_at, published_by
                ) VALUES (
                    gen_random_uuid(), :comp_id, 1, :code,
                    'Initial release — OCI flex compute instance with IPAM, naming, and image catalog resolvers',
                    NOW(), :user_id
                )
                ON CONFLICT DO NOTHING
            """), {
                "comp_id": str(oci_comp[0]),
                "user_id": user_id,
                "code": m066.OCI_CODE,
            })
        logger.info("Component seed: oci-vm-flex created")

    logger.info("Component seeds done")


def _replay_deployment_operations(conn) -> None:
    """Deployment workflow templates (090) and activities (092).

    090 mixes DDL (add_column) with seed INSERTs, so we can't call upgrade()
    after migrations have already run. Instead we seed directly with ON CONFLICT
    guards for idempotency. 093 is a pure UPDATE (no DDL) so we replay it via
    Alembic Operations context.
    """
    # ── Deployment workflow templates (from 090) ──
    template_count = conn.execute(
        sa.text("""
            SELECT count(*) FROM workflow_definitions
            WHERE is_template = true AND is_system = true
              AND workflow_type = 'DEPLOYMENT'
        """)
    ).scalar()

    if not template_count or template_count < 6:
        system_tenant = "00000000-0000-0000-0000-000000000000"
        empty_graph = '{"nodes": [], "connections": []}'
        templates = [
            ("deployment:deploy", "Default deployment workflow template — provisions a new resource."),
            ("deployment:decommission", "Default decommission workflow template — tears down a resource."),
            ("deployment:rollback", "Default rollback workflow template — reverts to a previous version."),
            ("deployment:upgrade", "Default upgrade workflow template — updates a resource in place."),
            ("deployment:validate", "Default validation workflow template — checks resource health."),
            ("deployment:dry-run", "Default dry-run workflow template — simulates deployment without changes."),
        ]
        for name, desc in templates:
            conn.execute(
                sa.text("""
                    INSERT INTO workflow_definitions (
                        id, tenant_id, name, description, version, graph, status,
                        created_by, timeout_seconds, max_concurrent, workflow_type,
                        is_system, is_template, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), CAST(:tid AS uuid), :name, :desc, 0,
                        CAST(:graph AS jsonb), 'ACTIVE', CAST(:tid AS uuid), 3600, 10,
                        'DEPLOYMENT', true, true, now(), now()
                    )
                    ON CONFLICT ON CONSTRAINT uq_workflow_def_tenant_name_version DO NOTHING
                """),
                {"tid": system_tenant, "name": name, "desc": desc, "graph": empty_graph},
            )
        logger.info("Migration 090: deployment templates seeded")
    else:
        logger.info("Deployment templates: %d exist — skipping", template_count)

    # ── Deployment activities (from 092) ──
    activity_count = conn.execute(
        sa.text("""
            SELECT count(*) FROM automated_activities
            WHERE is_component_activity = false AND tenant_id IS NULL
              AND slug IN ('deploy-resource', 'decommission-resource',
                           'rollback-resource', 'upgrade-resource',
                           'validate-resource', 'dry-run-resource')
        """)
    ).scalar()

    if not activity_count or activity_count < 6:
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        mc = MigrationContext.configure(conn)
        with Operations.context(mc):
            m = _load_migration("092_seed_deployment_activities.py")
            m.upgrade()
        logger.info("Migration 092: deployment activities seeded")
    else:
        logger.info("Deployment activities: %d exist — skipping", activity_count)

    # ── Update template graphs with activity nodes (093) ──
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mc = MigrationContext.configure(conn)
    with Operations.context(mc):
        m = _load_migration("093_update_deployment_templates.py")
        m.upgrade()
    logger.info("Migration 093: template graphs updated")

    # ── Activity-centric restructuring (096) ──
    # Check if is_component_activity column exists (migration 098 already applied)
    has_component_activity = conn.execute(
        sa.text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'automated_activities'
                  AND column_name = 'is_component_activity'
            )
        """)
    ).scalar()

    if has_component_activity:
        from alembic.migration import MigrationContext as MC2
        from alembic.operations import Operations as Ops2
        import json as _json

        mc = MC2.configure(conn)
        with Ops2.context(mc):
            m = _load_migration("096_activity_type_and_component_activities.py")

            # Soft-delete rollback/validate/dry-run templates
            conn.execute(sa.text("""
                UPDATE workflow_definitions
                SET deleted_at = NOW()
                WHERE is_template = true AND is_system = true
                  AND workflow_type = 'DEPLOYMENT'
                  AND name IN ('deployment:rollback', 'deployment:validate', 'deployment:dry-run')
                  AND deleted_at IS NULL
            """))

            # Update the 3 remaining templates with full activity pipelines
            for tname, tgraph in [
                ("deployment:deploy", m.DEPLOY_GRAPH),
                ("deployment:decommission", m.DECOMMISSION_GRAPH),
                ("deployment:upgrade", m.UPGRADE_GRAPH),
            ]:
                conn.execute(
                    sa.text("""
                        UPDATE workflow_definitions
                        SET graph = CAST(:graph AS jsonb), updated_at = NOW()
                        WHERE is_template = true AND is_system = true
                          AND workflow_type = 'DEPLOYMENT' AND name = :name
                          AND deleted_at IS NULL
                    """),
                    {"name": tname, "graph": _json.dumps(tgraph)},
                )

            # Soft-delete rollback/validate/dry-run component operations
            conn.execute(sa.text("""
                UPDATE component_operations
                SET deleted_at = NOW()
                WHERE name IN ('rollback', 'validate', 'dry-run')
                  AND operation_category = 'DEPLOYMENT'
                  AND deleted_at IS NULL
            """))

        logger.info("Migration 096: activity-centric restructuring replayed")
    else:
        logger.info("Migration 096: is_component_activity column not found — skipping (run alembic upgrade head first)")

    logger.info("Deployment operations done")


def _replay_stack_workflow_templates(conn) -> None:
    """Stack lifecycle workflow templates (105): provision, deprovision, upgrade, failover."""
    template_count = conn.execute(
        sa.text("""
            SELECT count(*) FROM workflow_definitions
            WHERE is_template = true AND is_system = true
              AND workflow_type = 'STACK'
        """)
    ).scalar()

    if template_count and template_count >= 4:
        logger.info("Stack workflow templates: %d exist — skipping", template_count)
        return

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mc = MigrationContext.configure(conn)
    with Operations.context(mc):
        m = _load_migration("105_stack_lifecycle_workflow_templates.py")
        m.upgrade()
    logger.info("Migration 105: stack lifecycle workflow templates seeded")


def _do_replay_seeds(conn) -> None:
    """Synchronous callback for run_sync — replays all skipped migration seeds."""
    tid = _get_root_tenant_id(conn)
    if not tid:
        logger.warning("No root tenant — skipping migration seed replay")
        return

    logger.info("Root tenant: %s", tid)
    _replay_025(conn, tid)
    _replay_038(conn, tid)
    _replay_039(conn, tid)
    _replay_084(conn, tid)
    _replay_components(conn)
    _replay_deployment_operations(conn)
    _replay_stack_workflow_templates(conn)
    logger.info("Migration seed replay done")


async def replay_migration_seeds() -> None:
    """Re-run seed migrations that were skipped because root tenant didn't exist yet.

    Uses run_sync (same pattern as Alembic's env.py) so we can call sync migration
    code through the asyncpg connection without needing psycopg2.
    """
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.connect() as conn:
        await conn.run_sync(_do_replay_seeds)
        await conn.commit()
    await engine.dispose()
    logger.info("Migration seed replay committed")


# ── Runtime seeders (async) ────────────────────────────────────


async def _provision_system_component_operations(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> None:
    """Provision deployment operations (activities + workflows) for all system components.

    This creates 6 per-component activities cloned from system defaults,
    3 workflow definitions cloned from templates, and 3 ComponentOperation records
    for each system component (Proxmox VM, OCI Flex VM).
    """
    from app.models.component import Component as ComponentModel, ComponentOperation

    result = await db.execute(
        select(ComponentModel).where(
            ComponentModel.is_system.is_(True),
            ComponentModel.deleted_at.is_(None),
        )
    )
    components = list(result.scalars().all())

    if not components:
        logger.info("Component operations: no system components found — skipping")
        return

    op_service = ComponentOperationService()

    for comp in components:
        # Check if this component already has deployment operations
        existing = await db.execute(
            select(ComponentOperation).where(
                ComponentOperation.component_id == comp.id,
                ComponentOperation.deleted_at.is_(None),
            )
        )
        if existing.scalars().first():
            logger.info(
                "Component operations: %s already has operations — skipping",
                comp.name,
            )
            continue

        try:
            ops = await op_service.provision_deployment_operations(
                db,
                component_id=comp.id,
                tenant_id=tenant_id,
                created_by=user_id,
                provider_id=str(comp.provider_id) if comp.provider_id else None,
                semantic_type_id=str(comp.semantic_type_id) if comp.semantic_type_id else None,
            )
            logger.info(
                "Component operations: %s — %d operations provisioned",
                comp.name,
                len(ops),
            )
        except Exception:
            logger.exception(
                "Component operations: failed to provision for %s", comp.name
            )


async def _seed_day2_operations(
    db: AsyncSession,
    tenant_id: str,
    user_id: str,
) -> None:
    """Seed day-2 operations (extend_disk, snapshot, restart, resize, etc.) for system components.

    This replicates the logic from migrations 068 (Proxmox) and 073 (OCI) which create
    workflow definitions and component_operations for day-2 actions.
    """
    # ── Proxmox VM: 3 day-2 operations ──

    pve = (await db.execute(
        sa.text("SELECT id FROM components WHERE name = 'pve-vm-basic' AND is_system = true LIMIT 1")
    )).fetchone()

    if pve:
        pve_ops = [
            {
                "op_name": "extend_disk",
                "op_display": "Extend Disk",
                "op_desc": "Resize a virtual disk and optionally extend the filesystem.",
                "op_input": '{"type":"object","properties":{"new_size_gb":{"type":"integer","description":"New total disk size in GB"},"extend_filesystem":{"type":"boolean","description":"Auto-extend filesystem","default":true},"disk_interface":{"type":"string","description":"Disk interface","default":"scsi0"}},"required":["new_size_gb"]}',
                "op_output": '{"type":"object","properties":{"old_size_gb":{"type":"integer"},"new_size_gb":{"type":"integer"},"filesystem_extended":{"type":"boolean"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": True,
                "op_downtime": "BRIEF",
                "op_order": 10,
                "wf_name": "PVE VM: Extend Disk",
                "wf_desc": "Multi-step workflow: resize Proxmox block device, extend guest filesystem",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"resize","type":"cloud_api","label":"Resize Block Device","position":{"x":200,"y":0}},{"id":"extend","type":"ssh_exec","label":"Extend Filesystem","position":{"x":400,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":600,"y":0}}],"connections":[{"source":"start","target":"resize","sourcePort":"out","targetPort":"in"},{"source":"resize","target":"extend","sourcePort":"out","targetPort":"in"},{"source":"extend","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "create_snapshot",
                "op_display": "Create Snapshot",
                "op_desc": "Create a point-in-time snapshot of the virtual machine.",
                "op_input": '{"type":"object","properties":{"snapshot_name":{"type":"string","description":"Snapshot name"},"description":{"type":"string","description":"Snapshot description"},"include_ram":{"type":"boolean","description":"Include RAM state","default":false}},"required":["snapshot_name"]}',
                "op_output": '{"type":"object","properties":{"snapshot_id":{"type":"string"},"snapshot_name":{"type":"string"},"created_at":{"type":"string"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "NONE",
                "op_order": 11,
                "wf_name": "PVE VM: Create Snapshot",
                "wf_desc": "Create and verify a Proxmox VM snapshot",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"snap","type":"cloud_api","label":"Create Snapshot","position":{"x":200,"y":0}},{"id":"verify","type":"cloud_api","label":"Verify","position":{"x":400,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":600,"y":0}}],"connections":[{"source":"start","target":"snap","sourcePort":"out","targetPort":"in"},{"source":"snap","target":"verify","sourcePort":"out","targetPort":"in"},{"source":"verify","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "restart",
                "op_display": "Restart VM",
                "op_desc": "Gracefully restart the virtual machine via ACPI shutdown then boot.",
                "op_input": '{"type":"object","properties":{"force":{"type":"boolean","description":"Force restart if graceful fails","default":false},"timeout_seconds":{"type":"integer","description":"Seconds to wait for shutdown","default":120}}}',
                "op_output": '{"type":"object","properties":{"previous_state":{"type":"string"},"current_state":{"type":"string"},"restart_method":{"type":"string"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "BRIEF",
                "op_order": 12,
                "wf_name": "PVE VM: Restart",
                "wf_desc": "Graceful shutdown, boot, verify running",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"shutdown","type":"cloud_api","label":"Shutdown","position":{"x":200,"y":0}},{"id":"wait","type":"delay","label":"Wait","position":{"x":400,"y":0}},{"id":"boot","type":"cloud_api","label":"Boot","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"shutdown","sourcePort":"out","targetPort":"in"},{"source":"shutdown","target":"wait","sourcePort":"out","targetPort":"in"},{"source":"wait","target":"boot","sourcePort":"out","targetPort":"in"},{"source":"boot","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
        ]
        count = await _insert_day2_ops(db, str(pve[0]), tenant_id, user_id, pve_ops)
        logger.info("Day-2 operations: pve-vm-basic — %d created", count)
    else:
        logger.info("Day-2 operations: pve-vm-basic not found — skipping")

    # ── OCI Flex VM: 6 day-2 operations ──

    oci = (await db.execute(
        sa.text("SELECT id FROM components WHERE name = 'oci-vm-flex' AND is_system = true LIMIT 1")
    )).fetchone()

    # Find OCI provider and VirtualMachine semantic type for workflow applicability
    oci_provider = (await db.execute(
        sa.text("SELECT id FROM semantic_providers WHERE name = 'oci' LIMIT 1")
    )).fetchone()
    vm_type = (await db.execute(
        sa.text("SELECT id FROM semantic_resource_types WHERE name = 'VirtualMachine' LIMIT 1")
    )).fetchone()

    if oci:
        oci_ops = [
            {
                "op_name": "resize",
                "op_display": "Resize Instance",
                "op_desc": "Change OCPU and memory allocation. Requires a brief stop/start cycle.",
                "op_input": '{"type":"object","properties":{"new_ocpus":{"type":"number","description":"New OCPU count"},"new_memory_gb":{"type":"number","description":"New memory in GB"},"new_boot_volume_gb":{"type":"integer","description":"New boot volume size in GB"}},"required":["new_ocpus","new_memory_gb"]}',
                "op_output": '{"type":"object","properties":{"old_ocpus":{"type":"number"},"new_ocpus":{"type":"number"},"old_memory_gb":{"type":"number"},"new_memory_gb":{"type":"number"},"reboot_required":{"type":"boolean"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": True,
                "op_downtime": "BRIEF",
                "op_order": 10,
                "wf_name": "OCI Flex VM: Resize",
                "wf_desc": "Validate shape limits, stop instance, update shape config, start, verify",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"validate","type":"script","label":"Validate","position":{"x":200,"y":0}},{"id":"stop","type":"cloud_api","label":"Stop","position":{"x":400,"y":0}},{"id":"resize","type":"cloud_api","label":"Resize","position":{"x":600,"y":0}},{"id":"start_vm","type":"cloud_api","label":"Start","position":{"x":800,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":1000,"y":0}}],"connections":[{"source":"start","target":"validate","sourcePort":"out","targetPort":"in"},{"source":"validate","target":"stop","sourcePort":"out","targetPort":"in"},{"source":"stop","target":"resize","sourcePort":"out","targetPort":"in"},{"source":"resize","target":"start_vm","sourcePort":"out","targetPort":"in"},{"source":"start_vm","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "stop_start",
                "op_display": "Stop / Start",
                "op_desc": "Stop or start the compute instance.",
                "op_input": '{"type":"object","properties":{"action":{"type":"string","enum":["stop","start"],"description":"Action to perform"},"force":{"type":"boolean","description":"Force stop","default":false}},"required":["action"]}',
                "op_output": '{"type":"object","properties":{"previous_state":{"type":"string"},"current_state":{"type":"string"},"action_performed":{"type":"string"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "BRIEF",
                "op_order": 11,
                "wf_name": "OCI Flex VM: Stop / Start",
                "wf_desc": "Check state, perform stop or start, wait, verify",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"check","type":"cloud_api","label":"Check State","position":{"x":200,"y":0}},{"id":"action","type":"cloud_api","label":"Stop/Start","position":{"x":400,"y":0}},{"id":"verify","type":"cloud_api","label":"Verify","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"check","sourcePort":"out","targetPort":"in"},{"source":"check","target":"action","sourcePort":"out","targetPort":"in"},{"source":"action","target":"verify","sourcePort":"out","targetPort":"in"},{"source":"verify","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "create_custom_image",
                "op_display": "Create Custom Image",
                "op_desc": "Capture a custom image from the instance boot volume.",
                "op_input": '{"type":"object","properties":{"image_name":{"type":"string","description":"Display name for the image"},"compartment_id":{"type":"string","description":"Target compartment OCID"}},"required":["image_name"]}',
                "op_output": '{"type":"object","properties":{"image_id":{"type":"string"},"image_name":{"type":"string"},"size_gb":{"type":"number"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "EXTENDED",
                "op_order": 12,
                "wf_name": "OCI Flex VM: Create Custom Image",
                "wf_desc": "Stop instance, create image, wait, restart instance",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"stop","type":"cloud_api","label":"Stop","position":{"x":200,"y":0}},{"id":"create","type":"cloud_api","label":"Create Image","position":{"x":400,"y":0}},{"id":"restart","type":"cloud_api","label":"Restart","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"stop","sourcePort":"out","targetPort":"in"},{"source":"stop","target":"create","sourcePort":"out","targetPort":"in"},{"source":"create","target":"restart","sourcePort":"out","targetPort":"in"},{"source":"restart","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "restart",
                "op_display": "Restart Instance",
                "op_desc": "Restart using SOFTRESET (ACPI) or RESET (hard reboot).",
                "op_input": '{"type":"object","properties":{"reset_type":{"type":"string","enum":["SOFTRESET","RESET"],"description":"Restart method","default":"SOFTRESET"},"timeout_seconds":{"type":"integer","description":"Seconds to wait","default":300}}}',
                "op_output": '{"type":"object","properties":{"previous_state":{"type":"string"},"current_state":{"type":"string"},"reset_type":{"type":"string"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "BRIEF",
                "op_order": 13,
                "wf_name": "OCI Flex VM: Restart",
                "wf_desc": "Send reset action, wait, verify running",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"reset","type":"cloud_api","label":"Reset","position":{"x":200,"y":0}},{"id":"wait","type":"delay","label":"Wait","position":{"x":400,"y":0}},{"id":"verify","type":"cloud_api","label":"Verify","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"reset","sourcePort":"out","targetPort":"in"},{"source":"reset","target":"wait","sourcePort":"out","targetPort":"in"},{"source":"wait","target":"verify","sourcePort":"out","targetPort":"in"},{"source":"verify","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "update_network",
                "op_display": "Update Network Config",
                "op_desc": "Update VNIC settings: NSGs, hostname label, source/dest check. No downtime.",
                "op_input": '{"type":"object","properties":{"vnic_id":{"type":"string","description":"VNIC OCID"},"new_nsg_ids":{"type":"array","items":{"type":"string"},"description":"NSG OCIDs"},"skip_source_dest_check":{"type":"boolean","description":"Disable source/dest check"},"new_hostname_label":{"type":"string","description":"New DNS hostname"}}}',
                "op_output": '{"type":"object","properties":{"vnic_id":{"type":"string"},"private_ip":{"type":"string"},"nsg_ids":{"type":"array","items":{"type":"string"}},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "NONE",
                "op_order": 14,
                "wf_name": "OCI Flex VM: Update Network",
                "wf_desc": "Resolve VNIC attachment, update VNIC config, verify",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"get_vnic","type":"cloud_api","label":"Get VNIC","position":{"x":200,"y":0}},{"id":"update","type":"cloud_api","label":"Update VNIC","position":{"x":400,"y":0}},{"id":"verify","type":"cloud_api","label":"Verify","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"get_vnic","sourcePort":"out","targetPort":"in"},{"source":"get_vnic","target":"update","sourcePort":"out","targetPort":"in"},{"source":"update","target":"verify","sourcePort":"out","targetPort":"in"},{"source":"verify","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
            {
                "op_name": "create_backup",
                "op_display": "Create Backup",
                "op_desc": "Create a boot volume backup (full or incremental). No instance downtime.",
                "op_input": '{"type":"object","properties":{"backup_name":{"type":"string","description":"Backup display name"},"backup_type":{"type":"string","enum":["FULL","INCREMENTAL"],"description":"Backup type","default":"INCREMENTAL"}},"required":["backup_name"]}',
                "op_output": '{"type":"object","properties":{"backup_id":{"type":"string"},"backup_name":{"type":"string"},"backup_type":{"type":"string"},"size_gb":{"type":"number"},"status":{"type":"string"}}}',
                "op_destructive": False,
                "op_approval": False,
                "op_downtime": "NONE",
                "op_order": 15,
                "wf_name": "OCI Flex VM: Create Backup",
                "wf_desc": "Get boot volume, create backup, wait, verify",
                "wf_graph": '{"nodes":[{"id":"start","type":"start","label":"Start","position":{"x":0,"y":0}},{"id":"get_vol","type":"cloud_api","label":"Get Boot Vol","position":{"x":200,"y":0}},{"id":"backup","type":"cloud_api","label":"Create Backup","position":{"x":400,"y":0}},{"id":"verify","type":"cloud_api","label":"Verify","position":{"x":600,"y":0}},{"id":"end","type":"end","label":"End","position":{"x":800,"y":0}}],"connections":[{"source":"start","target":"get_vol","sourcePort":"out","targetPort":"in"},{"source":"get_vol","target":"backup","sourcePort":"out","targetPort":"in"},{"source":"backup","target":"verify","sourcePort":"out","targetPort":"in"},{"source":"verify","target":"end","sourcePort":"out","targetPort":"in"}]}',
            },
        ]
        count = await _insert_day2_ops(
            db, str(oci[0]), tenant_id, user_id, oci_ops,
            semantic_type_id=str(vm_type[0]) if vm_type else None,
            provider_id=str(oci_provider[0]) if oci_provider else None,
        )
        logger.info("Day-2 operations: oci-vm-flex — %d created", count)
    else:
        logger.info("Day-2 operations: oci-vm-flex not found — skipping")


async def _insert_day2_ops(
    db: AsyncSession,
    component_id: str,
    tenant_id: str,
    user_id: str,
    operations: list[dict],
    semantic_type_id: str | None = None,
    provider_id: str | None = None,
) -> int:
    """Insert day-2 workflow definitions + component_operations. Returns count created."""
    created = 0
    for op_def in operations:
        # Skip if operation already exists
        existing = (await db.execute(
            sa.text(
                "SELECT id FROM component_operations "
                "WHERE component_id = :comp_id AND name = :name AND deleted_at IS NULL LIMIT 1"
            ),
            {"comp_id": component_id, "name": op_def["op_name"]},
        )).fetchone()
        if existing:
            continue

        # Check if workflow already exists
        wf = (await db.execute(
            sa.text("SELECT id FROM workflow_definitions WHERE name = :name AND deleted_at IS NULL LIMIT 1"),
            {"name": op_def["wf_name"]},
        )).fetchone()

        if not wf:
            # Create workflow definition
            wf_params: dict = {
                "tenant_id": tenant_id,
                "name": op_def["wf_name"],
                "desc": op_def["wf_desc"],
                "graph": op_def["wf_graph"],
                "user_id": user_id,
            }
            if semantic_type_id and provider_id:
                await db.execute(sa.text("""
                    INSERT INTO workflow_definitions (
                        id, tenant_id, name, description, workflow_type,
                        graph, status, version,
                        applicable_semantic_type_id, applicable_provider_id,
                        created_by, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :tenant_id, :name, :desc, 'AUTOMATION',
                        CAST(:graph AS jsonb), 'ACTIVE', 1,
                        :semantic_type_id, :provider_id,
                        :user_id, NOW(), NOW()
                    )
                """), {**wf_params, "semantic_type_id": semantic_type_id, "provider_id": provider_id})
            else:
                await db.execute(sa.text("""
                    INSERT INTO workflow_definitions (
                        id, tenant_id, name, description, workflow_type,
                        graph, status, version,
                        created_by, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :tenant_id, :name, :desc, 'AUTOMATION',
                        CAST(:graph AS jsonb), 'ACTIVE', 1,
                        :user_id, NOW(), NOW()
                    )
                """), wf_params)

            wf = (await db.execute(
                sa.text("SELECT id FROM workflow_definitions WHERE name = :name LIMIT 1"),
                {"name": op_def["wf_name"]},
            )).fetchone()

        if not wf:
            continue

        # Create component operation (schemas live on activity versions, not here)
        await db.execute(sa.text("""
            INSERT INTO component_operations (
                id, component_id, name, display_name, description,
                workflow_definition_id,
                is_destructive, requires_approval, estimated_downtime,
                sort_order, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :comp_id, :name, :display_name, :description,
                :wf_id,
                :is_destructive, :requires_approval, :downtime,
                :sort_order, NOW(), NOW()
            )
        """), {
            "comp_id": component_id,
            "name": op_def["op_name"],
            "display_name": op_def["op_display"],
            "description": op_def["op_desc"],
            "wf_id": str(wf[0]),
            "is_destructive": op_def["op_destructive"],
            "requires_approval": op_def["op_approval"],
            "downtime": op_def["op_downtime"],
            "sort_order": op_def["op_order"],
        })
        created += 1

    return created


async def _seed_stack_blueprints(
    db: AsyncSession, tenant_id: str, user_id: str
) -> None:
    """Seed PaaS stack blueprints with HA/DR patterns."""
    # Check if any blueprints already exist
    existing = (await db.execute(
        sa.text(
            "SELECT COUNT(*) FROM service_clusters "
            "WHERE cluster_type = 'stack_blueprint' AND deleted_at IS NULL"
        )
    )).scalar()
    if existing and existing > 0:
        logger.info("Stack blueprints: %d already exist — skipping", existing)
        return

    blueprints = [
        # ── Database Stacks ──────────────────────────────────────────
        {
            "name": "postgresql-ha",
            "display_name": "PostgreSQL HA Cluster",
            "description": (
                "Production-grade PostgreSQL with streaming replication, "
                "automatic failover (Patroni), PgBouncer connection pooling, "
                "and cross-region async DR replicas. Supports PITR to object storage."
            ),
            "category": "DATABASE",
            "icon": "database",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 1 min", "rto": "< 5 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "instance_size": {"type": "string", "enum": ["small", "medium", "large", "xlarge"]},
                    "replicas": {"type": "integer", "minimum": 1, "maximum": 5, "default": 2},
                    "storage_gb": {"type": "integer", "minimum": 20, "maximum": 2000, "default": 100},
                    "pg_version": {"type": "string", "enum": ["14", "15", "16"], "default": "16"},
                    "enable_dr_replica": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                    "backup_retention_days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
                    "max_connections": {"type": "integer", "minimum": 50, "maximum": 5000, "default": 200},
                },
                "required": ["instance_size", "storage_gb"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "connection_string": {"type": "string"},
                    "primary_host": {"type": "string"},
                    "replica_hosts": {"type": "array", "items": {"type": "string"}},
                    "pgbouncer_host": {"type": "string"},
                    "dr_replica_host": {"type": "string"},
                },
            },
            "slots": [
                {"name": "primary", "display_name": "Primary Node", "min": 1, "max": 1, "required": True, "order": 0},
                {"name": "replica", "display_name": "Streaming Replica", "min": 1, "max": 5, "required": True, "order": 1},
                {"name": "pgbouncer", "display_name": "PgBouncer Pooler", "min": 1, "max": 2, "required": True, "order": 2},
                {"name": "patroni", "display_name": "Patroni (Failover Manager)", "min": 3, "max": 3, "required": True, "order": 3},
                {"name": "backup_agent", "display_name": "WAL-G Backup Agent", "min": 1, "max": 1, "required": True, "order": 4},
                {"name": "dr_replica", "display_name": "DR Async Replica", "min": 0, "max": 2, "required": False, "order": 5},
            ],
        },
        {
            "name": "redis-sentinel",
            "display_name": "Redis Sentinel Cluster",
            "description": (
                "High-availability Redis with Sentinel-based failover, "
                "automatic leader election, and RDB/AOF persistence. "
                "Optional cross-region replica for DR with snapshot-based restore."
            ),
            "category": "DATABASE",
            "icon": "cache",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 5 min", "rto": "< 1 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "instance_size": {"type": "string", "enum": ["small", "medium", "large"]},
                    "maxmemory_gb": {"type": "integer", "minimum": 1, "maximum": 128, "default": 4},
                    "persistence": {"type": "string", "enum": ["rdb", "aof", "both", "none"], "default": "both"},
                    "sentinel_quorum": {"type": "integer", "minimum": 2, "maximum": 5, "default": 2},
                    "enable_dr": {"type": "boolean", "default": False},
                },
                "required": ["instance_size", "maxmemory_gb"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "sentinel_addresses": {"type": "array", "items": {"type": "string"}},
                    "master_name": {"type": "string"},
                    "connection_string": {"type": "string"},
                },
            },
            "slots": [
                {"name": "primary", "display_name": "Redis Primary", "min": 1, "max": 1, "required": True, "order": 0},
                {"name": "replica", "display_name": "Redis Replica", "min": 2, "max": 4, "required": True, "order": 1},
                {"name": "sentinel", "display_name": "Sentinel Node", "min": 3, "max": 5, "required": True, "order": 2},
                {"name": "dr_replica", "display_name": "DR Cross-Region Replica", "min": 0, "max": 1, "required": False, "order": 3},
            ],
        },
        {
            "name": "mongodb-replicaset",
            "display_name": "MongoDB Replica Set",
            "description": (
                "Production MongoDB replica set with automatic election, "
                "oplog-based PITR, and optional cross-site secondary for DR. "
                "Includes mongos router for sharded deployments."
            ),
            "category": "DATABASE",
            "icon": "database",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 2 min", "rto": "< 2 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "instance_size": {"type": "string", "enum": ["small", "medium", "large", "xlarge"]},
                    "storage_gb": {"type": "integer", "minimum": 10, "maximum": 4000, "default": 50},
                    "mongo_version": {"type": "string", "enum": ["6.0", "7.0"], "default": "7.0"},
                    "replica_members": {"type": "integer", "minimum": 3, "maximum": 7, "default": 3},
                    "enable_sharding": {"type": "boolean", "default": False},
                    "enable_dr_secondary": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                },
                "required": ["instance_size", "storage_gb"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "connection_string": {"type": "string"},
                    "replica_set_name": {"type": "string"},
                    "member_hosts": {"type": "array", "items": {"type": "string"}},
                },
            },
            "slots": [
                {"name": "member", "display_name": "Replica Set Member", "min": 3, "max": 7, "required": True, "order": 0},
                {"name": "mongos", "display_name": "Mongos Router", "min": 0, "max": 3, "required": False, "order": 1},
                {"name": "config_server", "display_name": "Config Server", "min": 0, "max": 3, "required": False, "order": 2},
                {"name": "backup_agent", "display_name": "Backup Agent", "min": 1, "max": 1, "required": True, "order": 3},
                {"name": "dr_secondary", "display_name": "DR Cross-Site Secondary", "min": 0, "max": 1, "required": False, "order": 4},
            ],
        },
        # ── Application Platform Stacks ──────────────────────────────
        {
            "name": "kubernetes-app-platform",
            "display_name": "Kubernetes App Platform",
            "description": (
                "Full Kubernetes platform with multi-master control plane, "
                "worker node pools, Ingress controller, cert-manager, and HPA. "
                "DR via Velero cluster backups and etcd snapshots to object storage. "
                "Supports failover to a secondary-region standby cluster."
            ),
            "category": "PLATFORM",
            "icon": "kubernetes",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 15 min", "rto": "< 30 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "k8s_version": {"type": "string", "enum": ["1.28", "1.29", "1.30"], "default": "1.30"},
                    "control_plane_nodes": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                    "worker_node_size": {"type": "string", "enum": ["small", "medium", "large", "xlarge"]},
                    "worker_min_count": {"type": "integer", "minimum": 1, "maximum": 50, "default": 3},
                    "worker_max_count": {"type": "integer", "minimum": 1, "maximum": 100, "default": 10},
                    "cni_plugin": {"type": "string", "enum": ["cilium", "calico", "flannel"], "default": "cilium"},
                    "enable_dr_cluster": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                    "storage_class": {"type": "string", "enum": ["standard", "ssd", "nvme"], "default": "ssd"},
                },
                "required": ["worker_node_size", "worker_min_count"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "api_server_endpoint": {"type": "string"},
                    "kubeconfig_secret": {"type": "string"},
                    "ingress_lb_ip": {"type": "string"},
                    "dr_api_server_endpoint": {"type": "string"},
                },
            },
            "slots": [
                {"name": "control_plane", "display_name": "Control Plane Node", "min": 1, "max": 5, "required": True, "order": 0},
                {"name": "worker", "display_name": "Worker Node", "min": 1, "max": 100, "required": True, "order": 1},
                {"name": "ingress", "display_name": "Ingress Controller", "min": 1, "max": 3, "required": True, "order": 2},
                {"name": "cert_manager", "display_name": "Cert-Manager", "min": 1, "max": 1, "required": True, "order": 3},
                {"name": "velero", "display_name": "Velero Backup", "min": 1, "max": 1, "required": True, "order": 4},
                {"name": "dr_cluster", "display_name": "DR Standby Cluster", "min": 0, "max": 1, "required": False, "order": 5},
            ],
        },
        {
            "name": "container-web-service",
            "display_name": "Container Web Service",
            "description": (
                "Containerized web application with load balancer, TLS termination, "
                "health checks, and auto-scaling. Rolling deploys with circuit breaker. "
                "DR via blue/green region failover with DNS-based traffic switching."
            ),
            "category": "COMPUTE",
            "icon": "container",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "0", "rto": "< 5 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "container_image": {"type": "string"},
                    "replicas": {"type": "integer", "minimum": 1, "maximum": 20, "default": 2},
                    "cpu_limit": {"type": "string", "enum": ["0.5", "1", "2", "4"], "default": "1"},
                    "memory_limit_mb": {"type": "integer", "minimum": 128, "maximum": 8192, "default": 512},
                    "port": {"type": "integer", "minimum": 1, "maximum": 65535, "default": 8080},
                    "health_check_path": {"type": "string", "default": "/health"},
                    "enable_tls": {"type": "boolean", "default": True},
                    "enable_dr_region": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                },
                "required": ["container_image", "replicas", "port"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "service_url": {"type": "string"},
                    "lb_address": {"type": "string"},
                    "dr_service_url": {"type": "string"},
                },
            },
            "slots": [
                {"name": "container", "display_name": "App Container", "min": 1, "max": 20, "required": True, "order": 0},
                {"name": "load_balancer", "display_name": "Load Balancer", "min": 1, "max": 2, "required": True, "order": 1},
                {"name": "tls", "display_name": "TLS Termination", "min": 1, "max": 1, "required": True, "order": 2},
                {"name": "health_check", "display_name": "Health Check Probe", "min": 1, "max": 1, "required": True, "order": 3},
                {"name": "dr_region", "display_name": "DR Region Deployment", "min": 0, "max": 1, "required": False, "order": 4},
            ],
        },
        # ── Messaging & Event Stacks ─────────────────────────────────
        {
            "name": "kafka-cluster",
            "display_name": "Kafka Event Streaming",
            "description": (
                "Apache Kafka cluster with KRaft consensus (no ZooKeeper), "
                "Schema Registry, and rack-aware replica placement. "
                "HA via ISR replication (min.insync.replicas=2). "
                "DR with MirrorMaker 2 cross-region replication."
            ),
            "category": "PLATFORM",
            "icon": "stream",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "0 (sync)", "rto": "< 10 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "broker_count": {"type": "integer", "minimum": 3, "maximum": 12, "default": 3},
                    "instance_size": {"type": "string", "enum": ["medium", "large", "xlarge"]},
                    "storage_gb_per_broker": {"type": "integer", "minimum": 100, "maximum": 5000, "default": 500},
                    "replication_factor": {"type": "integer", "minimum": 2, "maximum": 5, "default": 3},
                    "min_insync_replicas": {"type": "integer", "minimum": 1, "maximum": 4, "default": 2},
                    "enable_schema_registry": {"type": "boolean", "default": True},
                    "enable_dr_mirror": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                },
                "required": ["broker_count", "instance_size", "storage_gb_per_broker"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "bootstrap_servers": {"type": "string"},
                    "schema_registry_url": {"type": "string"},
                    "dr_bootstrap_servers": {"type": "string"},
                },
            },
            "slots": [
                {"name": "broker", "display_name": "Kafka Broker", "min": 3, "max": 12, "required": True, "order": 0},
                {"name": "schema_registry", "display_name": "Schema Registry", "min": 0, "max": 2, "required": False, "order": 1},
                {"name": "connect", "display_name": "Kafka Connect Worker", "min": 0, "max": 6, "required": False, "order": 2},
                {"name": "mirror_maker", "display_name": "MirrorMaker 2 (DR)", "min": 0, "max": 2, "required": False, "order": 3},
            ],
        },
        {
            "name": "rabbitmq-cluster",
            "display_name": "RabbitMQ Cluster",
            "description": (
                "Clustered RabbitMQ with quorum queues for HA, HAProxy load balancing, "
                "and auto-heal network partition handling. "
                "DR via Shovel-based cross-site replication and definition export/restore."
            ),
            "category": "PLATFORM",
            "icon": "queue",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 1 min", "rto": "< 5 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "node_count": {"type": "integer", "minimum": 3, "maximum": 7, "default": 3},
                    "instance_size": {"type": "string", "enum": ["small", "medium", "large"]},
                    "queue_type": {"type": "string", "enum": ["quorum", "classic_mirrored"], "default": "quorum"},
                    "enable_management_ui": {"type": "boolean", "default": True},
                    "enable_dr_shovel": {"type": "boolean", "default": False},
                    "dr_region": {"type": "string"},
                },
                "required": ["node_count", "instance_size"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "amqp_url": {"type": "string"},
                    "management_url": {"type": "string"},
                    "dr_amqp_url": {"type": "string"},
                },
            },
            "slots": [
                {"name": "node", "display_name": "RabbitMQ Node", "min": 3, "max": 7, "required": True, "order": 0},
                {"name": "haproxy", "display_name": "HAProxy LB", "min": 1, "max": 2, "required": True, "order": 1},
                {"name": "dr_shovel", "display_name": "DR Shovel Endpoint", "min": 0, "max": 1, "required": False, "order": 2},
            ],
        },
        # ── Storage Stacks ───────────────────────────────────────────
        {
            "name": "minio-distributed",
            "display_name": "MinIO Distributed Object Storage",
            "description": (
                "Distributed MinIO cluster with erasure coding (EC:4) for data protection, "
                "TLS encryption, and IAM policies. HA via distributed mode across nodes. "
                "DR via site-to-site bucket replication with versioning."
            ),
            "category": "STORAGE",
            "icon": "storage",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "near-zero", "rto": "< 10 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "node_count": {"type": "integer", "minimum": 4, "maximum": 16, "default": 4},
                    "disks_per_node": {"type": "integer", "minimum": 1, "maximum": 8, "default": 4},
                    "disk_size_gb": {"type": "integer", "minimum": 100, "maximum": 10000, "default": 500},
                    "erasure_coding": {"type": "string", "enum": ["EC:2", "EC:4", "EC:6"], "default": "EC:4"},
                    "enable_tls": {"type": "boolean", "default": True},
                    "enable_site_replication": {"type": "boolean", "default": False},
                    "dr_site_endpoint": {"type": "string"},
                },
                "required": ["node_count", "disk_size_gb"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "api_endpoint": {"type": "string"},
                    "console_endpoint": {"type": "string"},
                    "access_key": {"type": "string"},
                    "secret_key": {"type": "string"},
                },
            },
            "slots": [
                {"name": "node", "display_name": "MinIO Node", "min": 4, "max": 16, "required": True, "order": 0},
                {"name": "load_balancer", "display_name": "Load Balancer", "min": 1, "max": 2, "required": True, "order": 1},
                {"name": "dr_site", "display_name": "DR Replication Target", "min": 0, "max": 1, "required": False, "order": 2},
            ],
        },
        # ── Observability Stacks ─────────────────────────────────────
        {
            "name": "monitoring-stack",
            "display_name": "Prometheus + Grafana Monitoring",
            "description": (
                "Full observability stack: Prometheus for metrics, Grafana for dashboards, "
                "Alertmanager cluster for alerting (3-node gossip). "
                "HA via Thanos sidecar for deduplication. "
                "DR via Thanos Store Gateway with long-term object storage retention."
            ),
            "category": "MONITORING",
            "icon": "chart",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 5 min", "rto": "< 15 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "retention_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30},
                    "scrape_interval_seconds": {"type": "integer", "minimum": 5, "maximum": 300, "default": 15},
                    "alertmanager_nodes": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                    "enable_thanos": {"type": "boolean", "default": True},
                    "thanos_object_store": {"type": "string", "enum": ["minio", "s3", "gcs"], "default": "minio"},
                    "grafana_replicas": {"type": "integer", "minimum": 1, "maximum": 3, "default": 2},
                },
                "required": ["retention_days"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "prometheus_url": {"type": "string"},
                    "grafana_url": {"type": "string"},
                    "alertmanager_url": {"type": "string"},
                    "thanos_query_url": {"type": "string"},
                },
            },
            "slots": [
                {"name": "prometheus", "display_name": "Prometheus Server", "min": 1, "max": 2, "required": True, "order": 0},
                {"name": "alertmanager", "display_name": "Alertmanager", "min": 1, "max": 5, "required": True, "order": 1},
                {"name": "grafana", "display_name": "Grafana", "min": 1, "max": 3, "required": True, "order": 2},
                {"name": "thanos_sidecar", "display_name": "Thanos Sidecar", "min": 0, "max": 2, "required": False, "order": 3},
                {"name": "thanos_store", "display_name": "Thanos Store Gateway", "min": 0, "max": 2, "required": False, "order": 4},
                {"name": "node_exporter", "display_name": "Node Exporter", "min": 1, "max": 100, "required": True, "order": 5},
            ],
        },
        {
            "name": "log-aggregation",
            "display_name": "Loki Log Aggregation",
            "description": (
                "Centralized logging with Grafana Loki in microservices mode, "
                "Promtail/Fluentd log shippers, and Grafana for exploration. "
                "HA via replication factor 3 with read/write path separation. "
                "DR via log shipping to secondary region with S3 long-term retention."
            ),
            "category": "MONITORING",
            "icon": "log",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "< 5 min", "rto": "< 20 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "retention_days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30},
                    "replication_factor": {"type": "integer", "minimum": 1, "maximum": 5, "default": 3},
                    "log_shipper": {"type": "string", "enum": ["promtail", "fluentd", "fluent-bit"], "default": "promtail"},
                    "object_store": {"type": "string", "enum": ["minio", "s3", "gcs"], "default": "minio"},
                    "enable_dr_shipping": {"type": "boolean", "default": False},
                },
                "required": ["retention_days"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "loki_push_url": {"type": "string"},
                    "grafana_url": {"type": "string"},
                },
            },
            "slots": [
                {"name": "loki_write", "display_name": "Loki Write Path", "min": 1, "max": 3, "required": True, "order": 0},
                {"name": "loki_read", "display_name": "Loki Read Path", "min": 1, "max": 3, "required": True, "order": 1},
                {"name": "log_shipper", "display_name": "Log Shipper (DaemonSet)", "min": 1, "max": 100, "required": True, "order": 2},
                {"name": "grafana", "display_name": "Grafana", "min": 1, "max": 2, "required": True, "order": 3},
                {"name": "dr_forwarder", "display_name": "DR Log Forwarder", "min": 0, "max": 1, "required": False, "order": 4},
            ],
        },
        # ── Network & Security Stacks ────────────────────────────────
        {
            "name": "vpn-gateway",
            "display_name": "VPN Gateway",
            "description": (
                "Site-to-site or client VPN with WireGuard/IPSec, firewall rules, "
                "and DNS resolver integration. HA via active/passive pair with VRRP. "
                "DR with pre-provisioned standby gateway in secondary site."
            ),
            "category": "NETWORKING",
            "icon": "shield",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "0", "rto": "< 2 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "vpn_protocol": {"type": "string", "enum": ["wireguard", "ipsec", "openvpn"], "default": "wireguard"},
                    "tunnel_cidr": {"type": "string", "default": "10.200.0.0/24"},
                    "max_clients": {"type": "integer", "minimum": 10, "maximum": 1000, "default": 50},
                    "enable_ha_pair": {"type": "boolean", "default": True},
                    "enable_dr_standby": {"type": "boolean", "default": False},
                    "dr_site": {"type": "string"},
                },
                "required": ["vpn_protocol", "tunnel_cidr"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "gateway_endpoint": {"type": "string"},
                    "client_config_secret": {"type": "string"},
                    "dr_gateway_endpoint": {"type": "string"},
                },
            },
            "slots": [
                {"name": "gateway_primary", "display_name": "VPN Gateway (Active)", "min": 1, "max": 1, "required": True, "order": 0},
                {"name": "gateway_standby", "display_name": "VPN Gateway (Standby)", "min": 0, "max": 1, "required": False, "order": 1},
                {"name": "firewall", "display_name": "Firewall Rules", "min": 1, "max": 1, "required": True, "order": 2},
                {"name": "dns", "display_name": "DNS Resolver", "min": 1, "max": 2, "required": True, "order": 3},
                {"name": "dr_gateway", "display_name": "DR Standby Gateway", "min": 0, "max": 1, "required": False, "order": 4},
            ],
        },
        {
            "name": "reverse-proxy-waf",
            "display_name": "Reverse Proxy + WAF",
            "description": (
                "Reverse proxy with HAProxy/Nginx, ModSecurity/Coraza WAF rules, "
                "rate limiting, and DDoS mitigation. HA via active/active behind DNS "
                "round-robin or ECMP. DR with multi-region deployment and GSLB failover."
            ),
            "category": "SECURITY",
            "icon": "firewall",
            "is_published": True,
            "is_system": True,
            "tags": {"tier": "production", "ha": True, "dr": True, "rpo": "0", "rto": "< 1 min"},
            "input_schema": {
                "type": "object",
                "properties": {
                    "proxy_engine": {"type": "string", "enum": ["haproxy", "nginx", "envoy"], "default": "haproxy"},
                    "waf_engine": {"type": "string", "enum": ["modsecurity", "coraza", "none"], "default": "coraza"},
                    "max_rps": {"type": "integer", "minimum": 100, "maximum": 1000000, "default": 10000},
                    "ssl_policy": {"type": "string", "enum": ["modern", "intermediate", "old"], "default": "modern"},
                    "enable_gslb": {"type": "boolean", "default": False},
                    "regions": {"type": "array", "items": {"type": "string"}, "default": []},
                },
                "required": ["proxy_engine", "max_rps"],
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "proxy_vip": {"type": "string"},
                    "gslb_fqdn": {"type": "string"},
                    "waf_dashboard_url": {"type": "string"},
                },
            },
            "slots": [
                {"name": "proxy", "display_name": "Reverse Proxy", "min": 2, "max": 6, "required": True, "order": 0},
                {"name": "waf", "display_name": "WAF Engine", "min": 1, "max": 4, "required": True, "order": 1},
                {"name": "rate_limiter", "display_name": "Rate Limiter", "min": 1, "max": 2, "required": True, "order": 2},
                {"name": "gslb", "display_name": "GSLB Controller", "min": 0, "max": 1, "required": False, "order": 3},
            ],
        },
    ]

    created = 0
    import json as _json

    for bp in blueprints:
        # Insert the ServiceCluster (blueprint)
        await db.execute(sa.text("""
            INSERT INTO service_clusters (
                id, tenant_id, name, display_name, description,
                cluster_type, category, icon,
                input_schema, output_schema,
                tags, version, is_published, is_system,
                created_by, created_at, updated_at
            ) VALUES (
                gen_random_uuid(), :tenant_id, :name, :display_name, :description,
                'stack_blueprint', :category, :icon,
                CAST(:input_schema AS jsonb), CAST(:output_schema AS jsonb),
                CAST(:tags AS jsonb), 1, :is_published, :is_system,
                :user_id, NOW(), NOW()
            )
        """), {
            "tenant_id": tenant_id,
            "name": bp["name"],
            "display_name": bp["display_name"],
            "description": bp["description"],
            "category": bp["category"],
            "icon": bp["icon"],
            "input_schema": _json.dumps(bp["input_schema"]),
            "output_schema": _json.dumps(bp["output_schema"]),
            "tags": _json.dumps(bp["tags"]),
            "is_published": bp["is_published"],
            "is_system": bp["is_system"],
            "user_id": user_id,
        })

        # Fetch the generated ID
        row = (await db.execute(
            sa.text(
                "SELECT id FROM service_clusters WHERE name = :name "
                "AND tenant_id = :tid AND deleted_at IS NULL LIMIT 1"
            ),
            {"name": bp["name"], "tid": tenant_id},
        )).fetchone()
        if not row:
            continue

        bp_id = str(row[0])

        # Insert slots
        for slot in bp.get("slots", []):
            await db.execute(sa.text("""
                INSERT INTO service_cluster_slots (
                    id, cluster_id, name, display_name, description,
                    min_count, max_count, is_required, sort_order,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), :bp_id, :name, :display_name, :description,
                    :min_count, :max_count, :is_required, :sort_order,
                    NOW(), NOW()
                )
            """), {
                "bp_id": bp_id,
                "name": slot["name"],
                "display_name": slot["display_name"],
                "description": slot["display_name"],
                "min_count": slot["min"],
                "max_count": slot["max"],
                "is_required": slot["required"],
                "sort_order": slot["order"],
            })

        created += 1

    logger.info("Stack blueprints seeded: %d created", created)


async def seed_runtime_data() -> None:
    """Connect to the DB and run runtime seeders that need a session."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as db:
        try:
            result = await db.execute(
                select(Tenant).where(
                    Tenant.parent_id.is_(None),
                    Tenant.deleted_at.is_(None),
                )
            )
            root_tenant = result.scalar_one_or_none()
            if not root_tenant:
                logger.warning("No root tenant found — skipping runtime seeders")
                return

            result = await db.execute(
                select(User).where(
                    func.lower(User.email) == ADMIN_EMAIL.lower(),
                    User.deleted_at.is_(None),
                )
            )
            admin_user = result.scalar_one_or_none()
            if not admin_user:
                logger.warning("Admin user %s not found — skipping workflow seeder", ADMIN_EMAIL)

            # 1. Notification templates
            template_svc = TemplateService(db)
            count = await template_svc.seed_system_templates()
            logger.info("Notification templates seeded: %d created", count)

            # 2. CI classes from semantic types
            count = await sync_semantic_types_to_ci_classes(db)
            logger.info("CI classes synced: %d created/updated", count)

            # 3. System workflows (needs tenant + user)
            if admin_user:
                seeder = SystemWorkflowSeeder(db)
                workflows = await seeder.seed_for_tenant(
                    tenant_id=str(root_tenant.id),
                    system_user_id=str(admin_user.id),
                )
                logger.info(
                    "System workflows seeded: %d created/restored",
                    len(workflows),
                )

            # 4. Provision deployment operations for system components
            if admin_user:
                await _provision_system_component_operations(
                    db,
                    tenant_id=str(root_tenant.id),
                    user_id=str(admin_user.id),
                )

            # 5. Seed day-2 operations (extend_disk, snapshot, restart, resize, etc.)
            if admin_user:
                await _seed_day2_operations(
                    db,
                    tenant_id=str(root_tenant.id),
                    user_id=str(admin_user.id),
                )

            # 6. Seed stack blueprints (PaaS stacks with HA/DR)
            if admin_user:
                await _seed_stack_blueprints(
                    db,
                    tenant_id=str(root_tenant.id),
                    user_id=str(admin_user.id),
                )

            await db.commit()
            logger.info("All runtime data committed")

        except Exception:
            await db.rollback()
            logger.exception("Runtime seeding failed")
            sys.exit(1)

    await engine.dispose()


async def main() -> None:
    logger.info("=" * 50)
    logger.info("Nimbus Demo Data Seeder")
    logger.info("=" * 50)
    logger.info("Backend URL: %s", BACKEND_URL)
    logger.info("Admin email: %s", ADMIN_EMAIL)
    logger.info("Organization: %s", ORG_NAME)

    await call_setup_wizard()
    await replay_migration_seeds()
    await seed_runtime_data()

    logger.info("=" * 50)
    logger.info("Seeding complete!")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
