"""
Overview: Tests for notification data models — enums, field constraints, model relationships.
Architecture: Unit tests for notification data layer (Section 4)
Dependencies: pytest, app.models.notification, app.models.webhook_config, app.models.webhook_delivery
Concepts: Model validation, enum values, field constraints
"""

import uuid

from app.models.notification import Notification, NotificationCategory, NotificationChannel
from app.models.notification_preference import NotificationPreference
from app.models.notification_template import NotificationTemplate
from app.models.webhook_config import WebhookAuthType, WebhookConfig
from app.models.webhook_delivery import WebhookDelivery, WebhookDeliveryStatus


class TestNotificationEnums:
    """Test all notification-related enum values."""

    def test_notification_category_values(self):
        assert set(NotificationCategory) == {
            NotificationCategory.APPROVAL,
            NotificationCategory.SECURITY,
            NotificationCategory.SYSTEM,
            NotificationCategory.AUDIT,
            NotificationCategory.DRIFT,
            NotificationCategory.WORKFLOW,
            NotificationCategory.USER,
        }

    def test_notification_channel_values(self):
        assert set(NotificationChannel) == {
            NotificationChannel.EMAIL,
            NotificationChannel.IN_APP,
            NotificationChannel.WEBHOOK,
        }

    def test_webhook_auth_type_values(self):
        assert set(WebhookAuthType) == {
            WebhookAuthType.NONE,
            WebhookAuthType.API_KEY,
            WebhookAuthType.BASIC,
            WebhookAuthType.BEARER,
        }

    def test_webhook_delivery_status_values(self):
        assert set(WebhookDeliveryStatus) == {
            WebhookDeliveryStatus.PENDING,
            WebhookDeliveryStatus.DELIVERED,
            WebhookDeliveryStatus.FAILED,
            WebhookDeliveryStatus.DEAD_LETTER,
        }

    def test_enums_are_str_enums(self):
        assert isinstance(NotificationCategory.APPROVAL, str)
        assert isinstance(NotificationChannel.EMAIL, str)
        assert isinstance(WebhookAuthType.NONE, str)
        assert isinstance(WebhookDeliveryStatus.PENDING, str)


class TestNotificationModel:
    """Test Notification model instantiation."""

    def test_notification_creation(self):
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        n = Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            category=NotificationCategory.SYSTEM,
            event_type="maintenance_scheduled",
            title="Scheduled Maintenance",
            body="System maintenance planned for tonight.",
        )
        assert n.tenant_id == tenant_id
        assert n.user_id == user_id
        assert n.category == NotificationCategory.SYSTEM
        assert n.event_type == "maintenance_scheduled"
        assert n.title == "Scheduled Maintenance"

    def test_notification_tablename(self):
        assert Notification.__tablename__ == "notifications"


class TestNotificationPreferenceModel:
    """Test NotificationPreference model."""

    def test_preference_creation(self):
        pref = NotificationPreference(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            category=NotificationCategory.SECURITY,
            channel=NotificationChannel.EMAIL,
            enabled=False,
        )
        assert pref.category == NotificationCategory.SECURITY
        assert pref.channel == NotificationChannel.EMAIL
        assert pref.enabled is False

    def test_preference_tablename(self):
        assert NotificationPreference.__tablename__ == "notification_preferences"


class TestNotificationTemplateModel:
    """Test NotificationTemplate model."""

    def test_template_creation_system(self):
        t = NotificationTemplate(
            tenant_id=None,
            category=NotificationCategory.APPROVAL,
            event_type="approval_requested",
            channel=NotificationChannel.EMAIL,
            subject_template="[Nimbus] Approval: {{ title }}",
            body_template="Please review: {{ body }}",
            is_active=True,
        )
        assert t.tenant_id is None
        assert t.channel == NotificationChannel.EMAIL

    def test_template_tablename(self):
        assert NotificationTemplate.__tablename__ == "notification_templates"


class TestWebhookConfigModel:
    """Test WebhookConfig model."""

    def test_webhook_config_defaults(self):
        config = WebhookConfig(
            tenant_id=uuid.uuid4(),
            name="My Webhook",
            url="https://example.com/hook",
        )
        assert config.name == "My Webhook"
        assert config.url == "https://example.com/hook"

    def test_webhook_config_tablename(self):
        assert WebhookConfig.__tablename__ == "webhook_configs"


class TestWebhookDeliveryModel:
    """Test WebhookDelivery model."""

    def test_delivery_creation(self):
        d = WebhookDelivery(
            tenant_id=uuid.uuid4(),
            webhook_config_id=uuid.uuid4(),
            payload={"event": "test", "data": {"key": "value"}},
        )
        assert d.payload == {"event": "test", "data": {"key": "value"}}

    def test_delivery_tablename(self):
        assert WebhookDelivery.__tablename__ == "webhook_deliveries"

    def test_delivery_no_soft_delete_mixin(self):
        """WebhookDelivery should NOT have SoftDeleteMixin (deleted_at)."""
        assert not hasattr(WebhookDelivery, "deleted_at") or "deleted_at" not in {
            col.name for col in WebhookDelivery.__table__.columns
        }
