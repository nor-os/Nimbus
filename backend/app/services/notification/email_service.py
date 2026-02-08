"""
Overview: Email notification service — renders templates and queues Temporal activities.
Architecture: Email delivery channel for the notification subsystem (Section 4)
Dependencies: app.services.notification.template_service, temporalio
Concepts: Email delivery via Temporal, Jinja2 template rendering, SMTP
"""

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationCategory, NotificationChannel

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send(
        self,
        tenant_id: str | uuid.UUID,
        user_email: str,
        category: NotificationCategory,
        event_type: str,
        title: str,
        body: str,
        context: dict | None = None,
    ) -> bool:
        """Render email template and queue a Temporal activity for delivery.

        Returns True if the activity was successfully started, False otherwise.
        """
        from app.services.notification.template_service import TemplateService

        template_service = TemplateService(self.db)
        template = await template_service.get_template(
            tenant_id, category, event_type, NotificationChannel.EMAIL
        )

        render_context = {"title": title, "body": body, **(context or {})}

        if template:
            subject, rendered_body = template_service.render(template, render_context)
        else:
            subject = f"[Nimbus] {title}"
            rendered_body = body

        # Start Temporal activity
        try:
            from app.core.config import get_settings
            from app.core.temporal import get_temporal_client
            from app.workflows.activities.notification import SendEmailInput

            settings = get_settings()
            client = await get_temporal_client()

            await client.start_workflow(
                "SendEmailWorkflow",
                SendEmailInput(
                    to_email=user_email,
                    subject=subject or f"[Nimbus] {title}",
                    body=rendered_body,
                    from_email=settings.smtp_from_email,
                    from_name=settings.smtp_from_name,
                ),
                id=f"send-email-{uuid.uuid4()}",
                task_queue=settings.temporal_task_queue,
            )
            return True
        except Exception:
            logger.warning(
                "Failed to start email activity for %s (event: %s)",
                user_email,
                event_type,
                exc_info=True,
            )
            return False
