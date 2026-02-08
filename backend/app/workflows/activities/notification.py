"""
Overview: Temporal activities for notification delivery — email and webhook batch dispatch.
Architecture: Notification workflow activities (Section 9)
Dependencies: temporalio, aiosmtplib, httpx
Concepts: Durable email delivery, webhook batch dispatch, HMAC signing, retry policy
"""

import hashlib
import hmac
import json
import logging
from dataclasses import dataclass, field
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from temporalio import activity

logger = logging.getLogger(__name__)


# -- Email activity -----------------------------------------------------------


@dataclass
class SendEmailInput:
    to_email: str
    subject: str
    body: str
    from_email: str = "noreply@nimbus.local"
    from_name: str = "Nimbus"


@dataclass
class SendEmailResult:
    success: bool
    error: str | None = None


@activity.defn
async def send_email_activity(input: SendEmailInput) -> SendEmailResult:
    """Send an email via SMTP with retry support."""
    import aiosmtplib

    from app.core.config import get_settings

    settings = get_settings()

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{input.from_name} <{input.from_email}>"
        msg["To"] = input.to_email
        msg["Subject"] = input.subject
        msg.attach(MIMEText(input.body, "plain", "utf-8"))

        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            use_tls=settings.smtp_use_tls,
        )

        activity.logger.info("Email sent to %s: %s", input.to_email, input.subject)
        return SendEmailResult(success=True)

    except Exception as e:
        activity.logger.error("Email send failed for %s: %s", input.to_email, e)
        return SendEmailResult(success=False, error=str(e))


# -- Webhook batch activity ---------------------------------------------------


@dataclass
class WebhookTarget:
    url: str
    auth_type: str = "NONE"
    auth_config: dict | None = None
    secret: str | None = None


@dataclass
class SendWebhookBatchInput:
    delivery_ids: list[str]
    target: WebhookTarget = field(default_factory=WebhookTarget)
    payloads: list[dict] = field(default_factory=list)


@dataclass
class WebhookDeliveryResult:
    delivery_id: str
    success: bool
    status_code: int | None = None
    error: str | None = None


@dataclass
class SendWebhookBatchResult:
    results: list[WebhookDeliveryResult] = field(default_factory=list)


@activity.defn
async def send_webhook_batch_activity(input: SendWebhookBatchInput) -> SendWebhookBatchResult:
    """Deliver a batch of webhook payloads to a single target URL."""
    import httpx

    results: list[WebhookDeliveryResult] = []

    headers = {"Content-Type": "application/json"}
    _apply_auth_headers(headers, input.target)

    async with httpx.AsyncClient(timeout=30.0) as client:
        for delivery_id, payload in zip(input.delivery_ids, input.payloads, strict=True):
            try:
                body_bytes = json.dumps(payload).encode("utf-8")

                if input.target.secret:
                    signature = hmac.new(
                        input.target.secret.encode("utf-8"),
                        body_bytes,
                        hashlib.sha256,
                    ).hexdigest()
                    headers["X-Nimbus-Signature"] = f"sha256={signature}"

                response = await client.post(
                    input.target.url,
                    content=body_bytes,
                    headers=headers,
                )

                success = 200 <= response.status_code < 300
                results.append(
                    WebhookDeliveryResult(
                        delivery_id=delivery_id,
                        success=success,
                        status_code=response.status_code,
                        error=None if success else response.text[:500],
                    )
                )

            except Exception as e:
                activity.logger.error("Webhook delivery %s failed: %s", delivery_id, e)
                results.append(
                    WebhookDeliveryResult(
                        delivery_id=delivery_id,
                        success=False,
                        error=str(e)[:500],
                    )
                )

    return SendWebhookBatchResult(results=results)


def _apply_auth_headers(headers: dict, target: WebhookTarget) -> None:
    """Apply authentication headers based on webhook auth type."""
    if target.auth_type == "NONE" or not target.auth_config:
        return

    if target.auth_type == "API_KEY":
        header_name = target.auth_config.get("header_name", "X-API-Key")
        header_value = target.auth_config.get("api_key", "")
        headers[header_name] = header_value

    elif target.auth_type == "BASIC":
        import base64

        username = target.auth_config.get("username", "")
        password = target.auth_config.get("password", "")
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        headers["Authorization"] = f"Basic {credentials}"

    elif target.auth_type == "BEARER":
        token = target.auth_config.get("token", "")
        headers["Authorization"] = f"Bearer {token}"
