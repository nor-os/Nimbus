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
    "postgresql+asyncpg://nimbus:nimbus@localhost:5432/nimbus",
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
    """Component seeds (065, 066, 068, 073) — skip when users don't exist at migration time.

    All four use conn = op.get_bind() with built-in skip logic (no users/providers → return).
    We replay them via Alembic Operations context so op.get_bind() works.
    """
    count = conn.execute(
        sa.text("SELECT count(*) FROM components WHERE is_system = true")
    ).scalar()
    if count and count > 0:
        logger.info("Components: %d system components exist — skipping", count)
        return

    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    mc = MigrationContext.configure(conn)
    with Operations.context(mc):
        for filename in [
            "065_seed_example_vm_component.py",
            "066_update_and_add_example_components.py",
            "068_seed_component_operations.py",
            "073_seed_oci_flex_operations.py",
        ]:
            m = _load_migration(filename)
            m.upgrade()
            logger.info("Component seed %s replayed", filename.split("_", 1)[0])

    logger.info("Component seeds done")


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
