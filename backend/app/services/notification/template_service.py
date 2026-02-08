"""
Overview: Notification template service — CRUD, Jinja2 rendering, tenant/system fallback lookup.
Architecture: Template rendering layer for notification channels (Section 4)
Dependencies: sqlalchemy, jinja2, app.models.notification_template
Concepts: Jinja2 templates, tenant-first system-fallback resolution, template seeding
"""

import logging
import uuid
from datetime import UTC, datetime

from jinja2 import BaseLoader, Environment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationCategory, NotificationChannel
from app.models.notification_template import NotificationTemplate

logger = logging.getLogger(__name__)

_jinja_env = Environment(loader=BaseLoader(), autoescape=True)

# Default system templates seeded on first use
SYSTEM_TEMPLATES: list[dict] = [
    # approval_requested
    {
        "category": NotificationCategory.APPROVAL,
        "event_type": "approval_requested",
        "channel": NotificationChannel.EMAIL,
        "subject_template": "[Nimbus] Approval requested: {{ title }}",
        "body_template": (
            "Hello {{ user_name }},\n\n"
            "An approval has been requested:\n\n"
            "{{ title }}\n\n"
            "{{ body }}\n\n"
            "Please review and respond at your earliest convenience."
        ),
    },
    {
        "category": NotificationCategory.APPROVAL,
        "event_type": "approval_requested",
        "channel": NotificationChannel.IN_APP,
        "subject_template": "Approval requested",
        "body_template": "{{ title }}: {{ body }}",
    },
    # break_glass_activated
    {
        "category": NotificationCategory.SECURITY,
        "event_type": "break_glass_activated",
        "channel": NotificationChannel.EMAIL,
        "subject_template": "[Nimbus] SECURITY: Break-glass access activated",
        "body_template": (
            "SECURITY ALERT\n\n"
            "Break-glass emergency access has been activated.\n\n"
            "Actor: {{ actor_email }}\n"
            "Reason: {{ reason }}\n"
            "Time: {{ timestamp }}\n\n"
            "This requires immediate review."
        ),
    },
    {
        "category": NotificationCategory.SECURITY,
        "event_type": "break_glass_activated",
        "channel": NotificationChannel.IN_APP,
        "subject_template": "Break-glass access activated",
        "body_template": "Emergency access activated by {{ actor_email }}: {{ reason }}",
    },
    # maintenance_scheduled
    {
        "category": NotificationCategory.SYSTEM,
        "event_type": "maintenance_scheduled",
        "channel": NotificationChannel.EMAIL,
        "subject_template": "[Nimbus] Scheduled maintenance: {{ title }}",
        "body_template": (
            "Hello {{ user_name }},\n\n"
            "Scheduled maintenance has been planned:\n\n"
            "{{ title }}\n\n"
            "{{ body }}\n\n"
            "Start: {{ start_time }}\n"
            "End: {{ end_time }}"
        ),
    },
    {
        "category": NotificationCategory.SYSTEM,
        "event_type": "maintenance_scheduled",
        "channel": NotificationChannel.IN_APP,
        "subject_template": "Scheduled maintenance",
        "body_template": "{{ title }}: {{ body }}",
    },
]


