"""
Overview: Standalone demo data seeder — runs setup wizard + runtime seeders.
Architecture: Called as a one-shot container after migrations and backend are up.
Dependencies: httpx, sqlalchemy, app.services (template, cmdb, workflow seeders)
Concepts: Idempotent seeding, setup wizard automation, demo data population
"""

import asyncio
import logging
import os
import sys

import httpx
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
ADMIN_EMAIL = os.environ.get("NIMBUS_ADMIN_EMAIL", "admin@nimbus.local")
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


async def seed_runtime_data() -> None:
    """Connect to the DB and run runtime seeders that need a session."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as db:
        try:
            # Find root tenant (parent_id IS NULL, not deleted)
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

            # Find admin user
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
    await seed_runtime_data()

    logger.info("=" * 50)
    logger.info("Seeding complete!")
    logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
