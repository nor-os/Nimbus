"""
Overview: Tests for notification service layer — preferences, templates, webhook filtering.
Architecture: Unit tests for notification services (Section 4)
Dependencies: pytest, app.services.notification
Concepts: Preference defaults, template fallback, webhook event filtering, dispatch routing
"""

from app.services.notification.webhook_service import _matches_filter


class TestWebhookEventFiltering:
    """Test webhook event filter matching logic."""

    def test_null_filter_matches_everything(self):
        assert _matches_filter(None, "APPROVAL", "approval_requested") is True

    def test_empty_filter_matches_everything(self):
        assert _matches_filter({}, "SECURITY", "break_glass_activated") is True

    def test_category_filter_match(self):
        f = {"categories": ["APPROVAL", "SECURITY"]}
        assert _matches_filter(f, "APPROVAL", "approval_requested") is True

    def test_category_filter_no_match(self):
        f = {"categories": ["APPROVAL"]}
        assert _matches_filter(f, "SYSTEM", "maintenance_scheduled") is False

    def test_event_type_filter_match(self):
        f = {"event_types": ["approval_requested", "break_glass_activated"]}
        assert _matches_filter(f, "APPROVAL", "approval_requested") is True

    def test_event_type_filter_no_match(self):
        f = {"event_types": ["approval_requested"]}
        assert _matches_filter(f, "APPROVAL", "other_event") is False

    def test_combined_filter_match(self):
        f = {
            "categories": ["APPROVAL"],
            "event_types": ["approval_requested"],
        }
        assert _matches_filter(f, "APPROVAL", "approval_requested") is True

    def test_combined_filter_category_mismatch(self):
        f = {
            "categories": ["SECURITY"],
            "event_types": ["approval_requested"],
        }
        assert _matches_filter(f, "APPROVAL", "approval_requested") is False

    def test_combined_filter_event_mismatch(self):
        f = {
            "categories": ["APPROVAL"],
            "event_types": ["break_glass_activated"],
        }
        assert _matches_filter(f, "APPROVAL", "approval_requested") is False


class TestTemplateRendering:
    """Test Jinja2 template rendering."""

    def test_jinja2_render(self):
        from jinja2 import BaseLoader, Environment

        env = Environment(loader=BaseLoader(), autoescape=True)
        template = env.from_string("Hello {{ name }}, your request {{ title }} is pending.")
        result = template.render(name="Alice", title="VM Provisioning")
        assert "Alice" in result
        assert "VM Provisioning" in result

    def test_jinja2_render_missing_var(self):
        from jinja2 import BaseLoader, Environment

        env = Environment(loader=BaseLoader(), autoescape=True)
        template = env.from_string("Hello {{ name }}, status: {{ status }}")
        result = template.render(name="Bob")
        assert "Bob" in result
        assert "status:" in result  # Missing var renders empty


class TestNotificationSchemas:
    """Test Pydantic schema validation."""

    def test_notification_category_enum(self):
        from app.schemas.notification import NotificationCategoryEnum

        assert NotificationCategoryEnum.APPROVAL == "APPROVAL"
        assert NotificationCategoryEnum.SECURITY == "SECURITY"

    def test_webhook_config_create_validation(self):
        from app.schemas.notification import WebhookConfigCreate

        config = WebhookConfigCreate(
            name="Test",
            url="https://example.com/hook",
            batch_size=10,
        )
        assert config.name == "Test"
        assert config.batch_size == 10
        assert config.auth_type == "NONE"

    def test_webhook_config_create_batch_size_limits(self):
        import pytest

        from app.schemas.notification import WebhookConfigCreate

        with pytest.raises(Exception):
            WebhookConfigCreate(
                name="Test",
                url="https://example.com",
                batch_size=0,  # Below minimum of 1
            )

    def test_notification_preference_update(self):
        from app.schemas.notification import NotificationPreferenceUpdate

        update = NotificationPreferenceUpdate(
            category="APPROVAL",
            channel="EMAIL",
            enabled=False,
        )
        assert update.category == "APPROVAL"
        assert update.enabled is False


class TestGraphQLTypes:
    """Test Strawberry GraphQL type definitions."""

    def test_notification_category_gql_enum(self):
        from app.api.graphql.types.notification import NotificationCategoryGQL

        assert NotificationCategoryGQL.APPROVAL.value == "APPROVAL"
        assert len(NotificationCategoryGQL) == 7

    def test_notification_channel_gql_enum(self):
        from app.api.graphql.types.notification import NotificationChannelGQL

        assert NotificationChannelGQL.EMAIL.value == "EMAIL"
        assert len(NotificationChannelGQL) == 3

    def test_webhook_auth_type_gql_enum(self):
        from app.api.graphql.types.notification import WebhookAuthTypeGQL

        assert WebhookAuthTypeGQL.BEARER.value == "BEARER"
        assert len(WebhookAuthTypeGQL) == 4

    def test_webhook_delivery_status_gql_enum(self):
        from app.api.graphql.types.notification import WebhookDeliveryStatusGQL

        assert WebhookDeliveryStatusGQL.DEAD_LETTER.value == "DEAD_LETTER"
        assert len(WebhookDeliveryStatusGQL) == 4