class TemplateService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_template(
        self,
        tenant_id: str | uuid.UUID,
        category: NotificationCategory,
        event_type: str,
        channel: NotificationChannel,
    ) -> NotificationTemplate | None:
        """Look up a template: tenant-specific first, then system fallback."""
        tid = uuid.UUID(str(tenant_id))

        # Tenant-specific
        stmt = (
            select(NotificationTemplate)
            .where(
                NotificationTemplate.tenant_id == tid,
                NotificationTemplate.category == category,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active.is_(True),
                NotificationTemplate.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            return template

        # System fallback (tenant_id IS NULL)
        stmt = (
            select(NotificationTemplate)
            .where(
                NotificationTemplate.tenant_id.is_(None),
                NotificationTemplate.category == category,
                NotificationTemplate.event_type == event_type,
                NotificationTemplate.channel == channel,
                NotificationTemplate.is_active.is_(True),
                NotificationTemplate.deleted_at.is_(None),
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    def render(
        self, template: NotificationTemplate, context: dict
    ) -> tuple[str | None, str]:
        """Render a template with context, returning (subject, body)."""
        subject = None
        if template.subject_template:
            subject = _jinja_env.from_string(template.subject_template).render(**context)
        body = _jinja_env.from_string(template.body_template).render(**context)
        return subject, body

    async def list_templates(
        self, tenant_id: str | uuid.UUID | None = None
    ) -> list[NotificationTemplate]:
        """List templates, optionally filtered by tenant. Includes system templates."""
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.deleted_at.is_(None),
        )
        if tenant_id is not None:
            tid = uuid.UUID(str(tenant_id))
            stmt = stmt.where(
                (NotificationTemplate.tenant_id == tid)
                | (NotificationTemplate.tenant_id.is_(None))
            )
        stmt = stmt.order_by(NotificationTemplate.category, NotificationTemplate.event_type)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_template(
        self,
        tenant_id: str | uuid.UUID | None,
        category: NotificationCategory,
        event_type: str,
        channel: NotificationChannel,
        body_template: str,
        subject_template: str | None = None,
        is_active: bool = True,
    ) -> NotificationTemplate:
        """Create a notification template."""
        tid = uuid.UUID(str(tenant_id)) if tenant_id else None
        template = NotificationTemplate(
            tenant_id=tid,
            category=category,
            event_type=event_type,
            channel=channel,
            subject_template=subject_template,
            body_template=body_template,
            is_active=is_active,
        )
        self.db.add(template)
        await self.db.flush()
        return template

    async def update_template(
        self,
        template_id: str | uuid.UUID,
        tenant_id: str | uuid.UUID,
        **kwargs,
    ) -> NotificationTemplate | None:
        """Update a template by ID within a tenant scope."""
        tid = uuid.UUID(str(tenant_id))
        tmpl_id = uuid.UUID(str(template_id))
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.id == tmpl_id,
            NotificationTemplate.deleted_at.is_(None),
            (NotificationTemplate.tenant_id == tid) | (NotificationTemplate.tenant_id.is_(None)),
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        if not template:
            return None

        for key, value in kwargs.items():
            if value is not None and hasattr(template, key):
                setattr(template, key, value)
        await self.db.flush()
        return template

    async def delete_template(
        self, template_id: str | uuid.UUID, tenant_id: str | uuid.UUID
    ) -> bool:
        """Soft-delete a template."""
        tid = uuid.UUID(str(tenant_id))
        tmpl_id = uuid.UUID(str(template_id))
        stmt = select(NotificationTemplate).where(
            NotificationTemplate.id == tmpl_id,
            NotificationTemplate.tenant_id == tid,
            NotificationTemplate.deleted_at.is_(None),
        )
        result = await self.db.execute(stmt)
        template = result.scalar_one_or_none()
        if not template:
            return False
        template.deleted_at = datetime.now(UTC)
        await self.db.flush()
        return True

    async def seed_system_templates(self) -> int:
        """Seed default system templates if they don't exist. Returns count created."""
        created = 0
        for tpl_data in SYSTEM_TEMPLATES:
            # Check if system-level template already exists
            stmt = (
                select(NotificationTemplate)
                .where(
                    NotificationTemplate.tenant_id.is_(None),
                    NotificationTemplate.category == tpl_data["category"],
                    NotificationTemplate.event_type == tpl_data["event_type"],
                    NotificationTemplate.channel == tpl_data["channel"],
                    NotificationTemplate.deleted_at.is_(None),
                )
                .limit(1)
            )
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none():
                continue

            await self.create_template(
                tenant_id=None,
                category=tpl_data["category"],
                event_type=tpl_data["event_type"],
                channel=tpl_data["channel"],
                subject_template=tpl_data.get("subject_template"),
                body_template=tpl_data["body_template"],
            )
            created += 1

        return created
